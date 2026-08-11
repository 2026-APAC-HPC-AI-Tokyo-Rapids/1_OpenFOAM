from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics import pstream_facts


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
