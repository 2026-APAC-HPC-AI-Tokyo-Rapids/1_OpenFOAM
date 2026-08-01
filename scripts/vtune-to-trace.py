#!/usr/bin/env python3
"""Convert bounded VTune CSV reports to a small Chrome Trace Event file."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
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
class FunctionWindow:
    start_sec: float
    end_sec: float
    hotspots: tuple[Hotspot, ...]


@dataclass(frozen=True, slots=True)
class SolverIteration:
    simulation_time: str
    execution_time_sec: float
    clock_time_sec: float
    initial_residuals: dict[str, float]
    final_residuals: dict[str, float]
    linear_iterations: dict[str, int]
    continuity_local: float | None
    continuity_global: float | None
    continuity_cumulative: float | None


@dataclass(frozen=True, slots=True)
class SolverInterval:
    start_sec: float
    end_sec: float
    first_simulation_time: str
    last_simulation_time: str
    completed_iterations: int
    execution_time_start_sec: float
    execution_time_end_sec: float
    initial_residual_max: dict[str, float]
    final_residual_max: dict[str, float]
    linear_iterations_total: dict[str, int]
    continuity_local_max: float | None
    continuity_global_max_abs: float | None
    continuity_cumulative_final: float | None


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


def read_function_windows(
    directory: Path, timeline: list[TimeBin]
) -> list[FunctionWindow]:
    paths = sorted(path for path in directory.glob("*.csv") if path.name != "windows.csv")
    if not paths or not timeline:
        return []
    boundaries: dict[str, tuple[float, float]] = {}
    manifest = directory / "windows.csv"
    if manifest.is_file():
        for row in csv.DictReader(manifest.read_text(encoding="utf-8").splitlines()):
            start = _number(row.get("start_sec", ""))
            end = _number(row.get("end_sec", ""))
            name = (row.get("file") or "").strip()
            if name and start is not None and end is not None and end >= start:
                boundaries[name] = (start, end)
    timeline_start = timeline[0].start_sec
    duration = timeline[-1].end_sec - timeline_start
    result: list[FunctionWindow] = []
    for offset, path in enumerate(paths):
        start, end = boundaries.get(
            path.name,
            (
                timeline_start + duration * offset / len(paths),
                timeline_start + duration * (offset + 1) / len(paths),
            ),
        )
        result.append(
            FunctionWindow(start, end, tuple(read_hotspots(path)))
        )
    return result


_SOLVER_RE = re.compile(
    r"^[^:]+:\s+Solving for ([^,]+), Initial residual = ([^,]+), "
    r"Final residual = ([^,]+), No Iterations ([0-9]+)"
)
_CONTINUITY_RE = re.compile(
    r"^time step continuity errors\s*:\s*sum local = ([^,]+), "
    r"global = ([^,]+), cumulative = ([^,\s]+)"
)
_EXECUTION_RE = re.compile(
    r"^ExecutionTime = ([^\s]+) s\s+ClockTime = ([^\s]+) s"
)


def read_solver_iterations(path: Path) -> list[SolverIteration]:
    result: list[SolverIteration] = []
    simulation_time: str | None = None
    initial_residuals: dict[str, float] = {}
    final_residuals: dict[str, float] = {}
    linear_iterations: dict[str, int] = {}
    continuity_local: float | None = None
    continuity_global: float | None = None
    continuity_cumulative: float | None = None
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("Time = "):
            simulation_time = line.removeprefix("Time = ").strip()
            initial_residuals = {}
            final_residuals = {}
            linear_iterations = {}
            continuity_local = None
            continuity_global = None
            continuity_cumulative = None
            continue
        solver_match = _SOLVER_RE.match(line)
        if solver_match and simulation_time is not None:
            field = solver_match.group(1).strip()
            initial = _number(solver_match.group(2))
            final = _number(solver_match.group(3))
            if initial is not None:
                initial_residuals[field] = initial
            if final is not None:
                final_residuals[field] = final
            linear_iterations[field] = int(solver_match.group(4))
            continue
        continuity_match = _CONTINUITY_RE.match(line)
        if continuity_match and simulation_time is not None:
            continuity_local = _number(continuity_match.group(1))
            continuity_global = _number(continuity_match.group(2))
            continuity_cumulative = _number(continuity_match.group(3))
            continue
        execution_match = _EXECUTION_RE.match(line)
        if execution_match and simulation_time is not None:
            execution = _number(execution_match.group(1))
            clock = _number(execution_match.group(2))
            if execution is not None and clock is not None:
                result.append(
                    SolverIteration(
                        simulation_time,
                        execution,
                        clock,
                        dict(initial_residuals),
                        dict(final_residuals),
                        dict(linear_iterations),
                        continuity_local,
                        continuity_global,
                        continuity_cumulative,
                    )
                )
            simulation_time = None
    return result


def _field_max(
    iterations: list[SolverIteration], attribute: str
) -> dict[str, float]:
    names = {
        name
        for iteration in iterations
        for name in getattr(iteration, attribute)
    }
    return {
        name: max(
            getattr(iteration, attribute).get(name, 0.0)
            for iteration in iterations
        )
        for name in sorted(names)
    }


def build_solver_intervals(
    iterations: list[SolverIteration],
) -> list[SolverInterval]:
    if not iterations:
        return []
    grouped: list[list[SolverIteration]] = []
    for iteration in iterations:
        if grouped and grouped[-1][-1].clock_time_sec == iteration.clock_time_sec:
            grouped[-1].append(iteration)
        else:
            grouped.append([iteration])
    result: list[SolverInterval] = []
    pending: list[SolverIteration] = []
    previous_clock = 0.0
    previous_execution = 0.0
    for group in grouped:
        pending.extend(group)
        clock = group[-1].clock_time_sec
        if clock <= previous_clock:
            continue
        names = {
            name for iteration in pending for name in iteration.linear_iterations
        }
        continuity_local_values = [
            item.continuity_local
            for item in pending
            if item.continuity_local is not None
        ]
        continuity_global_values = [
            abs(item.continuity_global)
            for item in pending
            if item.continuity_global is not None
        ]
        continuity_cumulative_values = [
            item.continuity_cumulative
            for item in pending
            if item.continuity_cumulative is not None
        ]
        result.append(
            SolverInterval(
                previous_clock,
                clock,
                pending[0].simulation_time,
                pending[-1].simulation_time,
                len(pending),
                previous_execution,
                pending[-1].execution_time_sec,
                _field_max(pending, "initial_residuals"),
                _field_max(pending, "final_residuals"),
                {
                    name: sum(
                        item.linear_iterations.get(name, 0) for item in pending
                    )
                    for name in sorted(names)
                },
                max(continuity_local_values) if continuity_local_values else None,
                max(continuity_global_values) if continuity_global_values else None,
                (
                    continuity_cumulative_values[-1]
                    if continuity_cumulative_values
                    else None
                ),
            )
        )
        previous_clock = clock
        previous_execution = pending[-1].execution_time_sec
        pending = []
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


def _series_functions(
    windows: list[FunctionWindow], limit: int
) -> list[Hotspot]:
    totals: dict[tuple[str, str], float] = {}
    for window in windows:
        for item in window.hotspots:
            key = (item.function, item.module)
            totals[key] = totals.get(key, 0.0) + item.cpu_time_sec
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [
        Hotspot(function, module, cpu_time)
        for (function, module), cpu_time in ranked[:limit]
    ]


def _contiguous(intervals: list[tuple[float, float]]) -> bool:
    return bool(intervals) and all(
        math.isclose(left[1], right[0], abs_tol=1e-6)
        for left, right in zip(intervals, intervals[1:])
    )


def build_trace(
    timeline: list[TimeBin],
    hotspots: list[Hotspot],
    function_windows: list[FunctionWindow],
    solver_intervals: list[SolverInterval],
    *,
    run_label: str,
    max_time_bins: int,
    top_functions: int,
    time_series_functions: int,
    functions_per_window: int,
    function_report_limit: int,
) -> dict[str, Any]:
    bins = _thin(timeline, max_time_bins)
    series_functions = _series_functions(
        function_windows, time_series_functions
    )
    profile_cpu_time_sec = sum(item.cpu_time_sec for item in hotspots)
    timeline_end = bins[-1].end_sec if bins else 0.0
    events: list[dict[str, Any]] = [
        {
            "name": "process_name",
            "ph": "M",
            "pid": 1,
            "tid": 0,
            "args": {"name": f"{run_label}: measured execution timeline"},
        },
        {
            "name": "thread_name",
            "ph": "M",
            "pid": 1,
            "tid": 1,
            "args": {"name": "OpenFOAM solver clock (continuous)"},
        },
        {
            "name": "thread_name",
            "ph": "M",
            "pid": 1,
            "tid": 2,
            "args": {"name": "VTune CPU-time bins (continuous)"},
        },
        {
            "name": "thread_name",
            "ph": "M",
            "pid": 1,
            "tid": 3,
            "args": {"name": "VTune sampled-function windows (continuous)"},
        },
        {
            "name": "process_name",
            "ph": "M",
            "pid": 2,
            "tid": 0,
            "args": {"name": "VTune sampled CPU-time series"},
        },
    ]
    for item in solver_intervals:
        events.append(
            {
                "name": (
                    f"OpenFOAM iterations {item.first_simulation_time}"
                    f"–{item.last_simulation_time}"
                ),
                "cat": "openfoam-solver-clock",
                "ph": "X",
                "pid": 1,
                "tid": 1,
                "ts": round(item.start_sec * 1_000_000),
                "dur": max(
                    1, round((item.end_sec - item.start_sec) * 1_000_000)
                ),
                "args": {
                    "clock_start_sec": item.start_sec,
                    "clock_end_sec": item.end_sec,
                    "first_simulation_time": item.first_simulation_time,
                    "last_simulation_time": item.last_simulation_time,
                    "completed_iterations": item.completed_iterations,
                    "execution_time_start_sec": item.execution_time_start_sec,
                    "execution_time_end_sec": item.execution_time_end_sec,
                    "execution_cpu_delta_sec": round(
                        item.execution_time_end_sec
                        - item.execution_time_start_sec,
                        6,
                    ),
                    "initial_residual_max": item.initial_residual_max,
                    "final_residual_max": item.final_residual_max,
                    "linear_iterations_total": item.linear_iterations_total,
                    "continuity_local_max": item.continuity_local_max,
                    "continuity_global_max_abs": item.continuity_global_max_abs,
                    "continuity_cumulative_final": (
                        item.continuity_cumulative_final
                    ),
                    "source": "OpenFOAM solver log ClockTime",
                },
            }
        )
    solver_end = solver_intervals[-1].end_sec if solver_intervals else 0.0
    if solver_intervals and timeline_end > solver_end:
        events.append(
            {
                "name": "Solver finalization / profiler tail",
                "cat": "openfoam-solver-clock",
                "ph": "X",
                "pid": 1,
                "tid": 1,
                "ts": round(solver_end * 1_000_000),
                "dur": max(1, round((timeline_end - solver_end) * 1_000_000)),
                "args": {
                    "clock_start_sec": solver_end,
                    "clock_end_sec": timeline_end,
                    "completed_iterations": 0,
                    "source": "VTune elapsed time after last solver ClockTime",
                },
            }
        )
    for item in bins:
        events.append(
            {
                "name": "VTune CPU-time interval",
                "cat": "vtune-timeline",
                "ph": "X",
                "pid": 1,
                "tid": 2,
                "ts": round(item.start_sec * 1_000_000),
                "dur": max(1, round((item.end_sec - item.start_sec) * 1_000_000)),
                "args": {
                    "start_sec": item.start_sec,
                    "end_sec": item.end_sec,
                    **item.metrics,
                },
            }
        )
    for offset, window in enumerate(function_windows):
        displayed = window.hotspots[:functions_per_window]
        total_cpu_time = sum(item.cpu_time_sec for item in window.hotspots)
        category_cpu_time: dict[str, float] = {}
        for item in window.hotspots:
            category = hotspot_category(item)
            category_cpu_time[category] = (
                category_cpu_time.get(category, 0.0) + item.cpu_time_sec
            )
        events.append(
            {
                "name": f"Sample window {offset + 1}",
                "cat": "vtune-sample-window",
                "ph": "X",
                "pid": 1,
                "tid": 3,
                "ts": round(window.start_sec * 1_000_000),
                "dur": max(
                    1,
                    round((window.end_sec - window.start_sec) * 1_000_000),
                ),
                "args": {
                    "window_start_sec": window.start_sec,
                    "window_end_sec": window.end_sec,
                    "reported_function_count": len(window.hotspots),
                    "reported_cpu_time_sec": round(total_cpu_time, 6),
                    "category_cpu_time_sec": {
                        name: round(value, 6)
                        for name, value in sorted(category_cpu_time.items())
                    },
                    "hottest_sampled_functions": [
                        {
                            "rank": rank,
                            "function": item.function,
                            "module": item.module,
                            "category": hotspot_category(item),
                            "sampled_cpu_time_sec": item.cpu_time_sec,
                        }
                        for rank, item in enumerate(displayed, 1)
                    ],
                    "interpretation": (
                        "This block is the measured report window. Function values "
                        "are sampled CPU time inside it, not call boundaries."
                    ),
                },
            }
        )
    series_metadata: list[dict[str, Any]] = []
    for series_index, series in enumerate(series_functions, 1):
        key = (series.function, series.module)
        series_metadata.append(
            {
                "rank": series_index,
                "function": series.function,
                "module": series.module,
                "category": hotspot_category(series),
                "reported_cpu_time_sec": series.cpu_time_sec,
            }
        )
        for window in function_windows:
            values = {
                (item.function, item.module): item.cpu_time_sec
                for item in window.hotspots
            }
            events.append(
                {
                    "name": f"#{series_index} {series.function}",
                    "cat": "vtune-function-time-series",
                    "ph": "C",
                    "pid": 2,
                    "tid": series_index,
                    "ts": round(window.start_sec * 1_000_000),
                    "args": {
                        "sampled_cpu_time_sec": round(values.get(key, 0.0), 6)
                    },
                }
            )
    categories = ("MPI", "OpenFOAM", "Runtime", "Other")
    for category_index, category in enumerate(categories, len(series_functions) + 1):
        for window in function_windows:
            value = sum(
                item.cpu_time_sec
                for item in window.hotspots
                if hotspot_category(item) == category
            )
            events.append(
                {
                    "name": f"{category} sampled CPU time",
                    "cat": "vtune-category-time-series",
                    "ph": "C",
                    "pid": 2,
                    "tid": category_index,
                    "ts": round(window.start_sec * 1_000_000),
                    "args": {"sampled_cpu_time_sec": round(value, 6)},
                }
            )
    return {
        "displayTimeUnit": "ms",
        "metadata": {
            "source": "Intel VTune CSV reports and OpenFOAM solver log",
            "time_bins": len(bins),
            "aggregate_hotspot_count": min(top_functions, len(hotspots)),
            "sample_windows": len(function_windows),
            "sampled_function_values": sum(
                len(window.hotspots) for window in function_windows
            ),
            "time_series_functions": series_metadata,
            "solver_intervals": len(solver_intervals),
            "solver_iterations": sum(
                item.completed_iterations for item in solver_intervals
            ),
            "profile_cpu_time_sec": profile_cpu_time_sec,
            "timeline_start_sec": bins[0].start_sec if bins else None,
            "timeline_end_sec": bins[-1].end_sec if bins else None,
            "function_call_boundaries_available": False,
            "sample_window_boundaries_are_measured": True,
            "solver_intervals_use_logged_clock_time": True,
            "timeline_bins_contiguous": _contiguous(
                [(item.start_sec, item.end_sec) for item in bins]
            ),
            "sample_windows_contiguous": _contiguous(
                [
                    (item.start_sec, item.end_sec)
                    for item in function_windows
                ]
            ),
            "solver_intervals_contiguous": _contiguous(
                [
                    (item.start_sec, item.end_sec)
                    for item in solver_intervals
                ]
            ),
            "function_report_limit": function_report_limit,
            "function_reports_are_complete": function_report_limit == 0,
            "function_time_series_semantics": (
                "Sampled CPU time attributed to each measured report window; "
                "not wall-time occupancy or exact call duration."
            ),
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
    parser.add_argument("--solver-log", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--run-label", default="openfoam")
    parser.add_argument("--top-functions", type=int, default=50)
    parser.add_argument("--time-series-functions", type=int, default=12)
    parser.add_argument("--functions-per-window", type=int, default=8)
    parser.add_argument("--function-report-limit", type=int, default=0)
    parser.add_argument("--max-time-bins", type=int, default=300)
    parser.add_argument("--max-trace-bytes", type=int, default=5_000_000)
    arguments = parser.parse_args()
    if min(
        arguments.top_functions,
        arguments.time_series_functions,
        arguments.functions_per_window,
        arguments.max_time_bins,
        arguments.max_trace_bytes,
    ) <= 0:
        parser.error("limits must be positive")
    if arguments.function_report_limit < 0:
        parser.error("function-report-limit must be non-negative")

    timeline = read_timeline(arguments.timeline)
    hotspots = read_hotspots(arguments.hotspots)
    function_windows = (
        read_function_windows(arguments.function_slices_dir, timeline)
        if arguments.function_slices_dir
        else []
    )
    solver_iterations = (
        read_solver_iterations(arguments.solver_log)
        if arguments.solver_log and arguments.solver_log.is_file()
        else []
    )
    solver_intervals = build_solver_intervals(solver_iterations)
    time_bins = min(arguments.max_time_bins, len(timeline))
    top_functions = min(arguments.top_functions, len(hotspots))
    time_series_functions = arguments.time_series_functions
    functions_per_window = arguments.functions_per_window
    while True:
        document = build_trace(
            timeline,
            hotspots,
            function_windows,
            solver_intervals,
            run_label=arguments.run_label,
            max_time_bins=time_bins,
            top_functions=top_functions,
            time_series_functions=time_series_functions,
            functions_per_window=functions_per_window,
            function_report_limit=arguments.function_report_limit,
        )
        payload = _encoded(document)
        if len(payload) <= arguments.max_trace_bytes:
            break
        if time_series_functions > 4:
            time_series_functions = max(4, time_series_functions // 2)
        elif time_bins > 50:
            time_bins = max(50, time_bins // 2)
        elif functions_per_window > 2:
            functions_per_window = max(2, functions_per_window // 2)
        elif top_functions > 1:
            top_functions //= 2
        else:
            raise ValueError(
                "trace cannot fit max-trace-bytes even at the minimum detail"
            )

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(payload)
    summary = {
        "schema_version": 5,
        "run_label": arguments.run_label,
        "source_time_bins": len(timeline),
        "exported_time_bins": time_bins,
        "source_hotspots": len(hotspots),
        "exported_hotspots": top_functions,
        "source_sample_windows": len(function_windows),
        "exported_sample_windows": len(function_windows),
        "source_function_values": sum(
            len(window.hotspots) for window in function_windows
        ),
        "exported_time_series_functions": len(
            document["metadata"]["time_series_functions"]
        ),
        "exported_functions_per_window": functions_per_window,
        "solver_iterations": len(solver_iterations),
        "solver_intervals": len(solver_intervals),
        "function_report_limit": arguments.function_report_limit,
        "function_reports_are_complete": arguments.function_report_limit == 0,
        "timeline_bins_contiguous": document["metadata"][
            "timeline_bins_contiguous"
        ],
        "sample_windows_contiguous": document["metadata"][
            "sample_windows_contiguous"
        ],
        "solver_intervals_contiguous": document["metadata"][
            "solver_intervals_contiguous"
        ],
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
