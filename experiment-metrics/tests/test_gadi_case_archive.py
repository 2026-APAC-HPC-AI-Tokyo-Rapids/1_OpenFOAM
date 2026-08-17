from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "platforms/gadi/archive-openfoam-case.sh"
STAGE = ROOT / "platforms/gadi/stage-openfoam-case.sh"


def test_gadi_case_archive_splits_processor_directories_by_node(tmp_path: Path) -> None:
    cache_identity = "a" * 64
    expanded = tmp_path / "expanded"
    case = expanded / "case"
    (case / "constant/polyMesh").mkdir(parents=True)
    (case / "constant/transportProperties").write_text("transport\n")
    (case / "constant/polyMesh/owner").write_text("serial mesh\n")
    (case / "system").mkdir()
    (case / "system/controlDict").write_text("endTime 40;\n")
    (case / "0.orig").mkdir()
    (case / "0.orig/U").write_text("velocity\n")
    (case / "logs").mkdir()
    (case / "logs/checkMesh.log").write_text("mesh\n")
    for rank in range(4):
        processor = case / f"processor{rank}/constant/polyMesh"
        processor.mkdir(parents=True)
        (processor / "owner").write_text(f"rank {rank}\n")
    (expanded / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "openfoam-case-cache/v4",
                "cache_identity": cache_identity,
                "number_of_subdomains": 4,
            }
        )
    )
    archive_dir = tmp_path / "archives" / cache_identity
    archive_dir.parent.mkdir()

    subprocess.run(
        [SCRIPT, "create", expanded, archive_dir, cache_identity, "2", "2"], check=True
    )
    subprocess.run(
        [SCRIPT, "verify", archive_dir, cache_identity, "2", "2"], check=True
    )

    common = subprocess.run(
        ["tar", "-I", "zstd", "-tf", archive_dir / "common.tar.zst"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    node0 = subprocess.run(
        ["tar", "-I", "zstd", "-tf", archive_dir / "node-000.tar.zst"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    node1 = subprocess.run(
        ["tar", "-I", "zstd", "-tf", archive_dir / "node-001.tar.zst"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "constant/transportProperties" in common
    assert "constant/polyMesh/owner" not in common
    assert "processor0/" in node0 and "processor1/" in node0
    assert "processor2/" not in node0
    assert "processor2/" in node1 and "processor3/" in node1
    assert "processor0/" not in node1

    runtime = tmp_path / "runtime/OpenFOAM"
    (runtime / "etc").mkdir(parents=True)
    (runtime / "etc/bashrc").write_text(":\n")
    (runtime / "bin/tools").mkdir(parents=True)
    (runtime / "bin/tools/RunFunctions").write_text(
        'restore0Dir() { for directory in processor*; do mkdir -p "${directory}/0"; cp 0.orig/* "${directory}/0/"; done; }\n'
    )
    target = tmp_path / "jobfs/openfoam-case/occDrivAerStaticMesh"
    subprocess.run(
        [STAGE, archive_dir, cache_identity, "2", "2", "80", target, runtime.parent],
        check=True,
        env={"PATH": "/usr/bin:/bin", "PMI_RANK": "1"},
    )

    assert (target / "processor2/0/U").read_text() == "velocity\n"
    assert (target / "processor3/0/U").read_text() == "velocity\n"
    assert not (target / "processor0").exists()
    assert not (target / "constant/polyMesh").exists()
    assert (target / "system/controlDict").read_text() == "endTime 80;\n"
