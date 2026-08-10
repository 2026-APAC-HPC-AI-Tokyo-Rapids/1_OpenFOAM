from __future__ import annotations

from datetime import datetime

from ..model import Metric
from ..readers.pjstat import read

KEYS = [
    "scheduler.state",
    "scheduler.started_at",
    "scheduler.elapsed_sec",
    "scheduler.exit_code",
    "scheduler.signal",
    "scheduler.pjm_code",
    "scheduler.node_count.allocated",
    "resource.job.memory.max_rss_bytes",
    "resource.job.cpu.user_time_sec",
    "resource.job.cpu.system_time_sec",
]


def collect(job_id: str) -> list[Metric]:
    source = read(job_id)
    values = {key: "" for key in KEYS}
    values["scheduler.state"] = source.get("st", "")
    values["scheduler.started_at"] = _timestamp(source.get("sdt", ""))
    values["scheduler.elapsed_sec"] = _parenthetical(source.get("elp", ""))
    values["scheduler.exit_code"] = source.get("ec", "")
    signal = source.get("sn", "")
    values["scheduler.signal"] = "" if signal in ("", "0") else signal
    values["scheduler.pjm_code"] = source.get("pc", "")
    values["scheduler.node_count.allocated"] = source.get("nnumu", "")
    values["resource.job.memory.max_rss_bytes"] = _parenthetical(
        source.get("mmszu", "")
    )
    values["resource.job.cpu.user_time_sec"] = _milliseconds(source.get("uctmut", ""))
    values["resource.job.cpu.system_time_sec"] = _milliseconds(source.get("sctmut", ""))
    return [Metric(key, values[key]) for key in KEYS]


def _parenthetical(value: str) -> str:
    if "(" not in value or ")" not in value:
        return ""
    return value.rsplit("(", 1)[1].split(")", 1)[0].strip()


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.strptime(
            f"{value.strip()} +0900",
            "%Y/%m/%d %H:%M:%S %z",
        )
    except ValueError:
        return ""
    return parsed.isoformat()


def _milliseconds(value: str) -> str:
    try:
        return repr(float(value.strip()) / 1000)
    except ValueError:
        return ""
