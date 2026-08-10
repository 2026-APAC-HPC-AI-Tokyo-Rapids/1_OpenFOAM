#!/usr/bin/env python3
from __future__ import annotations

# ruff: noqa: E501
import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="capture-hardware")
    parser.add_argument("--mode", choices=["minimal", "profile-postrun"], required=True)
    parser.add_argument("--subject-kind", choices=["regular_run"], required=True)
    parser.add_argument("--subject-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--node-ordinal", type=int, required=True)
    arguments = parser.parse_args(argv)
    run_id, run_dir = _load_manifest(arguments.manifest)
    root = arguments.output_root.resolve()
    expected = (
        run_dir / "source/hardware"
        if arguments.mode == "minimal"
        else run_dir / "profile/raw/hardware"
    )
    if (
        arguments.subject_id != run_id
        or arguments.node_ordinal < 0
        or root != expected.resolve()
    ):
        raise ValueError("hardware probe identity or output root is invalid")
    root.mkdir(parents=True, exist_ok=True)
    if arguments.mode == "profile-postrun":
        _profile_capture(root, run_id, arguments.node_ordinal)
        return 0
    stderr = root / f"lscpu-node-{arguments.node_ordinal}.stderr.txt"
    completed = subprocess.run(
        ["lscpu", "--json"], check=False, text=True, capture_output=True, env=_c_env()
    )
    stderr.write_text(completed.stderr, encoding="utf-8")
    try:
        lscpu_json = json.loads(completed.stdout) if completed.returncode == 0 else None
    except json.JSONDecodeError:
        lscpu_json = None
    document = {
        "schema_version": "hardware-node/v1",
        "node_ordinal": arguments.node_ordinal,
        "hostname": socket.gethostname(),
        "commands": {
            "lscpu": {
                "argv": ["lscpu", "--json"],
                "exit_code": completed.returncode,
                "stderr_member": f"source/hardware/{stderr.name}",
            }
        },
        "lscpu_json": lscpu_json if isinstance(lscpu_json, dict) else None,
        "platform_settings": _platform_settings(),
    }
    target = root / f"node-{arguments.node_ordinal}.json"
    target.write_text(_canonical_json(document) + "\n", encoding="utf-8")
    return 0


def _profile_capture(root: Path, run_id: str, ordinal: int) -> None:
    node = root / f"node-{ordinal}"
    numa = node / "numa"
    numa.mkdir(parents=True, exist_ok=True)
    members: list[dict[str, object]] = []
    proc = node / "proc-meminfo.txt"
    proc.write_bytes(Path("/proc/meminfo").read_bytes())
    members.append(_member("proc_meminfo", None, proc, root))
    for directory in sorted(Path("/sys/devices/system/node").glob("node[0-9]*")):
        suffix = directory.name[4:]
        if not suffix.isdecimal():
            continue
        node_id = int(suffix)
        for role, filename in (
            ("numa_cpulist", "cpulist"),
            ("numa_meminfo", "meminfo"),
        ):
            source = directory / filename
            if not source.is_file():
                raise ValueError(f"missing NUMA source: {source}")
            target = numa / f"node-{node_id}-{filename}.txt"
            target.write_bytes(source.read_bytes())
            members.append(_member(role, node_id, target, root))
    document = {
        "schema_version": "profile-hardware-capture/v1",
        "run_id": run_id,
        "node_ordinal": ordinal,
        "hostname": socket.gethostname(),
        "members": sorted(
            members,
            key=lambda item: (
                str(item["role"]),
                -1 if item["numa_node_id"] is None else int(item["numa_node_id"]),
                str(item["path"]),
            ),
        ),
    }
    (node / "capture.json").write_text(
        _canonical_json(document) + "\n", encoding="utf-8"
    )


def _load_manifest(path: Path) -> tuple[str, Path]:
    document = json.loads(path.read_text(encoding="utf-8"))
    run_id = document.get("run_id") if isinstance(document, dict) else None
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != "run-manifest/v1"
        or document.get("subject_kind") != "regular_run"
        or not isinstance(run_id, str)
        or not re.fullmatch(r"r-[a-f0-9]{32}", run_id)
    ):
        raise ValueError("hardware probe requires a valid regular run manifest")
    resolved = path.resolve(strict=True)
    run_dir = resolved.parents[1]
    if resolved != run_dir / "control/run-manifest.json" or run_dir.name != run_id:
        raise ValueError("hardware probe manifest path is not run-bound")
    return run_id, run_dir


def _canonical_json(value: object) -> str:
    # The hardware schemas contain only integers, booleans, null, strings,
    # arrays, and ASCII object keys.  For that closed domain, sorted compact
    # JSON is byte-identical to RFC 8785 and keeps this installed probe
    # dependency-free.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _member(
    role: str, node_id: int | None, path: Path, root: Path
) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "role": role,
        "numa_node_id": node_id,
        "path": path.relative_to(root.parents[2]).as_posix(),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _c_env() -> dict[str, str]:
    return {**os.environ, "LC_ALL": "C", "LANG": "C"}


def _platform_settings() -> dict[str, object]:
    return {
        "kernel_release": _text("/proc/sys/kernel/osrelease"),
        "online_cpus": _cpu_list("/sys/devices/system/cpu/online"),
        "isolated_cpus": _cpu_list("/sys/devices/system/cpu/isolated"),
        "nohz_full_cpus": _cpu_list(
            "/sys/devices/system/cpu/nohz_full", null_empty=True
        ),
        "memory": _memory(),
        "numa_balancing_enabled": _bool_file("/proc/sys/kernel/numa_balancing"),
        "boost": _boost(),
        "cpufreq_policies": _cpufreq(),
    }


def _text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _cpu_list(path: str, *, null_empty: bool = False) -> list[int] | None:
    raw = _text(path)
    if raw is None:
        return None
    if not raw or (null_empty and raw == "(null)"):
        return []
    result: list[int] = []
    try:
        for part in raw.split(","):
            lower, separator, upper = part.partition("-")
            start = int(lower)
            end = int(upper) if separator else start
            if start < 0 or end < start:
                raise ValueError
            result.extend(range(start, end + 1))
    except ValueError:
        return None
    return result if result == sorted(set(result)) else None


def _memory() -> dict[str, int | None]:
    values: dict[str, int | None] = {
        "total_bytes": None,
        "hugepage_size_bytes": None,
        "hugepages_total": None,
    }
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            token = value.split()[0] if value.split() else ""
            if key == "MemTotal":
                values["total_bytes"] = int(token) * 1024
            elif key == "Hugepagesize":
                values["hugepage_size_bytes"] = int(token) * 1024
            elif key == "HugePages_Total":
                values["hugepages_total"] = int(token)
    except (OSError, ValueError):
        pass
    return values


def _bool_file(path: str) -> bool | None:
    value = _text(path)
    return {"0": False, "1": True}.get(value)


def _boost() -> dict[str, str | bool | None]:
    for path, invert in (
        ("/sys/devices/system/cpu/cpufreq/boost", False),
        ("/sys/devices/system/cpu/intel_pstate/no_turbo", True),
    ):
        raw = _text(path)
        if raw in {"0", "1"}:
            return {"source_path": path, "raw": raw, "enabled": (raw == "1") ^ invert}
    return {"source_path": None, "raw": None, "enabled": None}


def _cpufreq() -> list[dict[str, object]] | None:
    root = Path("/sys/devices/system/cpu/cpufreq")
    try:
        policies = sorted(
            (path for path in root.glob("policy*") if path.name[6:].isdigit()),
            key=lambda path: int(path.name[6:]),
        )
    except OSError:
        return None
    if not root.exists():
        return None
    output = []
    for policy in policies:
        related = _space_uints(policy / "related_cpus")
        output.append(
            {
                "policy_id": int(policy.name[6:]),
                "related_cpus": related,
                "driver": _text(str(policy / "scaling_driver")),
                "governor": _text(str(policy / "scaling_governor")),
                "min_hz": _khz(policy / "scaling_min_freq"),
                "max_hz": _khz(policy / "scaling_max_freq"),
            }
        )
    return output


def _space_uints(path: Path) -> list[int] | None:
    raw = _text(str(path))
    if raw is None:
        return None
    try:
        result = [int(item) for item in raw.split()]
    except ValueError:
        return None
    return (
        result
        if result == sorted(set(result)) and all(item >= 0 for item in result)
        else None
    )


def _khz(path: Path) -> int | None:
    raw = _text(str(path))
    return int(raw) * 1000 if raw is not None and re.fullmatch(r"[0-9]+", raw) else None


if __name__ == "__main__":
    raise SystemExit(main())
