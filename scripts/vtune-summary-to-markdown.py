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

    timeline = "available" if summary.get("timeline_available") else "not available"
    lines = [
        "## Intel VTune summary",
        "",
        f"- Run label: `{escape_table(summary.get('run_label', 'unknown'))}`",
        f"- Source hotspots: {summary.get('source_hotspots', 0)}",
        f"- Exported hotspots: {summary.get('exported_hotspots', 0)}",
        f"- Timeline intervals: {summary.get('exported_time_bins', 0)}",
        f"- Sampled function intervals: {summary.get('exported_function_intervals', 0)}",
        f"- Profile CPU time: {float(summary.get('profile_cpu_time_sec', 0)):.6f} s",
        f"- Timeline: {timeline}",
        f"- Chrome trace: {summary.get('trace_bytes', 0)} bytes",
        "- Perfetto uses actual VTune elapsed-time interval start/end boundaries.",
        "- Function spans show samples attributed to each interval, not exact call boundaries.",
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
