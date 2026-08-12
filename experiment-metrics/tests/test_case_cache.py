from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts" / "prepare-openfoam-case.sh"
GEOMETRIC_SCRIPT = (
    Path(__file__).parents[2] / "scripts" / "prepare-openfoam-geometric-case.sh"
)
MULTILEVEL_448_SCRIPT = (
    Path(__file__).parents[2] / "scripts" / "prepare-openfoam-multilevel-448-case.sh"
)
RENUMBER_SCRIPT = (
    Path(__file__).parents[2] / "scripts" / "prepare-openfoam-renumbered-case.sh"
)


def _executable(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
    path.chmod(0o755)
    return path


def test_prepare_case_uses_content_and_rank_specific_cache(tmp_path: Path) -> None:
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
        [SCRIPT, source, tmp_path / "case-1", block_mesh, decompose_par, "120"],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    second = subprocess.run(
        [SCRIPT, source, tmp_path / "case-2", block_mesh, decompose_par, "120"],
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
            "120",
            "--require-cache",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert "cache_hit=true" in required.stdout


def test_prepare_case_separates_different_subdomain_counts(tmp_path: Path) -> None:
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    source = tmp_path / "source"
    (source / "system").mkdir(parents=True)
    (source / "system" / "controlDict").write_text("application icoFoam;\n")
    block_mesh = _executable(tmp_path / "blockMesh", "mkdir -p constant/polyMesh\n")
    decompose_par = _executable(
        tmp_path / "decomposePar",
        "ranks=$(sed -n 's/^numberOfSubdomains \\([0-9][0-9]*\\);/\\1/p' system/decomposeParDict.6)\n"
        "for rank in $(seq 0 $((ranks - 1))); do mkdir -p \"processor${rank}\"; done\n",
    )
    environment = {**os.environ, "HOME": str(home)}

    for ranks in ("120", "240"):
        subprocess.run(
            [SCRIPT, source, tmp_path / f"case-{ranks}", block_mesh, decompose_par, ranks],
            check=True,
            env=environment,
        )

    cache_root = tmp_path / "home" / "share" / "openfoam-case-cache"
    assert len([path for path in cache_root.iterdir() if path.is_dir()]) == 2
    assert (tmp_path / "case-120" / "processor119").is_dir()
    assert (tmp_path / "case-240" / "processor239").is_dir()


def test_multilevel_448_profile_is_exact_and_cacheable(tmp_path: Path) -> None:
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    source = tmp_path / "source"
    (source / "system").mkdir(parents=True)
    (source / "system" / "controlDict").write_text("application icoFoam;\n")
    block_mesh = _executable(tmp_path / "blockMesh", "mkdir -p constant/polyMesh\n")
    decompose_par = _executable(
        tmp_path / "decomposePar",
        "for rank in $(seq 0 447); do mkdir -p \"processor${rank}\"; done\n",
    )
    environment = {**os.environ, "HOME": str(home)}

    first = subprocess.run(
        [MULTILEVEL_448_SCRIPT, source, tmp_path / "case-1", block_mesh, decompose_par],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    second = subprocess.run(
        [
            MULTILEVEL_448_SCRIPT,
            source,
            tmp_path / "case-2",
            block_mesh,
            decompose_par,
            "--require-cache",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    dictionary = (tmp_path / "case-2/system/decomposeParDict.6").read_text()
    assert "cache_hit=false" in first.stdout
    assert "cache_hit=true" in second.stdout
    assert "numberOfSubdomains 448;" in dictionary
    assert "coeffs { n (1 2 2);" in dictionary
    assert "coeffs { n (1 2 4);" in dictionary
    assert "coeffs { n (7 2 1);" in dictionary
    assert (tmp_path / "case-2/processor447").is_dir()


def test_geometric_profiles_have_separate_immutable_caches(tmp_path: Path) -> None:
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    source = tmp_path / "source"
    (source / "system").mkdir(parents=True)
    (source / "system" / "controlDict").write_text("application icoFoam;\n")
    block_mesh = _executable(tmp_path / "blockMesh", "mkdir -p constant/polyMesh\n")
    decompose_par = _executable(
        tmp_path / "decomposePar",
        "for rank in $(seq 0 479); do mkdir -p \"processor${rank}\"; done\n",
    )
    environment = {**os.environ, "HOME": str(home)}

    profiles = {
        "hierarchical-6x8x10": "n (6 8 10);",
        "multilevel-node-numa-4n480": "numberOfSubdomains 15;",
    }
    for profile, expected_text in profiles.items():
        target = tmp_path / f"case-{profile}"
        subprocess.run(
            [GEOMETRIC_SCRIPT, source, target, block_mesh, decompose_par, profile],
            check=True,
            env=environment,
        )
        assert expected_text in (target / "system" / "decomposeParDict.6").read_text()
        assert (target / "processor479").is_dir()

    cache_root = tmp_path / "home" / "share" / "openfoam-case-cache"
    assert len([path for path in cache_root.iterdir() if path.is_dir()]) == 2


def test_renumber_profiles_derive_separate_immutable_scotch_caches(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home" / "user"
    home.mkdir(parents=True)
    source = tmp_path / "source"
    (source / "system").mkdir(parents=True)
    (source / "system" / "controlDict").write_text("application icoFoam;\n")
    block_mesh = _executable(tmp_path / "blockMesh", "mkdir -p constant/polyMesh\n")
    decompose_par = _executable(
        tmp_path / "decomposePar",
        "for rank in $(seq 0 447); do "
        'mkdir -p "processor${rank}/constant/polyMesh"; done\n',
    )
    renumber_mesh = _executable(
        tmp_path / "renumberMesh",
        'printf "%s\\n" "$(sed -n \'s/^blockSize /blockSize /p\' '
        'system/renumberMeshDict)" > processor0/constant/polyMesh/ordering\n',
    )
    mpiexec = _executable(
        tmp_path / "mpirun",
        "shift 4\nexec \"$@\"\n",
    )
    environment = {**os.environ, "HOME": str(home)}

    for profile in ("renumber-cuthill-4n448", "renumber-block32768-4n448"):
        target = tmp_path / f"case-{profile}"
        first = subprocess.run(
            [
                RENUMBER_SCRIPT,
                source,
                target,
                SCRIPT,
                block_mesh,
                decompose_par,
                renumber_mesh,
                mpiexec,
                profile,
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        assert "cache_hit=false" in first.stdout
        assert (target / "logs/renumberMesh.log").is_file()
        dictionary = (target / "system/renumberMeshDict").read_text()
        assert ("blockSize 32768;" in dictionary) == profile.endswith("block32768-4n448")

    cache_root = tmp_path / "home" / "share" / "openfoam-case-cache"
    entries = [path for path in cache_root.iterdir() if path.is_dir()]
    assert len(entries) == 3  # one shared Scotch base and two ordered derivatives
