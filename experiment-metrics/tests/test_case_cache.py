from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

from experiment_metrics.fact import canonical_json

SCRIPT = Path(__file__).parents[2] / "scripts/prepare-openfoam-case.sh"


def _executable(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
    path.chmod(0o755)
    return path


def _inputs(tmp_path: Path) -> tuple[Path, ...]:
    source = tmp_path / "source"
    for relative, content in {
        "0.orig/U": "U\n",
        "system/controlDict": "endTime 4000;\n",
        "system/controlDict.noWrite": "endTime 4000;\n",
        "system/fvSolution": "base\n",
        "system/fvSolution.fixedIter": "fixed\n",
        "system/include/caseDefinition": "nCores 512;\ndecompositionMethod hierarchical;\n",
    }.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    mesh_root = tmp_path / "mesh"
    (mesh_root / "polyMesh").mkdir(parents=True)
    (mesh_root / "polyMesh/owner").write_text("mesh\n")
    archive = tmp_path / "polyMesh_65M.tar.gz"
    with tarfile.open(archive, "w:gz") as stream:
        stream.add(mesh_root / "polyMesh", arcname="polyMesh")
    members = sorted(
        str(path.relative_to(source)) for path in source.rglob("*") if path.is_file()
    )
    projection = [
        {
            "path": member,
            "size_bytes": (source / member).stat().st_size,
            "sha256": hashlib.sha256((source / member).read_bytes()).hexdigest(),
        }
        for member in members
    ]
    definition = tmp_path / "workload.json"
    definition.write_text(
        json.dumps(
            {
                "schema_version": "openfoam-workload/v1",
                "workload_id": "occDrivAerStaticMesh-65M",
                "solver": "simpleFoam",
                "distribution": "OpenFOAM.com",
                "release": "v2512",
                "case": {
                    "repository": "test",
                    "commit": "test",
                    "path": "test",
                    "identity_sha256": hashlib.sha256(
                        canonical_json(projection).encode()
                    ).hexdigest(),
                    "members": members,
                },
                "mesh": {
                    "url": "https://example.invalid/mesh",
                    "size_bytes": archive.stat().st_size,
                    "md5": hashlib.md5(archive.read_bytes()).hexdigest(),
                    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "cells": 2,
                },
                "iteration_by_nodes": {"1": 40, "2": 80, "4": 150},
            }
        )
    )
    sidecar = tmp_path / "build-sidecar.json"
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": "build-sidecar/v1",
                "source_commits": [{"commit_role": "openfoam_source", "oid": "a" * 40}],
                "compile_flags": ["WM_COMPILE_OPTION=Opt"],
                "precision": "DP",
                "label_bits": 32,
                "runtime_objects": [
                    {
                        "kind": "executable",
                        "role": "checkMesh",
                        "path": "bin/checkMesh",
                        "sha256": "b" * 64,
                    },
                    {
                        "kind": "executable",
                        "role": "decomposePar",
                        "path": "bin/decomposePar",
                        "sha256": "c" * 64,
                    },
                    {
                        "kind": "shared_library",
                        "path": "lib/libOpenFOAM.so",
                        "sha256": "d" * 64,
                    },
                ],
            }
        )
    )
    counter = tmp_path / "counter"
    check_mesh = _executable(
        tmp_path / "checkMesh", f"printf '%s\\n' checkMesh >> \"{counter}\"\n"
    )
    decompose_par = _executable(
        tmp_path / "decomposePar",
        f"ranks=$(sed -n -E 's/^(nCores[[:space:]]+)([0-9]+);/\\2/p' system/include/caseDefinition)\nfor rank in $(seq 0 $((ranks - 1))); do mkdir -p \"processor${{rank}}\"; done\nprintf '%s\\n' decomposePar >> \"{counter}\"\n",
    )
    return source, archive, definition, sidecar, check_mesh, decompose_par, counter


def test_prepare_case_uses_content_and_rank_specific_cache(tmp_path: Path) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, counter = _inputs(
        tmp_path
    )
    cache_root = tmp_path / "cache"
    base = [
        SCRIPT,
        source,
        tmp_path / "case-1",
        decompose_par,
        check_mesh,
        archive,
        definition,
        sidecar,
        "4",
        cache_root,
    ]
    first = subprocess.run(base, check=True, capture_output=True, text=True)
    second = subprocess.run(
        [*base[:2], tmp_path / "case-2", *base[3:]],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "cache_hit=false" in first.stdout
    assert "cache_hit=true" in second.stdout
    assert counter.read_text().splitlines() == ["checkMesh", "decomposePar"]
    assert (tmp_path / "case-2/processor3").is_dir()
    assert (tmp_path / "case-2/system/controlDict").read_text() == "endTime 4000;\n"
    assert (tmp_path / "case-2/system/fvSolution").read_text() == "fixed\n"
    manifest = json.loads(next(cache_root.glob("*/manifest.json")).read_text())
    assert manifest["schema_version"] == "openfoam-case-cache/v4"
    assert len(manifest["prepare_toolchain_identity"]) == 64

    required = subprocess.run(
        [*base[:2], tmp_path / "case-3", *base[3:], "--require-cache"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "cache_hit=true" in required.stdout


def test_prepare_case_separates_different_subdomain_counts(tmp_path: Path) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, _ = _inputs(
        tmp_path
    )
    cache_root = tmp_path / "cache"
    for ranks in ("2", "4"):
        subprocess.run(
            [
                SCRIPT,
                source,
                tmp_path / f"case-{ranks}",
                decompose_par,
                check_mesh,
                archive,
                definition,
                sidecar,
                ranks,
                cache_root,
            ],
            check=True,
        )
    assert len([path for path in cache_root.iterdir() if path.is_dir()]) == 2


def test_prepare_case_separates_different_build_toolchains(tmp_path: Path) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, counter = _inputs(
        tmp_path
    )
    cache_root = tmp_path / "cache"
    subprocess.run(
        [
            SCRIPT,
            source,
            tmp_path / "case-opt",
            decompose_par,
            check_mesh,
            archive,
            definition,
            sidecar,
            "4",
            cache_root,
        ],
        check=True,
    )
    document = json.loads(sidecar.read_text())
    document["compile_flags"] = ["WM_COMPILE_OPTION=OptAVX512"]
    sidecar.write_text(json.dumps(document))
    subprocess.run(
        [
            SCRIPT,
            source,
            tmp_path / "case-avx512",
            decompose_par,
            check_mesh,
            archive,
            definition,
            sidecar,
            "4",
            cache_root,
        ],
        check=True,
    )

    assert len([path for path in cache_root.iterdir() if path.is_dir()]) == 2
    assert counter.read_text().splitlines() == [
        "checkMesh",
        "decomposePar",
        "checkMesh",
        "decomposePar",
    ]


def test_prepare_case_can_resolve_identity_without_expanding(tmp_path: Path) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, counter = _inputs(
        tmp_path
    )
    cache_root = tmp_path / "cache"
    completed = subprocess.run(
        [
            SCRIPT,
            source,
            "-",
            decompose_par,
            check_mesh,
            archive,
            definition,
            sidecar,
            "4",
            cache_root,
            "--identity-only",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "cache_identity=" in completed.stdout
    assert f"cache_dir={cache_root}/" in completed.stdout
    assert not cache_root.exists()
    assert not counter.exists()
