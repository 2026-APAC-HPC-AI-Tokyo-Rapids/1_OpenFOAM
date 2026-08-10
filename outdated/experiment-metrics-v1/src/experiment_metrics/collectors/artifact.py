from __future__ import annotations

import os

from ..context import Context
from ..model import Metric
from ..readers.files import sha256_file
from .case import collect as collect_case
from .result import collect as collect_result


def collect(context: Context) -> list[Metric]:
    output_dir = (
        context.provision_dir / "logs" if context.provision_dir else context.case_dir
    )
    output_path = output_dir / "numerical-summary.md"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        values = [*collect_case(context), *collect_result(context)]
        lines = [
            "# Numerical validation summary",
            "",
            f"- `run`: `{context.run}`",
            "",
            "## Metrics",
            "",
        ]
        lines.extend(
            f"- `{metric.key}`: `{metric.value}`"
            for metric in sorted(values, key=lambda item: item.key.encode())
        )
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        size = str(os.stat(output_path).st_size)
        digest = sha256_file(output_path)
    except OSError:
        size = ""
        digest = ""
    return [
        Metric("artifact.numerical_summary.path", "numerical-summary.md"),
        Metric("artifact.numerical_summary.sha256", digest),
        Metric("artifact.numerical_summary.size_bytes", size),
    ]
