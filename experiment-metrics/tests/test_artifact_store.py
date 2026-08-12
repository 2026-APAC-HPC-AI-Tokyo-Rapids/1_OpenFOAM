from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics.artifact_store import RunPackager, validate_artifact_set
from experiment_metrics.manifest import init_run


def _run(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    purpose: str = "bench",
) -> Path:
    if purpose == "profile":
        identities = json.loads(json.dumps(identities))
        identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(
        None, tmp_path, identities, purpose=purpose, registry_path=registry_path
    )
    run_dir = manifest.parents[1]
    (run_dir / "logs/solver.log").write_text("done\n", encoding="utf-8")
    return manifest


def test_packager_excludes_merged_metrics_sidecar(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _run(tmp_path, registry_path, identities)
    result = RunPackager().package(
        manifest, run_members=(("logs/solver.log", "solver_log"),)
    )
    validated = validate_artifact_set(manifest, result.manifest_path)
    assert [path.name for path in validated.files] == ["run-artifacts.tar.zst"]
    artifact = json.loads(result.manifest_path.read_text())
    assert [row["role"] for row in artifact["files"]] == ["run_bundle"]


def test_profile_artifacts_retain_raw_profile_archive(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _run(tmp_path, registry_path, identities, "profile")
    with pytest.raises(ValueError, match="profile raw members"):
        RunPackager().package(
            manifest, run_members=(("logs/solver.log", "solver_log"),)
        )
    raw = manifest.parents[1] / "profile/raw/vtune-summary/hotspots.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("counter\n", encoding="utf-8")
    result = RunPackager().package(
        manifest,
        run_members=(("logs/solver.log", "solver_log"),),
        profile_members=("profile/raw/vtune-summary/hotspots.csv",),
    )
    assert [path.name for path in result.files] == [
        "run-artifacts.tar.zst",
        "profile-raw.tar.zst",
    ]


def test_artifact_hash_tampering_is_rejected(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _run(tmp_path, registry_path, identities)
    result = RunPackager().package(
        manifest, run_members=(("logs/solver.log", "solver_log"),)
    )
    document = json.loads(result.manifest_path.read_text())
    document["files"][0]["sha256"] = "0" * 64
    result.manifest_path.write_text(json.dumps(document) + "\n")
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_artifact_set(manifest, result.manifest_path)
