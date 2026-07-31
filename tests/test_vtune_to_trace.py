from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "vtune-to-trace.py"
MARKDOWN_SCRIPT = ROOT / "scripts" / "vtune-summary-to-markdown.py"
FIXTURES = ROOT / "tests" / "fixtures"


def load_converter():
    spec = importlib.util.spec_from_file_location("vtune_to_trace", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_reads_vtune_reports() -> None:
    converter = load_converter()
    timeline = converter.read_timeline(FIXTURES / "vtune-timeline.csv")
    hotspots = converter.read_hotspots(FIXTURES / "vtune-hotspots.csv")

    assert len(timeline) == 4
    assert timeline[-1].end_sec == 4.0
    assert hotspots[0].function == "PMPI_Allreduce"
    assert hotspots[0].cpu_time_sec == 11.36


def test_cli_writes_bounded_json_trace(tmp_path: Path) -> None:
    output = tmp_path / "trace.json"
    summary = tmp_path / "summary.json"
    function_slices = tmp_path / "function-slices"
    function_slices.mkdir()
    for index in range(2):
        (function_slices / f"{index:04d}.csv").write_text(
            (FIXTURES / "vtune-hotspots.csv").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--timeline",
            str(FIXTURES / "vtune-timeline.csv"),
            "--hotspots",
            str(FIXTURES / "vtune-hotspots.csv"),
            "--function-slices-dir",
            str(function_slices),
            "--output",
            str(output),
            "--summary",
            str(summary),
            "--max-time-bins",
            "2",
            "--top-functions",
            "2",
            "--max-trace-bytes",
            "5000",
            "--run-label",
            "test-run",
        ],
        check=True,
    )

    trace = json.loads(output.read_text(encoding="utf-8"))
    metadata = json.loads(summary.read_text(encoding="utf-8"))

    assert trace["metadata"]["time_bins"] == 2
    assert trace["metadata"]["aggregate_hotspot_count"] == 2
    assert "test-run" in trace["traceEvents"][0]["args"]["name"]
    timeline_events = [
        event
        for event in trace["traceEvents"]
        if event.get("cat") == "vtune-timeline"
    ]
    assert [(event["ts"], event["dur"]) for event in timeline_events] == [
        (0, 2_000_000),
        (2_000_000, 2_000_000),
    ]
    function_events = [
        event
        for event in trace["traceEvents"]
        if str(event.get("cat", "")).startswith("vtune-sampled-function")
    ]
    assert len(function_events) == 8
    assert function_events[0]["name"] == "PMPI_Allreduce"
    assert function_events[0]["args"]["category"] == "MPI"
    assert function_events[0]["args"]["interval_start_sec"] == 0.0
    assert function_events[0]["args"]["interval_end_sec"] == 2.0
    assert metadata["exported_time_bins"] == 2
    assert metadata["exported_hotspots"] == 2
    assert metadata["exported_function_intervals"] == 8
    assert metadata["top_hotspots"][0]["profile_cpu_percent"] == 52.641
    assert metadata["trace_bytes"] < 5000


def test_cli_accepts_empty_timeline_report(tmp_path: Path) -> None:
    timeline = tmp_path / "timeline.csv"
    timeline.touch()
    output = tmp_path / "trace.json"
    summary = tmp_path / "summary.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--timeline",
            str(timeline),
            "--hotspots",
            str(FIXTURES / "vtune-hotspots.csv"),
            "--output",
            str(output),
            "--summary",
            str(summary),
            "--top-functions",
            "2",
        ],
        check=True,
    )

    trace = json.loads(output.read_text(encoding="utf-8"))
    metadata = json.loads(summary.read_text(encoding="utf-8"))

    assert trace["metadata"]["time_bins"] == 0
    assert trace["metadata"]["aggregate_hotspot_count"] == 2
    assert not [event for event in trace["traceEvents"] if event.get("ph") == "X"]
    assert metadata["timeline_available"] is False
    assert metadata["elapsed_sec"] is None


def test_renders_actions_summary(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    output = tmp_path / "step-summary.md"
    summary.write_text(
        json.dumps(
            {
                "run_label": "rank-zero",
                "source_hotspots": 601,
                "exported_hotspots": 1,
                "exported_time_bins": 300,
                "exported_function_intervals": 200,
                "trace_bytes": 2231,
                "profile_cpu_time_sec": 20.0,
                "timeline_available": False,
                "top_hotspots": [
                    {
                        "function": "Foam::foo|bar",
                        "module": "libOpenFOAM.so",
                        "category": "OpenFOAM",
                        "cpu_time_sec": 4.379697,
                        "profile_cpu_percent": 21.898,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(MARKDOWN_SCRIPT),
            "--summary",
            str(summary),
            "--output",
            str(output),
            "--trace-url",
            "https://github.example/releases/download/vtune-latest/openfoam-vtune-trace.json",
        ],
        check=True,
    )

    markdown = output.read_text(encoding="utf-8")
    assert "## Intel VTune summary" in markdown
    assert "Foam::foo\\|bar" in markdown
    assert "OpenFOAM" in markdown
    assert "21.898%" in markdown
    assert "4.379697" in markdown
    assert "Timeline intervals: 300" in markdown
    assert "Sampled function intervals: 200" in markdown
    assert (
        "https://github.example/releases/download/vtune-latest/"
        "openfoam-vtune-trace.json"
    ) in markdown
    assert "there is no ZIP to extract" in markdown
    assert "https://ui.perfetto.dev/" in markdown


def test_exporter_derives_profile_result_directory(tmp_path: Path) -> None:
    profile_root = tmp_path / "profiles"
    result_dir = profile_root / "rank-zero"
    (result_dir / "vtune.compute-node").mkdir(parents=True)
    provision = tmp_path / "provision"
    scripts = provision / "scripts"
    scripts.mkdir(parents=True)
    (provision / "logs").mkdir()
    (scripts / "vtune-to-trace.py").symlink_to(SCRIPT)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_vtune = fake_bin / "vtune"
    fake_vtune.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
report=
while [[ $# -gt 0 ]]; do
  case "$1" in
    -report) report=$2; shift 2 ;;
    *) shift ;;
  esac
done
case "$report" in
  timeline) cat "$VTUNE_TIMELINE_FIXTURE" ;;
  hotspots) cat "$VTUNE_HOTSPOTS_FIXTURE" ;;
  *) exit 2 ;;
esac
""",
        encoding="utf-8",
    )
    fake_vtune.chmod(0o755)
    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fake_bin}:{environment['PATH']}",
            "OPENFOAM_PROFILE_DIR": str(profile_root),
            "OPENFOAM_PROFILE_LABEL": "rank-zero",
            "OPENFOAM_PYTHON": sys.executable,
            "OPENFOAM_VTUNE_FUNCTION_BINS": "2",
            "PROVISION_DIR": str(provision),
            "VTUNE_TIMELINE_FIXTURE": str(FIXTURES / "vtune-timeline.csv"),
            "VTUNE_HOTSPOTS_FIXTURE": str(FIXTURES / "vtune-hotspots.csv"),
        }
    )

    subprocess.run(
        [str(ROOT / "scripts" / "export-vtune-summary.sh")],
        env=environment,
        check=True,
    )

    assert (result_dir / "browser-summary" / "summary.json").is_file()
    assert (provision / "browser-summary" / "summary.json").is_file()
    assert (provision / "browser-summary" / "openfoam-vtune-trace.json").is_file()
    assert not (provision / "logs" / "summary.json").exists()
    assert not (provision / "logs" / "openfoam-vtune-trace.json").exists()
    assert not (provision / "logs" / "timeline.csv").exists()
    assert not (provision / "logs" / "hotspots.csv").exists()
    metadata = json.loads(
        (provision / "browser-summary" / "summary.json").read_text(encoding="utf-8")
    )
    assert metadata["timeline_available"] is True
    assert metadata["source_function_intervals"] == 8
