from __future__ import annotations

# ruff: noqa: E501
import hashlib
import json
import time
from pathlib import Path

import pytest

from experiment_metrics import init_run
from experiment_metrics.postrun import (
    mesh_facts_from_logs,
    mesh_topology_fact,
    minimal_hardware_fact,
    partition_facts,
    partition_requested_fact,
    profile_hardware_facts,
)
from experiment_metrics.probes.capture_hardware import main as capture_hardware


def _locator(path: str) -> dict[str, object]:
    return {
        "locator_kind": "runtime_relative_ephemeral",
        "path": path,
        "size_bytes": 1,
        "sha256": "a" * 64,
    }


def _write_mesh_logs(tmp_path: Path, ranks: int) -> tuple[Path, Path, Path]:
    block_log = tmp_path / "blockMesh.log"
    block_log.write_text(
        "\n".join(
            (
                "Mesh Information",
                f"  nPoints: {ranks * 2}",
                f"  nCells: {ranks}",
                f"  nFaces: {ranks * 3}",
                f"  nInternalFaces: {ranks * 2}",
            )
        )
    )
    decompose_log = tmp_path / "decomposePar.log"
    sections = []
    for rank in range(ranks):
        peer = rank + 1 if rank % 2 == 0 else rank - 1
        sections.append(
            "\n".join(
                (
                    f"Processor {rank}",
                    "    Number of cells = 1",
                    "    Number of points = 2",
                    f"    Number of faces shared with processor {peer} = 7",
                    "    Number of processor patches = 1",
                    "    Number of processor faces = 7",
                    "    Number of boundary faces = 0",
                )
            )
        )
    # This unindented aggregate appears after the last processor in real logs
    # and must not be mistaken for the last rank's value.
    decompose_log.write_text(
        "\n\n".join(sections) + f"\n\nNumber of processor faces = {ranks * 7}\n"
    )
    dictionary = tmp_path / "decomposeParDict"
    dictionary.write_text(f"numberOfSubdomains {ranks};\nmethod scotch;\n")
    return block_log, decompose_log, dictionary


def test_mesh_facts_are_parsed_from_existing_small_logs(tmp_path: Path) -> None:
    block_log, decompose_log, dictionary = _write_mesh_logs(tmp_path, 2)

    topology, requested, observed = mesh_facts_from_logs(
        block_log, decompose_log, dictionary
    )

    assert topology.logical_value == {
        "schema_version": "mesh-topology/v2",
        "cells": 2,
        "faces": 6,
        "points": 4,
        "internal_faces": 4,
    }
    assert requested.logical_value["subdomains"] == 2
    assert requested.logical_value["method"] == "scotch"
    assert requested.logical_value["schema_version"] == "partition-requested/v2"
    assert observed.logical_value["schema_version"] == "partition-observed/v2"
    assert observed.logical_value["subdomains"] == [
        {
            "rank": 0,
            "cell_count": 1,
            "processor_patch_count": 1,
            "processor_face_count": 7,
        },
        {
            "rank": 1,
            "cell_count": 1,
            "processor_patch_count": 1,
            "processor_face_count": 7,
        },
    ]
    assert observed.logical_value["interfaces"] == [
        {"lower_rank": 0, "upper_rank": 1, "face_count": 7}
    ]


def test_mesh_log_parser_is_subsecond_at_120_ranks(tmp_path: Path) -> None:
    inputs = _write_mesh_logs(tmp_path, 120)

    started = time.monotonic()
    facts = mesh_facts_from_logs(*inputs)
    elapsed = time.monotonic() - started

    assert len(facts[2].logical_value["subdomains"]) == 120
    assert elapsed < 1.0


def test_mesh_log_parser_rejects_asymmetric_interfaces(tmp_path: Path) -> None:
    block_log, decompose_log, dictionary = _write_mesh_logs(tmp_path, 2)
    decompose_log.write_text(
        decompose_log.read_text().replace(
            "faces shared with processor 0 = 7", "faces shared with processor 0 = 8"
        )
    )

    with pytest.raises(ValueError, match="asymmetric"):
        mesh_facts_from_logs(block_log, decompose_log, dictionary)


def test_closed_postrun_reducers_validate_hardware_mesh_and_partition(
    tmp_path: Path,
) -> None:
    hardware = tmp_path / "node-0.json"
    hardware.write_text(
        json.dumps(
            {
                "schema_version": "hardware-node/v1",
                "node_ordinal": 0,
                "hostname": "node-a",
                "commands": {
                    "lscpu": {
                        "argv": ["lscpu", "--json"],
                        "exit_code": 0,
                        "stderr_member": "source/hardware/lscpu-node-0.stderr.txt",
                    }
                },
                "lscpu_json": {
                    "lscpu": [
                        {"field": "Architecture:", "data": "x86_64"},
                        {"field": "Socket(s):", "data": "2"},
                        {"field": "Core(s) per socket:", "data": "4"},
                    ]
                },
                "platform_settings": {
                    "kernel_release": "6.0",
                    "online_cpus": [0],
                    "isolated_cpus": [],
                    "nohz_full_cpus": [],
                    "memory": {
                        "total_bytes": 1,
                        "hugepage_size_bytes": None,
                        "hugepages_total": None,
                    },
                    "numa_balancing_enabled": False,
                    "boost": {"source_path": None, "raw": None, "enabled": None},
                    "cpufreq_policies": [],
                },
            }
        )
    )
    projection = minimal_hardware_fact(
        hardware, run_id="r-" + "a" * 32, source_member="source/hardware/node-0.json"
    )
    assert projection.logical_value["cpu_identity"]["physical_cores"] == 8
    assert (
        projection.logical_value["source_sha256"]
        == hashlib.sha256(hardware.read_bytes()).hexdigest()
    )

    topology = tmp_path / "topology.json"
    topology.write_text(
        '{"schema_version":"mesh-topology/v1","cells":2,"faces":3,"points":4,"internal_faces":1}'
    )
    topology_fact = mesh_topology_fact(topology)
    dictionary = tmp_path / "decomposeParDict"
    dictionary.write_text("numberOfSubdomains 1;\nmethod scotch;\n")
    observed = tmp_path / "partition.json"
    locators = {
        name: _locator(f"constant/polyMesh/{name}")
        for name in ("points", "faces", "owner", "neighbour", "boundary")
    }
    addressing = {
        name: _locator(f"processor0/{name}")
        for name in ("cell", "face", "point", "boundary")
    }
    observed.write_text(
        json.dumps(
            {
                "schema_version": "partition-observed/v1",
                "serial_mesh": locators,
                "subdomains": [
                    {
                        "rank": 0,
                        "cell_count": 2,
                        "mesh": locators,
                        "addressing": addressing,
                    }
                ],
                "interfaces": [],
            }
        )
    )
    facts = partition_facts(dictionary, observed, topology=topology_fact.logical_value)
    assert facts[0].logical_value["method"] == "scotch"


def test_requested_partition_accepts_tracked_geometric_methods(tmp_path: Path) -> None:
    for method in ("hierarchical", "multiLevel"):
        dictionary = tmp_path / f"decomposeParDict-{method}"
        dictionary.write_text(f"numberOfSubdomains 480;\nmethod {method};\n")
        fact = partition_requested_fact(dictionary)
        assert fact.logical_value == {
            "schema_version": "partition-requested/v2",
            "source_sha256": hashlib.sha256(dictionary.read_bytes()).hexdigest(),
            "subdomains": 480,
            "method": method,
        }


def test_postrun_rejects_partition_cell_count_mismatch(tmp_path: Path) -> None:
    topology = tmp_path / "topology.json"
    topology.write_text(
        '{"schema_version":"mesh-topology/v1","cells":1,"faces":1,"points":1,"internal_faces":0}'
    )
    dictionary = tmp_path / "decomposeParDict"
    dictionary.write_text("numberOfSubdomains 1;\nmethod scotch;\n")
    observed = tmp_path / "partition.json"
    locator = _locator("x")
    observed.write_text(
        json.dumps(
            {
                "schema_version": "partition-observed/v1",
                "serial_mesh": {
                    name: locator
                    for name in ("points", "faces", "owner", "neighbour", "boundary")
                },
                "subdomains": [
                    {
                        "rank": 0,
                        "cell_count": 2,
                        "mesh": {
                            name: locator
                            for name in (
                                "points",
                                "faces",
                                "owner",
                                "neighbour",
                                "boundary",
                            )
                        },
                        "addressing": {
                            name: locator
                            for name in ("cell", "face", "point", "boundary")
                        },
                    }
                ],
                "interfaces": [],
            }
        )
    )
    with pytest.raises(ValueError, match="cell total"):
        partition_facts(
            dictionary, observed, topology=mesh_topology_fact(topology).logical_value
        )


def test_hardware_probe_writes_minimal_and_profile_sources(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest.parents[1]
    common = [
        "--subject-kind",
        "regular_run",
        "--subject-id",
        run_dir.name,
        "--manifest",
        str(manifest),
        "--node-ordinal",
        "0",
    ]
    assert (
        capture_hardware(
            [
                "--mode",
                "minimal",
                *common,
                "--output-root",
                str(run_dir / "source/hardware"),
            ]
        )
        == 0
    )
    assert (run_dir / "source/hardware/node-0.json").is_file()
    assert (
        capture_hardware(
            [
                "--mode",
                "profile-postrun",
                *common,
                "--output-root",
                str(run_dir / "profile/raw/hardware"),
            ]
        )
        == 0
    )
    assert (run_dir / "profile/raw/hardware/node-0/capture.json").is_file()
    profile_facts = profile_hardware_facts(
        run_dir / "profile/raw/hardware", run_id=run_dir.name, expected_nodes=1
    )
    assert profile_facts[0].key == "profile.hardware.node.0.summary"
    assert any(
        fact.key.startswith("profile.hardware.node.0.numa.") for fact in profile_facts
    )
