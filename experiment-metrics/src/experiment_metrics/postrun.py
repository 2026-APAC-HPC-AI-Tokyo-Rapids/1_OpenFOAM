from __future__ import annotations

import base64

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


def partition_requested_fact(dictionary: Path) -> Fact:
    return Fact("mesh.partition.requested", _requested_partition(dictionary))


def build_provision_fact(path: Path, *, purpose: str) -> Fact:
    from .provision import validate_provision_document

    document = _json(path)
    validate_provision_document(document, purpose=purpose)
    run_dir = path.parents[1]
    ldd_sources = [
        {
            "role": item["role"],
            "source": _expanded_member(item["source"], run_dir),
        }
        for item in document["ldd_raw"]
    ]
    expanded = {
        **document,
        "ldd_raw": ldd_sources,
        "launcher_version": _expanded_version(document["launcher_version"], run_dir),
    }
    if purpose == "profile":
        expanded["profiler_version"] = _expanded_version(
            document["profiler_version"], run_dir
        )
    return Fact("build.provision", expanded)


def profile_hardware_facts(
    root: Path, *, run_id: str, expected_nodes: int
) -> tuple[Fact, ...]:
    facts: list[Fact] = []
    run_dir = root.resolve().parents[2]
    if root.resolve() != run_dir / "profile/raw/hardware":
        raise ValueError("profile hardware root is outside the bound run")
    for ordinal in range(expected_nodes):
        capture_path = root / f"node-{ordinal}/capture.json"
        document = _json(capture_path)
        if (
            set(document)
            != {"schema_version", "run_id", "node_ordinal", "hostname", "members"}
            or document["schema_version"] != "profile-hardware-capture/v1"
            or document["run_id"] != run_id
            or document["node_ordinal"] != ordinal
            or not isinstance(document["hostname"], str)
            or not document["hostname"]
            or not isinstance(document["members"], list)
        ):
            raise ValueError("profile hardware capture is invalid")
        members = document["members"]
        proc = [item for item in members if item.get("role") == "proc_meminfo"]
        if len(proc) != 1 or proc[0].get("numa_node_id") is not None:
            raise ValueError("profile hardware proc meminfo is incomplete")
        proc_raw = _profile_member(proc[0], run_dir)
        available = _single_kb(proc_raw, rb"^MemAvailable:\s+([0-9]+)\s+kB$")
        facts.append(
            Fact(
                f"profile.hardware.node.{ordinal}.summary",
                {
                    "hostname": document["hostname"],
                    "postrun_mem_available_bytes": available * 1024,
                },
            )
        )
        node_ids = sorted(
            {
                item.get("numa_node_id")
                for item in members
                if item.get("role") in {"numa_cpulist", "numa_meminfo"}
            }
        )
        if any(
            not isinstance(node_id, int) or isinstance(node_id, bool)
            for node_id in node_ids
        ):
            raise ValueError("profile hardware NUMA node ID is invalid")
        for node_id in node_ids:
            cpulists = [
                item
                for item in members
                if item.get("role") == "numa_cpulist"
                and item.get("numa_node_id") == node_id
            ]
            meminfos = [
                item
                for item in members
                if item.get("role") == "numa_meminfo"
                and item.get("numa_node_id") == node_id
            ]
            if len(cpulists) != 1 or len(meminfos) != 1:
                raise ValueError("profile hardware NUMA members are incomplete")
            cpulist = _canonical_cpu_list(_profile_member(cpulists[0], run_dir))
            meminfo = _profile_member(meminfos[0], run_dir)
            total = _single_kb(
                meminfo, rf"^Node {node_id} MemTotal:\s+([0-9]+)\s+kB$".encode()
            )
            free = _single_kb(
                meminfo, rf"^Node {node_id} MemFree:\s+([0-9]+)\s+kB$".encode()
            )
            facts.append(
                Fact(
                    f"profile.hardware.node.{ordinal}.numa.{node_id}",
                    {
                        "cpulist": cpulist,
                        "mem_total_bytes": total * 1024,
                        "mem_free_bytes": free * 1024,
                    },
                )
            )
    return tuple(facts)


def _profile_member(value: object, root: Path) -> bytes:
    if not isinstance(value, dict) or set(value) != {
        "role",
        "numa_node_id",
        "path",
        "size_bytes",
        "sha256",
    }:
        raise ValueError("profile hardware member is invalid")
    path = (root / str(value["path"])).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("profile hardware member is outside the bound run")
    raw = path.read_bytes()
    if (
        len(raw) != value["size_bytes"]
        or hashlib.sha256(raw).hexdigest() != value["sha256"]
    ):
        raise ValueError("profile hardware member differs from its identity")
    return raw


def _single_kb(raw: bytes, pattern: bytes) -> int:
    matches = re.findall(pattern, raw, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError("profile hardware memory source is invalid")
    return int(matches[0])


def _canonical_cpu_list(raw: bytes) -> list[int]:
    text = raw.decode("ascii").strip()
    cpus: list[int] = []
    for token in text.split(",") if text else []:
        lower, separator, upper = token.partition("-")
        if not lower.isdecimal() or (separator and not upper.isdecimal()):
            raise ValueError("profile hardware CPU list is invalid")
        start = int(lower)
        end = int(upper) if separator else start
        if end < start:
            raise ValueError("profile hardware CPU range is reversed")
        cpus.extend(range(start, end + 1))
    if cpus != sorted(set(cpus)):
        raise ValueError("profile hardware CPU list is not canonical")
    return cpus


def _expanded_version(value: object, root: Path) -> dict[str, object]:
    assert isinstance(value, dict)
    return {
        **value,
        "stdout": _expanded_member(value["stdout"], root),
        "stderr": _expanded_member(value["stderr"], root),
    }


def _expanded_member(value: object, root: Path) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"path", "size_bytes", "sha256"}:
        raise ValueError("provision source member is invalid")
    path = (root / str(value["path"])).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("provision source member is outside the bound run")
    raw = path.read_bytes()
    if (
        len(raw) != value["size_bytes"]
        or hashlib.sha256(raw).hexdigest() != value["sha256"]
    ):
        raise ValueError("provision source member differs from its identity")
    return {**value, "content_b64": base64.b64encode(raw).decode("ascii")}


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


def mesh_facts_from_logs(
    check_mesh_log: Path, decompose_log: Path, dictionary: Path
) -> tuple[Fact, Fact, Fact]:
    """65Mセルのメッシュを開き直さず、保存済みの準備ログを解析する。"""

    check_text = check_mesh_log.read_text(encoding="utf-8", errors="replace")
    topology = {
        "schema_version": "mesh-topology/v2",
        "cells": _unique_log_uint(check_text, "cells"),
        "faces": _unique_log_uint(check_text, "faces"),
        "points": _unique_log_uint(check_text, "points"),
        "internal_faces": _unique_log_uint(check_text, "internal faces"),
    }
    if topology["internal_faces"] > topology["faces"]:
        raise ValueError("checkMeshの内部面数が総面数を超えています")
    requested = _requested_partition(dictionary)
    observed = _partition_log(
        decompose_log.read_text(encoding="utf-8", errors="replace"),
        requested_subdomains=requested["subdomains"],
        expected_cells=topology["cells"],
    )
    return (
        Fact("mesh.topology", topology),
        Fact("mesh.partition.requested", requested),
        Fact("mesh.partition.observed", observed),
    )


def _unique_log_uint(text: str, name: str) -> int:
    values = {
        int(match)
        for match in re.findall(rf"(?m)^\s*{re.escape(name)}:\s*([0-9]+)\s*$", text)
    }
    if len(values) != 1:
        raise ValueError(f"checkMeshログから一意な{name}を取得できません")
    return next(iter(values))


def _partition_log(
    text: str, *, requested_subdomains: object, expected_cells: object
) -> dict[str, object]:
    if not isinstance(requested_subdomains, int) or not isinstance(expected_cells, int):
        raise ValueError("partition log axes are invalid")
    starts = list(re.finditer(r"(?m)^Processor ([0-9]+)\s*$", text))
    if len(starts) != requested_subdomains:
        raise ValueError("decomposePar log processor count differs from request")
    subdomains: list[dict[str, object]] = []
    directed_interfaces: dict[tuple[int, int], int] = {}
    for index, match in enumerate(starts):
        rank = int(match.group(1))
        if rank != index:
            raise ValueError("decomposePar log processor ranks are not canonical")
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        body = text[match.end() : end]
        cells = _one_equals_uint(body, "Number of cells")
        patches = _one_equals_uint(body, "Number of processor patches")
        processor_faces = _one_equals_uint(body, "Number of processor faces")
        subdomains.append(
            {
                "rank": rank,
                "cell_count": cells,
                "processor_patch_count": patches,
                "processor_face_count": processor_faces,
            }
        )
        for peer, count in re.findall(
            r"(?m)^\s*Number of faces shared with processor ([0-9]+) = ([0-9]+)\s*$",
            body,
        ):
            directed_interfaces[(rank, int(peer))] = int(count)
    if sum(item["cell_count"] for item in subdomains) != expected_cells:
        raise ValueError("decomposeParとcheckMeshでセル総数が一致しません")
    interfaces: list[dict[str, int]] = []
    for (rank, peer), count in sorted(directed_interfaces.items()):
        if rank >= peer:
            continue
        if directed_interfaces.get((peer, rank)) != count:
            raise ValueError("decomposePar interface observations are asymmetric")
        interfaces.append({"lower_rank": rank, "upper_rank": peer, "face_count": count})
    return {
        "schema_version": "partition-observed/v2",
        "subdomains": subdomains,
        "interfaces": interfaces,
    }


def _one_equals_uint(text: str, label: str) -> int:
    matches = re.findall(
        rf"(?m)^[ \t]+{re.escape(label)}\s*=\s*([0-9]+)\s*$", text
    )
    if len(matches) != 1:
        raise ValueError(f"decomposePar log has no unique {label}")
    return int(matches[0])


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
    supported_methods = {"scotch", "hierarchical", "multiLevel"}
    if (
        number is None
        or method is None
        or method[1] not in supported_methods
        or int(number[1]) <= 0
    ):
        raise ValueError("decomposeParDict is not a supported closed configuration")
    return {
        "schema_version": "partition-requested/v2",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "subdomains": int(number[1]),
        "method": method[1],
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
        raise ValueError("領域分割後のセル総数がメッシュ構成と一致しません")
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
