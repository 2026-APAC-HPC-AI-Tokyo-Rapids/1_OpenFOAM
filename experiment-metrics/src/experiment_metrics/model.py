from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Metric:
    key: str
    value: str


def scalar(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return repr(value)
    return str(value)


def metrics(keys: list[str], values: dict[str, object]) -> list[Metric]:
    return [Metric(key, scalar(values.get(key))) for key in keys]
