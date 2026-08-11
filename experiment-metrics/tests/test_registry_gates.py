from __future__ import annotations

from pathlib import Path

import pytest

from experiment_metrics.registry import Registry


def test_default_registry_expands_all_required_pstream_rank_axes() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")
    required = registry.required_keys("bench", expected_pstream_ranks=120)

    assert len([key for key in required if key.startswith("solver.pstream.")]) == 360
    assert "solver.pstream.startup_applied.rank.0" in required
    assert "solver.pstream.runtime_current.rank.119" in required
    assert "solver.pstream.change_events.rank.119" in required
    assert {
        "solver.runtime_header",
        "solver.step_timings",
        "solver.pressure_solves",
        "solver.log_markers",
        "network.imb_mpi1.process_count",
        "network.imb_mpi1.message_size.min_bytes",
        "network.imb_mpi1.message_size.max_bytes",
        "network.imb_mpi1.iteration.max_per_sample",
        "network.imb_mpi1.iteration.time_limit_sec",
        "network.imb_mpi1.iteration.policy",
        "hardware.minimal.node.0",
        "mesh.partition.requested",
    }.issubset(required)
    assert "software.imb_mpi1.version" in required


def test_default_registry_expands_multi_node_hardware_axis() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")

    required = registry.required_keys(
        "bench", expected_pstream_ranks=4, expected_nodes=2
    )

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
    assert "workload_member" in registry.artifact_roles.run_bundle_source_roles
    assert registry.required_keys("profile", expected_pstream_ranks=2).issuperset(
        {"profile.perf_stat.rank.0", "profile.perf_stat.rank.1"}
    )
    assert {
        "artifact.subject_manifest",
        "artifact.build_sidecar",
        "artifact.build_provision",
        "artifact.instrumentation_bundle",
        "artifact.workload_manifest",
        "artifact.network_stdout",
        "openfoam.pstream-rank-events/v1",
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
        Registry.load(path).required_keys("bench", expected_pstream_ranks=1)
