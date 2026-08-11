from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "prepare-openfoam-case.sh"


def _executable(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
    path.chmod(0o755)
    return path


def test_prepare_case_uses_script_sha_cache(tmp_path: Path) -> None:
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    source = tmp_path / "source"
    (source / "system").mkdir(parents=True)
    (source / "0").mkdir()
    (source / "system" / "controlDict").write_text("application icoFoam;\n")
    counter = tmp_path / "counter"
    block_mesh = _executable(
        tmp_path / "blockMesh",
        f"mkdir -p constant/polyMesh\nprintf '%s\\n' blockMesh >> \"{counter}\"\n",
    )
    decompose_par = _executable(
        tmp_path / "decomposePar",
        "for rank in $(seq 0 119); do "
        'mkdir -p "processor${rank}/constant/polyMesh"; '
        "done\n"
        f"printf '%s\\n' decomposePar >> \"{counter}\"\n",
    )
    environment = {**os.environ, "HOME": str(home)}

    first = subprocess.run(
        [SCRIPT, source, tmp_path / "case-1", block_mesh, decompose_par],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    second = subprocess.run(
        [SCRIPT, source, tmp_path / "case-2", block_mesh, decompose_par],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert "cache_hit=false" in first.stdout
    assert "cache_hit=true" in second.stdout
    assert "flock" not in SCRIPT.read_text(encoding="utf-8")
    assert counter.read_text().splitlines() == ["blockMesh", "decomposePar"]
    cache_root = tmp_path / "home" / "share" / "openfoam-case-cache"
    cache_entries = [path for path in cache_root.iterdir() if path.is_dir()]
    assert len(cache_entries) == 1
    assert len(cache_entries[0].name) == 64
    assert (tmp_path / "case-2").is_symlink()
    assert (tmp_path / "case-2" / "processor119").is_dir()
    assert not os.access(tmp_path / "case-2" / "system" / "controlDict", os.W_OK)

    required = subprocess.run(
        [
            SCRIPT,
            source,
            tmp_path / "case-3",
            block_mesh,
            decompose_par,
            "--require-cache",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert "cache_hit=true" in required.stdout
