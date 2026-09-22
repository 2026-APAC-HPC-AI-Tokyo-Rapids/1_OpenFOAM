from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/transfer-vtune-result.sh"
PROFILE_RUN_ID = "r-0123456789abcdef0123456789abcdef-12345"
GITHUB_RUN_ID = "987654321"


def _environment(tmp_path: Path, *, broken_connection: bool = False, vtune_result: bool = True) -> tuple[dict[str, str], Path, Path]:
    runtime = tmp_path / "cluster-runs" / "runs" / "r-0123456789abcdef0123456789abcdef"
    source_dir = runtime / "large-output"
    result = source_dir / "vtune" / "rank-0-hotspots.result"
    if vtune_result:
        result.mkdir(parents=True)
        (result / "data.0").write_bytes(b"vtune raw data\n")
    else:
        result.parent.mkdir(parents=True)
    archive_root = tmp_path / "home-archive"
    for cluster in ("genkai", "gadi"):
        wrapper = tmp_path / f"{cluster}-shell"
        wrapper.write_text("#!/bin/sh\nprintf broken\n" if broken_connection else "#!/bin/sh\nexec \"$@\"\n")
        wrapper.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = str(tmp_path) + os.pathsep + environment["PATH"]
    environment["OPENFOAM_ARTIFACT_ARCHIVE_ROOT"] = str(archive_root)
    return environment, source_dir, archive_root


def _run(environment: dict[str, str], source_dir: Path, profile_run_id: str = PROFILE_RUN_ID, *, cluster: str = "genkai") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "--cluster", cluster, "--github-run-id", GITHUB_RUN_ID, "--profile-run-id", profile_run_id, "--source-dir", str(source_dir)],
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )


@pytest.mark.parametrize("cluster", ["genkai", "gadi"])
def test_transfer_archives_validates_and_preserves_source(tmp_path: Path, cluster: str) -> None:
    environment, source_dir, archive_root = _environment(tmp_path)

    completed = _run(environment, source_dir, cluster=cluster)

    assert completed.returncode == 0, completed.stderr
    destination = archive_root / GITHUB_RUN_ID / cluster / f"openfoam-{cluster}-v2-r-0123456789abcdef0123456789abcdef" / "large-output"
    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["schema_version"] == "openfoam-large-output-archive/v1"
    assert manifest["profile_run_id"] == PROFILE_RUN_ID
    assert manifest["source_connection"] == f"{cluster}-shell"
    assert "source_target" not in manifest
    assert manifest["vtune_result_available"] is True
    assert (destination / "vtune" / "vtune-result.tar.zst").is_file()
    assert [entry["path"] for entry in manifest["files"]] == ["vtune/vtune-result.tar.zst"]
    assert source_dir.is_dir()

    repeated = _run(environment, source_dir, cluster=cluster)
    assert repeated.returncode == 0, repeated.stderr
    assert not any(path.name.startswith(".") for path in destination.parent.iterdir())


def test_transfer_records_missing_vtune_result(tmp_path: Path) -> None:
    environment, source_dir, archive_root = _environment(tmp_path, vtune_result=False)

    completed = _run(environment, source_dir)

    assert completed.returncode == 0, completed.stderr
    destination = archive_root / GITHUB_RUN_ID / "genkai" / "openfoam-genkai-v2-r-0123456789abcdef0123456789abcdef" / "large-output"
    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["vtune_result_available"] is False
    assert not (destination / "vtune").exists()
    assert manifest["files"] == []
    assert source_dir.is_dir()


def test_transfer_uses_no_target_directory_move() -> None:
    assert 'mv -T -- "${staging}" "${destination}"' in SCRIPT.read_text()


def test_transfer_keeps_source_when_stream_is_invalid(tmp_path: Path) -> None:
    environment, source_dir, archive_root = _environment(tmp_path, broken_connection=True)

    completed = _run(environment, source_dir)

    assert completed.returncode != 0
    assert source_dir.is_dir()
    assert not (archive_root / GITHUB_RUN_ID / "genkai" / "openfoam-genkai-v2-r-0123456789abcdef0123456789abcdef" / "large-output").exists()


@pytest.mark.parametrize(
    "profile_run_id",
    ("../../escape", "r-short-123", "r-0123456789abcdef0123456789abcdef-bad/job"),
)
def test_transfer_rejects_unsafe_profile_run_id(tmp_path: Path, profile_run_id: str) -> None:
    environment, source_dir, _ = _environment(tmp_path)

    completed = _run(environment, source_dir, profile_run_id)

    assert completed.returncode == 64
    assert source_dir.is_dir()


def test_transfer_refuses_mismatched_existing_archive(tmp_path: Path) -> None:
    environment, source_dir, archive_root = _environment(tmp_path)
    destination = archive_root / GITHUB_RUN_ID / "genkai" / "openfoam-genkai-v2-r-0123456789abcdef0123456789abcdef" / "large-output"
    destination.mkdir(parents=True)
    (destination / "vtune").mkdir()
    (destination / "vtune" / "vtune-result.tar.zst").write_bytes(b"not an archive")
    (destination / "manifest.json").write_text("{}\n")

    completed = _run(environment, source_dir)

    assert completed.returncode != 0
    assert source_dir.is_dir()
