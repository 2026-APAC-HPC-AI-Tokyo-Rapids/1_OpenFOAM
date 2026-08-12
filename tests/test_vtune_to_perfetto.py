from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "vtune-to-perfetto.py"
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


def test_reads_exact_task_boundaries_and_fragmentation_statistics() -> None:
    converter = load_converter()
    trace = converter.read_task_trace(FIXTURES / "openfoam-task-trace.csv")
    summaries = converter.task_summaries(trace)

    assert trace.process_elapsed_sec == 4.0
    assert trace.dropped_events == 0
    assert len(trace.intervals) == 5
    assert trace.intervals[0].start_sec == 0.1
    assert trace.intervals[0].end_sec == 0.3
    assert summaries[0]["function"] == "Foam::GaussSeidelSmoother::smooth"
    assert summaries[0]["calls"] == 3
    assert summaries[0]["inclusive_wall_time_sec"] == 0.7
    assert summaries[0]["call_duration_p50_us"] == 200_000
    assert summaries[0]["gap_p50_us"] == 800_000


def test_reads_solver_log_as_continuous_clock_intervals() -> None:
    converter = load_converter()
    iterations = converter.read_solver_iterations(FIXTURES / "openfoam-solver.log")
    intervals = converter.build_solver_intervals(iterations)

    assert len(iterations) == 3
    assert [(item.start_sec, item.end_sec) for item in intervals] == [
        (0.0, 1.0),
        (1.0, 2.0),
    ]
    assert intervals[0].completed_iterations == 2
    assert intervals[0].first_simulation_time == "1"
    assert intervals[0].last_simulation_time == "2"
    assert intervals[0].initial_residual_max == {"Ux": 0.1, "Uy": 0.2}
    assert intervals[0].linear_iterations_total == {"Ux": 3, "Uy": 3}
    assert intervals[0].continuity_global_max_abs == 2e-06


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
    (function_slices / "windows.csv").write_text(
        "file,start_sec,end_sec\n0000.csv,0.0,1.5\n0001.csv,1.5,4.0\n",
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
            "--solver-log",
            str(FIXTURES / "openfoam-solver.log"),
            "--task-trace",
            str(FIXTURES / "openfoam-task-trace.csv"),
            "--output",
            str(output),
            "--summary",
            str(summary),
            "--max-time-bins",
            "2",
            "--top-functions",
            "2",
            "--time-series-functions",
            "2",
            "--functions-per-window",
            "3",
            "--max-trace-bytes",
            "20000",
            "--max-task-events",
            "3",
            "--task-occupancy-bins",
            "2",
            "--run-label",
            "test-run",
        ],
        check=True,
    )

    trace = json.loads(output.read_text(encoding="utf-8"))
    metadata = json.loads(summary.read_text(encoding="utf-8"))

    assert trace["metadata"]["time_bins"] == 2
    assert trace["metadata"]["aggregate_hotspot_count"] == 2
    assert trace["metadata"]["timeline_bins_contiguous"] is True
    assert trace["metadata"]["sample_windows_contiguous"] is True
    assert trace["metadata"]["solver_intervals_contiguous"] is True
    assert trace["metadata"]["function_reports_are_complete"] is True
    assert trace["metadata"]["function_call_boundaries_available"] is True
    assert trace["metadata"]["source_exact_task_events"] == 5
    assert trace["metadata"]["exported_exact_task_events"] == 3
    assert trace["metadata"]["exact_task_events_are_complete"] is False
    assert trace["metadata"]["exact_task_recorder_dropped_events"] == 0
    assert trace["metadata"]["exact_task_source_is_complete"] is True
    assert "test-run" in trace["traceEvents"][0]["args"]["name"]
    timeline_events = [
        event for event in trace["traceEvents"] if event.get("cat") == "vtune-timeline"
    ]
    assert [(event["ts"], event["dur"]) for event in timeline_events] == [
        (0, 2_000_000),
        (2_000_000, 2_000_000),
    ]
    sample_windows = [
        event
        for event in trace["traceEvents"]
        if event.get("cat") == "vtune-sample-window"
    ]
    assert len(sample_windows) == 2
    assert sample_windows[0]["ts"] == 0
    assert sample_windows[0]["dur"] == 1_500_000
    assert sample_windows[0]["args"]["reported_function_count"] == 4
    assert (
        sample_windows[0]["args"]["hottest_sampled_functions"][0]["function"]
        == "PMPI_Allreduce"
    )
    solver_events = [
        event
        for event in trace["traceEvents"]
        if event.get("cat") == "openfoam-solver-clock"
    ]
    assert [(event["ts"], event["dur"]) for event in solver_events] == [
        (0, 1_000_000),
        (1_000_000, 1_000_000),
        (2_000_000, 2_000_000),
    ]
    function_counters = [
        event
        for event in trace["traceEvents"]
        if event.get("cat") == "vtune-function-time-series"
    ]
    assert len(function_counters) == 4
    assert function_counters[0]["ph"] == "C"
    assert function_counters[0]["args"]["sampled_cpu_time_sec"] == 11.36
    exact_function_events = [
        event
        for event in trace["traceEvents"]
        if event.get("cat") == "openfoam-exact-function"
    ]
    assert len(exact_function_events) == 3
    assert all(event["ph"] == "X" for event in exact_function_events)
    assert all(event["dur"] > 0 for event in exact_function_events)
    exact_occupancy = [
        event
        for event in trace["traceEvents"]
        if event.get("cat") == "openfoam-exact-occupancy"
    ]
    assert len(exact_occupancy) == 4
    assert metadata["exported_time_bins"] == 2
    assert metadata["exported_hotspots"] == 2
    assert metadata["exported_sample_windows"] == 2
    assert metadata["source_function_values"] == 8
    assert metadata["exported_time_series_functions"] == 2
    assert metadata["exported_functions_per_window"] == 3
    assert metadata["solver_iterations"] == 3
    assert metadata["solver_intervals"] == 2
    assert metadata["source_exact_task_events"] == 5
    assert metadata["exported_exact_task_events"] == 3
    assert len(metadata["exact_task_function_summaries"]) == 2
    assert metadata["function_reports_are_complete"] is True
    assert metadata["top_hotspots"][0]["profile_cpu_percent"] == 52.641
    assert metadata["trace_bytes"] < 20000


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


def test_workflow_retains_perfetto_artifact_on_github() -> None:
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")

    assert "openfoam-vtune-perfetto-${{ steps.v2_context.outputs.run_id }}" in workflow
    assert "retention-days: 90" in workflow
    assert 'startswith("openfoam-vtune-perfetto-") | not' in workflow


def test_exporter_writes_run_scoped_perfetto_artifact(tmp_path: Path) -> None:
    result_dir = tmp_path / "vtune.compute-node"
    result_dir.mkdir()
    run_dir = tmp_path / "run"
    (run_dir / "logs").mkdir(parents=True)
    (run_dir / "logs" / "solver.log").write_text(
        (FIXTURES / "openfoam-solver.log").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    provision = tmp_path / "provision"
    scripts = provision / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "vtune-to-perfetto.py").symlink_to(SCRIPT)
    python_dir = provision / "experiment-metrics" / ".venv" / "bin"
    python_dir.mkdir(parents=True)
    (python_dir / "python").symlink_to(sys.executable)
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
            "OPENFOAM_VTUNE_FUNCTION_BINS": "2",
            "PROVISION_DIR": str(provision),
            "RUN_DIR": str(run_dir),
            "RUN_LABEL": "rank-zero",
            "VTUNE_RESULT_DIR": str(result_dir),
            "VTUNE_TIMELINE_FIXTURE": str(FIXTURES / "vtune-timeline.csv"),
            "VTUNE_HOTSPOTS_FIXTURE": str(FIXTURES / "vtune-hotspots.csv"),
        }
    )

    subprocess.run(
        [str(ROOT / "scripts" / "export-vtune-perfetto.sh")],
        env=environment,
        check=True,
    )

    artifact = run_dir / "profile" / "raw" / "vtune-perfetto"
    assert (artifact / "summary.json").is_file()
    assert (artifact / "openfoam-vtune-perfetto.json").is_file()
    assert (artifact / "timeline.csv").is_file()
    assert (artifact / "hotspots.csv").is_file()
    metadata = json.loads((artifact / "summary.json").read_text(encoding="utf-8"))
    assert metadata["timeline_available"] is True
    assert metadata["source_sample_windows"] == 2
    assert metadata["source_function_values"] == 8
    assert metadata["solver_iterations"] == 3
    assert metadata["source_exact_task_events"] == 0
