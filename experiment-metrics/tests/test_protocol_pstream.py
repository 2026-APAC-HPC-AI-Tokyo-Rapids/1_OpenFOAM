from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from experiment_metrics import Recorder, init_run, merge_run, pstream_facts, run_stage


def _event(
    run_id: str, rank: int, sequence: int, event_type: str, payload: dict[str, object]
) -> dict[str, object]:
    return {
        "schema_version": "openfoam-pstream-event/v1",
        "run_id": run_id,
        "producer_id": "openfoam.pstream-hook/v1",
        "rank": rank,
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload,
    }


def _write_rank(path: Path, run_id: str) -> None:
    startup = {
        "node_comms_control": 1,
        "node_comms_min": 2,
        "using_node_comms": True,
        "num_nodes": 1,
        "topology_control": 3,
        "configured_mpi_buffer_value": 0,
        "environment_mpi_buffer_bytes_applied": None,
        "attached_buffer_bytes": 0,
    }
    runtime = {
        "float_transfer": False,
        "n_procs_simple_sum": 1,
        "n_procs_nonblocking_exchange": 2,
        "tuning_nbx": 3,
        "pstream_buffers_algorithm": 4,
        "default_comms_type": "nonBlocking",
        "n_poll_proc_interfaces": 5,
        "max_comms_size": 6,
        "node_comms_control": 1,
        "node_comms_min": 2,
        "topology_control": 3,
        "using_node_comms": True,
    }
    events = [
        _event(run_id, 0, 0, "startup_applied", startup),
        _event(run_id, 0, 1, "runtime_current", runtime),
        _event(
            run_id,
            0,
            2,
            "runtime_change",
            {"field": "max_comms_size", "old": 6, "new": 7},
        ),
    ]
    path.write_text("".join(json.dumps(event) + "\n" for event in events))


def test_pstream_reducer_requires_complete_rank_streams(tmp_path: Path) -> None:
    source = tmp_path / "pstream"
    source.mkdir()
    _write_rank(source / "rank-0.jsonl", "r-" + "a" * 32)

    facts = pstream_facts(source, run_id="r-" + "a" * 32, expected_ranks=(0,))

    assert [fact.key for fact in facts] == [
        "solver.pstream.startup_applied.rank.0",
        "solver.pstream.runtime_current.rank.0",
        "solver.pstream.change_events.rank.0",
    ]
    assert facts[-1].logical_value["events"] == [
        {"field": "max_comms_size", "old": 6, "new": 7}
    ]
    with pytest.raises(ValueError, match="do not match"):
        pstream_facts(source, run_id="r-" + "a" * 32, expected_ranks=(0, 1))


def test_protocol_derived_stage_absence_marks_merge_incomplete(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    protocol = tmp_path / "protocol.toml"
    protocol.write_text(
        """
[protocol]
schema_version = "openfoam-v2-run-protocol/v1"

[variant.bench]
expected_stages = ["solver"]
expected_pstream_ranks = 1

[variant.profile]
expected_stages = ["solver"]
expected_pstream_ranks = 1
""".strip()
        + "\n"
    )

    missing_manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    outcome = merge_run(
        missing_manifest,
        missing_manifest.parents[1],
        registry_path=registry_path,
        protocol_path=protocol,
    )

    assert not outcome.collection_complete
    assert outcome.missing_stages == ("solver",)

    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest_path.parents[1]
    with Recorder.open(
        manifest_path,
        registry_path,
        "stage.runner",
        run_dir,
        fragment_id="stage.solver",
    ) as recorder:
        run_stage(
            "solver",
            [sys.executable, "-c", "raise SystemExit(0)"],
            cwd=tmp_path,
            stderr_mode="separate",
            recorder=recorder,
        )
    outcome = merge_run(
        manifest_path, run_dir, registry_path=registry_path, protocol_path=protocol
    )
    assert outcome.collection_complete
    assert outcome.missing_stages == ()


def test_unsuccessful_expected_stage_cannot_complete(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    protocol = tmp_path / "protocol.toml"
    protocol.write_text(
        """
[protocol]
schema_version = "openfoam-v2-run-protocol/v1"

[variant.bench]
expected_stages = ["solver"]
expected_pstream_ranks = 1

[variant.profile]
expected_stages = ["solver"]
expected_pstream_ranks = 1
""".strip()
        + "\n"
    )
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest.parents[1]
    with Recorder.open(
        manifest, registry_path, "stage.runner", run_dir, fragment_id="stage.solver"
    ) as recorder:
        run_stage(
            "solver",
            [sys.executable, "-c", "raise SystemExit(2)"],
            cwd=tmp_path,
            stderr_mode="separate",
            recorder=recorder,
        )
    outcome = merge_run(
        manifest, run_dir, registry_path=registry_path, protocol_path=protocol
    )
    assert not outcome.collection_complete
    assert outcome.missing_stages == ("solver",)
