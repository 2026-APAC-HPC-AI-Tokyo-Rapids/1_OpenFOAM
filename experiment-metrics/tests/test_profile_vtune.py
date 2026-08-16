from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from experiment_metrics.manifest import init_run
from experiment_metrics.profile_vtune import parse_hotspots, record_vtune_hotspots

ROOT = Path(__file__).parents[2]
HEADER = (
    "Function,Module,CPU Time,CPU Time:Effective Time,CPU Time:Spin Time,"
    "CPU Time:Spin Time:MPI Busy Wait Time,CPU Time:Spin Time:Other,"
    "CPU Time:Overhead Time,CPU Time:Overhead Time:Other\n"
)
HARDWARE_HEADER = (
    "Function,Module,CPU Time,CPU Time:Effective Time,CPU Time:Spin Time,"
    "CPU Time:Overhead Time\n"
)


def _row(function: str, module: str, cpu_time: str) -> str:
    return f"{function},{module},{cpu_time},{cpu_time},0.0,0.0,0.0,0.0,0.0\n"


def _profile_run(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> Path:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    return init_run(
        None,
        tmp_path,
        profile_identities,
        purpose="profile",
        registry_path=registry_path,
    )


def test_parser_preserves_exact_lexemes_and_orders_hotspots() -> None:
    hotspots = parse_hotspots(
        "metadata\n" + HEADER + _row("slow", "lib.so", "0.120")
        + _row("fast", "lib.so", "1.5")
    )

    assert [item.function for item in hotspots] == ["fast", "slow"]
    assert hotspots[1].cpu_time_lexeme == "0.120"
    assert str(hotspots[1].cpu_time_sec) == "0.120"


@pytest.mark.parametrize(
    "source",
    [
        "Function,Module,CPU Time\nf,m,1\n",
        HEADER + "f,m,1,1,0,0,0,0\n",
        HEADER + _row("", "m", "1"),
        HEADER + "f,m,1,1,not-a-number,0,0,0,0\n",
    ],
)
def test_parser_rejects_lossy_or_ambiguous_reports(source: str) -> None:
    with pytest.raises(ValueError):
        parse_hotspots(source)


def test_parser_preserves_duplicate_function_module_rows() -> None:
    hotspots = parse_hotspots(
        HEADER + _row("f", "m", "1") + _row("f", "m", "2")
    )

    assert [item.cpu_time_lexeme for item in hotspots] == ["2", "1"]
    assert [item.report_row for item in hotspots] == [3, 2]


def test_parser_accepts_hardware_sampling_hotspot_columns() -> None:
    hotspots = parse_hotspots(HARDWARE_HEADER + "f,m,1.25,1.25,0.0,0.0\n")

    assert hotspots[0].function == "f"
    assert hotspots[0].cpu_time_lexeme == "1.25"


def test_recording_writes_one_fact_and_derives_safe_actions_summary(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    root = run_dir / "profile/raw/vtune-summary"
    root.mkdir()
    report = root / "hotspots.csv"
    status = root / "collection-status.json"
    summary = root / "summary.json"
    markdown = root / "summary.md"
    report.write_text(
        HEADER
        + _row("name`with|syntax", "lib|x.so", "1.25")
        + _row("wait", "libmpi.so", "0.250")
    )
    status.write_text(
        '{"schema_version":"vtune-collection-status/v1",'
        '"target_exit_code":0,"vtune_exit_code":0}\n'
    )

    fragment = record_vtune_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        report_path=report,
        status_path=status,
        summary_path=summary,
        markdown_path=markdown,
        profiled_rank=0,
        collection_duration_sec=60,
    )

    row = json.loads(fragment.read_text())
    assert row["key"] == "profile.vtune_hotspots"
    value = json.loads(row["value"])
    assert value["collection"]["target_mode"] == "attach"
    assert value["collection"]["analysis_type"] == "hotspots"
    assert value["collection"]["sampling_mode"] == "sw"
    assert value["sources"]["report"]["member"] == (
        "profile/raw/vtune-summary/hotspots.csv"
    )
    document = json.loads(summary.read_text())
    assert document["reported_cpu_time_sec"] == "1.5"
    rendered = markdown.read_text()
    assert "name`with\\|syntax" in rendered
    assert "`name`with" not in rendered
    assert "Full VTune results remain in the cluster profile storage." in rendered
    assert "Genkai" not in rendered


def test_hpc_characterization_records_hardware_sampling(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    root = run_dir / "profile/raw/vtune-summary"
    root.mkdir()
    (root / "hotspots.csv").write_text(HEADER + _row("f", "m", "1"))
    (root / "collection-status.json").write_text(
        '{"schema_version":"vtune-collection-status/v1",'
        '"target_exit_code":0,"vtune_exit_code":0}\n'
    )

    fragment = record_vtune_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        report_path=root / "hotspots.csv",
        status_path=root / "collection-status.json",
        summary_path=root / "summary.json",
        markdown_path=root / "summary.md",
        profiled_rank=3,
        analysis_type="hpc-performance",
        collection_duration_sec=60,
    )

    value = json.loads(json.loads(fragment.read_text())["value"])
    assert value["schema_version"] == "openfoam-vtune-profile/v2"
    assert value["collection"]["analysis_type"] == "hpc-performance"
    assert value["collection"]["sampling_mode"] == "hw"


def test_memory_access_requires_and_records_supplemental_reports(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    root = run_dir / "profile/raw/vtune-summary"
    root.mkdir()
    (root / "hotspots.csv").write_text(HEADER + _row("f", "m", "1"))
    (root / "memory-summary.txt").write_text("Memory Bound: 42.0%\n")
    (root / "memory-functions.csv").write_text(
        "Function,Module,CPU Time,Memory Bound\nf,m,1.0,42.0%\n"
    )
    (root / "collection-status.json").write_text(
        '{"schema_version":"vtune-collection-status/v1",'
        '"target_exit_code":0,"vtune_exit_code":0}\n'
    )

    fragment = record_vtune_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        report_path=root / "hotspots.csv",
        status_path=root / "collection-status.json",
        summary_path=root / "summary.json",
        markdown_path=root / "summary.md",
        profiled_rank=365,
        analysis_type="memory-access",
        collection_duration_sec=60,
    )

    value = json.loads(json.loads(fragment.read_text())["value"])
    assert value["collection"]["analysis_type"] == "memory-access"
    assert value["collection"]["target_mode"] == "launch"
    assert value["collection"]["dram_bandwidth_limits"] is True
    assert value["collection"]["data_limit_mb"] == 0
    assert value["collection"]["core_event_scope"] == "profiled_rank_process"
    assert value["collection"]["uncore_bandwidth_scope"] == "profiled_rank_compute_node"
    assert value["sources"]["memory_summary"]["member"].endswith("memory-summary.txt")
    assert value["sources"]["memory_functions"]["member"].endswith(
        "memory-functions.csv"
    )


def test_collection_failure_does_not_publish_a_fact(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    root = run_dir / "profile/raw/vtune-summary"
    root.mkdir()
    report = root / "hotspots.csv"
    status = root / "collection-status.json"
    report.write_text(HEADER + _row("f", "m", "1"))
    status.write_text(
        '{"schema_version":"vtune-collection-status/v1",'
        '"target_exit_code":0,"vtune_exit_code":1}\n'
    )

    with pytest.raises(ValueError, match="did not complete"):
        record_vtune_hotspots(
            manifest_path=manifest,
            runtime_dir=run_dir,
            report_path=report,
            status_path=status,
            summary_path=root / "summary.json",
            markdown_path=root / "summary.md",
            profiled_rank=0,
            collection_duration_sec=60,
        )
    fragment = (
        run_dir
        / "domain/fragments/compute.vtune_hotspots_parser--vtune-hotspots.jsonl"
    )
    assert not fragment.exists()


@pytest.mark.parametrize(
    ("vtune_exit", "target_exit", "expected_exit"),
    [(7, 0, 0), (0, 3, 3)],
)
def test_profile_wrapper_keeps_solver_status_authoritative(
    tmp_path: Path, vtune_exit: int, target_exit: int, expected_exit: int
) -> None:
    provision = tmp_path / "provision/scripts"
    provision.mkdir(parents=True)
    launcher = provision / "allow-vtune-attach.py"
    launcher.write_text("#!/bin/sh\nexec \"$@\"\n")
    launcher.chmod(0o755)
    vtune = tmp_path / "vtune"
    vtune.write_text(f"#!/bin/sh\nexit {vtune_exit}\n")
    vtune.chmod(0o755)
    target = tmp_path / "target"
    target.write_text(f"#!/bin/sh\nexit {target_exit}\n")
    target.chmod(0o755)
    status = tmp_path / "profile/raw/vtune-summary/collection-status.json"
    environment = {
        **os.environ,
        "OPENFOAM_VTUNE_RESULT_DIR": str(tmp_path / "result"),
        "OPENFOAM_VTUNE_STATUS_PATH": str(status),
        "OPENFOAM_VTUNE_PATH": str(vtune),
        "OPENFOAM_VTUNE_ANALYSIS": "hotspots",
        "OPENFOAM_VTUNE_DURATION_SEC": "1",
        "PROVISION_DIR": str(tmp_path / "provision"),
    }

    completed = subprocess.run(
        ["bash", str(ROOT / "scripts/exec-profiler.sh"), str(target)],
        env=environment,
        check=False,
    )

    assert completed.returncode == expected_exit
    document = json.loads(status.read_text())
    assert document["vtune_exit_code"] == vtune_exit
    assert document["target_exit_code"] == target_exit


@pytest.mark.parametrize("analysis", ["hpc-performance", "memory-access"])
def test_hardware_profile_wrapper_launches_target_through_vtune(
    tmp_path: Path, analysis: str
) -> None:
    provision = tmp_path / "provision/scripts"
    provision.mkdir(parents=True)
    launcher = provision / "allow-vtune-attach.py"
    launcher.write_text("#!/bin/sh\nexec \"$@\"\n")
    launcher.chmod(0o755)
    vtune = tmp_path / "vtune"
    vtune.write_text(
        "#!/bin/sh\n"
        "while [ \"$#\" -gt 0 ] && [ \"$1\" != -- ]; do shift; done\n"
        "[ \"$#\" -gt 0 ] && shift\n"
        "printf '%s' \"$1\" > \"$FAKE_VTUNE_TARGET_PATH\"\n"
        "exec \"$@\"\n"
    )
    vtune.chmod(0o755)
    marker = tmp_path / "target-ran"
    target = tmp_path / "target"
    target.write_text(f"#!/bin/sh\nprintf ran > {marker}\n")
    target.chmod(0o755)
    status = tmp_path / "profile/raw/vtune-summary/collection-status.json"
    environment = {
        **os.environ,
        "OPENFOAM_VTUNE_RESULT_DIR": str(tmp_path / "result"),
        "OPENFOAM_VTUNE_STATUS_PATH": str(status),
        "OPENFOAM_VTUNE_PATH": str(vtune),
        "OPENFOAM_VTUNE_ANALYSIS": analysis,
        "OPENFOAM_VTUNE_DURATION_SEC": "1",
        "PROVISION_DIR": str(tmp_path / "provision"),
        "FAKE_VTUNE_TARGET_PATH": str(tmp_path / "vtune-target"),
    }

    completed = subprocess.run(
        ["bash", str(ROOT / "scripts/exec-profiler.sh"), str(target)],
        env=environment,
        check=False,
    )

    assert completed.returncode == 0
    assert marker.read_text() == "ran"
    assert (tmp_path / "vtune-target").read_text() == str(target)
    assert json.loads(status.read_text()) == {
        "schema_version": "vtune-collection-status/v1",
        "target_exit_code": 0,
        "vtune_exit_code": 0,
    }
