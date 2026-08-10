from __future__ import annotations

import json
import os
import re
import socket
import tempfile
from collections import Counter
from pathlib import Path

from .fact import Fact, canonical_json

_CPU_LIST = re.compile(r"^[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*$")


def capture_rank_placement(
    output: Path,
    *,
    run_id: str,
    global_rank: int,
    node_ordinal: int,
    local_rank: int,
    local_size: int,
) -> Path:
    if (
        global_rank < 0
        or node_ordinal < 0
        or local_rank < 0
        or local_size <= 0
        or local_rank >= local_size
    ):
        raise ValueError("rank placement indices are invalid")
    mems = None
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        if line.startswith("Mems_allowed_list:"):
            candidate = line.partition(":")[2].strip()
            if candidate and _CPU_LIST.fullmatch(candidate) is None:
                raise ValueError("rank NUMA memory list is invalid")
            mems = candidate
            break
    document = {
        "schema_version": "rank-placement/v1",
        "run_id": run_id,
        "global_rank": global_rank,
        "node_ordinal": node_ordinal,
        "local_rank": local_rank,
        "local_size": local_size,
        "hostname": socket.gethostname(),
        "cpu_affinity": sorted(os.sched_getaffinity(0)),
        "numa_mems": mems,
    }
    _atomic_text(output, canonical_json(document) + "\n")
    return output


def placement_fact(
    root: Path,
    *,
    run_id: str,
    expected_ranks: int,
    expected_nodes: int,
    ranks_per_node: int,
) -> Fact:
    records = []
    for rank in range(expected_ranks):
        path = root / f"rank-{rank}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        _validate_record(document, run_id, rank)
        records.append(document)
    hosts = Counter(str(item["hostname"]) for item in records)
    if len(hosts) != expected_nodes or set(hosts.values()) != {ranks_per_node}:
        raise ValueError("rank placement host cardinality differs from protocol")
    for hostname in hosts:
        local = [item for item in records if item["hostname"] == hostname]
        if {item["local_size"] for item in local} != {ranks_per_node} or {
            item["local_rank"] for item in local
        } != set(range(ranks_per_node)):
            raise ValueError("rank placement local axes are invalid")
    node_hosts: dict[int, set[str]] = {}
    for item in records:
        ordinal = int(item["node_ordinal"])
        node_hosts.setdefault(ordinal, set()).add(str(item["hostname"]))
        if ordinal != int(item["global_rank"]) // ranks_per_node:
            raise ValueError("rank placement global/node axes are invalid")
    if set(node_hosts) != set(range(expected_nodes)) or any(
        len(hostnames) != 1 for hostnames in node_hosts.values()
    ):
        raise ValueError("rank placement node ordinal axis is invalid")
    return Fact("parallel.rank_placement", records)


def _validate_record(document: object, run_id: str, rank: int) -> None:
    required = {
        "schema_version",
        "run_id",
        "global_rank",
        "node_ordinal",
        "local_rank",
        "local_size",
        "hostname",
        "cpu_affinity",
        "numa_mems",
    }
    if (
        not isinstance(document, dict)
        or set(document) != required
        or document["schema_version"] != "rank-placement/v1"
        or document["run_id"] != run_id
        or document["global_rank"] != rank
        or not isinstance(document["node_ordinal"], int)
        or isinstance(document["node_ordinal"], bool)
        or document["node_ordinal"] < 0
        or not isinstance(document["local_rank"], int)
        or isinstance(document["local_rank"], bool)
        or not isinstance(document["local_size"], int)
        or isinstance(document["local_size"], bool)
        or document["local_rank"] < 0
        or document["local_size"] <= document["local_rank"]
        or not isinstance(document["hostname"], str)
        or not document["hostname"]
        or not isinstance(document["cpu_affinity"], list)
        or document["cpu_affinity"] != sorted(set(document["cpu_affinity"]))
        or not all(
            isinstance(cpu, int) and not isinstance(cpu, bool) and cpu >= 0
            for cpu in document["cpu_affinity"]
        )
        or (
            document["numa_mems"] is not None
            and (
                not isinstance(document["numa_mems"], str)
                or (
                    document["numa_mems"]
                    and _CPU_LIST.fullmatch(document["numa_mems"]) is None
                )
            )
        )
    ):
        raise ValueError("rank placement record has an invalid schema")


def _atomic_text(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)
