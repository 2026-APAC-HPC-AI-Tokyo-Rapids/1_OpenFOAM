from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics.environment import (
    capture_rank_delta,
    capture_snapshot,
    escape_name,
    parse_snapshot,
    reconstruct_rank_environments,
    snapshot_bytes,
)
from experiment_metrics.fact import canonical_json
from experiment_metrics.placement import placement_fact


def test_nul_environment_snapshot_and_rank_delta_round_trip(tmp_path: Path) -> None:
    common = {b"Z": b"last", b"A": b"one", b"DROP": b"gone"}
    snapshot = tmp_path / "host.snapshot"
    capture_snapshot(snapshot, common)

    assert snapshot.read_bytes() == b"A\0one\0DROP\0gone\0Z\0last\0"
    assert parse_snapshot(snapshot.read_bytes()) == common

    deltas = tmp_path / "delta"
    capture_rank_delta(
        snapshot,
        deltas / "rank-0.delta.json",
        rank=0,
        environment={b"A": b"two", b"Z": b"last", b"NEW": b"\xff"},
    )
    assert reconstruct_rank_environments(snapshot, deltas, expected_ranks=1) == (
        {b"A": b"two", b"Z": b"last", b"NEW": b"\xff"},
    )
    assert escape_name(b"A.B_\xff") == "A~2EB_~FF"


def test_nul_environment_rejects_noncanonical_names() -> None:
    with pytest.raises(ValueError, match="canonical"):
        parse_snapshot(b"B\0one\0A\0two\0")
    with pytest.raises(ValueError, match="invalid name"):
        snapshot_bytes({b"A=B": b"value"})


def test_rank_placement_closes_global_node_and_local_axes(tmp_path: Path) -> None:
    root = tmp_path / "placement"
    root.mkdir()
    for rank in range(4):
        node = rank // 2
        document = {
            "schema_version": "rank-placement/v1",
            "run_id": "r-" + "a" * 32,
            "global_rank": rank,
            "node_ordinal": node,
            "local_rank": rank % 2,
            "local_size": 2,
            "hostname": f"node-{node}",
            "cpu_affinity": [rank],
            "numa_mems": "0",
        }
        (root / f"rank-{rank}.json").write_text(canonical_json(document) + "\n")

    fact = placement_fact(
        root,
        run_id="r-" + "a" * 32,
        expected_ranks=4,
        expected_nodes=2,
        ranks_per_node=2,
    )
    assert fact.key == "parallel.rank_placement"
    assert [item["node_ordinal"] for item in fact.logical_value] == [0, 0, 1, 1]

    malformed = json.loads((root / "rank-3.json").read_text())
    malformed["node_ordinal"] = 0
    (root / "rank-3.json").write_text(canonical_json(malformed) + "\n")
    with pytest.raises(ValueError, match="global/node"):
        placement_fact(
            root,
            run_id="r-" + "a" * 32,
            expected_ranks=4,
            expected_nodes=2,
            ranks_per_node=2,
        )
