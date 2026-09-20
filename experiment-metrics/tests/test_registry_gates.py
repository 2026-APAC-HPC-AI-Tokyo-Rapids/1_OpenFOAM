from __future__ import annotations

from pathlib import Path

import pytest

from experiment_metrics.registry import Registry


def test_default_registry_does_not_require_removed_pstream_instrumentation() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")
    required = registry.required_keys("bench")

    assert not {key for key in required if key.startswith("solver.pstream.")}
    assert {
        "solver.runtime_header",
        "solver.step_timings",
        "solver.pressure_solves",
        "solver.log_markers",
        "result.official",
        "source.track.head_commit",
        "build.provenance",
        "build.provision",
        "workload.manifest",
        "network.imb_mpi1.process_count",
        "network.imb_mpi1.message_size.min_bytes",
        "network.imb_mpi1.message_size.max_bytes",
        "network.imb_mpi1.iteration.max_per_sample",
        "network.imb_mpi1.iteration.time_limit_sec",
        "network.imb_mpi1.iteration.policy",
        "hardware.minimal.node.0",
        "mesh.partition.requested",
        "mesh.partition.observed",
        "mesh.topology",
    }.issubset(required)
    assert "software.imb_mpi1.version" in required


def test_default_registry_expands_multi_node_hardware_axis() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")

    required = registry.required_keys("bench", expected_nodes=2)

    assert {key for key in required if key.startswith("hardware.minimal.node.")} == {
        "hardware.minimal.node.0",
        "hardware.minimal.node.1",
    }


def test_default_registry_exposes_closed_machine_contract_graph() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")

    assert registry.contract is not None
    assert registry.contract.repository_id == "apac2026-openfoam"
    assert {item.identifier for item in registry.producers}.issubset(
        {item.identifier for item in registry.producer_contracts}
    )
    assert {item.key_pattern for item in registry.facts} == {
        item.pattern for item in registry.keys
    }
    assert registry.spec_for("artifact.build_manifest_sha256").owner == (
        "runner.artifact_index"
    )
    assert (
        next(
            item
            for item in registry.facts
            if item.key_pattern == "artifact.build_manifest_sha256"
        ).reducer_id
        == "identity/v1"
    )
    assert registry.artifact_roles is not None
    assert registry.artifact_roles.filename("run_bundle") == ("run-artifacts.tar.zst")
    assert {"pbs_log", "pjm_log", "workload_member"}.issubset(
        registry.artifact_roles.run_bundle_source_roles
    )
    assert "profile.vtune_hotspots" not in registry.required_keys("profile")
    assert {"openfoam.vtune-hotspots/v1", "openfoam.craypat-apa/v1"}.issubset(
        {item.identifier for item in registry.producer_contracts}
    )
    assert {
        "artifact.subject_manifest",
        "artifact.build_sidecar",
        "artifact.build_provision",
        "artifact.instrumentation_bundle",
        "artifact.workload_manifest",
        "artifact.network_stdout",
    }.issubset(
        {
            source_id
            for source_id, _ in registry.required_literal_sources(
                "bench", storages=frozenset({"run_bundle"})
            )
        }
    )


def test_required_wildcard_without_a_protocol_axis_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "registry.toml"
    path.write_text(
        """
[registry]
schema_version = "test/v1"

[[producers]]
id = "p"
required_for = ["bench"]

[[keys]]
pattern = "unknown.*"
owner = "p"
logical_type = "string"
required_for = ["bench"]
""".strip()
        + "\n"
    )
    with pytest.raises(ValueError, match="wildcard"):
        Registry.load(path).required_keys("bench")
