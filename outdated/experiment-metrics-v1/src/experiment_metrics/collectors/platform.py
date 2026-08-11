from __future__ import annotations

import base64
import json
import os
import platform
import re
import socket
from pathlib import Path

from ..command import run
from ..model import Metric

ENV_NAME = re.compile(rb"^[A-Za-z][A-Za-z0-9_]*$")


def collect(_: Path) -> list[Metric]:
    result = _environment()
    environment_names = set(os.environ)

    os_release = platform.freedesktop_os_release()
    result.extend(
        [
            Metric("system.os.id", os_release.get("ID", "")),
            Metric("system.os.version_id", os_release.get("VERSION_ID", "")),
            Metric("system.kernel.release", os.uname().release),
        ]
    )
    if not ({"PXMYCLST"} & environment_names):
        result.append(Metric("system.cluster", "genkai"))
    if not ({"HOSTTYPE", "WM_ARCH"} & environment_names):
        result.append(Metric("system.architecture", os.uname().machine))
    if not ({"HOSTNAME", "PJM_NODE"} & environment_names):
        result.append(Metric("system.node.hostname", socket.gethostname()))

    result.extend(_cpu())
    try:
        affinity = len(os.sched_getaffinity(0))
        result.append(Metric("hardware.cpu.available_logical_count", str(affinity)))
    except OSError:
        result.append(Metric("hardware.cpu.available_logical_count", ""))
    result.append(Metric("hardware.memory.total_bytes", _memory_total()))
    return result


def _environment() -> list[Metric]:
    result: list[Metric] = []
    for name, value in os.environb.items():
        if ENV_NAME.fullmatch(name):
            name_token = name.decode("ascii")
        else:
            name_token = f"encoded.{name.hex()}"
        try:
            decoded = value.decode("utf-8")
            key = f"env.{name_token}"
        except UnicodeDecodeError:
            decoded = base64.b64encode(value).decode("ascii")
            key = f"env.bytes.{name_token}"
        result.append(Metric(key, decoded))
    return result


def _cpu() -> list[Metric]:
    keys = {
        "Model name": "hardware.cpu.model",
        "Socket(s)": "hardware.cpu.socket_count",
        "Core(s) per socket": "hardware.cpu.cores_per_socket",
        "Thread(s) per core": "hardware.cpu.threads_per_core",
    }
    values = {metric_key: "" for metric_key in keys.values()}
    command = run(["lscpu", "--json"])
    if command.returncode == 0:
        try:
            payload = json.loads(command.stdout)
            fields = {
                item.get("field", "").removesuffix(":"): str(item.get("data", ""))
                for item in payload.get("lscpu", [])
            }
            for source, metric_key in keys.items():
                values[metric_key] = fields.get(source, "")
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
    return [Metric(key, value) for key, value in values.items()]


def _memory_total() -> str:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return str(int(line.split()[1]) * 1024)
    except (OSError, ValueError, IndexError):
        pass
    return ""
