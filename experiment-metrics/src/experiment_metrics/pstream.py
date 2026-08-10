from __future__ import annotations

import json
import re
from pathlib import Path

from .fact import Fact

_RANK_FILE = re.compile(r"^rank-(\d+)\.jsonl$")
_STARTUP = {
    "node_comms_control",
    "node_comms_min",
    "using_node_comms",
    "num_nodes",
    "topology_control",
    "configured_mpi_buffer_value",
    "environment_mpi_buffer_bytes_applied",
    "attached_buffer_bytes",
}
_RUNTIME = {
    "float_transfer",
    "n_procs_simple_sum",
    "n_procs_nonblocking_exchange",
    "tuning_nbx",
    "pstream_buffers_algorithm",
    "default_comms_type",
    "n_poll_proc_interfaces",
    "max_comms_size",
    "node_comms_control",
    "node_comms_min",
    "topology_control",
    "using_node_comms",
}
_ENVELOPE = {
    "schema_version",
    "run_id",
    "producer_id",
    "rank",
    "sequence",
    "event_type",
    "payload",
}


def pstream_facts(
    source_dir: Path, *, run_id: str, expected_ranks: tuple[int, ...]
) -> tuple[Fact, ...]:
    """Reduce exactly one validated startup/runtime stream for every rank."""

    files: dict[int, Path] = {}
    for path in source_dir.glob("*.jsonl"):
        match = _RANK_FILE.fullmatch(path.name)
        if match is None:
            raise ValueError(f"invalid Pstream source filename: {path.name}")
        rank = int(match[1])
        if rank in files:
            raise ValueError(f"duplicate Pstream rank source: {rank}")
        files[rank] = path
    if set(files) != set(expected_ranks):
        raise ValueError("Pstream source ranks do not match expected ranks")
    facts: list[Fact] = []
    for rank in expected_ranks:
        startup, runtime, changes = _rank_events(files[rank], run_id, rank)
        source_member = f"domain/pstream/rank-{rank}.jsonl"
        facts.extend(
            (
                Fact(
                    f"solver.pstream.startup_applied.rank.{rank}",
                    {
                        "schema_version": "pstream-startup/v1",
                        "source_member": source_member,
                        "payload": startup,
                    },
                ),
                Fact(
                    f"solver.pstream.runtime_current.rank.{rank}",
                    {
                        "schema_version": "pstream-runtime/v1",
                        "source_member": source_member,
                        "payload": runtime,
                    },
                ),
                Fact(
                    f"solver.pstream.change_events.rank.{rank}",
                    {
                        "schema_version": "pstream-changes/v1",
                        "source_member": source_member,
                        "events": changes,
                    },
                ),
            )
        )
    return tuple(facts)


def _rank_events(
    path: Path, run_id: str, rank: int
) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
    try:
        events = [
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        ]
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid Pstream JSONL: {path.name}") from error
    if len(events) < 2:
        raise ValueError(f"Pstream source is truncated: {path.name}")
    normalized: list[dict[str, object]] = []
    for sequence, event in enumerate(events):
        normalized.append(_event(event, run_id, rank, sequence))
    if [event["event_type"] for event in normalized[:2]] != [
        "startup_applied",
        "runtime_current",
    ] or any(event["event_type"] != "runtime_change" for event in normalized[2:]):
        raise ValueError(f"Pstream event order is invalid: {path.name}")
    return (
        normalized[0]["payload"],  # type: ignore[return-value]
        normalized[1]["payload"],  # type: ignore[return-value]
        [event["payload"] for event in normalized[2:]],  # type: ignore[misc]
    )


def _event(raw: object, run_id: str, rank: int, sequence: int) -> dict[str, object]:
    if not isinstance(raw, dict) or set(raw) != _ENVELOPE:
        raise ValueError("Pstream event has an invalid envelope")
    if (
        raw["schema_version"] != "openfoam-pstream-event/v1"
        or raw["run_id"] != run_id
        or raw["producer_id"] != "openfoam.pstream-hook/v1"
        or raw["rank"] != rank
        or raw["sequence"] != sequence
        or raw["event_type"]
        not in {"startup_applied", "runtime_current", "runtime_change"}
        or not isinstance(raw["payload"], dict)
    ):
        raise ValueError("Pstream event identity is invalid")
    payload = raw["payload"]
    event_type = raw["event_type"]
    if event_type == "startup_applied":
        _startup_payload(payload)
    elif event_type == "runtime_current":
        _runtime_payload(payload)
    else:
        _change_payload(payload)
    return raw


def _integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _startup_payload(payload: dict[str, object]) -> None:
    if (
        set(payload) != _STARTUP
        or not all(
            _integer(payload[name])
            for name in _STARTUP
            - {"using_node_comms", "environment_mpi_buffer_bytes_applied"}
        )
        or not isinstance(payload["using_node_comms"], bool)
    ):
        raise ValueError("Pstream startup payload is invalid")
    environment = payload["environment_mpi_buffer_bytes_applied"]
    if environment is not None and (not _integer(environment) or environment <= 0):
        raise ValueError("Pstream environment buffer is invalid")
    if payload["num_nodes"] <= 0 or payload["attached_buffer_bytes"] < 0:
        raise ValueError("Pstream startup bounds are invalid")


def _runtime_payload(payload: dict[str, object]) -> None:
    integer_fields = _RUNTIME - {
        "float_transfer",
        "using_node_comms",
        "default_comms_type",
    }
    if (
        set(payload) != _RUNTIME
        or not all(_integer(payload[name]) for name in integer_fields)
        or not isinstance(payload["float_transfer"], bool)
        or not isinstance(payload["using_node_comms"], bool)
        or payload["default_comms_type"] not in {"buffered", "scheduled", "nonBlocking"}
    ):
        raise ValueError("Pstream runtime payload is invalid")


def _change_payload(payload: dict[str, object]) -> None:
    if set(payload) != {"field", "old", "new"} or payload["field"] not in _RUNTIME:
        raise ValueError("Pstream change payload is invalid")
    field = payload["field"]
    for value in (payload["old"], payload["new"]):
        if field in {"float_transfer", "using_node_comms"}:
            valid = isinstance(value, bool)
        elif field == "default_comms_type":
            valid = value in {"buffered", "scheduled", "nonBlocking"}
        else:
            valid = _integer(value)
        if not valid:
            raise ValueError("Pstream change values are invalid")
