from __future__ import annotations

import json
import sys
from pathlib import Path

from experiment_metrics import Recorder, init_run, run_stage
from experiment_metrics.cli import main


def test_stage_records_exact_argv_cwd_termination_and_wall_time(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    argv = [sys.executable, "-c", "raise SystemExit(3)"]
    with Recorder.open(
        manifest_path, registry_path, "stage.runner", runtime_dir, fragment_id="solver"
    ) as recorder:
        termination = run_stage(
            "solver", argv, cwd=tmp_path, stderr_mode="separate", recorder=recorder
        )

    assert termination.kind == "exit"
    assert termination.code == 3
    rows = [
        json.loads(line)
        for line in (runtime_dir / "domain/fragments/stage.runner--solver.jsonl")
        .read_text()
        .splitlines()
    ]
    launch = next(row for row in rows if row["key"].endswith(".launch"))
    assert json.loads(launch["value"])["argv"] == argv
    assert json.loads(launch["value"])["cwd"] == str(tmp_path)
    assert any(row["key"].endswith(".wall_time_sec") for row in rows)


def test_stage_spawn_error_and_cli_signal_exit_precedence(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    with Recorder.open(
        manifest_path, registry_path, "stage.runner", runtime_dir, fragment_id="missing"
    ) as recorder:
        termination = run_stage(
            "missing",
            [str(tmp_path / "does-not-exist")],
            cwd=tmp_path,
            stderr_mode="stdout",
            recorder=recorder,
        )
    assert termination.kind == "spawn_error"

    result = main(
        [
            "run-stage",
            "--manifest",
            str(manifest_path),
            "--runtime-dir",
            str(runtime_dir),
            "--registry",
            str(registry_path),
            "--producer",
            "stage.runner",
            "--stage",
            "signal",
            "--cwd",
            str(tmp_path),
            "--fragment-id",
            "signal",
            "--",
            sys.executable,
            "-c",
            "import os, signal; os.kill(os.getpid(), signal.SIGTERM)",
        ]
    )
    assert result == 143


def test_cli_uses_distinct_stage_fragment_instances(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    common = [
        "--manifest",
        str(manifest_path),
        "--runtime-dir",
        str(runtime_dir),
        "--registry",
        str(registry_path),
        "--producer",
        "stage.runner",
        "--cwd",
        str(tmp_path),
        "--",
        sys.executable,
        "-c",
        "raise SystemExit(0)",
    ]

    assert main(["run-stage", "--stage", "first", *common]) == 0
    assert main(["run-stage", "--stage", "second", *common]) == 0
    fragments = sorted((runtime_dir / "domain/fragments").glob("stage.runner--*.jsonl"))
    assert [path.name for path in fragments] == [
        "stage.runner--stage.first.jsonl",
        "stage.runner--stage.second.jsonl",
    ]


def test_stage_captures_combined_stdout_without_a_shell_pipeline(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    output = runtime_dir / "logs/combined.log"
    with Recorder.open(
        manifest_path, registry_path, "stage.runner", runtime_dir, fragment_id="capture"
    ) as recorder:
        termination = run_stage(
            "capture",
            [
                sys.executable,
                "-c",
                "import sys; print('out', flush=True); print('err', file=sys.stderr)",
            ],
            cwd=tmp_path,
            stderr_mode="stdout",
            stdout_path=output,
            recorder=recorder,
        )

    assert termination.code == 0
    assert output.read_text().splitlines() == ["out", "err"]
