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
        "mesh.topology",
        "mesh.partition.requested",
        "mesh.partition.observed",
    }.issubset(required)
    assert "software.imb_mpi1.version" not in required


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
    assert {item.identifier for item in registry.artifact_projections} == {
        "openfoam.source_track",
        "openfoam.build_provenance",
        "openfoam.build_provision",
        "openfoam.minimal_hardware",
        "openfoam.workload_manifest",
        "openfoam.workload_member",
        "openfoam.profile_hardware",
        "openfoam.mpi_network",
    }
    assert registry.artifact_roles is not None
    assert registry.artifact_roles.filename("run_bundle") == ("run-artifacts.tar.zst")
    assert "workload_member" in registry.artifact_roles.run_bundle_source_roles
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
