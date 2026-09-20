from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from experiment_metrics.imb import (
    IMBResult,
    _validate_imb_argv,
    parse_imb_mpi1,
    validate_imb_results,
)
from experiment_metrics.reducers import network_config_facts
from experiment_metrics.registry import Registry

FIXTURES = Path(__file__).parent / "fixtures"


class _Protocol:
    ranks = 120
    ranks_per_node = 120


def _imb_command() -> list[str]:
    return [
        "/opt/intel/mpi/bin/IMB-MPI1",
        "-npmin",
        "120",
        "-msglog",
        "0:22",
        "-iter",
        "1000",
        "-time",
        "1",
        "-iter_policy",
        "dynamic",
        "PingPong",
        "Sendrecv",
        "Allreduce",
    ]


def test_imb_argv_accepts_cluster_launcher_shapes() -> None:
    genkai = [
        "/opt/intel/mpi/bin/mpirun",
        "-np",
        "120",
        "-ppn",
        "120",
        "-genv",
        "PATH",
        "/opt/intel/mpi/bin:/usr/bin",
        *_imb_command(),
    ]
    gadi = [
        "/opt/nci/mpi/bin/mpirun",
        "-hosts",
        "gadi-gpu-v100-0001",
        "-np",
        "120",
        "-ppn",
        "120",
        *_imb_command(),
    ]
    aspire2a = [
        "/opt/cray/pe/pals/bin/mpiexec",
        "-n",
        "120",
        "-ppn",
        "120",
        *_imb_command(),
    ]

    _validate_imb_argv(genkai, _Protocol())  # type: ignore[arg-type]
    _validate_imb_argv(gadi, _Protocol())  # type: ignore[arg-type]
    _validate_imb_argv(aspire2a, _Protocol())  # type: ignore[arg-type]


def test_imb_argv_rejects_unowned_launcher_options() -> None:
    argv = [
        "/opt/intel/mpi/bin/mpirun",
        "--allow-run-as-root",
        "-np",
        "120",
        "-ppn",
        "120",
        *_imb_command(),
    ]

    with pytest.raises(ValueError, match="launcher shape"):
        _validate_imb_argv(argv, _Protocol())  # type: ignore[arg-type]


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


def test_imb_parser_accepts_intel_sendrecv_min_avg_max_columns() -> None:
    text = (
        (FIXTURES / "imb-complete.txt")
        .read_text()
        .replace(
            "#bytes #repetitions t[usec] Mbytes/sec\n"
            "0 1000 1.1e-1 0.0\n"
            "1 1000 2.6e-1 3.1e+0\n",
            "#bytes #repetitions t_min[usec] t_max[usec] t_avg[usec] Mbytes/sec\n"
            "0 1000 1.0e-1 1.2e-1 1.1e-1 0.0\n"
            "1 1000 2.5e-1 2.7e-1 2.6e-1 3.1e+0\n",
        )
    )

    sendrecv = [item for item in parse_imb_mpi1(text) if item.benchmark == "Sendrecv"]

    assert sendrecv[0].time_min_us == Decimal("1.0e-1")
    assert sendrecv[0].time_avg_us == Decimal("1.1e-1")
    assert sendrecv[0].time_max_us == Decimal("1.2e-1")
    assert sendrecv[1].bandwidth_mbytes_per_sec == Decimal("3.1e+0")


def test_intel_imb_version_banner_is_unambiguous() -> None:
    from experiment_metrics.imb import _VERSION

    match = _VERSION.fullmatch("#    Intel(R) MPI Benchmarks 2021.9, MPI-1 part")

    assert match is not None
    assert next(group for group in match.groups() if group is not None) == "2021.9"
    assert _VERSION.fullmatch("# Version : Linux kernel version") is None


def test_result_axes_follow_intel_benchmark_semantics() -> None:
    transfer_sizes = (0, *(1 << exponent for exponent in range(23)))
    collective_sizes = (0, *(1 << exponent for exponent in range(2, 23)))
    results = tuple(
        IMBResult(benchmark, count, size, 1000, None, None, Decimal("1"), None)
        for benchmark, count, sizes in (
            ("PingPong", 2, transfer_sizes),
            ("Sendrecv", 120, transfer_sizes),
            ("Allreduce", 120, collective_sizes),
        )
        for size in sizes
    )

    validate_imb_results(results, 120)

    with pytest.raises(ValueError, match="PingPong process count"):
        validate_imb_results(
            tuple(
                IMBResult(
                    item.benchmark,
                    120 if item.benchmark == "PingPong" else item.process_count,
                    item.message_bytes,
                    item.iterations,
                    item.time_min_us,
                    item.time_avg_us,
                    item.time_max_us,
                    item.bandwidth_mbytes_per_sec,
                )
                for item in results
            ),
            120,
        )


def test_imb_parser_rejects_truncated_target_output() -> None:
    text = (
        (FIXTURES / "imb-complete.txt")
        .read_text()
        .replace("0 1000 1.0e-1 3.0e-1 2.0e-1\n", "")
        .replace("1 1000 2.0e-1 4.0e-1 3.0e-1\n", "")
    )
    with pytest.raises(ValueError, match="incomplete"):
        parse_imb_mpi1(text)


def test_network_config_reducer_creates_only_config_facts() -> None:
    results = parse_imb_mpi1((FIXTURES / "imb-complete.txt").read_text())
    facts = network_config_facts(
        results,
        "2021.3",
        process_count=2,
        time_limit_sec=1,
        iteration_policy="dynamic",
    )

    scalar = [fact for fact in facts if ".result." not in fact.key]
    assert {(fact.key, fact.logical_value) for fact in scalar} == {
        ("network.imb_mpi1.process_count", 2),
        ("network.imb_mpi1.message_size.min_bytes", 0),
        ("network.imb_mpi1.message_size.max_bytes", 1),
        ("network.imb_mpi1.iteration.max_per_sample", 1000),
        ("network.imb_mpi1.iteration.time_limit_sec", 1),
        ("network.imb_mpi1.iteration.policy", "dynamic"),
        ("software.imb_mpi1.version", "2021.3"),
    }
    result_facts = [fact for fact in facts if ".result." in fact.key]
    assert len(result_facts) == len(results)
    assert result_facts[0].key == "network.imb_mpi1.result.pingpong.0"


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
