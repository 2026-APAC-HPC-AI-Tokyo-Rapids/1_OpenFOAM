"""Validated AMD uProf hotspot facts and bounded Actions summaries."""

from __future__ import annotations

import csv
import hashlib
import os
import re
import shlex
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .fact import Fact, canonical_json
from .manifest import RunManifest
from .recording import Recorder

_VERSION = "5.3.521.0"
_NUMBER = re.compile(r"^[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$")
_FUNCTION_SECTION = re.compile(r"^[0-9]+ HOTTEST FUNCTIONS \(Sort Event - CPU_TIME\)$")
_FUNCTION_HEADER = ["FUNCTION", "CPU_TIME (seconds)", "TOTAL_CPU_TIME (s)", "Module"]


@dataclass(frozen=True, slots=True)
class UProfHotspot:
    report_row: int
    function: str
    module: str
    cpu_time_lexeme: str
    total_cpu_time_lexeme: str
    cpu_time_sec: Decimal
    total_cpu_time_sec: Decimal

    def fact_value(self) -> dict[str, object]:
        return {
            "report_row": self.report_row,
            "function": self.function,
            "module": self.module,
            "cpu_time_lexeme": self.cpu_time_lexeme,
            "cpu_time_sec": _decimal_text(self.cpu_time_sec),
            "total_cpu_time_lexeme": self.total_cpu_time_lexeme,
            "total_cpu_time_sec": _decimal_text(self.total_cpu_time_sec),
        }


@dataclass(frozen=True, slots=True)
class UProfReport:
    target_path: str
    duration_lexeme: str
    duration_sec: Decimal
    thread_count: int
    mpi_ranks: int
    mpi_hosts: int
    ranks_per_node: tuple[tuple[str, int], ...]
    hotspots: tuple[UProfHotspot, ...]


def parse_uprof_hotspots(text: str) -> UProfReport:
    """Parse the sectioned report emitted by the pinned uProf 5.3 CLI."""

    # uProf 5.3 writes headers such as `"CPU_TIME" (seconds)`, which are not
    # strict RFC CSV. Python's documented non-strict reader preserves the
    # intended fields; exact section and header checks below close the format.
    try:
        records = list(csv.reader(text.splitlines()))
    except csv.Error as error:
        raise ValueError("AMD uProf hotspot report is malformed") from error
    if not records or [f"AMD uProf (Version:{_VERSION})"] not in records:
        raise ValueError("AMD uProf report version is not the pinned 5.3.521.0")

    metadata = _unique_metadata(records)
    if metadata.get("Profile Session Type:") != "Hotspots":
        raise ValueError("AMD uProf report is not a Hotspots session")
    if metadata.get("Call Stack Sampling:") != "True":
        raise ValueError("AMD uProf report did not collect call stacks")
    collect = shlex.split(_required(metadata, "Collect Command:"))
    report = shlex.split(_required(metadata, "Report Command:"))
    if (
        not _contains_sequence(collect, ("--config", "hotspots"))
        or "-g" not in collect
        or "--mpi" not in collect
    ):
        raise ValueError(
            "AMD uProf collect command differs from the MPI Hotspots protocol"
        )
    if (
        not _contains_sequence(report, ("--host", "all"))
        or "--detail" not in report
        or not _contains_sequence(report, ("--cutoff", "30"))
    ):
        raise ValueError(
            "AMD uProf report command differs from the all-host detail protocol"
        )

    duration_lexeme = _required(metadata, "Profile Duration:")
    if not duration_lexeme.endswith(" seconds"):
        raise ValueError("AMD uProf profile duration unit is invalid")
    duration_sec = _decimal(duration_lexeme.removesuffix(" seconds"))
    thread_count = _integer(_required(metadata, "Thread Count"), "thread count")
    mpi_ranks = _integer(_required(metadata, "Number Of MPI ranks"), "MPI rank count")
    mpi_hosts = _integer(_required(metadata, "Number Of MPI hosts"), "MPI host count")

    ranks_per_node_header = [
        index for index, row in enumerate(records) if row == ["MPI Ranks Per Node"]
    ]
    if len(ranks_per_node_header) != 1:
        raise ValueError("AMD uProf report must contain one MPI Ranks Per Node section")
    ranks_per_node: list[tuple[str, int]] = []
    for row in records[ranks_per_node_header[0] + 1 :]:
        if not row:
            break
        if len(row) != 2 or not row[0].strip():
            raise ValueError("AMD uProf MPI ranks-per-node row is invalid")
        ranks_per_node.append(
            (row[0].strip(), _integer(row[1].strip(), "ranks per node"))
        )
    if (
        len(ranks_per_node) != mpi_hosts
        or sum(value for _, value in ranks_per_node) != mpi_ranks
    ):
        raise ValueError("AMD uProf MPI topology totals are inconsistent")

    section = [
        index
        for index, row in enumerate(records)
        if len(row) == 1 and _FUNCTION_SECTION.fullmatch(row[0])
    ]
    if (
        len(section) != 1
        or section[0] + 1 >= len(records)
        or records[section[0] + 1] != _FUNCTION_HEADER
    ):
        raise ValueError(
            "AMD uProf report must contain one exact hottest-functions section"
        )
    hotspots: list[UProfHotspot] = []
    for report_row, row in enumerate(records[section[0] + 2 :], start=section[0] + 3):
        if not row:
            break
        if len(row) != 4:
            raise ValueError("AMD uProf hotspot row has an unexpected column count")
        function, cpu_lexeme, total_lexeme, module = (item.strip() for item in row)
        if not function or not module:
            raise ValueError("AMD uProf hotspot function or module is empty")
        hotspots.append(
            UProfHotspot(
                report_row,
                function,
                module,
                cpu_lexeme,
                total_lexeme,
                _decimal(cpu_lexeme),
                _decimal(total_lexeme),
            )
        )
    if not hotspots:
        raise ValueError("AMD uProf report contains no hotspot functions")
    ordered = tuple(
        sorted(
            hotspots,
            key=lambda item: (
                -item.cpu_time_sec,
                item.function.encode(),
                item.module.encode(),
                item.report_row,
            ),
        )
    )
    return UProfReport(
        _required(metadata, "Target Path:"),
        duration_lexeme,
        duration_sec,
        thread_count,
        mpi_ranks,
        mpi_hosts,
        tuple(ranks_per_node),
        ordered,
    )


def record_uprof_hotspots(
    *,
    manifest_path: Path,
    runtime_dir: Path,
    report_path: Path,
    summary_path: Path,
    markdown_path: Path,
    limit: int = 30,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    if run_dir != manifest.path.parents[1] or manifest.purpose != "profile":
        raise ValueError("AMD uProf facts require the bound profile run")
    if limit <= 0:
        raise ValueError("AMD uProf summary limit is invalid")
    expected = {
        report_path: run_dir / "profile/raw/uprof/report.csv",
        summary_path: run_dir / "results/uprof-summary.json",
        markdown_path: run_dir / "results/uprof-summary.md",
    }
    for supplied, required in expected.items():
        if supplied.resolve() != required.resolve():
            raise ValueError(
                "AMD uProf source or output path is outside its fixed run path"
            )
    parsed = parse_uprof_hotspots(report_path.read_text(encoding="utf-8-sig"))
    value = {
        "schema_version": "openfoam-uprof-profile/v1",
        "tool_version": _VERSION,
        "target_path": parsed.target_path,
        "collection": {
            "analysis_type": "hotspots",
            "call_stack_sampling": True,
            "mpi": True,
            "report_host_scope": "all",
            "report_cutoff": 30,
        },
        "profile_duration_lexeme": parsed.duration_lexeme,
        "profile_duration_sec": _decimal_text(parsed.duration_sec),
        "thread_count": parsed.thread_count,
        "mpi_ranks": parsed.mpi_ranks,
        "mpi_hosts": parsed.mpi_hosts,
        "ranks_per_node": [
            {"host": host, "ranks": ranks} for host, ranks in parsed.ranks_per_node
        ],
        "source": _source(report_path, run_dir),
        "hotspots": [item.fact_value() for item in parsed.hotspots],
    }
    summary = _summary(value, parsed.hotspots, limit=limit)
    summary_path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    _atomic_text(summary_path, canonical_json(summary) + "\n")
    _atomic_text(markdown_path, _markdown(summary))
    with Recorder.open(
        manifest.path,
        "runner.uprof_hotspots_parser",
        run_dir,
        fragment_id="uprof-hotspots",
    ) as recorder:
        recorder.record(Fact("profile.uprof_hotspots", value))
    return recorder.fragment_path


def _unique_metadata(records: list[list[str]]) -> dict[str, str]:
    wanted = {
        "Target Path:",
        "Collect Command:",
        "Report Command:",
        "Profile Session Type:",
        "Profile Duration:",
        "Call Stack Sampling:",
        "Thread Count",
        "Number Of MPI ranks",
        "Number Of MPI hosts",
    }
    values: dict[str, str] = {}
    for row in records:
        if len(row) == 2 and row[0] in wanted:
            if row[0] in values:
                raise ValueError(f"AMD uProf report repeats metadata: {row[0]}")
            values[row[0]] = row[1].strip()
    return values


def _required(values: dict[str, str], key: str) -> str:
    value = values.get(key, "")
    if not value:
        raise ValueError(f"AMD uProf report lacks metadata: {key}")
    return value


def _contains_sequence(values: list[str], expected: tuple[str, str]) -> bool:
    return any(
        tuple(values[index : index + 2]) == expected for index in range(len(values) - 1)
    )


def _integer(value: str, label: str) -> int:
    if not value.isascii() or not value.isdecimal() or int(value) <= 0:
        raise ValueError(f"AMD uProf {label} is invalid")
    return int(value)


def _decimal(value: str) -> Decimal:
    if _NUMBER.fullmatch(value) is None:
        raise ValueError(f"AMD uProf time has an unsupported value: {value!r}")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("AMD uProf time is invalid") from error
    if not number.is_finite() or number < 0:
        raise ValueError("AMD uProf time must be finite and non-negative")
    return number


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _source(path: Path, run_dir: Path) -> dict[str, object]:
    content = path.read_bytes()
    return {
        "member": path.relative_to(run_dir).as_posix(),
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _summary(
    value: dict[str, object], hotspots: tuple[UProfHotspot, ...], *, limit: int
) -> dict[str, object]:
    return {
        "schema_version": "openfoam-uprof-hotspots-summary/v1",
        "tool_version": value["tool_version"],
        "profile_duration_sec": value["profile_duration_sec"],
        "mpi_ranks": value["mpi_ranks"],
        "mpi_hosts": value["mpi_hosts"],
        "source_hotspots": len(hotspots),
        "exported_hotspots": min(len(hotspots), limit),
        "top_hotspots": [item.fact_value() for item in hotspots[:limit]],
    }


def _markdown(summary: dict[str, object]) -> str:
    rows = summary["top_hotspots"]
    assert isinstance(rows, list)
    lines = [
        "## AMD uProf Hotspots",
        "",
        f"- AMD uProf: {summary['tool_version']}",
        f"- Profile duration: {summary['profile_duration_sec']} s",
        f"- MPI topology: {summary['mpi_ranks']} ranks / {summary['mpi_hosts']} hosts",
        f"- Reported functions: {summary['source_hotspots']}",
        "",
        "| Rank | Function | Module | Self CPU time (s) | Total CPU time (s) |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for rank, row in enumerate(rows, 1):
        assert isinstance(row, dict)
        lines.append(
            f"| {rank} | {_escape(row['function'])} | {_escape(row['module'])} | {row['cpu_time_sec']} | {row['total_cpu_time_sec']} |"
        )
    lines.extend(
        [
            "",
            "The table is derived from the validated all-host uProf report. The complete session is retained in the profile artifact.",
            "",
        ]
    )
    return "\n".join(lines)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _atomic_text(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".uprof-", delete=False
    ) as stream:
        temporary = Path(stream.name)
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
