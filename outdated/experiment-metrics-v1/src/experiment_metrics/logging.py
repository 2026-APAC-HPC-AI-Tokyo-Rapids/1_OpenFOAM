from __future__ import annotations

import sys


def warning(message: str) -> None:
    print(f"experiment-metrics: warning: {message}", file=sys.stderr)
