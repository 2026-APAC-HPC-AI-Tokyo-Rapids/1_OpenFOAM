from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from experiment_metrics import init_run
from experiment_metrics.scheduler import (
    capture_scheduler_terminal,
    parse_scheduler_accounting,
    submit_run,
)
from experiment_metrics.supervisor import (
    finish_supervisor,
    mark_pipeline,
    start_supervisor,
)

REGISTRY = Path(__file__).parents[1] / "registry/openfoam-v2.toml"
PROTOCOL = (
    Path(__file__).parents[1] / "registry/openfoam-v2-protocol-scotch-1n-120r.toml"
)


def test_submission_and_terminal_accounting_are_bound_by_job_id(
    tmp_path: Path, identities: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=REGISTRY)
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "scripts").mkdir(parents=True)
    execution = provision / "scripts/run-openfoam.pjm"
    execution.write_bytes(b"#!/bin/sh\n")
    multiplexer = tmp_path / "bin/.cltkexec"
    multiplexer.parent.mkdir()
    multiplexer.write_bytes(b"fixture")
    pjsub = multiplexer.with_name("pjsub")
    pjstat = multiplexer.with_name("pjstat")
    pjsub.symlink_to(multiplexer.name)
    pjstat.symlink_to(multiplexer.name)
    monkeypatch.setenv(
        "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE", "/secret/runner-only.json"
    )

    submitted = submit_run(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=PROTOCOL,
        pjm_script_repository_path="scripts/run-openfoam.pjm",
        execution_script=execution,
        provision_dir=provision,
        pjsub_path=pjsub,
        execute=lambda argv: subprocess.CompletedProcess(
            argv, 0, b"Job 12345 submitted.\n", b""
        ),
    )
    assert submitted.job_id == "12345"
    request = json.loads(submitted.request_path.read_text())
    assert request["nodes"] == 1
    assert request["ranks"] == 120
    assert request["iterations"] == 40
    assert request["workload_id"] == "occDrivAerStaticMesh-65M"
    assert request["distribution"] == "OpenFOAM.com"
    assert request["release"] == "v2512"
    assert request["solver"] == "simpleFoam"
    assert request["profile_rank"] == 0
    assert request["profile_analysis"] == "hotspots"
    assert request["argv"][0] == str(pjsub)
    exported = request["argv"][request["argv"].index("-x") + 1]
    assert "OPENFOAM_MPI_PROCS=120" in exported
    assert "OPENFOAM_RUN_PURPOSE=bench" in exported
    assert "OPENFOAM_WORKLOAD_ID=occDrivAerStaticMesh-65M" in exported
    assert "OPENFOAM_DISTRIBUTION=OpenFOAM.com" in exported
    assert "OPENFOAM_RELEASE=v2512" in exported
    assert "OPENFOAM_SOLVER=simpleFoam" in exported
    assert "OPENFOAM_VTUNE_RANK=0" in exported
    assert "OPENFOAM_VTUNE_ANALYSIS=hotspots" in exported
    assert "EXPERIMENT_METRICS_BIGQUERY_CONFIG" not in exported
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE" not in exported

    (run_dir / "control/job-entry.json").write_text(
        json.dumps({"scheduler_job_id": "12345"}) + "\n"
    )
    raw = b"12345\tEND\t2026-08-10T00:00:00\t1.5\t0\t1\t120\t1\t4096\t2\t3\n"
    accounting_path = capture_scheduler_terminal(
        manifest_path=manifest,
        runtime_dir=run_dir,
        job_id="12345",
        pjstat_path=pjstat,
        execute=lambda argv: subprocess.CompletedProcess(argv, 0, raw, b""),
    )
    accounting = json.loads(accounting_path.read_text())
    assert accounting["jid"] == "12345"
    assert accounting["nnumu"] == {"lexeme": "1", "value": 1}
    terminal = json.loads((run_dir / "control/scheduler-terminal.json").read_text())
    assert terminal["argv"][0] == str(pjstat)


def test_submission_derives_vtune_profile_purpose_from_manifest(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(
        None, tmp_path, profile_identities, registry_path=REGISTRY, purpose="profile"
    )
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "scripts").mkdir(parents=True)
    execution = provision / "scripts/run-openfoam.pjm"
    execution.write_bytes(b"#!/bin/sh\n")
    pjsub = tmp_path / "pjsub"
    pjsub.write_bytes(b"fixture")

    submitted = submit_run(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=PROTOCOL,
        pjm_script_repository_path="scripts/run-openfoam.pjm",
        execution_script=execution,
        provision_dir=provision,
        profile_rank=37,
        profile_analysis="hpc-performance",
        pjsub_path=pjsub,
        execute=lambda argv: subprocess.CompletedProcess(
            argv, 0, b"Job 23456 submitted.\n", b""
        ),
    )

    assert submitted.job_id == "23456"
    request = json.loads(submitted.request_path.read_text())
    exported = request["argv"][request["argv"].index("-x") + 1]
    assert "OPENFOAM_RUN_PURPOSE=profile" in exported
    assert "OPENFOAM_VTUNE_RANK=37" in exported
    assert "OPENFOAM_VTUNE_ANALYSIS=hpc-performance" in exported
    assert request["profile_rank"] == 37
    assert request["profile_analysis"] == "hpc-performance"


def test_submission_accepts_memory_access_profile(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(
        None, tmp_path, profile_identities, registry_path=REGISTRY, purpose="profile"
    )
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "scripts").mkdir(parents=True)
    execution = provision / "scripts/run-openfoam.pjm"
    execution.write_bytes(b"#!/bin/sh\n")
    pjsub = tmp_path / "pjsub"
    pjsub.write_bytes(b"fixture")

    submitted = submit_run(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=PROTOCOL,
        pjm_script_repository_path="scripts/run-openfoam.pjm",
        execution_script=execution,
        provision_dir=provision,
        profile_rank=3,
        profile_analysis="memory-access",
        pjsub_path=pjsub,
        execute=lambda argv: subprocess.CompletedProcess(
            argv, 0, b"Job 34567 submitted.\n", b""
        ),
    )

    request = json.loads(submitted.request_path.read_text())
    exported = request["argv"][request["argv"].index("-x") + 1]
    assert "OPENFOAM_VTUNE_ANALYSIS=memory-access" in exported
    assert request["profile_analysis"] == "memory-access"


def test_submission_rejects_invalid_profile_rank(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=REGISTRY)
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "scripts").mkdir(parents=True)
    execution = provision / "scripts/run-openfoam.pjm"
    execution.write_bytes(b"#!/bin/sh\n")

    with pytest.raises(ValueError, match="nonzero profile rank"):
        submit_run(
            manifest_path=manifest,
            runtime_dir=run_dir,
            protocol_path=PROTOCOL,
            pjm_script_repository_path="scripts/run-openfoam.pjm",
            execution_script=execution,
            provision_dir=provision,
            profile_rank=1,
        )


def test_parse_scheduler_accounting_accepts_genkai_history_data() -> None:
    raw = (
        b"H\tJOB ID\tSTATE\tJOB START DATE\tELAPSE TIME (USE)\tEXIT CODE\t"
        b"SIGNAL NO\tPJM CODE\tNODE NUM (USE)\tMAX MEMORY SIZE (USE)\t"
        b"USER CPU TIME (USE)\tSYSTEM CPU TIME (USE)\tMAX MEMORY SIZE (USE)\t"
        b"USER CPU TIME (USE)\tSYSTEM CPU TIME (USE)\n"
        b"\t6438276\tEXT\t2026/08/10 22:07:30\t00:25:03 (1503)\t-\t24\t11\t1\t"
        b"81876.1 MiB (85853274112)\t24729340 ms\t627660 ms\t"
        b"81876.1 MiB (85853274112)\t24729340 ms\t627660 ms\n"
    )

    accounting = parse_scheduler_accounting(raw, expected_job_id="6438276")

    assert accounting["st"] == "EXT"
    assert accounting["elp"] == {"lexeme": "00:25:03 (1503)", "seconds": 1503.0}
    assert accounting["ec"] == {"lexeme": "-", "value": None}
    assert accounting["sn"] == {"lexeme": "24", "value": 24}
    assert accounting["pc"] == {"lexeme": "11", "value": 11}
    assert accounting["mmszu"] == {
        "lexeme": "81876.1 MiB (85853274112)",
        "bytes": 85853274112,
    }
    assert accounting["uctmut"] == {
        "lexeme": "24729340 ms",
        "seconds": 24729.34,
    }
    assert accounting["sctmut"] == {"lexeme": "627660 ms", "seconds": 627.66}
    assert accounting["node_usage"] == [
        {
            "node_ordinal": 0,
            "mmszu": {
                "lexeme": "81876.1 MiB (85853274112)",
                "bytes": 85853274112,
            },
            "uctmut": {"lexeme": "24729340 ms", "seconds": 24729.34},
            "sctmut": {"lexeme": "627660 ms", "seconds": 627.66},
        }
    ]


def test_parse_scheduler_accounting_accepts_per_node_genkai_values() -> None:
    raw = (
        b"\t6438276\tEND\t2026/08/10 22:07:30\t1\t0\t0\t0\t2\t"
        b"8192\t40 ms\t6 ms\t4096\t21 ms\t2 ms\t4000\t19 ms\t4 ms\n"
    )

    accounting = parse_scheduler_accounting(raw, expected_job_id="6438276")

    assert accounting["nnumu"]["value"] == 2
    assert accounting["node_usage"] == [
        {
            "node_ordinal": 0,
            "mmszu": {"lexeme": "4096", "bytes": 4096},
            "uctmut": {"lexeme": "21 ms", "seconds": 0.021},
            "sctmut": {"lexeme": "2 ms", "seconds": 0.002},
        },
        {
            "node_ordinal": 1,
            "mmszu": {"lexeme": "4000", "bytes": 4000},
            "uctmut": {"lexeme": "19 ms", "seconds": 0.019},
            "sctmut": {"lexeme": "4 ms", "seconds": 0.004},
        },
    ]


def test_parse_scheduler_accounting_rejects_wrong_per_node_column_count() -> None:
    raw = b"\t6438276\tEND\tdate\t1\t0\t0\t0\t2\t8192\t40\t6\t4096\t21\t2\n"

    with pytest.raises(ValueError, match="invalid per-node columns"):
        parse_scheduler_accounting(raw, expected_job_id="6438276")


def test_supervisor_captures_entry_lifecycle_and_pipeline(
    tmp_path: Path,
    identities: dict[str, object],
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=REGISTRY)
    run_dir = manifest.parents[1]
    state = run_dir / "domain/supervisor-state.json"
    start_supervisor(manifest, state, job_id="9876")
    mark_pipeline(state, "start")
    mark_pipeline(state, "finish")
    fragment = finish_supervisor(manifest, state, exit_code=0)

    assert not state.exists()
    assert (run_dir / "source/env/job-entry.snapshot").is_file()
    rows = [json.loads(line) for line in fragment.read_text().splitlines()]
    values = {row["key"]: row["value"] for row in rows}
    assert values["scheduler.job_entry_job_id"] == "9876"
    assert values["run.exit_code"] == "0"
    assert "perf.pipeline.wall_time_sec" in values
