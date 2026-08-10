from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from experiment_metrics import RunManifest, init_run
from experiment_metrics.artifact_store import RunPackager, validate_artifact_set


def _run(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    purpose: str = "bench",
) -> tuple[Path, RunManifest]:
    selected = identities
    if purpose == "profile":
        selected = {
            **identities,
            "source_track": {
                **identities["source_track"],  # type: ignore[arg-type]
                "base_role": "profile_base",
            },
        }
    path = init_run(
        None,
        tmp_path,
        selected,
        purpose=purpose,
        registry_path=registry_path,
    )
    return path, RunManifest.load(path)


def _write_metrics(
    run_dir: Path, run_id: str, *, foreign_run: str | None = None
) -> None:
    run = foreign_run or run_id
    (run_dir / "metrics.jsonl").write_text(
        json.dumps(
            {"run": run, "key": "collection_complete", "value": "true"},
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def _bench_members(run_dir: Path) -> tuple[tuple[str, str], ...]:
    (run_dir / "logs/solver.log").write_text("complete\n", encoding="utf-8")
    return (
        ("control/run-manifest.json", "run_manifest"),
        ("logs/solver.log", "solver_log"),
    )


def test_packager_creates_and_revalidates_closed_bench_artifact_set(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, manifest = _run(tmp_path, registry_path, identities)
    run_dir = manifest.path.parents[1]
    _write_metrics(run_dir, manifest.run_id)

    result = RunPackager().package(manifest_path, run_members=_bench_members(run_dir))
    validated = validate_artifact_set(manifest_path, result.manifest_path)

    assert [path.name for path in result.files] == [
        "run-artifacts.tar.zst",
        "metrics.jsonl",
    ]
    assert validated.files == result.files
    assert validated.metrics_rows[0].run == manifest.run_id
    artifact = json.loads(result.manifest_path.read_text())
    assert [item["role"] for item in artifact["files"]] == [
        "run_bundle",
        "metrics",
    ]
    for item, path in zip(artifact["files"], result.files, strict=True):
        assert item["size_bytes"] == path.stat().st_size
        assert item["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    members = subprocess.run(
        ["tar", "-I", "zstd", "-tf", run_dir / "run-artifacts.tar.zst"],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    assert members == [
        "control/run-manifest.json",
        "logs/solver.log",
        "bundle.manifest.json",
    ]


def test_packager_rejects_foreign_or_noncanonical_metrics(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, manifest = _run(tmp_path, registry_path, identities)
    run_dir = manifest.path.parents[1]
    members = _bench_members(run_dir)
    _write_metrics(run_dir, manifest.run_id, foreign_run="r-" + "f" * 32)
    with pytest.raises(ValueError, match="foreign run"):
        RunPackager().package(manifest_path, run_members=members)

    (run_dir / "metrics.jsonl").write_text(
        f'{{"key":"a","run":"{manifest.run_id}","value":"0"}}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ordered run/key/value"):
        RunPackager().package(manifest_path, run_members=members)


def test_packager_rejects_unsafe_or_open_run_members(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, manifest = _run(tmp_path, registry_path, identities)
    run_dir = manifest.path.parents[1]
    _write_metrics(run_dir, manifest.run_id)
    (run_dir / "logs/solver.log").write_text("complete\n", encoding="utf-8")

    with pytest.raises(ValueError, match="run_manifest"):
        RunPackager().package(
            manifest_path,
            run_members=(("control/run-manifest.json", "wrong_role"),),
        )
    with pytest.raises(ValueError, match="absent from the registry"):
        RunPackager().package(
            manifest_path,
            run_members=(
                ("control/run-manifest.json", "run_manifest"),
                ("logs/solver.log", "unknown_source_role"),
            ),
        )
    with pytest.raises(ValueError, match="unsafe artifact member"):
        RunPackager().package(
            manifest_path,
            run_members=(("../outside", "invalid"),),
        )
    (run_dir / "logs/solver-link.log").symlink_to(run_dir / "logs/solver.log")
    with pytest.raises(ValueError, match="symlink"):
        RunPackager().package(
            manifest_path,
            run_members=(
                ("control/run-manifest.json", "run_manifest"),
                ("logs/solver-link.log", "solver_log"),
            ),
        )


def test_profile_requires_profile_raw_and_uses_exact_outer_role_set(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, manifest = _run(
        tmp_path, registry_path, identities, purpose="profile"
    )
    run_dir = manifest.path.parents[1]
    _write_metrics(run_dir, manifest.run_id)
    members = _bench_members(run_dir)
    with pytest.raises(ValueError, match="profile raw members"):
        RunPackager().package(manifest_path, run_members=members)

    raw = run_dir / "profile/raw/perf/rank-0.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("counter\n", encoding="utf-8")
    result = RunPackager().package(
        manifest_path,
        run_members=members,
        profile_members=("profile/raw/perf/rank-0.csv",),
    )
    artifact = json.loads(result.manifest_path.read_text())
    assert [item["role"] for item in artifact["files"]] == [
        "run_bundle",
        "metrics",
        "profile_raw",
    ]


def test_artifact_set_rejects_role_order_filename_and_hash_tampering(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, manifest = _run(tmp_path, registry_path, identities)
    run_dir = manifest.path.parents[1]
    _write_metrics(run_dir, manifest.run_id)
    result = RunPackager().package(manifest_path, run_members=_bench_members(run_dir))
    document = json.loads(result.manifest_path.read_text())
    document["files"].reverse()
    result.manifest_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="role order"):
        validate_artifact_set(manifest_path, result.manifest_path)

    document["files"].reverse()
    document["files"][1]["sha256"] = "0" * 64
    result.manifest_path.write_text(json.dumps(document) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_artifact_set(manifest_path, result.manifest_path)

    result.manifest_path.rename(run_dir / "renamed-manifest.json")
    with pytest.raises(ValueError, match="fixed run-root filename"):
        validate_artifact_set(manifest_path, run_dir / "renamed-manifest.json")
