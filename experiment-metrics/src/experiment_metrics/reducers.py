from __future__ import annotations

from decimal import Decimal

from .fact import Fact
from .imb import IMBResult
from .protocol import RunProtocol
from .solver_log import ParsedSolverLog, evaluate_official


def solver_log_facts(parsed: ParsedSolverLog, protocol: RunProtocol) -> tuple[Fact, ...]:
    official = evaluate_official(parsed, iterations=protocol.iteration_target, expected_cells=protocol.expected_cells, ranks=protocol.ranks, release=protocol.release, solver=protocol.solver)
    facts: list[Fact] = [
        Fact("solver.step_timings", _json_value(list(parsed.step_timings))),
        Fact("solver.pressure_solves", _json_value(list(parsed.pressure_solves))),
        Fact("solver.log_markers", _json_value(parsed.log_markers)),
        Fact(
            "result.official",
            {
                "schema_version": "openfoam-official-result/v1",
                "valid": official.valid,
                "average_wall_clock_seconds_per_iteration": _decimal_text(official.average_wall_clock_sec),
                "standard_deviation_seconds": _decimal_text(official.standard_deviation_sec),
                "measured_iterations": official.measured_iterations,
                "configured_iterations": protocol.iteration_target,
                "workload_id": protocol.workload_id,
                "workload_identity": protocol.expected_workload_identity,
                "cells": protocol.expected_cells,
                "solver": protocol.solver,
                "distribution": protocol.distribution,
                "release": protocol.release,
                "ranks": parsed.observed_nprocs,
                "nodes": len(parsed.observed_hosts) if parsed.observed_hosts else None,
            },
        ),
    ]
    if parsed.runtime_header is not None:
        facts.insert(
            0, Fact("solver.runtime_header", _json_value(parsed.runtime_header))
        )
    return tuple(facts)


def network_config_facts(
    results: tuple[IMBResult, ...],
    version: str | None,
    *,
    process_count: int,
    time_limit_sec: int,
    iteration_policy: str,
) -> tuple[Fact, ...]:
    """Reduce one validated IMB capture's scalar command/result settings."""

    message_sizes = {item.message_bytes for item in results}
    iterations = {item.iterations for item in results}
    if process_count <= 0 or time_limit_sec <= 0 or iteration_policy != "dynamic":
        raise ValueError("network command settings do not match the v2 protocol")
    facts = [
        Fact("network.imb_mpi1.process_count", process_count),
        Fact("network.imb_mpi1.message_size.min_bytes", min(message_sizes)),
        Fact("network.imb_mpi1.message_size.max_bytes", max(message_sizes)),
        Fact("network.imb_mpi1.iteration.max_per_sample", max(iterations)),
        Fact("network.imb_mpi1.iteration.time_limit_sec", time_limit_sec),
        Fact("network.imb_mpi1.iteration.policy", iteration_policy),
    ]
    if version is not None:
        facts.append(Fact("software.imb_mpi1.version", version))
    for item in results:
        facts.append(
            Fact(
                "network.imb_mpi1.result."
                f"{item.benchmark.lower()}.{item.message_bytes}",
                {
                    "benchmark": item.benchmark,
                    "process_count": item.process_count,
                    "message_bytes": item.message_bytes,
                    "iterations": item.iterations,
                    "time_min_us": _decimal_text(item.time_min_us),
                    "time_avg_us": _decimal_text(item.time_avg_us),
                    "time_max_us": _decimal_text(item.time_max_us),
                    "bandwidth_mbytes_per_sec": _decimal_text(
                        item.bandwidth_mbytes_per_sec
                    ),
                },
            )
        )
    return tuple(facts)


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value
