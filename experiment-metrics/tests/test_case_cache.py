from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from experiment_metrics.fact import canonical_json

SCRIPT = Path(__file__).parents[2] / "scripts/prepare-openfoam-case.sh"
LOGIN_CHECK = SCRIPT.with_name("check-openfoam-case-cache.sh")


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
        "system/decomposeParDict": "numberOfSubdomains $nCores;\nmethod $decompositionMethod;\n",
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


@pytest.mark.parametrize("cluster", ["genkai", "gadi", "aspire2a"])
def test_login_cache_check_skips_compute_only_for_matching_valid_cache(tmp_path: Path, cluster: str) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, counter = _inputs(tmp_path)
    provision = tmp_path / "provision"
    (provision / "benchmark").mkdir(parents=True)
    (provision / "control").mkdir()
    (provision / "scripts").symlink_to(SCRIPT.parent, target_is_directory=True)
    (provision / "platforms").symlink_to(SCRIPT.parents[1] / "platforms", target_is_directory=True)
    (provision / "benchmark/occDrivAerStaticMesh").symlink_to(source, target_is_directory=True)
    (provision / "benchmark/workload.json").symlink_to(definition)
    (provision / "control/build-sidecar.json").symlink_to(sidecar)
    cache_root = tmp_path / "cache"
    subdomains = "128" if cluster == "aspire2a" else "4"
    changed_subdomains = "256" if cluster == "aspire2a" else "8"
    command = [LOGIN_CHECK, cluster, provision, subdomains, cache_root, archive]
    assert subprocess.run(command, capture_output=True).returncode == 75
    assert not counter.exists()

    expanded = tmp_path / "expanded" if cluster in {"gadi", "aspire2a"} else cache_root
    prepare_options = ["--multi-level-ranks-per-node", "128"] if cluster == "aspire2a" else []
    prepared = subprocess.run([SCRIPT, source, "-", decompose_par, check_mesh, archive, definition, sidecar, subdomains, expanded, *prepare_options], check=True, capture_output=True, text=True)
    cache_dir = Path(next(line.removeprefix("cache_dir=") for line in prepared.stdout.splitlines() if line.startswith("cache_dir=")))
    if cluster in {"gadi", "aspire2a"}:
        archived = cache_root / cache_dir.name
        subprocess.run([SCRIPT.parents[1] / f"platforms/{cluster}/archive-openfoam-case.sh", "create", cache_dir, archived, cache_dir.name], check=True, capture_output=True)
        cache_dir = archived
    hits_before = counter.read_text()
    hit = subprocess.run(command, check=True, capture_output=True, text=True)
    assert "cache_hit=true" in hit.stdout
    assert str(cache_dir) in hit.stdout
    assert counter.read_text() == hits_before
    # MPI decomposition and toolchain changes never reuse the old READY marker.
    assert subprocess.run([*command[:3], changed_subdomains, *command[4:]], capture_output=True).returncode == 75
    original = sidecar.read_text()
    sidecar.write_text(original.replace("WM_COMPILE_OPTION=Opt", "WM_COMPILE_OPTION=Debug"))
    assert subprocess.run(command, capture_output=True).returncode == 75
    sidecar.write_text(original)
    case_member = source / "0.orig/U"
    case_member.write_text("different input\n")
    assert subprocess.run(command, capture_output=True).returncode == 75
    case_member.write_text("U\n")
    if cluster in {"gadi", "aspire2a"}:
        (cache_dir / "case.tar.zst").write_bytes(b"damaged archive")
    else:
        (cache_dir / "READY").unlink()
    assert subprocess.run(command, capture_output=True).returncode == 75
    assert counter.read_text() == hits_before
    archive.write_bytes(b"invalid official mesh")
    assert subprocess.run(command, capture_output=True).returncode == 2


@pytest.mark.parametrize("cluster", ["genkai", "gadi", "aspire2a"])
def test_workflow_checks_cache_before_prepare_submission(cluster: str) -> None:
    workflow = (SCRIPT.parents[1] / f".github/workflows/{cluster}.yml").read_text()
    stage = workflow.split("  prepare-case:", 1)[1].split("\n  run:", 1)[0]
    assert stage.index(f'check-openfoam-case-cache.sh" {cluster}') < stage.index("$(pjsub" if cluster == "genkai" else "$(qsub")
    assert 'then\n            exit 0\n          else\n            test "$?" -eq 75\n          fi' in stage
    provision = workflow.split("  provision:", 1)[1].split("  prepare-case:", 1)[0]
    assert "scripts/check-openfoam-case-cache.sh" in provision


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


def test_prepare_case_reports_tool_log_before_failed_temporary_is_removed(
    tmp_path: Path,
) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, _ = _inputs(
        tmp_path
    )
    _executable(check_mesh, "printf '%s\\n' 'decisive checkMesh failure' >&2\nexit 23\n")
    cache_root = tmp_path / "cache"

    failed = subprocess.run(
        [
            SCRIPT,
            source,
            tmp_path / "case",
            decompose_par,
            check_mesh,
            archive,
            definition,
            sidecar,
            "4",
            cache_root,
        ],
        capture_output=True,
        text=True,
    )

    assert failed.returncode == 23
    assert "checkMesh.log" in failed.stderr
    assert "decisive checkMesh failure" in failed.stderr
    assert list(cache_root.glob("*.tmp.*")) == []


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


def test_prepare_case_records_node_aware_multilevel_decomposition(tmp_path: Path) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, _ = _inputs(
        tmp_path
    )
    cache_root = tmp_path / "cache"
    target = tmp_path / "case"
    subprocess.run(
        [
            SCRIPT,
            source,
            target,
            decompose_par,
            check_mesh,
            archive,
            definition,
            sidecar,
            "512",
            cache_root,
            "--multi-level-ranks-per-node",
            "128",
        ],
        check=True,
    )

    manifest = json.loads(next(cache_root.glob("*/manifest.json")).read_text())
    assert manifest["method"] == "multiLevel"
    assert manifest["domains"] == [4, 128]
    assert "decompositionMethod multiLevel;" in (
        target / "system/include/caseDefinition"
    ).read_text()
    dictionary = (target / "system/decomposeParDict").read_text()
    assert "method $decompositionMethod;" in dictionary
    assert "multiLevelCoeffs" in dictionary
    assert "domains (4 128);" in dictionary


def test_prepare_case_records_socket_aware_multilevel_decomposition(tmp_path: Path) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, _ = _inputs(tmp_path)
    cache_root = tmp_path / "cache"
    target = tmp_path / "case"
    base = [SCRIPT, source, target, decompose_par, check_mesh, archive, definition, sidecar, "512", cache_root]
    subprocess.run([*base, "--multi-level-domains", "4,2,64"], check=True)

    manifest = json.loads(next(cache_root.glob("*/manifest.json")).read_text())
    assert manifest["method"] == "multiLevel"
    assert manifest["domains"] == [4, 2, 64]
    assert "domains (4 2 64);" in (target / "system/decomposeParDict").read_text()
    assert subprocess.run([*base, "--identity-only", "--multi-level-domains", "4,2,64"], check=True, capture_output=True).stdout
    assert subprocess.run([*base, "--identity-only", "--multi-level-domains", "4,2,16"], capture_output=True).returncode != 0
    assert subprocess.run([*base, "--identity-only", "--multi-level-ranks-per-node", "128", "--multi-level-domains", "4,2,64"], capture_output=True).returncode != 0


def test_prepare_case_keeps_scotch_and_multilevel_caches_separate(tmp_path: Path) -> None:
    source, archive, definition, sidecar, check_mesh, decompose_par, _ = _inputs(
        tmp_path
    )
    cache_root = tmp_path / "cache"
    base = [SCRIPT, source, "-", decompose_par, check_mesh, archive, definition, sidecar, "128", cache_root]
    subprocess.run(base, check=True)
    subprocess.run([*base, "--multi-level-ranks-per-node", "128"], check=True)

    manifests = [json.loads(path.read_text()) for path in cache_root.glob("*/manifest.json")]
    assert {manifest["method"] for manifest in manifests} == {"scotch", "multiLevel"}
    assert len(manifests) == 2


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
