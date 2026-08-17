from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from experiment_metrics import capture_workload, init_run, load_workload_definition
from experiment_metrics.cli import main

ROOT = Path(__file__).parents[2]
DEFINITION = ROOT / "benchmark/workload.json"
OFFICIAL_CASE = ROOT / "benchmark/occDrivAerStaticMesh"


def test_capture_workload_copies_and_seals_exact_members(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest.parents[1]
    definition = load_workload_definition(DEFINITION)

    path = capture_workload(manifest, OFFICIAL_CASE, run_dir / "source/workload", DEFINITION)
    document = json.loads(path.read_text())

    assert document["schema_version"] == "workload-manifest/v2"
    assert document["workload_identity"] == definition.case_identity
    assert [item["path"] for item in document["members"]] == list(definition.case_members)
    for item in document["members"]:
        copied = run_dir / "source/workload" / item["path"]
        assert copied.read_bytes() == (OFFICIAL_CASE / item["path"]).read_bytes()
        assert item["sha256"] == hashlib.sha256(copied.read_bytes()).hexdigest()


def test_capture_workload_rejects_changed_member(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path / "runs", identities, registry_path=registry_path)
    case = tmp_path / "case"
    shutil.copytree(OFFICIAL_CASE, case)
    (case / "system/controlDict").write_text("changed\n")
    with pytest.raises(ValueError, match="固定済みの課題識別情報"):
        capture_workload(manifest, case, manifest.parents[1] / "source/workload", DEFINITION)


def test_capture_workload_cli(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    assert main(["capture-workload", "--manifest", str(manifest), "--case-root", str(OFFICIAL_CASE), "--definition", str(DEFINITION), "--output-root", str(manifest.parents[1] / "source/workload")]) == 0
    fragment = manifest.parents[1] / "domain/fragments/runner.workload_manifest--workload.jsonl"
    rows = [json.loads(line) for line in fragment.read_text().splitlines()]
    assert [row["key"] for row in rows] == ["workload.manifest"]


def test_manifest_rejects_noncanonical_repository_identity(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    with pytest.raises(ValueError, match="apac2026-openfoam"):
        init_run(None, tmp_path, identities, repository_id="owner/repository", registry_path=registry_path)
