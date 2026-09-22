from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from experiment_metrics import init_run
from experiment_metrics.pbs_scheduler import (
    capture_pbs_terminal,
    parse_pbs_accounting,
    submit_pbs_run,
)

REGISTRY = Path(__file__).parents[1] / "registry/openfoam-v2.toml"
PROTOCOL = (
    Path(__file__).parents[1] / "registry/openfoam-v2-protocol-gadi-scotch-1n-104r.toml"
)
ASPIRE2A_PROTOCOL = Path(__file__).parents[1] / "registry/openfoam-v2-protocol-aspire2a-scotch-2n-256r.toml"


def test_pbs_submission_and_terminal_are_bound(
    tmp_path: Path, identities: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=REGISTRY)
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "platforms/gadi").mkdir(parents=True)
    execution = provision / "platforms/gadi/run-openfoam.pbs"
    execution.write_bytes(b"#!/bin/sh\n")
    launcher = tmp_path / "launcher"
    launcher.write_bytes(b"fixture")
    launcher.chmod(0o755)
    monkeypatch.setenv(
        "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE", "/secret/runner-only.json"
    )

    outcome = submit_pbs_run(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=PROTOCOL,
        pbs_script_repository_path="platforms/gadi/run-openfoam.pbs",
        execution_script=execution,
        provision_dir=provision,
        qsub_path=launcher,
        execute=lambda argv: subprocess.CompletedProcess(
            argv, 0, b"176123456.gadi-pbs\n", b""
        ),
    )
    assert outcome.job_id == "176123456.gadi-pbs"
    request = json.loads(outcome.request_path.read_text())
    assert request["nodes"] == 1
    assert request["ranks"] == 104
    assert request["iterations"] == 40
    assert request["workload_id"] == "occDrivAerStaticMesh-65M"
    assert request["distribution"] == "OpenFOAM.com"
    assert request["release"] == "v2512"
    assert request["solver"] == "simpleFoam"
    assert "ncpus=104,mem=400GB,jobfs=100GB,storage=scratch/hb15" in request["argv"]
    exported = request["argv"][request["argv"].index("-v") + 1]
    assert "OPENFOAM_WORKLOAD_ID=occDrivAerStaticMesh-65M" in exported
    assert "OPENFOAM_DISTRIBUTION=OpenFOAM.com" in exported
    assert "OPENFOAM_RELEASE=v2512" in exported
    assert "OPENFOAM_SOLVER=simpleFoam" in exported
    assert "EXPERIMENT_METRICS_BIGQUERY_CONFIG" not in exported
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE" not in exported
    (run_dir / "control/job-entry.json").write_text(
        json.dumps({"scheduler_job_id": outcome.job_id}) + "\n"
    )
    raw = f"""Job Id: {outcome.job_id}
    job_state = F
    Exit_status = 0
    stime = Sat Aug 15 01:02:03 2026
    Resource_List.ncpus = 104
    resources_used.walltime = 00:03:04
    resources_used.cput = 05:18:09
    resources_used.mem = 81234567kb
""".encode()
    accounting_path = capture_pbs_terminal(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=PROTOCOL,
        job_id=outcome.job_id,
        qstat_path=launcher,
        execute=lambda argv: subprocess.CompletedProcess(argv, 0, raw, b""),
    )
    accounting = json.loads(accounting_path.read_text())
    terminal = json.loads((run_dir / "control/scheduler-terminal.json").read_text())
    assert terminal["argv"] == [str(launcher), "-fx", outcome.job_id]
    assert accounting["jid"] == outcome.job_id
    assert accounting["nnumu"]["value"] == 1
    assert accounting["elp"]["seconds"] == 184.0
    assert accounting["mmszu"]["bytes"] == 81234567 * 1024


def test_parse_pbs_accounting_rejects_wrong_cpu_count() -> None:
    raw = b"Job Id: 1.gadi-pbs\n    Resource_List.ncpus = 48\n"
    try:
        parse_pbs_accounting(
            raw, expected_job_id="1.gadi-pbs", expected_nodes=1, expected_ranks=104
        )
    except ValueError as error:
        assert "CPU allocation" in str(error)
    else:
        raise AssertionError("wrong PBS CPU count was accepted")


def test_pbs_submission_derives_profile_from_manifest(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(
        None, tmp_path, profile_identities, registry_path=REGISTRY, purpose="profile"
    )
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "platforms/gadi").mkdir(parents=True)
    execution = provision / "platforms/gadi/run-openfoam.pbs"
    execution.write_bytes(b"#!/bin/sh\n")
    launcher = tmp_path / "launcher"
    launcher.write_bytes(b"fixture")
    launcher.chmod(0o755)

    outcome = submit_pbs_run(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=PROTOCOL,
        pbs_script_repository_path="platforms/gadi/run-openfoam.pbs",
        execution_script=execution,
        provision_dir=provision,
        profile_rank=37,
        profile_analysis="hpc-performance",
        qsub_path=launcher,
        execute=lambda argv: subprocess.CompletedProcess(
            argv, 0, b"176123457.gadi-pbs\n", b""
        ),
    )

    request = json.loads(outcome.request_path.read_text())
    exported = request["argv"][request["argv"].index("-v") + 1]
    assert "OPENFOAM_RUN_PURPOSE=profile" in exported
    assert "OPENFOAM_VTUNE_RANK=37" in exported
    assert "OPENFOAM_VTUNE_ANALYSIS=hpc-performance" in exported
    assert request["profile_rank"] == 37
    assert request["profile_analysis"] == "hpc-performance"


def test_aspire2a_submission_uses_exclusive_full_nodes(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(None, tmp_path, profile_identities, registry_path=REGISTRY, purpose="profile")
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "platforms/aspire2a").mkdir(parents=True)
    execution = provision / "platforms/aspire2a/run-openfoam.pbs"
    execution.write_bytes(b"#!/bin/sh\n")
    launcher = tmp_path / "launcher"
    launcher.write_bytes(b"fixture")
    launcher.chmod(0o755)

    outcome = submit_pbs_run(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=ASPIRE2A_PROTOCOL,
        pbs_script_repository_path="platforms/aspire2a/run-openfoam.pbs",
        execution_script=execution,
        provision_dir=provision,
        profile_tool="uprof",
        qsub_path=launcher,
        execute=lambda argv: subprocess.CompletedProcess(argv, 0, b"24499999.pbs\n", b""),
    )

    request = json.loads(outcome.request_path.read_text())
    argv = request["argv"]
    assert argv[argv.index("-P") + 1] == "59000014"
    assert argv[argv.index("-q") + 1] == "normal"
    assert "select=2:ncpus=128:mpiprocs=128:ompthreads=1:mem=400gb" in argv
    assert "place=excl" in argv
    exported = argv[argv.index("-v") + 1]
    assert "OPENFOAM_PROFILE_TOOL=uprof" in exported
    assert "OPENFOAM_VTUNE" not in exported
    assert request["profile_tool"] == "uprof"


def test_aspire2a_submission_exports_uprof_assessment(tmp_path: Path, identities: dict[str, object]) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(None, tmp_path, profile_identities, registry_path=REGISTRY, purpose="profile")
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "platforms/aspire2a").mkdir(parents=True)
    execution = provision / "platforms/aspire2a/run-openfoam.pbs"
    execution.write_bytes(b"#!/bin/sh\n")
    launcher = tmp_path / "launcher"
    launcher.write_bytes(b"fixture")
    launcher.chmod(0o755)

    outcome = submit_pbs_run(manifest_path=manifest, runtime_dir=run_dir, protocol_path=ASPIRE2A_PROTOCOL, pbs_script_repository_path="platforms/aspire2a/run-openfoam.pbs", execution_script=execution, provision_dir=provision, profile_tool="uprof", profile_analysis="assess", qsub_path=launcher, execute=lambda argv: subprocess.CompletedProcess(argv, 0, b"24500000.pbs\n", b""))

    exported = outcome.request_path.read_text()
    assert "OPENFOAM_UPROF_ANALYSIS=assess" in exported
    assert "OPENFOAM_VTUNE_ANALYSIS" not in exported


def test_aspire2a_submission_accepts_craypat_mpi(tmp_path: Path, identities: dict[str, object]) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(None, tmp_path, profile_identities, registry_path=REGISTRY, purpose="profile")
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    (provision / "platforms/aspire2a").mkdir(parents=True)
    execution = provision / "platforms/aspire2a/run-openfoam.pbs"
    execution.write_bytes(b"#!/bin/sh\n")
    launcher = tmp_path / "launcher"
    launcher.write_bytes(b"fixture")
    launcher.chmod(0o755)

    outcome = submit_pbs_run(manifest_path=manifest, runtime_dir=run_dir, protocol_path=ASPIRE2A_PROTOCOL, pbs_script_repository_path="platforms/aspire2a/run-openfoam.pbs", execution_script=execution, provision_dir=provision, profile_tool="craypat", profile_analysis="mpi", qsub_path=launcher, execute=lambda argv: subprocess.CompletedProcess(argv, 0, b"24500001.pbs\n", b""))

    exported = outcome.request_path.read_text()
    assert "OPENFOAM_PROFILE_TOOL=craypat" in exported
    assert "OPENFOAM_UPROF_ANALYSIS" not in exported
    assert "OPENFOAM_VTUNE_ANALYSIS" not in exported
