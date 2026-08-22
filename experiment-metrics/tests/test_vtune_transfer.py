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


def _environment(tmp_path: Path, *, broken_ssh: bool = False, vtune_result: bool = True) -> tuple[dict[str, str], Path, Path]:
    source_root = tmp_path / "cluster-profile"
    result = source_root / PROFILE_RUN_ID / "rank-0-hotspots.result"
    if vtune_result:
        result.mkdir(parents=True)
        (result / "data.0").write_bytes(b"vtune raw data\n")
    else:
        result.parent.mkdir(parents=True)
    paraview = source_root / PROFILE_RUN_ID / "paraview"
    paraview.mkdir()
    case = tmp_path / "paraview-case"
    case.mkdir()
    (case / "occDrivAerStaticMesh.foam").write_text("")
    subprocess.run(["tar", "-I", "zstd", "-cf", paraview / "paraview-case.tar.zst", "-C", case, "occDrivAerStaticMesh.foam"], check=True)
    paraview_archive = paraview / "paraview-case.tar.zst"
    paraview_manifest = {
        "schema_version": "openfoam-paraview-archive/v1",
        "run_id": "r-0123456789abcdef0123456789abcdef",
        "profile_run_id": PROFILE_RUN_ID,
        "archive": {
            "path": "paraview-case.tar.zst",
            "size_bytes": paraview_archive.stat().st_size,
            "sha256": subprocess.check_output(["sha256sum", paraview_archive], text=True).split()[0],
        },
    }
    (paraview / "manifest.json").write_text(json.dumps(paraview_manifest) + "\n")
    archive_root = tmp_path / "home-archive"
    config = tmp_path / "transfer.env"
    config.write_text(
        "\n".join(
            (
                "OPENFOAM_VTUNE_GENKAI_SSH_TARGET=fake-genkai",
                "OPENFOAM_VTUNE_GENKAI_ROOT=" + str(source_root),
                "OPENFOAM_VTUNE_GADI_SSH_TARGET=fake-gadi",
                "OPENFOAM_VTUNE_GADI_ROOT=" + str(source_root),
                "OPENFOAM_ARTIFACT_ARCHIVE_ROOT=" + str(archive_root),
                "",
            )
        )
    )
    fake_ssh = tmp_path / "fake-ssh"
    if broken_ssh:
        fake_ssh.write_text("#!/bin/sh\nprintf broken\n")
    else:
        fake_ssh.write_text("#!/bin/sh\nshift\nexec \"$@\"\n")
    fake_ssh.chmod(0o755)
    environment = os.environ.copy()
    environment["OPENFOAM_VTUNE_TRANSFER_CONFIG"] = str(config)
    environment["OPENFOAM_VTUNE_SSH_BIN"] = str(fake_ssh)
    return environment, source_root, archive_root


def _run(environment: dict[str, str], profile_run_id: str = PROFILE_RUN_ID) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), "--cluster", "genkai", "--github-run-id", GITHUB_RUN_ID, "--profile-run-id", profile_run_id],
        check=False,
        text=True,
        capture_output=True,
        env=environment,
    )


def test_transfer_archives_validates_and_removes_source(tmp_path: Path) -> None:
    environment, source_root, archive_root = _environment(tmp_path)

    completed = _run(environment)

    assert completed.returncode == 0, completed.stderr
    destination = archive_root / GITHUB_RUN_ID / "genkai" / "openfoam-genkai-v2-r-0123456789abcdef0123456789abcdef" / "large-output"
    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["schema_version"] == "openfoam-large-output-archive/v1"
    assert manifest["profile_run_id"] == PROFILE_RUN_ID
    assert manifest["vtune_result_available"] is True
    assert (destination / "vtune" / "vtune-result.tar.zst").is_file()
    assert (destination / "paraview" / "paraview-case.tar.zst").is_file()
    assert not (source_root / PROFILE_RUN_ID).exists()

    repeated = _run(environment)
    assert repeated.returncode == 0, repeated.stderr
    assert not any(path.name.startswith(".") for path in destination.parent.iterdir())


def test_transfer_keeps_paraview_when_vtune_produced_no_result(tmp_path: Path) -> None:
    environment, source_root, archive_root = _environment(tmp_path, vtune_result=False)

    completed = _run(environment)

    assert completed.returncode == 0, completed.stderr
    destination = archive_root / GITHUB_RUN_ID / "genkai" / "openfoam-genkai-v2-r-0123456789abcdef0123456789abcdef" / "large-output"
    manifest = json.loads((destination / "manifest.json").read_text())
    assert manifest["vtune_result_available"] is False
    assert not (destination / "vtune").exists()
    assert (destination / "paraview" / "paraview-case.tar.zst").is_file()
    assert [entry["path"] for entry in manifest["files"]] == ["paraview/paraview-case.tar.zst", "paraview/manifest.json"]
    assert not (source_root / PROFILE_RUN_ID).exists()


def test_transfer_uses_no_target_directory_move() -> None:
    assert 'mv -T -- "${staging}" "${destination}"' in SCRIPT.read_text()


def test_transfer_keeps_source_when_stream_is_invalid(tmp_path: Path) -> None:
    environment, source_root, archive_root = _environment(tmp_path, broken_ssh=True)

    completed = _run(environment)

    assert completed.returncode != 0
    assert (source_root / PROFILE_RUN_ID).is_dir()
    assert not (archive_root / GITHUB_RUN_ID / "genkai" / "openfoam-genkai-v2-r-0123456789abcdef0123456789abcdef" / "large-output").exists()


@pytest.mark.parametrize(
    "profile_run_id",
    ("../../escape", "r-short-123", "r-0123456789abcdef0123456789abcdef-bad/job"),
)
def test_transfer_rejects_unsafe_profile_run_id(tmp_path: Path, profile_run_id: str) -> None:
    environment, source_root, _ = _environment(tmp_path)

    completed = _run(environment, profile_run_id)

    assert completed.returncode == 64
    assert (source_root / PROFILE_RUN_ID).is_dir()


def test_transfer_refuses_mismatched_existing_archive(tmp_path: Path) -> None:
    environment, source_root, archive_root = _environment(tmp_path)
    destination = archive_root / GITHUB_RUN_ID / "genkai" / "openfoam-genkai-v2-r-0123456789abcdef0123456789abcdef" / "large-output"
    destination.mkdir(parents=True)
    (destination / "vtune").mkdir()
    (destination / "vtune" / "vtune-result.tar.zst").write_bytes(b"not an archive")
    (destination / "manifest.json").write_text("{}\n")

    completed = _run(environment)

    assert completed.returncode != 0
    assert (source_root / PROFILE_RUN_ID).is_dir()
