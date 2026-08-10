from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from experiment_metrics.imb import parse_imb_mpi1
from experiment_metrics.reducers import network_config_facts, network_projection_rows
from experiment_metrics.registry import Registry

FIXTURES = Path(__file__).parent / "fixtures"


def test_imb_parser_handles_zero_scientific_values_and_warning_text() -> None:
    results = parse_imb_mpi1((FIXTURES / "imb-complete.txt").read_text())

    assert len(results) == 6
    pingpong = results[0]
    allreduce = results[-1]
    assert pingpong.message_bytes == 0
    assert pingpong.time_max_us == Decimal("0.1")
    assert pingpong.bandwidth_mbytes_per_sec == Decimal("0.0")
    assert allreduce.benchmark == "Allreduce"
    assert allreduce.time_min_us == Decimal("0.2")
    assert allreduce.time_avg_us == Decimal("0.3")
    assert allreduce.time_max_us == Decimal("0.4")
    assert allreduce.bandwidth_mbytes_per_sec is None


def test_imb_parser_accepts_multiple_process_count_sections() -> None:
    text = (
        (FIXTURES / "imb-complete.txt").read_text()
        + """
# Benchmarking PingPong
# #processes = 8
#bytes #repetitions t[usec] Mbytes/sec
0 1000 5e-1 0
"""
    )
    results = parse_imb_mpi1(text)

    assert results[-1].benchmark == "PingPong"
    assert results[-1].process_count == 8


def test_imb_parser_rejects_truncated_target_output() -> None:
    text = (
        (FIXTURES / "imb-complete.txt")
        .read_text()
        .replace("0 1000 1.0e-1 3.0e-1 2.0e-1\n", "")
        .replace("1 1000 2.0e-1 4.0e-1 3.0e-1\n", "")
    )
    with pytest.raises(ValueError, match="incomplete"):
        parse_imb_mpi1(text)


def test_network_projection_has_contract_grain_and_relative_source() -> None:
    results = parse_imb_mpi1((FIXTURES / "imb-complete.txt").read_text())
    rows = network_projection_rows(
        "r-" + "a" * 32, results, "source/network/imb-mpi1/stdout.txt"
    )

    assert set(rows[0]) == {
        "run_id",
        "benchmark",
        "process_count",
        "message_bytes",
        "iterations",
        "time_min_us",
        "time_avg_us",
        "time_max_us",
        "bandwidth_mbytes_per_sec",
        "source_member",
    }
    assert rows[0]["time_max_us"] == 0.1
    with pytest.raises(ValueError, match="relative"):
        network_projection_rows("r", results, "/foreign/stdout.txt")


def test_network_config_reducer_creates_only_config_facts() -> None:
    results = parse_imb_mpi1((FIXTURES / "imb-complete.txt").read_text())
    facts = network_config_facts(
        results, "2021.3", time_limit_sec=1, iteration_policy="dynamic"
    )

    assert {(fact.key, fact.logical_value) for fact in facts} == {
        ("network.imb_mpi1.process_count", 2),
        ("network.imb_mpi1.message_size.min_bytes", 0),
        ("network.imb_mpi1.message_size.max_bytes", 1),
        ("network.imb_mpi1.iteration.max_per_sample", 1000),
        ("network.imb_mpi1.iteration.time_limit_sec", 1),
        ("network.imb_mpi1.iteration.policy", "dynamic"),
        ("software.imb_mpi1.version", "2021.3"),
    }


def test_network_fact_keys_are_owned_by_the_network_parser() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")

    assert {
        registry.spec_for(key).owner
        for key in (
            "network.imb_mpi1.process_count",
            "network.imb_mpi1.message_size.min_bytes",
            "network.imb_mpi1.message_size.max_bytes",
            "network.imb_mpi1.iteration.max_per_sample",
            "software.imb_mpi1.version",
        )
    } == {"network.parser"}
