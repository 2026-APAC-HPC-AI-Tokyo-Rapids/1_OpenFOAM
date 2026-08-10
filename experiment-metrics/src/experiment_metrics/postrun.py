from __future__ import annotations

# ruff: noqa: E501
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from .fact import Fact

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_MESH_FIELDS = ("points", "faces", "owner", "neighbour", "boundary")


def minimal_hardware_fact(path: Path, *, run_id: str, source_member: str) -> Fact:
    source = _source(path, source_member)
    document = _json(path)
    _hardware(document)
    ordinal = document["node_ordinal"]
    if source_member != f"source/hardware/node-{ordinal}.json":
        raise ValueError("minimal hardware source member differs from node ordinal")
    lscpu = document["lscpu_json"]
    return Fact(
        f"hardware.minimal.node.{ordinal}",
        {
            "schema_version": "minimal-hardware-projection/v1",
            "subject_kind": "regular_run",
            "subject_id": run_id,
            "node_ordinal": ordinal,
            "hostname": document["hostname"],
            "cpu_identity": _cpu_identity(lscpu),
            "platform_settings": document["platform_settings"],
            "source_member": source_member,
            "source_sha256": source["sha256"],
        },
    )


def mesh_topology_fact(path: Path) -> Fact:
    document = _json(path)
    expected = {"schema_version", "cells", "faces", "points", "internal_faces"}
    if set(document) != expected or document["schema_version"] != "mesh-topology/v1":
        raise ValueError("mesh topology has an invalid schema")
    for name in expected - {"schema_version"}:
        if not _uint(document[name]):
            raise ValueError("mesh topology has invalid counts")
    if document["internal_faces"] > document["faces"]:
        raise ValueError("mesh topology internal faces exceed faces")
    return Fact("mesh.topology", document)


def partition_facts(
    dictionary: Path, observed: Path, *, topology: dict[str, object]
) -> tuple[Fact, Fact]:
    requested = _requested_partition(dictionary)
    document = _json(observed)
    _partition(document, requested["subdomains"], topology)
    return Fact("mesh.partition.requested", requested), Fact(
        "mesh.partition.observed", document
    )


def _requested_partition(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    number = re.search(r"\bnumberOfSubdomains\s+([0-9]+)\s*;", text)
    method = re.search(r"\bmethod\s+(\S+)\s*;", text)
    if number is None or method is None or method[1] != "scotch" or int(number[1]) <= 0:
        raise ValueError("decomposeParDict is not the closed scotch configuration")
    return {
        "schema_version": "partition-requested/v1",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "subdomains": int(number[1]),
        "method": "scotch",
    }


def _partition(
    document: object, requested_subdomains: object, topology: dict[str, object]
) -> None:
    if (
        not isinstance(document, dict)
        or set(document)
        != {
            "schema_version",
            "serial_mesh",
            "subdomains",
            "interfaces",
        }
        or document["schema_version"] != "partition-observed/v1"
    ):
        raise ValueError("partition observation has an invalid schema")
    _locator_object(document["serial_mesh"])
    subdomains = document["subdomains"]
    interfaces = document["interfaces"]
    if not isinstance(subdomains, list) or len(subdomains) != requested_subdomains:
        raise ValueError("partition subdomains do not match requested count")
    cells = 0
    for rank, item in enumerate(subdomains):
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "rank",
                "cell_count",
                "mesh",
                "addressing",
            }
            or item["rank"] != rank
            or not _uint(item["cell_count"])
            or item["cell_count"] == 0
        ):
            raise ValueError("partition subdomain is invalid")
        _locator_object(item["mesh"])
        _addressing_object(item["addressing"])
        cells += item["cell_count"]
    if cells != topology["cells"]:
        raise ValueError("partition cell total does not match mesh topology")
    if not isinstance(interfaces, list):
        raise ValueError("partition interfaces are invalid")
    previous: tuple[int, int] | None = None
    for item in interfaces:
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "lower_rank",
                "upper_rank",
                "n_faces",
            }
            or not all(_uint(item[name]) for name in item)
        ):
            raise ValueError("partition interface is invalid")
        key = (item["lower_rank"], item["upper_rank"])
        if (
            key[0] >= key[1]
            or key[1] >= requested_subdomains
            or (previous and key <= previous)
        ):
            raise ValueError("partition interfaces are not canonical")
        previous = key


def _locator_object(value: object) -> None:
    if not isinstance(value, dict) or tuple(value) != _MESH_FIELDS:
        raise ValueError("partition locator fields are invalid")
    for locator in value.values():
        if (
            not isinstance(locator, dict)
            or set(locator)
            != {
                "locator_kind",
                "path",
                "size_bytes",
                "sha256",
            }
            or locator["locator_kind"] != "runtime_relative_ephemeral"
            or not _relative(locator["path"])
            or not _uint(locator["size_bytes"])
            or not isinstance(locator["sha256"], str)
            or not _SHA256.fullmatch(locator["sha256"])
        ):
            raise ValueError("partition locator is invalid")


def _addressing_object(value: object) -> None:
    names = ("cell", "face", "point", "boundary")
    if not isinstance(value, dict) or tuple(value) != names:
        raise ValueError("partition addressing fields are invalid")
    for locator in value.values():
        _locator_object(
            {
                "points": locator,
                "faces": locator,
                "owner": locator,
                "neighbour": locator,
                "boundary": locator,
            }
        )


def _hardware(document: object) -> None:
    fields = {
        "schema_version",
        "node_ordinal",
        "hostname",
        "commands",
        "lscpu_json",
        "platform_settings",
    }
    if (
        not isinstance(document, dict)
        or set(document) != fields
        or document["schema_version"] != "hardware-node/v1"
        or not _uint(document["node_ordinal"])
        or not isinstance(document["hostname"], str)
        or not document["hostname"]
    ):
        raise ValueError("hardware source has an invalid schema")
    command = document["commands"]
    if (
        not isinstance(command, dict)
        or set(command) != {"lscpu"}
        or not isinstance(command["lscpu"], dict)
        or set(command["lscpu"]) != {"argv", "exit_code", "stderr_member"}
        or command["lscpu"]["argv"] != ["lscpu", "--json"]
        or not isinstance(command["lscpu"]["exit_code"], int)
        or not _relative(command["lscpu"]["stderr_member"])
    ):
        raise ValueError("hardware lscpu command is invalid")
    if document["lscpu_json"] is not None and not isinstance(
        document["lscpu_json"], dict
    ):
        raise ValueError("hardware lscpu JSON is invalid")
    _settings(document["platform_settings"])


def _settings(value: object) -> None:
    fields = {
        "kernel_release",
        "online_cpus",
        "isolated_cpus",
        "nohz_full_cpus",
        "memory",
        "numa_balancing_enabled",
        "boost",
        "cpufreq_policies",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("hardware platform settings are invalid")
    for name in ("online_cpus", "isolated_cpus", "nohz_full_cpus"):
        sequence = value[name]
        if sequence is not None and (
            not isinstance(sequence, list)
            or not all(_uint(item) for item in sequence)
            or sequence != sorted(set(sequence))
        ):
            raise ValueError("hardware CPU set is invalid")


def _cpu_identity(lscpu: object) -> dict[str, object]:
    labels = {
        "Architecture": "architecture",
        "Model name": "model_name",
        "Vendor ID": "vendor_id",
        "CPU family": "cpu_family",
        "Model": "model",
        "Stepping": "stepping",
        "NUMA node(s)": "numa_nodes",
    }
    result: dict[str, object] = {value: None for value in labels.values()}
    sockets = cores = None
    if isinstance(lscpu, dict) and isinstance(lscpu.get("lscpu"), list):
        values = {
            str(item.get("field", "")).rstrip(":"): item.get("data")
            for item in lscpu["lscpu"]
            if isinstance(item, dict)
        }
        for label, key in labels.items():
            value = values.get(label)
            result[key] = str(value) if value not in (None, "") else None
        sockets, cores = values.get("Socket(s)"), values.get("Core(s) per socket")
    result["physical_cores"] = _product(sockets, cores)
    for name in ("numa_nodes",):
        result[name] = _positive_int(result[name])
    return result


def _product(left: object, right: object) -> int | None:
    left_value, right_value = _positive_int(left), _positive_int(right)
    return (
        left_value * right_value
        if left_value is not None and right_value is not None
        else None
    )


def _positive_int(value: object) -> int | None:
    return int(value) if isinstance(value, str) and value.isdecimal() else None


def _source(path: Path, source_member: str) -> dict[str, object]:
    raw = path.read_bytes()
    if not _relative(source_member):
        raise ValueError("source member must be a relative POSIX path")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _relative(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not PurePosixPath(value).is_absolute()
        and ".." not in PurePosixPath(value).parts
    )


def _uint(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0
