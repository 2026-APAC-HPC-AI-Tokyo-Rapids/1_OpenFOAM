from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from experiment_metrics import init_run
from experiment_metrics.scheduler import capture_scheduler_terminal, submit_run
from experiment_metrics.supervisor import (
    finish_supervisor,
    mark_pipeline,
    start_supervisor,
)

REGISTRY = Path(__file__).parents[1] / "registry/openfoam-v2.toml"
PROTOCOL = Path(__file__).parents[1] / "registry/openfoam-v2-protocol.toml"


def test_submission_and_terminal_accounting_are_bound_by_job_id(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=REGISTRY)
    run_dir = manifest.parents[1]
    repository = tmp_path / "repository"
    provision = tmp_path / "provision"
    (repository / "scripts").mkdir(parents=True)
    (provision / "scripts").mkdir(parents=True)
    source = repository / "scripts/run-openfoam.pjm"
    execution = provision / "scripts/run-openfoam.pjm"
    source.write_bytes(b"#!/bin/sh\n")
    execution.write_bytes(source.read_bytes())
    multiplexer = tmp_path / "bin/.cltkexec"
    multiplexer.parent.mkdir()
    multiplexer.write_bytes(b"fixture")
    pjsub = multiplexer.with_name("pjsub")
    pjstat = multiplexer.with_name("pjstat")
    pjsub.symlink_to(multiplexer.name)
    pjstat.symlink_to(multiplexer.name)

    submitted = submit_run(
        manifest_path=manifest,
        runtime_dir=run_dir,
        registry_path=REGISTRY,
        protocol_path=PROTOCOL,
        repository_root=repository,
        pjm_script_repository_path="scripts/run-openfoam.pjm",
        execution_script=execution,
        provision_dir=provision,
        profile_mode="direct",
        pjsub_path=pjsub,
        execute=lambda argv: subprocess.CompletedProcess(
            argv, 0, b"Job 12345 submitted.\n", b""
        ),
    )
    assert submitted.job_id == "12345"
    request = json.loads(submitted.request_path.read_text())
    assert request["nodes"] == 1
    assert request["ranks"] == 120
    assert request["argv"][0] == str(pjsub)
    assert "OPENFOAM_RANKS=120" in next(
        item for item in request["argv"] if item.startswith("OPENFOAM_NODES=")
    )

    (run_dir / "control/job-entry.json").write_text(
        json.dumps({"pjm_job_id": "12345"}) + "\n"
    )
    raw = b"12345\tEND\t2026-08-10T00:00:00\t1.5\t0\t1\t120\t1\t4096\t2\t3\n"
    accounting_path = capture_scheduler_terminal(
        manifest_path=manifest,
        runtime_dir=run_dir,
        registry_path=REGISTRY,
        job_id="12345",
        pjstat_path=pjstat,
        execute=lambda argv: subprocess.CompletedProcess(argv, 0, raw, b""),
    )
    accounting = json.loads(accounting_path.read_text())
    assert accounting["jid"] == "12345"
    assert accounting["nnumu"] == {"lexeme": "1", "value": 1}
    terminal = json.loads(
        (run_dir / "control/scheduler-terminal.json").read_text()
    )
    assert terminal["argv"][0] == str(pjstat)


def test_supervisor_captures_entry_lifecycle_and_pipeline(
    tmp_path: Path,
    identities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=REGISTRY)
    run_dir = manifest.parents[1]
    state = run_dir / "domain/supervisor-state.json"
    monkeypatch.setenv("PJM_JOBID", "9876")

    start_supervisor(manifest, state)
    mark_pipeline(state, "start")
    mark_pipeline(state, "finish")
    fragment = finish_supervisor(manifest, state, REGISTRY, exit_code=0)

    assert not state.exists()
    assert (run_dir / "source/env/job-entry.snapshot").is_file()
    rows = [json.loads(line) for line in fragment.read_text().splitlines()]
    values = {row["key"]: row["value"] for row in rows}
    assert values["scheduler.job_entry_job_id"] == "9876"
    assert values["run.exit_code"] == "0"
    assert "perf.pipeline.wall_time_sec" in values
