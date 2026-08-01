#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path


def escape_table(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render(summary: dict[str, object], trace_url: str) -> str:
    hotspots = summary.get("top_hotspots", [])
    if not isinstance(hotspots, list):
        raise ValueError("top_hotspots must be a list")
    exact_tasks = summary.get("exact_task_function_summaries", [])
    if not isinstance(exact_tasks, list):
        raise ValueError("exact_task_function_summaries must be a list")

    timeline = "available" if summary.get("timeline_available") else "not available"
    lines = [
        "## Intel VTune summary",
        "",
        f"- Run label: `{escape_table(summary.get('run_label', 'unknown'))}`",
        f"- Source hotspots: {summary.get('source_hotspots', 0)}",
        f"- Exported hotspots: {summary.get('exported_hotspots', 0)}",
        f"- Timeline intervals: {summary.get('exported_time_bins', 0)}",
        f"- Sample windows: {summary.get('exported_sample_windows', 0)}",
        f"- Function values: {summary.get('source_function_values', 0)}",
        f"- Function time series: {summary.get('exported_time_series_functions', 0)}",
        f"- Functions shown per window: {summary.get('exported_functions_per_window', 0)}",
        f"- Solver iterations: {summary.get('solver_iterations', 0)}",
        f"- Solver clock intervals: {summary.get('solver_intervals', 0)}",
        f"- Exact source task calls: {summary.get('source_exact_task_events', 0)}",
        f"- Exact exported task calls: {summary.get('exported_exact_task_events', 0)}",
        f"- Exact task export complete: {summary.get('exact_task_events_are_complete', False)}",
        f"- Recorder-dropped task calls: {summary.get('exact_task_recorder_dropped_events', 0)}",
        f"- Timeline bins contiguous: {summary.get('timeline_bins_contiguous', False)}",
        f"- Sample windows contiguous: {summary.get('sample_windows_contiguous', False)}",
        f"- Function reports complete: {summary.get('function_reports_are_complete', False)}",
        f"- Profile CPU time: {float(summary.get('profile_cpu_time_sec', 0)):.6f} s",
        f"- Timeline: {timeline}",
        f"- Chrome trace: {summary.get('trace_bytes', 0)} bytes",
        "- Continuous blocks are measured VTune windows or OpenFOAM ClockTime intervals.",
        (
            "- Sampled function tracks remain estimates. Exact OpenFOAM task tracks "
            "use directly measured entry/exit boundaries when available."
        ),
        "",
        "| Rank | Category | Function | Module | CPU time (s) | Profile CPU |",
        "| ---: | --- | --- | --- | ---: | ---: |",
    ]
    for rank, item in enumerate(hotspots, 1):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| {rank} | {escape_table(item.get('category', 'Other'))} "
            f"| `{escape_table(item.get('function', ''))}` "
            f"| `{escape_table(item.get('module', ''))}` "
            f"| {float(item.get('cpu_time_sec', 0)):.6f} "
            f"| {float(item.get('profile_cpu_percent', 0)):.3f}% |"
        )

    if exact_tasks:
        lines.extend(
            [
                "",
                "### Exact instrumented function boundaries",
                "",
                (
                    "| Function | Calls | Inclusive wall (s) | Process occupancy "
                    "| p50 (µs) | p95 (µs) | Gap p50 (µs) | <100µs |"
                ),
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in exact_tasks:
            if not isinstance(item, dict):
                continue
            gap = item.get("gap_p50_us")
            gap_text = f"{float(gap):.3f}" if gap is not None else "n/a"
            lines.append(
                f"| `{escape_table(item.get('function', ''))}` "
                f"| {int(item.get('calls', 0))} "
                f"| {float(item.get('inclusive_wall_time_sec', 0)):.6f} "
                f"| {float(item.get('process_occupancy_percent', 0)):.3f}% "
                f"| {float(item.get('call_duration_p50_us', 0)):.3f} "
                f"| {float(item.get('call_duration_p95_us', 0)):.3f} "
                f"| {gap_text} "
                f"| {float(item.get('calls_below_100us_percent', 0)):.3f}% |"
            )

    lines.extend(
        [
            "",
            f"[Download `openfoam-vtune-trace.json` directly]({trace_url}), then drag "
            "it into [Perfetto](https://ui.perfetto.dev/) for the Chrome Trace view. "
            "The download is a plain JSON file; there is no ZIP to extract.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--trace-url", required=True)
    arguments = parser.parse_args()

    summary = json.loads(arguments.summary.read_text(encoding="utf-8"))
    markdown = render(summary, arguments.trace_url)
    with arguments.output.open("a", encoding="utf-8") as stream:
        stream.write(markdown)


if __name__ == "__main__":
    main()
