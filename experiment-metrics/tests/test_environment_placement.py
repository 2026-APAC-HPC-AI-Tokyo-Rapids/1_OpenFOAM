from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics import init_run
from experiment_metrics.environment import (
    capture_snapshot,
    environment_facts,
    escape_name,
    parse_snapshot,
    snapshot_bytes,
)
from experiment_metrics.fact import canonical_json
from experiment_metrics.placement import placement_fact
from experiment_metrics.rank_wrapper import main as rank_wrapper_main


def test_nul_environment_snapshot_projects_plain_utf8_values(tmp_path: Path) -> None:
    common = {b"Z": b"last", b"A": b"one", b"DROP": b"gone"}
    snapshot = tmp_path / "host.snapshot"
    capture_snapshot(snapshot, common)

    assert snapshot.read_bytes() == b"A\0one\0DROP\0gone\0Z\0last\0"
    assert parse_snapshot(snapshot.read_bytes()) == common

    facts = environment_facts(snapshot)
    assert [(fact.key, fact.logical_value) for fact in facts] == [
        ("env.A", "one"),
        ("env.DROP", "gone"),
        ("env.Z", "last"),
    ]
    assert escape_name(b"A.B_\xff") == "A~2EB_~FF"


def test_environment_fact_rejects_non_utf8_value(tmp_path: Path) -> None:
    snapshot = tmp_path / "host.snapshot"
    capture_snapshot(snapshot, {b"INVALID": b"\xff"})
    with pytest.raises(ValueError, match="not UTF-8"):
        environment_facts(snapshot)


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


def test_rank_wrapper_can_capture_placement_without_launching_solver(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    placement_root = manifest.parents[1] / "source/placement"
    monkeypatch.setenv("TEST_GLOBAL_RANK", "0")
    monkeypatch.setenv("TEST_LOCAL_RANK", "0")
    monkeypatch.setenv("TEST_LOCAL_SIZE", "1")

    result = rank_wrapper_main([
        "--manifest", str(manifest),
        "--expected-ranks", "1",
        "--expected-nodes", "1",
        "--placement-root", str(placement_root),
        "--global-rank-env", "TEST_GLOBAL_RANK",
        "--local-rank-env", "TEST_LOCAL_RANK",
        "--local-size-env", "TEST_LOCAL_SIZE",
        "--capture-only",
    ])

    assert result == 0
    document = json.loads((placement_root / "rank-0.json").read_text())
    assert document["run_id"] == manifest.parents[1].name
    assert document["global_rank"] == 0
