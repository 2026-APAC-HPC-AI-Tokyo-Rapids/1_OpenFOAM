"""Profile-only ``perf stat`` parsing and projection helpers.

The profile path is intentionally local and dependency free.  A rank wrapper
records the launch-effective rank metadata, then replaces itself with one
``perf stat`` process.  This module validates the resulting closed seven-column
CSV and projects observed rows without manufacturing rows for missing ranks.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

EVENTS = (
    "cycles",
    "instructions",
    "branches",
    "branch-misses",
    "cache-misses",
)
CSV_FIELDS = (
    "count_lexeme",
    "unit",
    "event_name",
    "running_ns_lexeme",
    "percent_running_lexeme",
    "metric_value_lexeme",
    "metric_unit",
)
_EVENT_INDEX = {event: index for index, event in enumerate(EVENTS)}
_RANK_FILE = re.compile(r"^rank-([0-9]+)\.csv$")
_RANK_METADATA = re.compile(r"^rank-([0-9]+)\.json$")
_CPU_LIST = re.compile(r"^[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*$")
_NUMERIC = re.compile(
    r"^[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?$"
)
_NULL_METRIC = frozenset(
    {"", "<not counted>", "<not supported>", "not counted", "not supported"}
)


class PerfValidationError(ValueError):
    """A profile source does not satisfy the closed perf contract."""


class PerfConflictError(PerfValidationError):
    """A logical projection grain has more than one distinct value."""

    def __init__(self, conflicts: tuple[ProjectionConflict, ...]) -> None:
        self.conflicts = conflicts
        super().__init__(f"{len(conflicts)} perf projection conflict(s)")


@dataclass(frozen=True, slots=True)
class PerfItem:
    """One event in the exact five-event order."""

    event_name: str
    raw_count_lexeme: str
    count: Decimal | None
    unit: str | None
    running_ns_lexeme: str
    running_ns: Decimal | None
    percent_running_lexeme: str
    percent_running: Decimal | None
    metric_value_lexeme: str
    metric_unit: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "event_name": self.event_name,
            "raw_count_lexeme": self.raw_count_lexeme,
            "count": self.count,
            "unit": self.unit,
            "running_ns_lexeme": self.running_ns_lexeme,
            "running_ns": self.running_ns,
            "percent_running_lexeme": self.percent_running_lexeme,
            "percent_running": self.percent_running,
            "metric_value_lexeme": self.metric_value_lexeme,
            "metric_unit": self.metric_unit,
        }


@dataclass(frozen=True, slots=True)
class PerfStatRecord:
    """Validated rank-level source record from one CSV member."""

    run_id: str
    global_rank: int
    items: tuple[PerfItem, ...]
    source_member: str
    source_sha256: str

    def __post_init__(self) -> None:
        _run_id(self.run_id)
        _rank(self.global_rank)
        _member(self.source_member)
        _sha256(self.source_sha256)
        if tuple(item.event_name for item in self.items) != EVENTS:
            raise PerfValidationError("perf items must contain the exact five events")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "perf-stat/v1",
            "run_id": self.run_id,
            "global_rank": self.global_rank,
            "items": [item.as_dict() for item in self.items],
            "source_member": self.source_member,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True, slots=True)
class RankFact:
    """Launch-effective rank, argv, environment, and affinity observation."""

    run_id: str
    global_rank: int
    local_rank: int
    local_size: int
    hostname: str
    cpu_affinity: tuple[int, ...]
    numa_mems: str | None
    argv: tuple[str, ...]
    environment: tuple[tuple[str, str], ...]
    source_member: str
    source_sha256: str

    def __post_init__(self) -> None:
        _run_id(self.run_id)
        _rank(self.global_rank)
        if self.local_rank < 0 or self.local_size <= self.local_rank:
            raise PerfValidationError("rank local axes are invalid")
        if not self.hostname:
            raise PerfValidationError("rank hostname is empty")
        if tuple(sorted(set(self.cpu_affinity))) != self.cpu_affinity or any(
            cpu < 0 for cpu in self.cpu_affinity
        ):
            raise PerfValidationError("rank CPU affinity is not sorted and unique")
        if not self.argv or any(
            not isinstance(item, str) or not item for item in self.argv
        ):
            raise PerfValidationError("rank argv is invalid")
        if (
            tuple(sorted(self.environment, key=lambda item: item[0].encode()))
            != self.environment
        ):
            raise PerfValidationError("rank environment is not byte ordered")
        _member(self.source_member)
        _sha256(self.source_sha256)

    def as_dict(self) -> dict[str, object]:
        return {
            "projection_relation": "openfoam_rank_placements_v2",
            "run": self.run_id,
            "global_rank": self.global_rank,
            "local_rank": self.local_rank,
            "local_size": self.local_size,
            "hostname": self.hostname,
            "cpu_affinity": list(self.cpu_affinity),
            "numa_mems": self.numa_mems,
            "argv": list(self.argv),
            "environment": dict(self.environment),
            "source_member": self.source_member,
            "source_sha256": self.source_sha256,
        }


@dataclass(frozen=True, slots=True)
class PerfProjectionRow:
    """One closed ``openfoam_perf_counters_v2`` row."""

    run_id: str
    global_rank: int
    item: PerfItem
    source_member: str
    source_sha256: str

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": "perf-counter-projection/v1",
            "run_id": self.run_id,
            "global_rank": self.global_rank,
            "event_name": self.item.event_name,
            "raw_count_lexeme": self.item.raw_count_lexeme,
            "count": self.item.count,
            "unit": self.item.unit,
            "running_ns_lexeme": self.item.running_ns_lexeme,
            "running_ns": self.item.running_ns,
            "percent_running_lexeme": self.item.percent_running_lexeme,
            "percent_running": self.item.percent_running,
            "metric_value_lexeme": self.item.metric_value_lexeme,
            "metric_unit": self.item.metric_unit,
            "source_member": self.source_member,
            "source_sha256": self.source_sha256,
        }

    def to_fact_rows(self) -> tuple[dict[str, object], ...]:
        """Return lossless three-column raw Fact-shaped values for appenders."""

        prefix = f"profile.perf.rank.{self.global_rank}.{self.item.event_name}"
        values = (
            (f"{prefix}.raw_count_lexeme", self.item.raw_count_lexeme),
            (f"{prefix}.count", self.item.count),
            (f"{prefix}.unit", self.item.unit),
            (f"{prefix}.running_ns", self.item.running_ns),
            (f"{prefix}.percent_running", self.item.percent_running),
            (f"{prefix}.running_ns_lexeme", self.item.running_ns_lexeme),
            (f"{prefix}.percent_running_lexeme", self.item.percent_running_lexeme),
        )
        return tuple(
            {"run": self.run_id, "key": key, "value": _fact_value(value)}
            for key, value in values
        )


@dataclass(frozen=True, slots=True)
class ProjectionConflict:
    grain: tuple[object, ...]
    rows: tuple[PerfProjectionRow, ...]


@dataclass(frozen=True, slots=True)
class PerfProjection:
    """Observed profile rows plus rank completeness and conflict status."""

    run_id: str
    expected_ranks: int
    rows: tuple[PerfProjectionRow, ...]
    rank_facts: tuple[RankFact, ...]
    missing_ranks: tuple[int, ...]
    conflicts: tuple[ProjectionConflict, ...] = ()

    @property
    def is_complete(self) -> bool:
        return not self.missing_ranks and not self.conflicts

    def require_complete(self) -> tuple[PerfProjectionRow, ...]:
        if not self.is_complete:
            raise PerfValidationError(
                f"profile perf collection incomplete: missing={self.missing_ranks}, "
                f"conflicts={len(self.conflicts)}"
            )
        return self.rows

    def require_conflict_free(self) -> tuple[PerfProjectionRow, ...]:
        if self.conflicts:
            raise PerfConflictError(self.conflicts)
        return self.rows


def perf_command(
    perf: Path, output: Path, solver: Path, solver_argv: Iterable[str]
) -> tuple[str, ...]:
    """Build the exact shell-free child argv fixed by the profile contract."""

    if not perf.is_absolute() or not solver.is_absolute() or not output.is_absolute():
        raise PerfValidationError("perf, solver, and output paths must be absolute")
    return (
        str(perf),
        "stat",
        "--no-big-num",
        "-x,",
        "-o",
        str(output),
        "-e",
        ",".join(EVENTS),
        "--",
        str(solver),
        *tuple(solver_argv),
    )


def parse_perf_csv(
    text: str,
    *,
    run_id: str,
    global_rank: int,
    source_member: str = "profile/raw/perf/rank.csv",
    source_sha256: str = "0" * 64,
) -> PerfStatRecord:
    """Parse one fixed-seven-column perf CSV into an exact five-event record."""

    _run_id(run_id)
    _rank(global_rank)
    _member(source_member)
    _sha256(source_sha256)
    # perf writes a provenance comment and a blank separator before the
    # requested event records.  They are source evidence, but not CSV rows.
    data_lines = tuple(
        line for line in text.splitlines() if line and not line.startswith("#")
    )
    reader = csv.reader(data_lines, strict=True)
    rows = list(reader)
    if len(rows) != len(EVENTS) or any(len(row) != len(CSV_FIELDS) for row in rows):
        raise PerfValidationError(
            "perf CSV must contain exactly five seven-column rows"
        )
    items: list[PerfItem] = []
    for ordinal, row in enumerate(rows):
        expected_event = EVENTS[ordinal]
        if row[2] != expected_event:
            raise PerfValidationError(
                f"perf event order differs at {ordinal}: {row[2]!r}"
            )
        items.append(
            PerfItem(
                event_name=row[2],
                raw_count_lexeme=row[0],
                count=_number_or_none(row[0]),
                unit=row[1] or None,
                running_ns_lexeme=row[3],
                running_ns=_number_or_none(row[3]),
                percent_running_lexeme=row[4],
                percent_running=_number_or_none(row[4]),
                metric_value_lexeme=row[5],
                metric_unit=row[6] or None,
            )
        )
    return PerfStatRecord(
        run_id, global_rank, tuple(items), source_member, source_sha256
    )


def parse_perf_file(
    path: Path, *, run_id: str, global_rank: int, source_member: str | None = None
) -> PerfStatRecord:
    """Parse a rank CSV and bind its exact source-member SHA-256."""

    member = source_member or f"profile/raw/perf/rank-{global_rank}.csv"
    return parse_perf_csv(
        path.read_text(encoding="utf-8"),
        run_id=run_id,
        global_rank=global_rank,
        source_member=member,
        source_sha256=_sha256_file(path),
    )


def project_perf_record(record: PerfStatRecord) -> tuple[PerfProjectionRow, ...]:
    return tuple(
        PerfProjectionRow(
            record.run_id,
            record.global_rank,
            item,
            record.source_member,
            record.source_sha256,
        )
        for item in record.items
    )


def deduplicate_projection_rows(
    rows: Iterable[PerfProjectionRow],
) -> tuple[tuple[PerfProjectionRow, ...], tuple[ProjectionConflict, ...]]:
    """Collapse exact duplicates and retain all differing grain values."""

    groups: dict[tuple[str, int, str], list[PerfProjectionRow]] = defaultdict(list)
    for row in rows:
        groups[(row.run_id, row.global_rank, row.item.event_name)].append(row)
    unique: list[PerfProjectionRow] = []
    conflicts: list[ProjectionConflict] = []
    for grain in sorted(groups):
        identities: dict[str, PerfProjectionRow] = {}
        for row in groups[grain]:
            identities.setdefault(_canonical(row.as_dict()), row)
        ordered = tuple(identities[key] for key in sorted(identities))
        if len(ordered) == 1:
            unique.append(ordered[0])
        else:
            conflicts.append(ProjectionConflict(grain, ordered))
    return tuple(unique), tuple(conflicts)


def validate_rank_completeness(
    rows: Iterable[PerfProjectionRow], *, expected_ranks: int
) -> tuple[int, ...]:
    """Return missing global ranks; never synthesize placeholder rows."""

    if expected_ranks <= 0:
        raise PerfValidationError("expected ranks must be positive")
    observed = {row.global_rank for row in rows}
    if any(rank < 0 or rank >= expected_ranks for rank in observed):
        raise PerfValidationError("observed rank is outside expected range")
    return tuple(rank for rank in range(expected_ranks) if rank not in observed)


def parse_rank_fact(path: Path, *, run_id: str, global_rank: int) -> RankFact:
    """Validate the wrapper's closed launch sidecar."""

    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "run_id",
        "global_rank",
        "local_rank",
        "local_size",
        "hostname",
        "cpu_affinity",
        "numa_mems",
        "argv",
        "environment",
        "output_member",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise PerfValidationError("rank launch sidecar is not closed")
    if (
        value["schema_version"] != "openfoam-rank-launch/v1"
        or value["run_id"] != run_id
        or value["global_rank"] != global_rank
    ):
        raise PerfValidationError("rank launch identity differs")
    if not isinstance(value["local_rank"], int) or not isinstance(
        value["local_size"], int
    ):
        raise PerfValidationError("rank local axes are not integers")
    affinity = value["cpu_affinity"]
    if not isinstance(affinity, list) or any(
        not isinstance(item, int) or isinstance(item, bool) or item < 0
        for item in affinity
    ):
        raise PerfValidationError("rank CPU affinity is invalid")
    environment = value["environment"]
    if not isinstance(environment, dict) or any(
        not isinstance(key, str) or not isinstance(item, str)
        for key, item in environment.items()
    ):
        raise PerfValidationError("rank environment is invalid")
    argv = value["argv"]
    if not isinstance(argv, list) or any(
        not isinstance(item, str) or not item for item in argv
    ):
        raise PerfValidationError("rank argv is invalid")
    if not isinstance(value["hostname"], str) or not value["hostname"]:
        raise PerfValidationError("rank hostname is invalid")
    numa_mems = value["numa_mems"]
    if numa_mems is not None and (
        not isinstance(numa_mems, str)
        or (numa_mems and _CPU_LIST.fullmatch(numa_mems) is None)
    ):
        raise PerfValidationError("rank NUMA memory list is invalid")
    expected_output_member = f"profile/raw/perf/rank-{global_rank}.csv"
    if value["output_member"] != expected_output_member:
        raise PerfValidationError("rank output member does not bind to rank")
    _member(value["output_member"])
    return RankFact(
        run_id,
        global_rank,
        value["local_rank"],
        value["local_size"],
        value["hostname"],
        tuple(affinity),
        numa_mems,
        tuple(argv),
        tuple(sorted(environment.items(), key=lambda item: item[0].encode())),
        value["output_member"],
        _sha256_file(path),
    )


def project_profile_perf(
    runtime_dir: Path, *, run_id: str, expected_ranks: int = 120
) -> PerfProjection:
    """Read observed rank CSV/sidecars below ``profile/raw/perf``."""

    _run_id(run_id)
    if expected_ranks <= 0:
        raise PerfValidationError("expected ranks must be positive")
    perf_dir = (runtime_dir / "profile/raw/perf").resolve()
    if not perf_dir.is_dir():
        return PerfProjection(
            run_id, expected_ranks, (), (), tuple(range(expected_ranks))
        )
    csv_files = _rank_files(perf_dir, _RANK_FILE)
    metadata_files = _rank_files(perf_dir, _RANK_METADATA)
    rows: list[PerfProjectionRow] = []
    rank_facts: list[RankFact] = []
    for rank, path in sorted(csv_files.items()):
        if rank >= expected_ranks:
            raise PerfValidationError("perf CSV rank is outside expected range")
        member = f"profile/raw/perf/rank-{rank}.csv"
        record = parse_perf_file(
            path, run_id=run_id, global_rank=rank, source_member=member
        )
        rows.extend(project_perf_record(record))
    for rank, path in sorted(metadata_files.items()):
        if rank >= expected_ranks:
            raise PerfValidationError("rank sidecar is outside expected range")
        rank_facts.append(parse_rank_fact(path, run_id=run_id, global_rank=rank))
    unique_rows, conflicts = deduplicate_projection_rows(rows)
    observed_perf_ranks = {row.global_rank for row in unique_rows}
    observed_fact_ranks = {fact.global_rank for fact in rank_facts}
    missing = tuple(
        rank
        for rank in range(expected_ranks)
        if rank not in observed_perf_ranks or rank not in observed_fact_ranks
    )
    return PerfProjection(
        run_id,
        expected_ranks,
        unique_rows,
        tuple(rank_facts),
        missing,
        conflicts,
    )


def project_perf_rows(
    runtime_dir: Path, run_id: str, expected_ranks: int = 120
) -> PerfProjection:
    """Positional compatibility wrapper for append adapters."""

    return project_profile_perf(
        runtime_dir, run_id=run_id, expected_ranks=expected_ranks
    )


def profile_perf_fact_values(
    runtime_dir: Path, *, run_id: str, expected_ranks: int
) -> tuple[dict[str, object], ...]:
    """Return one closed, complete perf-stat value for every expected rank."""

    projection = project_profile_perf(
        runtime_dir, run_id=run_id, expected_ranks=expected_ranks
    )
    projection.require_complete()
    values = []
    for rank in range(expected_ranks):
        record = parse_perf_file(
            runtime_dir / f"profile/raw/perf/rank-{rank}.csv",
            run_id=run_id,
            global_rank=rank,
        )
        values.append(
            {
                "schema_version": "perf-stat/v1",
                "run_id": record.run_id,
                "global_rank": record.global_rank,
                "items": [
                    _json_numbers(
                        {
                            "event_name": item.event_name,
                            "raw_count_lexeme": item.raw_count_lexeme,
                            "count": item.count,
                            "unit": item.unit,
                            "running_ns": item.running_ns,
                            "percent_running": item.percent_running,
                        }
                    )
                    for item in record.items
                ],
            }
        )
    return tuple(values)


def _rank_files(root: Path, pattern: re.Pattern[str]) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for path in root.iterdir():
        match = pattern.fullmatch(path.name)
        if match is None:
            continue
        rank = int(match.group(1))
        if rank in result:
            raise PerfValidationError("duplicate rank source")
        if not path.is_file() or path.is_symlink():
            raise PerfValidationError("rank source is not a regular file")
        result[rank] = path
    return result


def _number_or_none(lexeme: str) -> Decimal | None:
    if lexeme.strip().lower() in _NULL_METRIC:
        return None
    if _NUMERIC.fullmatch(lexeme) is None:
        raise PerfValidationError(f"numeric lexeme is invalid: {lexeme!r}")
    try:
        value = Decimal(lexeme)
    except InvalidOperation as error:
        raise PerfValidationError(f"numeric lexeme is invalid: {lexeme!r}") from error
    if not value.is_finite():
        raise PerfValidationError("numeric lexeme is not finite")
    return value


def _json_numbers(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_numbers(item) for key, item in value.items()}
    return value


def _fact_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    return value


def _canonical(value: object) -> str:
    return json.dumps(
        value, default=_json_default, sort_keys=True, separators=(",", ":")
    )


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    raise TypeError(f"not JSON compatible: {type(value)!r}")


def _run_id(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise PerfValidationError("run ID must be nonempty")
    return value


def _rank(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise PerfValidationError("global rank must be a nonnegative integer")
    return value


def _member(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise PerfValidationError("source member is not a safe relative path")
    return value


def _sha256(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise PerfValidationError("source SHA-256 is invalid")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
