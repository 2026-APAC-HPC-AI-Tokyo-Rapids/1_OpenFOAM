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


def parse_uprof_hotspots(
    text: str, *, expected_host_scope: str = "all", expected_cutoff: int = 30
) -> UProfReport:
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
        not _contains_sequence(report, ("--host", expected_host_scope))
        or "--detail" not in report
        or not _contains_sequence(report, ("--cutoff", str(expected_cutoff)))
    ):
        raise ValueError(
            "AMD uProf report command differs from the expected detail protocol"
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
    report_root: Path,
    expected_hosts: int,
    expected_ranks: int,
    summary_path: Path,
    markdown_path: Path,
    limit: int = 30,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    if run_dir != manifest.path.parents[1] or manifest.purpose != "profile":
        raise ValueError("AMD uProf facts require the bound profile run")
    if limit <= 0 or expected_hosts <= 0 or expected_ranks <= 0:
        raise ValueError("AMD uProf summary limit is invalid")
    expected = {
        report_root: run_dir / "profile/raw/uprof/reports",
        summary_path: run_dir / "results/uprof-summary.json",
        markdown_path: run_dir / "results/uprof-summary.md",
    }
    for supplied, required in expected.items():
        if supplied.resolve() != required.resolve():
            raise ValueError(
                "AMD uProf source or output path is outside its fixed run path"
            )
    reports = sorted(report_root.glob("*.csv"), key=lambda path: path.name.encode())
    if len(reports) != expected_hosts:
        raise ValueError("AMD uProf host report count differs from the scheduler request")
    parsed_by_host: list[tuple[str, UProfReport, Path]] = []
    for report_path in reports:
        host = report_path.stem
        if re.fullmatch(r"[A-Za-z0-9._-]+", host) is None:
            raise ValueError("AMD uProf host report has an invalid host name")
        parsed_host = parse_uprof_hotspots(
            report_path.read_text(encoding="utf-8-sig"),
            expected_host_scope=host,
            expected_cutoff=0,
        )
        if parsed_host.mpi_hosts != 1 or parsed_host.ranks_per_node != (
            (host, parsed_host.mpi_ranks),
        ):
            raise ValueError("AMD uProf host report topology is inconsistent")
        parsed_by_host.append((host, parsed_host, report_path))
    parsed = _aggregate_host_reports(parsed_by_host)
    if parsed.mpi_hosts != expected_hosts or parsed.mpi_ranks != expected_ranks:
        raise ValueError("AMD uProf aggregate topology differs from the protocol")
    value = {
        "schema_version": "openfoam-uprof-profile/v1",
        "tool_version": _VERSION,
        "target_path": parsed.target_path,
        "collection": {
            "analysis_type": "hotspots",
            "call_stack_sampling": True,
            "mpi": True,
            "report_host_scope": "per-host",
            "report_cutoff": 0,
            "aggregation": "sum function/module CPU times across complete host reports",
        },
        "profile_duration_lexeme": parsed.duration_lexeme,
        "profile_duration_sec": _decimal_text(parsed.duration_sec),
        "thread_count": parsed.thread_count,
        "mpi_ranks": parsed.mpi_ranks,
        "mpi_hosts": parsed.mpi_hosts,
        "ranks_per_node": [
            {"host": host, "ranks": ranks} for host, ranks in parsed.ranks_per_node
        ],
        "source": {
            "reports": [
                {"host": host, **_source(report_path, run_dir)}
                for host, _, report_path in parsed_by_host
            ]
        },
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


def _aggregate_host_reports(
    reports: list[tuple[str, UProfReport, Path]],
) -> UProfReport:
    targets = {report.target_path for _, report, _ in reports}
    if len(targets) != 1:
        raise ValueError("AMD uProf host reports disagree on the target path")
    totals: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}
    for _, report, _ in reports:
        for hotspot in report.hotspots:
            key = (hotspot.function, hotspot.module)
            cpu_time, total_cpu_time = totals.get(key, (Decimal(0), Decimal(0)))
            totals[key] = (
                cpu_time + hotspot.cpu_time_sec,
                total_cpu_time + hotspot.total_cpu_time_sec,
            )
    ordered_totals = sorted(
        totals.items(),
        key=lambda item: (-item[1][0], item[0][0].encode(), item[0][1].encode()),
    )
    hotspots = tuple(
        UProfHotspot(
            report_row,
            function,
            module,
            _decimal_text(cpu_time),
            _decimal_text(total_cpu_time),
            cpu_time,
            total_cpu_time,
        )
        for report_row, ((function, module), (cpu_time, total_cpu_time)) in enumerate(
            ordered_totals, 1
        )
    )
    duration = max(report.duration_sec for _, report, _ in reports)
    return UProfReport(
        targets.pop(),
        f"{_decimal_text(duration)} seconds",
        duration,
        sum(report.thread_count for _, report, _ in reports),
        sum(report.mpi_ranks for _, report, _ in reports),
        len(reports),
        tuple((host, report.mpi_ranks) for host, report, _ in reports),
        hotspots,
    )


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
            "The table aggregates validated complete reports from every host. The complete sessions are retained in the profile artifact.",
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
