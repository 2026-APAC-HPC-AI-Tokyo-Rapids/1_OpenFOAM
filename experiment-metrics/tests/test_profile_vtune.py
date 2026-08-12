from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from experiment_metrics.manifest import init_run
from experiment_metrics.profile_vtune import parse_hotspots, record_vtune_hotspots

ROOT = Path(__file__).parents[2]


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
        "metadata\nFunction,Module,CPU Time\nslow,lib.so,120ms\nfast,lib.so,1.5s\n"
    )

    assert [item.function for item in hotspots] == ["fast", "slow"]
    assert hotspots[1].cpu_time_lexeme == "120ms"
    assert str(hotspots[1].cpu_time_sec) == "0.120"


@pytest.mark.parametrize(
    "source",
    [
        "Function,Module,CPU Time\nf,m,1\n",
        "Function,Module,CPU Time,Extra\nf,m,1s,x\n",
        "Function,Module,CPU Time\nf,m,1s\nf,m,2s\n",
        "Function,Module,CPU Time\n,m,1s\n",
    ],
)
def test_parser_rejects_lossy_or_ambiguous_reports(source: str) -> None:
    with pytest.raises(ValueError):
        parse_hotspots(source)


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
        "Function,Module,CPU Time\n"
        "name`with|syntax,lib|x.so,1.25s\n"
        "wait,libmpi.so,250ms\n"
    )
    status.write_text(
        '{"schema_version":"vtune-collection-status/v1",'
        '"target_exit_code":0,"vtune_exit_code":0}\n'
    )

    fragment = record_vtune_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        registry_path=registry_path,
        report_path=report,
        status_path=status,
        summary_path=summary,
        markdown_path=markdown,
        profiled_rank=0,
        collection_duration_sec=60,
    )

    row = json.loads(fragment.read_text())
    assert row["key"] == "profile.vtune_hotspots.rank.0"
    value = json.loads(row["value"])
    assert value["collection"]["target_mode"] == "attach"
    assert value["sources"]["report"]["member"] == (
        "profile/raw/vtune-summary/hotspots.csv"
    )
    document = json.loads(summary.read_text())
    assert document["reported_cpu_time_sec"] == "1.5"
    rendered = markdown.read_text()
    assert "name`with\\|syntax" in rendered
    assert "`name`with" not in rendered


def test_collection_failure_does_not_publish_a_fact(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    root = run_dir / "profile/raw/vtune-summary"
    root.mkdir()
    report = root / "hotspots.csv"
    status = root / "collection-status.json"
    report.write_text("Function,Module,CPU Time\nf,m,1s\n")
    status.write_text(
        '{"schema_version":"vtune-collection-status/v1",'
        '"target_exit_code":0,"vtune_exit_code":1}\n'
    )

    with pytest.raises(ValueError, match="did not complete"):
        record_vtune_hotspots(
            manifest_path=manifest,
            runtime_dir=run_dir,
            registry_path=registry_path,
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
