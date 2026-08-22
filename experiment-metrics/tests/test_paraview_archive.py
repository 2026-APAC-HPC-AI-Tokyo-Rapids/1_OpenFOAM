from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_SCRIPT = ROOT / "scripts/archive-paraview-case.sh"
FINALIZE_SCRIPT = ROOT / "scripts/finalize-paraview-case.sh"
RUN_ID = "r-0123456789abcdef0123456789abcdef"
PROFILE_RUN_ID = RUN_ID + "-12345.gadi-pbs"


def test_node_parts_become_one_paraview_archive(tmp_path: Path) -> None:
    case = tmp_path / "case"
    output = tmp_path / "output"
    for relative in ("0.orig", "constant", "system"):
        (case / relative).mkdir(parents=True)
        (case / relative / "input").write_text(relative + "\n")
    for rank in range(4):
        processor = case / f"processor{rank}"
        (processor / "constant" / "polyMesh").mkdir(parents=True)
        (processor / "150").mkdir()
        (processor / "150" / "U").write_text(f"rank {rank}\n")

    for node in range(2):
        environment = os.environ.copy()
        environment["TEST_NODE_ORDINAL"] = str(node)
        subprocess.run(["bash", ARCHIVE_SCRIPT, case, output, "2", "2", "TEST_NODE_ORDINAL"], check=True, env=environment)
    subprocess.run(["bash", FINALIZE_SCRIPT, output, RUN_ID, PROFILE_RUN_ID, "2"], check=True)

    archive = output / "paraview-case.tar.zst"
    listing = subprocess.check_output(["tar", "-I", "zstd", "-tf", archive], text=True).splitlines()
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["schema_version"] == "openfoam-paraview-archive/v1"
    assert manifest["archive"]["size_bytes"] == archive.stat().st_size
    assert "occDrivAerStaticMesh.foam" in listing
    assert all(any(path.startswith(f"processor{rank}/150/") for path in listing) for rank in range(4))
    assert not list(output.glob("*.tar"))
