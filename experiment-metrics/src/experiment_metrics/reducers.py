from __future__ import annotations

from decimal import Decimal
from pathlib import PurePosixPath

from .fact import Fact
from .imb import IMBResult
from .solver_log import ParsedSolverLog


def solver_log_facts(parsed: ParsedSolverLog) -> tuple[Fact, ...]:
    facts: list[Fact] = [
        Fact("solver.step_timings", _json_value(list(parsed.step_timings))),
        Fact("solver.pressure_solves", _json_value(list(parsed.pressure_solves))),
        Fact("solver.log_markers", _json_value(parsed.log_markers)),
    ]
    if parsed.runtime_header is not None:
        facts.insert(
            0, Fact("solver.runtime_header", _json_value(parsed.runtime_header))
        )
    return tuple(facts)


def network_projection_rows(
    run_id: str, results: tuple[IMBResult, ...], source_member: str
) -> tuple[dict[str, object], ...]:
    path = PurePosixPath(source_member)
    if not run_id or path.is_absolute() or ".." in path.parts or not source_member:
        raise ValueError("network source_member must be a nonempty relative path")
    return tuple(
        {
            "run_id": run_id,
            "benchmark": item.benchmark,
            "process_count": item.process_count,
            "message_bytes": item.message_bytes,
            "iterations": item.iterations,
            "time_min_us": _json_value(item.time_min_us),
            "time_avg_us": _json_value(item.time_avg_us),
            "time_max_us": _json_value(item.time_max_us),
            "bandwidth_mbytes_per_sec": _json_value(item.bandwidth_mbytes_per_sec),
            "source_member": source_member,
        }
        for item in results
    )


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
    return tuple(facts)


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
