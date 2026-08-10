from __future__ import annotations

from ..context import Context
from ..model import Metric
from ..readers.dictionary import read_entry


def collect(context: Context) -> list[Metric]:
    path = "system/decomposeParDict.6"
    return [
        Metric(
            "parallel.decomposition.method",
            read_entry(context.case_dir, path, "method"),
        ),
        Metric(
            "parallel.decomposition.subdomains",
            read_entry(context.case_dir, path, "numberOfSubdomains"),
        ),
    ]
