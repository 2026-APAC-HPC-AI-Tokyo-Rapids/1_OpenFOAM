from __future__ import annotations

# ruff: noqa: E501
import hashlib
import json
from pathlib import Path

import pytest

from experiment_metrics import init_run
from experiment_metrics.postrun import (
    mesh_topology_fact,
    minimal_hardware_fact,
    partition_facts,
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
