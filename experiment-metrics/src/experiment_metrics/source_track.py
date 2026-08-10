from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path, PurePosixPath

from .fact import canonical_json


def source_track_identities(
    *,
    repository: Path,
    purpose: str,
    base_commit: str,
    control_plane_files: list[str],
    instrumentation_bundle_sha256: str,
) -> dict[str, object]:
    repo = repository.resolve(strict=True)
    if purpose not in {"bench", "profile"}:
        raise ValueError("source track purpose must be bench or profile")
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("source track requires a clean checkout")
    algorithm = _git(repo, "rev-parse", "--show-object-format")
    head = _git(repo, "rev-parse", "HEAD")
    base = _git(repo, "rev-parse", f"{base_commit}^{{commit}}")
    if subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base, head],
        check=False,
    ).returncode:
        raise ValueError("source track base is not an ancestor of head")
    remote_refs = _git(
        repo,
        "for-each-ref",
        "--format=%(refname)",
        "--contains",
        head,
        "refs/remotes/origin",
    ).splitlines()
    if not remote_refs:
        raise ValueError("source head is not reachable from an origin remote ref")
    if control_plane_files != sorted(set(control_plane_files), key=str.encode):
        raise ValueError("control-plane paths must be byte-sorted and unique")
    observations: list[dict[str, str]] = []
    for relative in control_plane_files:
        path = PurePosixPath(relative)
        if not relative or path.is_absolute() or ".." in path.parts:
            raise ValueError("control-plane path is not repository-relative")
        if not (repo / relative).is_file():
            raise ValueError(f"control-plane file is absent: {relative}")
        observations.append(
            {
                "path": relative,
                "blob_oid": _git(repo, "rev-parse", f"HEAD:{relative}"),
            }
        )
    control_identity = hashlib.sha256(canonical_json(observations).encode()).hexdigest()
    if len(instrumentation_bundle_sha256) != 64 or any(
        character not in "0123456789abcdef"
        for character in instrumentation_bundle_sha256
    ):
        raise ValueError("instrumentation bundle identity must be a SHA-256")
    return {
        "source_track": {
            "object_hash_algorithm": algorithm,
            "base_role": "score_reference" if purpose == "bench" else "profile_base",
            "base_commit": base,
            "head_commit": head,
        },
        "observed_control_plane_sha256": control_identity,
        "instrumentation_bundle_sha256": instrumentation_bundle_sha256,
    }


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
