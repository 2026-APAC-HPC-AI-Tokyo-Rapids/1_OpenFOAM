from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "platforms/gadi/archive-openfoam-case.sh"
STAGE = ROOT / "platforms/gadi/stage-openfoam-case.sh"
STAGE_RANK_CONTEXT = ROOT / "platforms/gadi/stage-rank-context.sh"
COLLECT_RANK_PLACEMENT = ROOT / "platforms/gadi/collect-rank-placement.sh"


def test_gadi_stages_the_complete_case_on_every_node(tmp_path: Path) -> None:
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
    for path in case.rglob("*"):
        path.chmod(0o555 if path.is_dir() else 0o444)
    case.chmod(0o555)
    archive_dir = tmp_path / "archives" / cache_identity
    archive_dir.parent.mkdir()

    subprocess.run([SCRIPT, "create", expanded, archive_dir, cache_identity], check=True)
    subprocess.run([SCRIPT, "verify", archive_dir, cache_identity], check=True)
    archive_manifest = json.loads((archive_dir / "manifest.json").read_text())
    assert archive_manifest["schema_version"] == "openfoam-case-archive/v2"
    assert archive_manifest["number_of_subdomains"] == 4
    assert archive_manifest["archive"]["name"] == "case.tar.zst"

    contents = subprocess.run(
        ["tar", "-I", "zstd", "-tf", archive_dir / "case.tar.zst"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "constant/transportProperties" in contents
    assert "constant/polyMesh/owner" in contents
    for rank in range(4):
        assert f"processor{rank}/" in contents

    runtime = tmp_path / "runtime/OpenFOAM"
    (runtime / "etc").mkdir(parents=True)
    (runtime / "etc/bashrc").write_text(":\n")
    (runtime / "bin/tools").mkdir(parents=True)
    (runtime / "bin/tools/RunFunctions").write_text(
        'restore0Dir() { for directory in processor*; do mkdir -p "${directory}/0"; cp 0.orig/* "${directory}/0/"; done; }\n'
    )
    targets = [
        tmp_path / "node0/openfoam-case/occDrivAerStaticMesh",
        tmp_path / "node1/openfoam-case/occDrivAerStaticMesh",
    ]
    for target in targets:
        subprocess.run(
            [STAGE, archive_dir, cache_identity, "80", target, runtime.parent],
            check=True,
            env={"PATH": "/usr/bin:/bin"},
        )
        for rank in range(4):
            assert (target / f"processor{rank}/0/U").read_text() == "velocity\n"
        assert (target / "constant/polyMesh/owner").read_text() == "serial mesh\n"
        assert (target / "system/controlDict").read_text() == "endTime 80;\n"


def test_gadi_rank_context_stays_local_until_node_leader_collects_it(tmp_path: Path) -> None:
    run_manifest = tmp_path / "shared/run-manifest.json"
    run_manifest.parent.mkdir()
    run_manifest.write_text('{"schema_version":"run-manifest/v1"}\n')
    local_root = tmp_path / "jobfs/openfoam-run"
    subprocess.run([STAGE_RANK_CONTEXT, run_manifest, local_root], check=True)

    assert (local_root / "control/run-manifest.json").read_bytes() == run_manifest.read_bytes()
    placement = local_root / "source/placement"
    (placement / "rank-2.json").write_text("two\n")
    (placement / "rank-3.json").write_text("three\n")
    shared_placement = tmp_path / "shared/placement"
    subprocess.run([COLLECT_RANK_PLACEMENT, placement, shared_placement, "2"], check=True)

    assert sorted(path.name for path in shared_placement.iterdir()) == ["rank-2.json", "rank-3.json"]
