from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE_SCRIPT = ROOT / "platforms/gadi/stage-openfoam-runtime.sh"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gadi_stages_compute_tools_with_the_openfoam_runtime(tmp_path: Path) -> None:
    build_source = tmp_path / "build-source"
    solver = build_source / "OpenFOAM/platforms/linux64IcxDPInt32Opt/bin/simpleFoam"
    solver.parent.mkdir(parents=True)
    solver.write_text("#!/bin/sh\n")
    solver.chmod(0o755)
    build_archive = tmp_path / "build.tar.zst"
    subprocess.run(["tar", "-I", "zstd", "-cf", build_archive, "-C", build_source, "."], check=True)
    sidecar = tmp_path / "build-sidecar.json"
    sidecar.write_text(json.dumps({"build_archive": {"size_bytes": build_archive.stat().st_size, "sha256": _sha256(build_archive)}}) + "\n")

    tools_source = tmp_path / "tools-source"
    rank_python = tools_source / "experiment-metrics/.venv/bin/python"
    profiler = tools_source / "scripts/exec-profiler.sh"
    rank_python.parent.mkdir(parents=True)
    profiler.parent.mkdir(parents=True)
    rank_python.write_text("#!/bin/sh\n")
    profiler.write_text("#!/bin/sh\n")
    rank_python.chmod(0o755)
    profiler.chmod(0o755)
    tools_archive = tmp_path / "compute-tools.tar.zst"
    subprocess.run(["tar", "-I", "zstd", "-cf", tools_archive, "-C", tools_source, "."], check=True)
    tools_manifest = tmp_path / "compute-tools.json"
    tools_manifest.write_text(json.dumps({"schema_version": "openfoam-compute-tools-archive/v1", "archive": {"path": "compute-tools.tar.zst", "size_bytes": tools_archive.stat().st_size, "sha256": _sha256(tools_archive)}}) + "\n")

    target = tmp_path / "runtime"
    subprocess.run(["bash", STAGE_SCRIPT, build_archive, sidecar, tools_archive, tools_manifest, target], check=True)

    assert (target / "OpenFOAM/platforms/linux64IcxDPInt32Opt/bin/simpleFoam").is_file()
    assert (target / "experiment-metrics/.venv/bin/python").is_file()
    assert (target / "scripts/exec-profiler.sh").is_file()
