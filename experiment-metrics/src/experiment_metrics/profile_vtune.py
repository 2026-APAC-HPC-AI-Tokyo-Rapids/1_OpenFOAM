"""Validated VTune hotspot facts and bounded Actions summaries."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .fact import Fact, canonical_json
from .manifest import RunManifest
from .recording import Recorder

_NUMBER = re.compile(
    r"^[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$"
)
_REPORT_HEADER = [
    "Function",
    "Module",
    "CPU Time",
    "CPU Time:Effective Time",
    "CPU Time:Spin Time",
    "CPU Time:Spin Time:MPI Busy Wait Time",
    "CPU Time:Spin Time:Other",
    "CPU Time:Overhead Time",
    "CPU Time:Overhead Time:Other",
]


@dataclass(frozen=True, slots=True)
class Hotspot:
    report_row: int
    function: str
    module: str
    cpu_time_lexeme: str
    cpu_time_sec: Decimal

    def fact_value(self) -> dict[str, object]:
        return {
            "report_row": self.report_row,
            "function": self.function,
            "module": self.module,
            "cpu_time_lexeme": self.cpu_time_lexeme,
            "cpu_time_sec": _decimal_text(self.cpu_time_sec),
        }


def parse_hotspots(text: str) -> tuple[Hotspot, ...]:
    """Parse the exact three-column report emitted by the VTune command."""

    try:
        records = list(csv.reader(text.splitlines(), strict=True))
    except csv.Error as error:
        raise ValueError("VTune hotspot CSV is malformed") from error
    headers = [index for index, row in enumerate(records) if row == _REPORT_HEADER]
    if len(headers) != 1:
        raise ValueError("VTune hotspot CSV must contain one exact header")
    rows: list[Hotspot] = []
    for report_row, record in enumerate(
        records[headers[0] + 1 :], start=headers[0] + 2
    ):
        if not record:
            continue
        if len(record) != len(_REPORT_HEADER):
            raise ValueError("VTune hotspot CSV row has an unexpected column count")
        function, module, lexeme, *breakdown = (item.strip() for item in record)
        if not function:
            raise ValueError("VTune hotspot function is empty")
        for value in breakdown:
            _seconds(value)
        rows.append(Hotspot(report_row, function, module, lexeme, _seconds(lexeme)))
    if not rows:
        raise ValueError("VTune hotspot CSV contains no function rows")
    return tuple(
        sorted(
            rows,
            key=lambda item: (
                -item.cpu_time_sec,
                item.function.encode(),
                item.module.encode(),
                item.report_row,
            ),
        )
    )


def record_vtune_hotspots(
    *,
    manifest_path: Path,
    runtime_dir: Path,
    registry_path: Path,
    report_path: Path,
    status_path: Path,
    summary_path: Path,
    markdown_path: Path,
    profiled_rank: int,
    collection_duration_sec: int,
    limit: int = 30,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    if run_dir != manifest.path.parents[1] or manifest.purpose != "profile":
        raise ValueError("VTune facts require the bound profile run")
    if profiled_rank < 0 or collection_duration_sec <= 0 or limit <= 0:
        raise ValueError("VTune rank, duration, and summary limit are invalid")
    expected_root = run_dir / "profile/raw/vtune-summary"
    expected = {
        report_path: expected_root / "hotspots.csv",
        status_path: expected_root / "collection-status.json",
        summary_path: expected_root / "summary.json",
        markdown_path: expected_root / "summary.md",
    }
    for supplied, required in expected.items():
        if supplied.resolve() != required.resolve():
            raise ValueError(
                "VTune source or output path is outside its fixed run path"
            )

    status = _collection_status(status_path)
    if status["target_exit_code"] != 0 or status["vtune_exit_code"] != 0:
        raise ValueError("VTune collection did not complete successfully")
    hotspots = parse_hotspots(report_path.read_text(encoding="utf-8-sig"))
    value = {
        "schema_version": "openfoam-vtune-hotspots/v1",
        "profiled_rank": profiled_rank,
        "collection": {
            "analysis_type": "hotspots",
            "target_mode": "attach",
            "sampling_mode": "sw",
            "stack_collection": False,
            "requested_duration_sec": collection_duration_sec,
            "report_time_unit": "seconds",
        },
        "sources": {
            "report": _source(report_path, run_dir),
            "collection_status": _source(status_path, run_dir),
        },
        "hotspots": [item.fact_value() for item in hotspots],
    }
    summary = _summary(value, hotspots, limit=limit)
    _atomic_text(summary_path, canonical_json(summary) + "\n")
    _atomic_text(markdown_path, _markdown(summary))
    with Recorder.open(
        manifest.path,
        registry_path,
        "compute.vtune_hotspots_parser",
        run_dir,
        fragment_id="vtune-hotspots",
    ) as recorder:
        recorder.record(Fact(f"profile.vtune_hotspots.rank.{profiled_rank}", value))
    return recorder.fragment_path


def _collection_status(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or set(value)
        != {"schema_version", "target_exit_code", "vtune_exit_code"}
        or value["schema_version"] != "vtune-collection-status/v1"
        or any(
            isinstance(value[name], bool) or not isinstance(value[name], int)
            for name in ("target_exit_code", "vtune_exit_code")
        )
    ):
        raise ValueError("VTune collection status is invalid")
    return value


def _summary(
    value: dict[str, object], hotspots: tuple[Hotspot, ...], *, limit: int
) -> dict[str, object]:
    total = sum((item.cpu_time_sec for item in hotspots), Decimal(0))
    top: list[dict[str, object]] = []
    for item in hotspots[:limit]:
        percent = Decimal(0) if total == 0 else Decimal(100) * item.cpu_time_sec / total
        top.append(
            {**item.fact_value(), "reported_cpu_percent": _decimal_text(percent)}
        )
    collection = value["collection"]
    assert isinstance(collection, dict)
    return {
        "schema_version": "openfoam-vtune-hotspots-summary/v1",
        "profiled_rank": value["profiled_rank"],
        "collection_duration_sec": collection["requested_duration_sec"],
        "source_hotspots": len(hotspots),
        "exported_hotspots": len(top),
        "reported_cpu_time_sec": _decimal_text(total),
        "top_hotspots": top,
    }


def _markdown(summary: dict[str, object]) -> str:
    rows = summary["top_hotspots"]
    assert isinstance(rows, list)
    lines = [
        "## Intel VTune hotspots",
        "",
        f"- Profiled MPI rank: {summary['profiled_rank']}",
        f"- Attached sampling window: {summary['collection_duration_sec']} s",
        f"- Reported functions: {summary['source_hotspots']}",
        f"- Total reported CPU time: {summary['reported_cpu_time_sec']} s",
        "",
        "| Rank | Function | Module | CPU time (s) | Reported CPU time |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for rank, row in enumerate(rows, 1):
        assert isinstance(row, dict)
        lines.append(
            f"| {rank} | {_escape(row['function'])} | {_escape(row['module'])} "
            f"| {row['cpu_time_sec']} | {row['reported_cpu_percent']}% |"
        )
    lines.extend(
        [
            "",
            (
                "The table is derived from the validated VTune report for one "
                "representative MPI rank. Full VTune results remain on Genkai."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _seconds(value: str) -> Decimal:
    if _NUMBER.fullmatch(value) is None:
        raise ValueError(f"VTune CPU time has an unsupported value: {value!r}")
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("VTune CPU time is invalid") from error
    if not number.is_finite() or number < 0:
        raise ValueError("VTune CPU time must be finite and non-negative")
    return number


def _source(path: Path, run_dir: Path) -> dict[str, object]:
    content = path.read_bytes()
    return {
        "member": path.relative_to(run_dir).as_posix(),
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _atomic_text(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".vtune-", delete=False
    ) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)
