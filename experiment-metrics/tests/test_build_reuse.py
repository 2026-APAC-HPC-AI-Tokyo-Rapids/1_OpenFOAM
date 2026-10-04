"""Exercise archive reuse against its original build commit, including reused runs."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("changed_path", "cluster", "source_changed", "matches"),
    [
        ("README.md", "genkai", False, True),
        ("scripts/run-openfoam.sh", "genkai", False, True),
        ("experiment-metrics/src/experiment_metrics/coefficient.py", "genkai", False, True),
        ("scripts/build-openfoam-task.sh", "genkai", False, False),
        ("scripts/build-openfoam.sh", "genkai", False, False),
        ("experiment-metrics/native/mesh-facts/mesh-facts.C", "genkai", False, False),
        ("platforms/genkai/build-environment.sh", "genkai", False, False),
        ("platforms/gadi/build-environment.sh", "genkai", False, True),
        ("platforms/gadi/build-environment.sh", "gadi", False, False),
        ("platforms/aspire2a/build-environment.sh", "aspire2a", False, False),
        ("platforms/aspire2a/toolchain.conf", "aspire2a", False, False),
        ("platforms/aspire2a/toolchain.sh", "aspire2a", False, False),
        ("platforms/aspire2a/toolchain.conf", "genkai", False, True),
        ("platforms/gadi/build-environment.sh", "aspire2a", False, True),
        ("patches/openfoam/0001-change.patch", "genkai", False, False),
        ("patches/openfoam/0001-change.patch", "aspire2a", False, False),
        ("README.md", "genkai", True, False),
    ],
)
def test_reuse_compares_original_build_inputs(
    tmp_path: Path, changed_path: str, cluster: str, source_changed: bool, matches: bool
) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "--quiet")
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    git("commit", "--allow-empty", "--quiet", "-m", "original build")
    original = git("rev-parse", "HEAD")
    changed = tmp_path / changed_path
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("changed\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "change inputs")
    # A subsequent reused-run commit cannot hide earlier build input changes.
    git("commit", "--allow-empty", "--quiet", "-m", "reuse run")
    sidecar = tmp_path / "sidecar.json"
    sidecar.write_text(json.dumps({"source_commits": [
        {"commit_role": "build_definition", "oid": original},
        {"commit_role": "openfoam_source", "oid": "a" * 40},
        {"commit_role": "thirdparty_source", "oid": "b" * 40},
    ]}))
    result = subprocess.run(
        [str(ROOT / "scripts/build-inputs-match.sh"), cluster, str(sidecar)],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_SHA": git("rev-parse", "HEAD"), "OPENFOAM_SOURCE_OID": ("c" if source_changed else "a") * 40, "THIRDPARTY_SOURCE_OID": "b" * 40},
        capture_output=True,
        text=True,
    )
    assert (result.returncode == 0) == matches, result.stderr
