from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from experiment_metrics.source_track import source_track_identities


def _repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    for relative in ("a.txt", "nested/b.txt"):
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


def test_source_track_gates_clean_remote_reachable_control_plane(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    identities = source_track_identities(
        repository=repo,
        purpose="bench",
        base_commit=head,
        control_plane_files=["a.txt", "nested/b.txt"],
        instrumentation_bundle_sha256="a" * 64,
    )

    assert identities["source_track"]["base_role"] == "score_reference"
    assert identities["source_track"]["head_commit"] == head
    assert len(identities["observed_control_plane_sha256"]) == 64


def test_source_track_rejects_dirty_and_unreachable_checkout(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (repo / "dirty.txt").write_text("dirty\n")
    with pytest.raises(ValueError, match="clean"):
        source_track_identities(
            repository=repo,
            purpose="bench",
            base_commit=head,
            control_plane_files=["a.txt"],
            instrumentation_bundle_sha256="a" * 64,
        )
    (repo / "dirty.txt").unlink()
    subprocess.run(
        ["git", "-C", str(repo), "update-ref", "-d", "refs/remotes/origin/main"],
        check=True,
    )
    with pytest.raises(ValueError, match="reachable"):
        source_track_identities(
            repository=repo,
            purpose="bench",
            base_commit=head,
            control_plane_files=["a.txt"],
            instrumentation_bundle_sha256="a" * 64,
        )
