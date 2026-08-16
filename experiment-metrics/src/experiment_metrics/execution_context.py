from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .environment import environment_facts, parse_snapshot
from .manifest import RunManifest
from .placement import placement_fact
from .protocol import RunProtocol
from .recording import Recorder
from .solver_log import parse_solver_log


def record_execution_context(
    *,
    manifest_path: Path,
    runtime_dir: Path,
    registry_path: Path,
    protocol_path: Path,
    host_snapshot: Path,
    placement_root: Path,
    scheduler_request: Path,
    scheduler_accounting: Path,
    decompose_dictionary: Path,
    solver_log: Path,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    if run_dir != manifest.path.parents[1]:
        raise ValueError("execution context runtime differs from manifest")
    protocol = RunProtocol.load(protocol_path, manifest.purpose)
    request = _json(scheduler_request)
    accounting = _json(scheduler_accounting)
    _validate_request(request, protocol)
    if accounting.get("schema_version") != "scheduler-accounting/v2" or (
        accounting.get("nnumu", {}).get("value") != protocol.nodes
    ):
        raise ValueError("scheduler allocation node count differs from protocol")
    dictionary = decompose_dictionary.read_text(encoding="utf-8")
    match = re.search(r"\bnumberOfSubdomains\s+([0-9]+)\s*;", dictionary)
    if match is None or int(match.group(1)) != protocol.ranks:
        raise ValueError("decomposition rank count differs from protocol")
    placement = placement_fact(
        placement_root,
        run_id=manifest.run_id,
        expected_ranks=protocol.ranks,
        expected_nodes=protocol.nodes,
        ranks_per_node=protocol.ranks_per_node,
    )
    records = placement.logical_value
    assert isinstance(records, list)
    parsed = parse_solver_log(solver_log.read_text(encoding="utf-8", errors="replace"))
    header = parsed.runtime_header
    if header is None or header["nprocs"] != protocol.ranks:
        raise ValueError("solver runtime rank count differs from protocol")
    placement_hosts = Counter(str(item["hostname"]) for item in records)
    header_hosts = Counter(
        {str(item["hostname"]): int(item["ranks"]) for item in header["hosts"]}
    )
    if placement_hosts != header_hosts or len(placement_hosts) != protocol.nodes:
        raise ValueError("solver and placement host mappings differ")
    environment = parse_snapshot(host_snapshot.read_bytes())
    for name, expected in protocol.transport_environment.items():
        if environment.get(name.encode()) != expected.encode():
            raise ValueError("launch-effective MPI transport differs from protocol")
    facts = (
        *environment_facts(host_snapshot),
        placement,
    )
    with Recorder.open(
        manifest.path,
        registry_path,
        "runner.execution_context_parser",
        run_dir,
        fragment_id="execution-context",
    ) as recorder:
        for fact in facts:
            recorder.record(fact)
    return recorder.fragment_path


def _validate_request(request: dict[str, object], protocol: RunProtocol) -> None:
    if (
        request.get("schema_version") != "scheduler-request/v1"
        or request.get("nodes") != protocol.nodes
        or request.get("ranks") != protocol.ranks
        or request.get("resource_group") != protocol.resource_group
        or request.get("transport_policy") != protocol.transport_policy
    ):
        raise ValueError("scheduler request differs from protocol")


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value
