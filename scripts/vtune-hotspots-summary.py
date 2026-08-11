#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


def _number(value: str) -> float | None:
    text = value.strip().replace(",", "")
    if not text:
        return None
    multipliers = {
        "ns": 1e-9,
        "us": 1e-6,
        "ms": 1e-3,
        "s": 1.0,
    }
    multiplier = 1.0
    for suffix, candidate in multipliers.items():
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            multiplier = candidate
            break
    try:
        number = float(text) * multiplier
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def read_hotspots(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if "Function" in line), None
    )
    if header_index is None:
        raise ValueError(f"{path}: Function header was not found")
    rows = csv.DictReader(lines[header_index:])
    hotspots: list[dict[str, object]] = []
    for row in rows:
        function = (row.get("Function") or "").strip()
        module = (row.get("Module") or "").strip()
        cpu_key = next((key for key in row if key and "CPU Time" in key), None)
        cpu_time = _number(row.get(cpu_key, "") if cpu_key else "")
        if function and cpu_time is not None:
            hotspots.append(
                {
                    "function": function,
                    "module": module,
                    "cpu_time_sec": cpu_time,
                }
            )
    if not hotspots:
        raise ValueError(f"{path}: no VTune hotspots were parsed")
    return sorted(hotspots, key=lambda item: item["cpu_time_sec"], reverse=True)


def _escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render_markdown(summary: dict[str, object]) -> str:
    hotspots = summary["top_hotspots"]
    assert isinstance(hotspots, list)
    lines = [
        "## Intel VTune hotspots",
        "",
        f"- Profiled MPI rank: {summary['profiled_rank']}",
        f"- Reported functions: {summary['source_hotspots']}",
        f"- Total reported CPU time: {summary['reported_cpu_time_sec']:.6f} s",
        "",
        "| Rank | Function | Module | CPU time (s) | Reported CPU time |",
        "| ---: | --- | --- | ---: | ---: |",
    ]
    for rank, item in enumerate(hotspots, 1):
        assert isinstance(item, dict)
        lines.append(
            f"| {rank} | `{_escape(item['function'])}` | `{_escape(item['module'])}` "
            f"| {item['cpu_time_sec']:.6f} | {item['reported_cpu_percent']:.3f}% |"
        )
    lines.extend(
        [
            "",
            (
                "The table is generated from the VTune hotspots report for one "
                "representative MPI rank. Full VTune results remain on Genkai."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def build_summary(
    hotspots: list[dict[str, object]], *, profiled_rank: int, limit: int
) -> dict[str, object]:
    total = sum(float(item["cpu_time_sec"]) for item in hotspots)
    top = []
    for item in hotspots[:limit]:
        cpu_time = float(item["cpu_time_sec"])
        top.append(
            {
                **item,
                "reported_cpu_percent": 100.0 * cpu_time / total if total else 0.0,
            }
        )
    return {
        "schema_version": "openfoam-vtune-hotspots-summary/v1",
        "profiled_rank": profiled_rank,
        "source_hotspots": len(hotspots),
        "exported_hotspots": len(top),
        "reported_cpu_time_sec": total,
        "top_hotspots": top,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hotspots", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--profiled-rank", type=int, default=0)
    parser.add_argument("--limit", type=int, default=30)
    arguments = parser.parse_args()
    if arguments.profiled_rank < 0 or arguments.limit <= 0:
        parser.error("profiled rank must be non-negative and limit must be positive")

    summary = build_summary(
        read_hotspots(arguments.hotspots),
        profiled_rank=arguments.profiled_rank,
        limit=arguments.limit,
    )
    arguments.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    arguments.markdown.write_text(render_markdown(summary), encoding="utf-8")


if __name__ == "__main__":
    main()
