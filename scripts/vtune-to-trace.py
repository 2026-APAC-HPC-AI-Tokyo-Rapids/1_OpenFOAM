#!/usr/bin/env python3
"""Convert bounded VTune CSV reports to a small Chrome Trace Event file."""

from __future__ import annotations

import argparse
import csv
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


@dataclass(frozen=True, slots=True)
class FunctionSlice:
    start_sec: float
    end_sec: float
    rank: int
    hotspot: Hotspot


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


def read_function_slices(directory: Path, timeline: list[TimeBin]) -> list[FunctionSlice]:
    paths = sorted(directory.glob("*.csv"))
    if not paths or not timeline:
        return []
    timeline_start = timeline[0].start_sec
    timeline_end = timeline[-1].end_sec
    duration = timeline_end - timeline_start
    result: list[FunctionSlice] = []
    for index, path in enumerate(paths):
        start = timeline_start + duration * index / len(paths)
        end = timeline_start + duration * (index + 1) / len(paths)
        for rank, hotspot in enumerate(read_hotspots(path), 1):
            result.append(FunctionSlice(start, end, rank, hotspot))
    return result


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


def hotspot_category(item: Hotspot) -> str:
    module = item.module.lower()
    function = item.function.lower()
    if "mpi" in module or function.startswith(("pmpi_", "mpi_", "internal_i")):
        return "MPI"
    if any(
        name in module
        for name in ("openfoam", "finitevolume", "mesh", "simplefoam")
    ) or function.startswith("foam::"):
        return "OpenFOAM"
    if any(name in module for name in ("libc.", "libstdc++", "libdl.", "libpthread")):
        return "Runtime"
    return "Other"


def _limit_evenly(items: list[FunctionSlice], limit: int) -> list[FunctionSlice]:
    if len(items) <= limit:
        return items
    return [items[offset * len(items) // limit] for offset in range(limit)]


def build_trace(
    timeline: list[TimeBin],
    hotspots: list[Hotspot],
    function_slices: list[FunctionSlice],
    *,
    run_label: str,
    max_time_bins: int,
    top_functions: int,
    max_function_slices: int,
) -> dict[str, Any]:
    bins = _thin(timeline, max_time_bins)
    slices = _limit_evenly(function_slices, max_function_slices)
    profile_cpu_time_sec = sum(item.cpu_time_sec for item in hotspots)
    events: list[dict[str, Any]] = [
        {
            "name": "process_name",
            "ph": "M",
            "pid": 1,
            "tid": 0,
            "args": {"name": f"{run_label}: sampled execution timeline"},
        },
        {
            "name": "thread_name",
            "ph": "M",
            "pid": 1,
            "tid": 1,
            "args": {"name": "VTune CPU-time intervals"},
        },
    ]
    for item in bins:
        events.append(
            {
                "name": "VTune CPU-time interval",
                "cat": "vtune-timeline",
                "ph": "X",
                "pid": 1,
                "tid": 1,
                "ts": round(item.start_sec * 1_000_000),
                "dur": max(1, round((item.end_sec - item.start_sec) * 1_000_000)),
                "args": {
                    "start_sec": item.start_sec,
                    "end_sec": item.end_sec,
                    **item.metrics,
                },
            }
        )
    slice_ranks = sorted({item.rank for item in slices})
    for rank in slice_ranks:
        events.extend(
            [
                {
                    "name": "thread_name",
                    "ph": "M",
                    "pid": 1,
                    "tid": 10 + rank,
                    "args": {"name": f"Sampled hotspot rank #{rank} per interval"},
                },
                {
                    "name": "thread_sort_index",
                    "ph": "M",
                    "pid": 1,
                    "tid": 10 + rank,
                    "args": {"sort_index": 10 + rank},
                },
            ]
        )
    for item in slices:
        hotspot = item.hotspot
        category = hotspot_category(hotspot)
        events.append(
            {
                "name": hotspot.function,
                "cat": f"vtune-sampled-function,{category.lower()}",
                "ph": "X",
                "pid": 1,
                "tid": 10 + item.rank,
                "ts": round(item.start_sec * 1_000_000),
                "dur": max(
                    1, round((item.end_sec - item.start_sec) * 1_000_000)
                ),
                "args": {
                    "interval_start_sec": item.start_sec,
                    "interval_end_sec": item.end_sec,
                    "interval_rank": item.rank,
                    "category": category,
                    "module": hotspot.module,
                    "sampled_cpu_time_sec": hotspot.cpu_time_sec,
                    "interpretation": (
                        "Function samples attributed to this elapsed-time interval; "
                        "boundaries are sampling bins, not exact function calls."
                    ),
                },
            }
        )
    return {
        "displayTimeUnit": "ms",
        "metadata": {
            "source": "Intel VTune CSV reports",
            "time_bins": len(bins),
            "aggregate_hotspot_count": min(top_functions, len(hotspots)),
            "sampled_function_intervals": len(slices),
            "profile_cpu_time_sec": profile_cpu_time_sec,
            "timeline_start_sec": bins[0].start_sec if bins else None,
            "timeline_end_sec": bins[-1].end_sec if bins else None,
            "function_boundaries_are_sampling_intervals": True,
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
    parser.add_argument("--function-slices-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--run-label", default="openfoam")
    parser.add_argument("--top-functions", type=int, default=50)
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
    function_slices = (
        read_function_slices(arguments.function_slices_dir, timeline)
        if arguments.function_slices_dir
        else []
    )
    time_bins = min(arguments.max_time_bins, len(timeline))
    top_functions = min(arguments.top_functions, len(hotspots))
    function_slice_limit = len(function_slices)
    while True:
        document = build_trace(
            timeline,
            hotspots,
            function_slices,
            run_label=arguments.run_label,
            max_time_bins=time_bins,
            top_functions=top_functions,
            max_function_slices=function_slice_limit,
        )
        payload = _encoded(document)
        if len(payload) <= arguments.max_trace_bytes:
            break
        if time_bins > 10:
            time_bins = max(10, time_bins // 2)
        elif function_slice_limit > 10:
            function_slice_limit = max(10, function_slice_limit // 2)
        elif top_functions > 1:
            top_functions //= 2
        else:
            raise ValueError(
                "trace cannot fit max-trace-bytes even at the minimum detail"
            )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(payload)
    summary = {
        "schema_version": 4,
        "run_label": arguments.run_label,
        "source_time_bins": len(timeline),
        "exported_time_bins": time_bins,
        "source_hotspots": len(hotspots),
        "exported_hotspots": top_functions,
        "source_function_intervals": len(function_slices),
        "exported_function_intervals": function_slice_limit,
        "trace_bytes": len(payload),
        "profile_cpu_time_sec": sum(item.cpu_time_sec for item in hotspots),
        "timeline_available": bool(timeline),
        "elapsed_sec": timeline[-1].end_sec if timeline else None,
        "top_hotspots": [
            {
                "function": item.function,
                "module": item.module,
                "category": hotspot_category(item),
                "cpu_time_sec": item.cpu_time_sec,
                "profile_cpu_percent": round(
                    item.cpu_time_sec
                    / sum(source.cpu_time_sec for source in hotspots)
                    * 100,
                    3,
                )
                if hotspots
                else 0.0,
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
