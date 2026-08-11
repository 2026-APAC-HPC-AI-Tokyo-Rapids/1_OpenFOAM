from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .protocol import RunProtocol

BENCHMARKS = ("PingPong", "Sendrecv", "Allreduce")
_SECTION = re.compile(r"^#\s*Benchmarking\s+(PingPong|Sendrecv|Allreduce)\s*$")
_PROCESSES = re.compile(r"^#\s*#?processes\s*=\s*(\d+)\s*$", re.IGNORECASE)
_VERSION = re.compile(
    r"^(?:IMB-MPI1\s+(\S+)|#\s+Intel\(R\) MPI Benchmarks\s+(\S+),\s+MPI-1 part)\s*$"
)


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


@dataclass(frozen=True, slots=True)
class IMBCapture:
    results: tuple[IMBResult, ...]
    version: str
    process_count: int
    time_limit_sec: int
    iteration_policy: str


def validate_imb_capture(
    *,
    stdout_path: Path,
    stderr_path: Path,
    argv_path: Path,
    protocol: RunProtocol,
) -> IMBCapture:
    """Validate the launch command and both durable output streams together."""

    stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_path.read_bytes()
    document = json.loads(argv_path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "argv"}
        or document["schema_version"] != "argv/v1"
        or not isinstance(document["argv"], list)
        or not all(isinstance(item, str) and item for item in document["argv"])
    ):
        raise ValueError("IMB argv record is not a closed argv/v1 object")
    argv = document["argv"]
    assert isinstance(argv, list)
    if (
        len(argv) != 19
        or not Path(argv[0]).is_absolute()
        or not Path(argv[5]).is_absolute()
    ):
        raise ValueError("IMB argv does not have the closed command shape")
    expected_tail = [
        "-np",
        str(protocol.ranks),
        "-ppn",
        str(protocol.ranks_per_node),
        argv[5],
        "-npmin",
        str(protocol.ranks),
        "-msglog",
        "0:22",
        "-iter",
        "1000",
        "-time",
        "1",
        "-iter_policy",
        "dynamic",
        "PingPong",
        "Sendrecv",
        "Allreduce",
    ]
    if argv[1:] != expected_tail:
        raise ValueError("IMB argv differs from the protocol command")
    results = parse_imb_mpi1(stdout)
    expected_process_counts = {
        "PingPong": 2,
        "Sendrecv": protocol.ranks,
        "Allreduce": protocol.ranks,
    }
    for benchmark, expected_process_count in expected_process_counts.items():
        observed_process_counts = {
            item.process_count for item in results if item.benchmark == benchmark
        }
        if observed_process_counts != {expected_process_count}:
            raise ValueError(f"IMB {benchmark} process count differs from the protocol")
    transfer_sizes = {0, *(1 << exponent for exponent in range(23))}
    expected_sizes = {
        "PingPong": transfer_sizes,
        "Sendrecv": transfer_sizes,
        # Intel IMB uses MPI_INT for this collective, so msglog 0:22 starts
        # with zero bytes and then four bytes rather than one and two bytes.
        "Allreduce": {0, *(1 << exponent for exponent in range(2, 23))},
    }
    for benchmark in BENCHMARKS:
        observed_sizes = {
            item.message_bytes for item in results if item.benchmark == benchmark
        }
        if observed_sizes != expected_sizes[benchmark]:
            raise ValueError(f"IMB {benchmark} message-size sweep is incomplete")
    versions = [
        next(group for group in match.groups() if group is not None)
        for line in stdout.splitlines()
        if (match := _VERSION.match(line))
    ]
    if len(versions) != 1:
        raise ValueError("IMB output has no unique software version")
    return IMBCapture(results, versions[0], protocol.ranks, 1, "dynamic")


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
    multi_time_header = {
        "bytes",
        "repetitions",
        "t_min[usec]",
        "t_max[usec]",
        "t_avg[usec]",
    }
    if benchmark == "Allreduce" or multi_time_header.issubset(columns):
        bandwidth = (
            _decimal_column(columns, "mbytes/sec")
            if benchmark == "Sendrecv"
            else None
        )
        if bandwidth is not None and bandwidth < 0:
            raise ValueError(f"IMB {benchmark} row has invalid transfer values")
        return IMBResult(
            benchmark,
            process_count,
            message_bytes,
            iterations,
            _decimal_column(columns, "t_min[usec]"),
            _decimal_column(columns, "t_avg[usec]"),
            _decimal_column(columns, "t_max[usec]"),
            bandwidth,
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
