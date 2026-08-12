from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiment_metrics import WORKLOAD_MEMBERS, capture_workload, init_run
from experiment_metrics.cli import main


def _case(root: Path) -> Path:
    case = root / "case"
    for index, relative in enumerate(WORKLOAD_MEMBERS):
        path = case / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"member-{index}\n".encode())
    return case


def test_capture_workload_copies_and_seals_exact_members(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest.parents[1]
    case = _case(tmp_path)

    path = capture_workload(manifest, case, run_dir / "source/workload")
    document = json.loads(path.read_text())

    assert document["schema_version"] == "workload-manifest/v1"
    assert [item["path"] for item in document["members"]] == list(WORKLOAD_MEMBERS)
    for item in document["members"]:
        copied = run_dir / "source/workload" / item["path"]
        assert copied.read_bytes() == (case / item["path"]).read_bytes()
        assert item["size_bytes"] == copied.stat().st_size
        assert item["sha256"] == hashlib.sha256(copied.read_bytes()).hexdigest()


def test_capture_workload_rejects_missing_member_and_wrong_output_root(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    case = _case(tmp_path)
    (case / WORKLOAD_MEMBERS[-1]).unlink()
    with pytest.raises(FileNotFoundError):
        capture_workload(manifest, case, manifest.parents[1] / "source/workload")

    (case / WORKLOAD_MEMBERS[-1]).write_text("restored\n")
    with pytest.raises(ValueError, match="outside the bound run"):
        capture_workload(manifest, case, tmp_path / "foreign")


def test_capture_workload_cli(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    case = _case(tmp_path)
    assert (
        main(
            [
                "capture-workload",
                "--manifest",
                str(manifest),
                "--case-root",
                str(case),
                "--output-root",
                str(manifest.parents[1] / "source/workload"),
                "--registry",
                str(registry_path),
            ]
        )
        == 0
    )
    fragment = (
        manifest.parents[1]
        / "domain/fragments/runner.workload_manifest--workload.jsonl"
    )
    rows = [json.loads(line) for line in fragment.read_text().splitlines()]
    assert rows[0]["key"] == "workload.manifest"
    assert [row["key"] for row in rows[1:]] == [
        "workload.member.initial_u",
        "workload.member.initial_p",
        "workload.member.transport_properties",
        "workload.member.block_mesh_dict",
        "workload.member.control_dict",
        "workload.member.fv_schemes",
        "workload.member.fv_solution",
    ]


def test_manifest_rejects_noncanonical_repository_identity(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    with pytest.raises(ValueError, match="apac2026-openfoam"):
        init_run(
            None,
            tmp_path,
            identities,
            repository_id="owner/repository",
            registry_path=registry_path,
        )
