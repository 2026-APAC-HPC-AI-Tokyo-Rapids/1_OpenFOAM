from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/remove-openfoam-runtime.sh"
RUN_ID = "r-0123456789abcdef0123456789abcdef"


def _environment(tmp_path: Path) -> dict[str, str]:
    fake_connection = tmp_path / "genkai-shell"
    fake_connection.write_text("#!/bin/sh\nexec \"$@\"\n")
    fake_connection.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = f"{tmp_path}:{environment['PATH']}"
    return environment


def _run(environment: dict[str, str], run_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(SCRIPT), "--cluster", "genkai", "--connection", "genkai-shell", "--run-dir", str(run_dir)], check=False, text=True, capture_output=True, env=environment)


def test_removes_exact_runtime_directory(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    run_dir = tmp_path / "openfoam-runs" / "runs" / RUN_ID
    run_dir.mkdir(parents=True)
    (run_dir / "large-output").mkdir()

    completed = _run(environment, run_dir)

    assert completed.returncode == 0, completed.stderr
    assert not run_dir.exists()
    assert run_dir.parent.is_dir()


def test_removes_runtime_with_read_only_openfoam_directories(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    run_dir = tmp_path / "openfoam-runs" / "runs" / RUN_ID
    mesh = run_dir / "work" / "occDrivAerStaticMesh" / "processor0" / "constant" / "polyMesh"
    mesh.mkdir(parents=True)
    (mesh / "points").write_text("mesh\n")
    mesh.chmod(0o555)
    mesh.parent.chmod(0o555)

    completed = _run(environment, run_dir)

    assert completed.returncode == 0, completed.stderr
    assert not run_dir.exists()


def test_missing_runtime_is_idempotent(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    run_dir = tmp_path / "openfoam-runs" / "runs" / RUN_ID

    completed = _run(environment, run_dir)

    assert completed.returncode == 0, completed.stderr


def test_rejects_missing_connection(tmp_path: Path) -> None:
    run_dir = tmp_path / "openfoam-runs" / "runs" / RUN_ID
    run_dir.mkdir(parents=True)

    completed = subprocess.run(["bash", str(SCRIPT), "--cluster", "genkai", "--run-dir", str(run_dir)], check=False, text=True, capture_output=True, env=_environment(tmp_path))

    assert completed.returncode == 64
    assert "--connectionが必要" in completed.stderr
    assert run_dir.is_dir()


def test_rejects_connection_for_another_cluster(tmp_path: Path) -> None:
    run_dir = tmp_path / "openfoam-runs" / "runs" / RUN_ID
    run_dir.mkdir(parents=True)
    environment = os.environ.copy()

    completed = subprocess.run(["bash", str(SCRIPT), "--cluster", "genkai", "--connection", "gadi-shell", "--run-dir", str(run_dir)], check=False, text=True, capture_output=True, env=environment)

    assert completed.returncode == 64
    assert "genkai-shellを指定" in completed.stderr
    assert run_dir.is_dir()


def test_rejects_unavailable_connection(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    (tmp_path / "genkai-shell").unlink()
    # Bash itself is invoked by absolute path; prevent finding a real wrapper.
    environment["PATH"] = str(tmp_path)
    run_dir = tmp_path / "runs" / RUN_ID
    run_dir.mkdir(parents=True)
    (tmp_path / "basename").symlink_to("/usr/bin/basename")
    completed = subprocess.run(["/bin/bash", str(SCRIPT), "--cluster", "genkai", "--connection", "genkai-shell", "--run-dir", str(run_dir)], check=False, text=True, capture_output=True, env=environment)
    assert completed.returncode == 69
    assert "接続コマンドが見つかりません" in completed.stderr
    assert run_dir.is_dir()


def test_rejects_runtime_outside_runs_parent(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    run_dir = tmp_path / "other" / RUN_ID
    run_dir.mkdir(parents=True)

    completed = _run(environment, run_dir)

    assert completed.returncode != 0
    assert run_dir.is_dir()


def test_rejects_symlink_runtime(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    actual = tmp_path / "actual" / RUN_ID
    actual.mkdir(parents=True)
    runs = tmp_path / "openfoam-runs" / "runs"
    runs.mkdir(parents=True)
    link = runs / RUN_ID
    link.symlink_to(actual, target_is_directory=True)

    completed = _run(environment, link)

    assert completed.returncode != 0
    assert actual.is_dir()
