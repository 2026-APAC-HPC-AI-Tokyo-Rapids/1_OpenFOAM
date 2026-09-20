from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

import experiment_metrics.build_provenance as provenance
from experiment_metrics import init_run
from experiment_metrics.build_provenance import (
    EXECUTABLE_ROLES,
    PARTITION_SOURCE_PATHS,
    build_artifact_facts,
    capture_build_state,
    finalize_build_sidecar,
    verify_build_pair,
)


def _definition_repo(root: Path) -> Path:
    repo = root / "definition"
    repo.mkdir()
    for relative in PARTITION_SOURCE_PATHS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative + "\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", head],
        check=True,
    )
    return repo


def test_build_sidecar_seals_source_toolchain_runtime_and_archive(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition = _definition_repo(tmp_path)
    tree = tmp_path / "tree"
    bin_dir = tree / "OpenFOAM/platforms/test/bin"
    bin_dir.mkdir(parents=True)
    paths: dict[str, Path] = {}
    for role in EXECUTABLE_ROLES[:-1]:
        path = bin_dir / role
        shutil.copy2("/bin/true", path)
        paths[role] = path
    capture = bin_dir / "capture-hardware"
    capture.write_text("#!/usr/bin/env python3\n")
    capture.chmod(0o755)
    paths["capture-hardware"] = capture
    compiler_redirect = tmp_path / "compiler-redirect"
    compiler_redirect.write_text(
        '#!/usr/bin/env bash\ncase "${0##*/}" in cc|cxx) exit 0 ;; *) exit 64 ;; esac\n'
    )
    compiler_redirect.chmod(0o755)
    compiler_c = tmp_path / "cc"
    compiler_cxx = tmp_path / "cxx"
    compiler_c.symlink_to(compiler_redirect)
    compiler_cxx.symlink_to(compiler_redirect)
    monkeypatch.setattr(provenance, "_which", lambda _name: Path("/bin/true"))

    state = capture_build_state(
        output=tmp_path / "state.json",
        build_tree=tree,
        build_definition_repo=definition,
        openfoam_oid="a" * 40,
        openfoam_algorithm="sha1",
        thirdparty_oid="b" * 40,
        thirdparty_algorithm="sha1",
        executable_paths=paths,
        compile_flags=["WM_PRECISION_OPTION=DP", "WM_LABEL_SIZE=64"],
        compiler_c=compiler_c,
        compiler_cxx=compiler_cxx,
        mpi_launcher=Path("/bin/true"),
        precision="DP",
        label_bits=64,
    )
    archive = tmp_path / "build.tar.zst"
    archive.write_bytes(b"immutable-build-archive")
    sidecar = finalize_build_sidecar(state, archive, tmp_path / "sidecar.json")
    document = verify_build_pair(sidecar, archive)

    assert [item["commit_role"] for item in document["source_commits"]] == [
        "build_definition",
        "openfoam_source",
        "thirdparty_source",
    ]
    assert {
        item["role"]
        for item in document["runtime_objects"]
        if item["kind"] == "executable"
    } == set(EXECUTABLE_ROLES)
    assert document["build_archive"]["size_bytes"] == archive.stat().st_size
    assert document["toolchain_commands"][0]["argv"][0] == str(compiler_c)
    assert document["toolchain_commands"][1]["argv"][0] == str(compiler_cxx)

    manifest = init_run(
        None, tmp_path / "runtime", identities, registry_path=registry_path
    )
    installed = manifest.parents[1] / "control/build-sidecar.json"
    shutil.copy2(sidecar, installed)
    shutil.copytree(
        tree / "control/build-raw", manifest.parents[1] / "control/build-raw"
    )
    facts = build_artifact_facts(manifest, installed)
    assert facts[0].key == "artifact.build_manifest_sha256"
    assert facts[0].logical_value == hashlib.sha256(installed.read_bytes()).hexdigest()
    assert facts[1].key == "build.provenance"
    assert facts[1].logical_value["precision"] == "DP"

    archive.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="does not match"):
        verify_build_pair(sidecar, archive)
