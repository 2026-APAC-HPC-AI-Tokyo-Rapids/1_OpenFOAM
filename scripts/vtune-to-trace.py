#!/usr/bin/env python3
"""Convert bounded VTune CSV reports to a small Chrome Trace Event file."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class TimeBin:
    start_sec: float
    end_sec: float
    metrics: dict[str, float]


@dataclass(frozen=True, slots=True)
class Hotspot:
    function: str
    module: str
    cpu_time_sec: float


def _number(value: str) -> float | None:
    text = value.strip().replace(",", "")
    if not text:
        return None
    if text.endswith("%"):
        text = text[:-1]
    if text.endswith("s"):
        text = text[:-1]
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _rows(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for index, line in enumerate(lines):
        if all(name in line for name in required):
            return list(csv.DictReader(lines[index:]))
    raise ValueError(f"{path}: header containing {required!r} was not found")


def read_timeline(path: Path) -> list[TimeBin]:
    if path.stat().st_size == 0:
        return []
    rows = _rows(path, ("Bin Start Time", "Bin End Time"))
    result: list[TimeBin] = []
    for row in rows:
        start = _number(row.get("Bin Start Time", ""))
        end = _number(row.get("Bin End Time", ""))
        if start is None or end is None or end < start:
            continue
        metrics: dict[str, float] = {}
        for key, value in row.items():
            if key in {"timeBin", "Bin Start Time", "Bin End Time"} or value is None:
                continue
            parsed = _number(value)
            if parsed is not None:
                metrics[key.strip()] = parsed
        result.append(TimeBin(start, end, metrics))
    return result


def read_hotspots(path: Path) -> list[Hotspot]:
    rows = _rows(path, ("Function",))
    result: list[Hotspot] = []
    for row in rows:
        function = (row.get("Function") or "").strip()
        module = (row.get("Module") or "").strip()
        cpu_key = next((key for key in row if key and "CPU Time" in key), "")
        cpu_time = _number(row.get(cpu_key, "") if cpu_key else "")
        if function and cpu_time is not None:
            result.append(Hotspot(function, module, cpu_time))
    return sorted(result, key=lambda item: item.cpu_time_sec, reverse=True)


def _thin(items: list[TimeBin], limit: int) -> list[TimeBin]:
    if len(items) <= limit:
        return items
    selected: list[TimeBin] = []
    for offset in range(limit):
        start = offset * len(items) // limit
        end = (offset + 1) * len(items) // limit
        group = items[start:end]
        names = {name for item in group for name in item.metrics}
        metrics = {
            name: sum(item.metrics.get(name, 0.0) for item in group)
            / len(group)
            for name in names
        }
        selected.append(TimeBin(group[0].start_sec, group[-1].end_sec, metrics))
    return selected


def build_trace(
    timeline: list[TimeBin],
    hotspots: list[Hotspot],
    *,
    run_label: str,
    max_time_bins: int,
    top_functions: int,
) -> dict[str, Any]:
    bins = _thin(timeline, max_time_bins)
    selected_hotspots = hotspots[:top_functions]
    events: list[dict[str, Any]] = [
        {
            "name": "process_name",
            "ph": "M",
            "pid": 1,
            "tid": 0,
            "args": {"name": run_label},
        }
    ]
    for item in bins:
        timestamp_us = round((item.start_sec + item.end_sec) * 500_000)
        for metric, value in sorted(item.metrics.items()):
            events.append(
                {
                    "name": metric,
                    "cat": "vtune-timeline",
                    "ph": "C",
                    "pid": 1,
                    "tid": 0,
                    "ts": timestamp_us,
                    "args": {"value": value},
                }
            )
    if selected_hotspots:
        events.append(
            {
                "name": "VTune hotspots summary",
                "cat": "vtune-summary",
                "ph": "I",
                "s": "p",
                "pid": 1,
                "tid": 0,
                "ts": round(bins[-1].end_sec * 1_000_000) if bins else 0,
                "args": {
                    f"{index + 1}. {item.function}": {
                        "module": item.module,
                        "cpu_time_sec": item.cpu_time_sec,
                    }
                    for index, item in enumerate(selected_hotspots)
                },
            }
        )
    return {
        "displayTimeUnit": "ms",
        "metadata": {
            "source": "Intel VTune CSV reports",
            "time_bins": len(bins),
            "hotspot_count": len(selected_hotspots),
        },
        "traceEvents": events,
    }


def _encoded(document: dict[str, Any]) -> bytes:
    return json.dumps(
        document, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--hotspots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--run-label", default="openfoam")
    parser.add_argument("--top-functions", type=int, default=20)
    parser.add_argument("--max-time-bins", type=int, default=300)
    parser.add_argument("--max-trace-bytes", type=int, default=5_000_000)
    arguments = parser.parse_args()
    if min(
        arguments.top_functions,
        arguments.max_time_bins,
        arguments.max_trace_bytes,
    ) <= 0:
        parser.error("limits must be positive")

    timeline = read_timeline(arguments.timeline)
    hotspots = read_hotspots(arguments.hotspots)
    time_bins = min(arguments.max_time_bins, len(timeline))
    top_functions = min(arguments.top_functions, len(hotspots))
    while True:
        document = build_trace(
            timeline,
            hotspots,
            run_label=arguments.run_label,
            max_time_bins=time_bins,
            top_functions=top_functions,
        )
        payload = _encoded(document)
        if len(payload) <= arguments.max_trace_bytes:
            break
        if time_bins > 10:
            time_bins = max(10, time_bins // 2)
        elif top_functions > 1:
            top_functions //= 2
        else:
            raise ValueError(
                "trace cannot fit max-trace-bytes even at the minimum detail"
            )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(arguments.output, "wb", compresslevel=9) as stream:
        stream.write(payload)
    summary = {
        "schema_version": 1,
        "run_label": arguments.run_label,
        "source_time_bins": len(timeline),
        "exported_time_bins": time_bins,
        "source_hotspots": len(hotspots),
        "exported_hotspots": top_functions,
        "uncompressed_trace_bytes": len(payload),
        "compressed_trace_bytes": arguments.output.stat().st_size,
        "timeline_available": bool(timeline),
        "elapsed_sec": timeline[-1].end_sec if timeline else None,
        "top_hotspots": [
            {
                "function": item.function,
                "module": item.module,
                "cpu_time_sec": item.cpu_time_sec,
            }
            for item in hotspots[:top_functions]
        ],
    }
    arguments.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
