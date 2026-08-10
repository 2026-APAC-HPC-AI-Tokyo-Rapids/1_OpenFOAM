from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

BENCHMARKS = ("PingPong", "Sendrecv", "Allreduce")
_SECTION = re.compile(r"^#\s*Benchmarking\s+(PingPong|Sendrecv|Allreduce)\s*$")
_PROCESSES = re.compile(r"^#\s*#?processes\s*=\s*(\d+)\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class IMBResult:
    benchmark: str
    process_count: int
    message_bytes: int
    iterations: int
    time_min_us: Decimal | None
    time_avg_us: Decimal | None
    time_max_us: Decimal | None
    bandwidth_mbytes_per_sec: Decimal | None


def parse_imb_mpi1(text: str) -> tuple[IMBResult, ...]:
    """Parse only complete IMB-MPI1 target sections.

    Any malformed or truncated PingPong, Sendrecv, or Allreduce section rejects
    the whole capture so callers never publish a partial network relation.
    """

    lines = text.splitlines()
    starts = [
        (index, match[1])
        for index, line in enumerate(lines)
        if (match := _SECTION.match(line))
    ]
    by_benchmark: dict[str, int] = {name: 0 for name in BENCHMARKS}
    result: list[IMBResult] = []
    for position, (start, benchmark) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        section = lines[start:end]
        result.extend(_parse_section(benchmark, section))
        by_benchmark[benchmark] += 1
    if not starts or any(count == 0 for count in by_benchmark.values()):
        raise ValueError("IMB output is missing a required benchmark section")
    return tuple(result)


def _parse_section(benchmark: str, lines: list[str]) -> list[IMBResult]:
    process_count: int | None = None
    header: list[str] | None = None
    rows: list[IMBResult] = []
    for line in lines:
        process_match = _PROCESSES.match(line)
        if process_match:
            process_count = int(process_match[1])
            continue
        stripped = line.strip()
        if (
            stripped.startswith("#")
            and "bytes" in stripped.lower()
            and "repetitions" in stripped.lower()
        ):
            header = [token.lstrip("#") for token in stripped.lower().split()]
            continue
        if not stripped or stripped.startswith("#"):
            continue
        tokens = stripped.split()
        if not tokens[0].isdigit():
            continue  # IMB warning/progress text is not a data record.
        if process_count is None or header is None:
            raise ValueError(f"IMB {benchmark} data precedes its header")
        rows.append(_parse_row(benchmark, process_count, header, tokens))
    if process_count is None or header is None or not rows:
        raise ValueError(f"IMB {benchmark} section is incomplete")
    return rows


def _parse_row(
    benchmark: str, process_count: int, header: list[str], tokens: list[str]
) -> IMBResult:
    if process_count <= 0 or len(tokens) != len(header):
        raise ValueError(f"IMB {benchmark} row does not match its header")
    columns = dict(zip(header, tokens, strict=True))
    message_bytes = _integer(columns, "bytes")
    iterations = _integer(columns, "repetitions")
    if message_bytes < 0 or iterations <= 0:
        raise ValueError(f"IMB {benchmark} row has invalid cardinality")
    if benchmark == "Allreduce":
        return IMBResult(
            benchmark,
            process_count,
            message_bytes,
            iterations,
            _decimal_column(columns, "t_min[usec]"),
            _decimal_column(columns, "t_avg[usec]"),
            _decimal_column(columns, "t_max[usec]"),
            None,
        )
    time = _decimal_column(columns, "t[usec]")
    bandwidth = _decimal_column(columns, "mbytes/sec")
    if time is None or bandwidth is None or bandwidth < 0:
        raise ValueError(f"IMB {benchmark} row has invalid transfer values")
    return IMBResult(
        benchmark,
        process_count,
        message_bytes,
        iterations,
        None,
        None,
        time,
        bandwidth,
    )


def _integer(columns: dict[str, str], name: str) -> int:
    value = columns.get(name)
    if value is None or not value.isdecimal():
        raise ValueError(f"IMB row has no integer {name}")
    return int(value)


def _decimal_column(columns: dict[str, str], name: str) -> Decimal | None:
    value = columns.get(name)
    if value is None:
        raise ValueError(f"IMB row has no {name}")
    try:
        result = Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"IMB row has invalid {name}") from error
    return result if result.is_finite() else None
