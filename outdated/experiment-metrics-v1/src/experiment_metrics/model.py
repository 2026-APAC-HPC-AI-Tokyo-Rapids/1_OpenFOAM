from __future__ import annotations

import math
from dataclasses import dataclass


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


@dataclass(frozen=True, slots=True, init=False)
class Metric:
    key: str
    value: str

    def __init__(self, key: str, value: object | None) -> None:
        object.__setattr__(self, "key", key)
        object.__setattr__(self, "value", scalar(value))


def metrics(keys: list[str], values: dict[str, object]) -> list[Metric]:
    return [Metric(key, values.get(key)) for key in keys]
