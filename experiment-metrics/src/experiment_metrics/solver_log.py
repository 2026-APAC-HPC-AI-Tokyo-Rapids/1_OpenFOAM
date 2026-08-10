from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

EXPECTED_CELLS = 64_000_000
EXPECTED_STEPS = 5
EXPECTED_SOLVES = 10
EXPECTED_ITERATIONS = 321

_TIME = re.compile(r"^Time\s*=\s*(?P<value>\S+)\s*$")
_EXECUTION = re.compile(
    r"^ExecutionTime\s*=\s*(?P<execution>\S+)\s+s(?:\s+ClockTime\s*=\s*(?P<clock>\S+)\s+s)?"
)
_PRESSURE = re.compile(
    r"Solving for p,\s*Initial residual\s*=\s*(?P<initial>[^,]+),\s*"
    r"Final residual\s*=\s*(?P<final>[^,]+),\s*No Iterations\s+(?P<iterations>\S+)"
)
_HEADER = {
    "build": re.compile(r"^Build\s*:\s*(.+)$"),
    "arch": re.compile(r"^Arch\s*:\s*(.+)$"),
    "exec": re.compile(r"^Exec\s*:\s*(.+)$"),
    "file_handler": re.compile(r"^I/O\s*:\s*(.+)$"),
    "nprocs": re.compile(r"^nProcs\s*:\s*(\d+)\s*$"),
}
_HOST_BLOCK = re.compile(
    r"^Hosts\s*:\s*$\n\((?P<body>.*?)^\)", re.MULTILINE | re.DOTALL
)
_HOST = re.compile(r"^\s*\((?P<host>\S+)\s+(?P<ranks>\d+)\)\s*$")
_BADNUM = re.compile(r"\b(?:nan|inf)\b", re.IGNORECASE)
_CELLS = re.compile(r"nCells:\s*(\d+)")


@dataclass(frozen=True, slots=True)
class ParsedSolverLog:
    runtime_header: dict[str, object] | None
    step_timings: tuple[dict[str, object], ...]
    pressure_solves: tuple[dict[str, object], ...]
    log_markers: dict[str, object]
    observed_nprocs: int | None
    observed_hosts: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class OfficialEvaluation:
    valid: bool
    fvops_trim_m: Decimal | None
    seconds_per_step: Decimal | None
    trim_seconds: Decimal | None


def parse_solver_log(text: str) -> ParsedSolverLog:
    lines = text.splitlines()
    current_time: str | None = None
    timings: list[dict[str, object]] = []
    solves: list[dict[str, object]] = []
    badnum_lines = 0
    for line in lines:
        time_match = _TIME.match(line)
        if time_match:
            current_time = time_match["value"]
        execution_match = _EXECUTION.match(line)
        if execution_match:
            execution = execution_match["execution"]
            clock = execution_match["clock"]
            timings.append(
                {
                    "simulation_time_lexeme": current_time,
                    "simulation_time": _decimal_or_none(current_time),
                    "execution_lexeme": execution,
                    "execution_sec": _decimal_or_none(execution),
                    "clock_lexeme": clock,
                    "clock_sec": _decimal_or_none(clock),
                }
            )
        pressure_match = _PRESSURE.search(line)
        if pressure_match:
            initial = pressure_match["initial"].strip()
            final = pressure_match["final"].strip()
            iterations = pressure_match["iterations"]
            solves.append(
                {
                    "simulation_time_lexeme": current_time,
                    "initial_residual_lexeme": initial,
                    "initial_residual": _decimal_or_none(initial),
                    "final_residual_lexeme": final,
                    "final_residual": _decimal_or_none(final),
                    "iterations_lexeme": iterations,
                    "iterations": _integer_or_none(iterations),
                }
            )
        if (
            line.startswith("Time = ")
            or line.startswith("ExecutionTime")
            or "Solving for " in line
        ) and _BADNUM.search(line):
            badnum_lines += 1

    observed_hosts = _parse_hosts(text)
    # A missing Hosts block is permitted by the evaluator, but a present block
    # must be parseable before it can be projected as a canonical header.
    hosts_valid = not re.search(r"^Hosts\s*:", text, re.MULTILINE) or bool(
        observed_hosts
    )
    observed_nprocs = _single_nprocs(lines)
    return ParsedSolverLog(
        runtime_header=_runtime_header(
            lines, observed_nprocs, observed_hosts, hosts_valid
        ),
        step_timings=tuple(timings),
        pressure_solves=tuple(solves),
        log_markers={
            "schema_version": "official-marker/v1",
            "end_count": sum(line.startswith("End") for line in lines),
            "badnum_line_count": badnum_lines,
            "log_ncells": _first_cells(text),
        },
        observed_nprocs=observed_nprocs,
        observed_hosts=observed_hosts,
    )


def evaluate_official(parsed: ParsedSolverLog) -> OfficialEvaluation:
    markers = parsed.log_markers
    valid = (
        markers["end_count"] == 1
        and markers["badnum_line_count"] == 0
        and len(parsed.step_timings) == EXPECTED_STEPS
        and len(parsed.pressure_solves) == EXPECTED_SOLVES
        and sum(
            item["iterations_lexeme"] == str(EXPECTED_ITERATIONS)
            for item in parsed.pressure_solves
        )
        == EXPECTED_SOLVES
        and (markers["log_ncells"] is None or markers["log_ncells"] == EXPECTED_CELLS)
        and _ranks_are_consistent(parsed)
    )
    if not valid:
        return OfficialEvaluation(False, None, None, None)
    first = parsed.step_timings[0]["execution_sec"]
    last = parsed.step_timings[-1]["execution_sec"]
    if not isinstance(first, Decimal) or not isinstance(last, Decimal):
        return OfficialEvaluation(True, None, None, None)
    trim = last - first
    if trim <= 0:
        return OfficialEvaluation(True, None, None, None)
    step_count = Decimal(EXPECTED_STEPS - 1)
    return OfficialEvaluation(
        True,
        (Decimal(EXPECTED_CELLS) * step_count / trim / Decimal(1_000_000)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        ),
        (trim / step_count).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        trim,
    )


def _runtime_header(
    lines: list[str],
    nprocs: int | None,
    hosts: tuple[dict[str, object], ...],
    hosts_valid: bool,
) -> dict[str, object] | None:
    values: dict[str, str] = {}
    for name, expression in _HEADER.items():
        matches = [
            match.group(1) for line in lines if (match := expression.match(line))
        ]
        if len(set(matches)) != 1:
            return None
        values[name] = matches[0]
    if nprocs is None or not hosts_valid or values["file_handler"] != "uncollated":
        return None
    if hosts and sum(item["ranks"] for item in hosts) != nprocs:
        return None
    return {
        "schema_version": "openfoam-header/v1",
        "build": values["build"],
        "arch": values["arch"],
        "exec": values["exec"],
        "file_handler": values["file_handler"],
        "nprocs": nprocs,
        "hosts": list(hosts),
    }


def _parse_hosts(text: str) -> tuple[dict[str, object], ...]:
    blocks = _HOST_BLOCK.findall(text)
    if not blocks:
        return ()
    parsed: list[tuple[tuple[tuple[str, int], ...], ...]] = []
    for body in blocks:
        entries: list[tuple[str, int]] = []
        for line in body.splitlines():
            if not line.strip():
                continue
            match = _HOST.match(line)
            if match is None:
                return ()
            entries.append((match["host"], int(match["ranks"])))
        if not entries or len({host for host, _ in entries}) != len(entries):
            return ()
        parsed.append(tuple(sorted(entries, key=lambda item: item[0].encode())))
    if len(set(parsed)) != 1:
        return ()
    return tuple({"hostname": host, "ranks": ranks} for host, ranks in parsed[0])


def _single_nprocs(lines: list[str]) -> int | None:
    values = {
        int(match.group(1))
        for line in lines
        if (match := _HEADER["nprocs"].match(line)) is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _first_cells(text: str) -> int | None:
    match = _CELLS.search(text)
    return int(match.group(1)) if match else None


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(value)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def _integer_or_none(value: str) -> int | None:
    return int(value) if value.isdecimal() else None


def _ranks_are_consistent(parsed: ParsedSolverLog) -> bool:
    return not (
        parsed.observed_nprocs
        and parsed.observed_hosts
        and sum(item["ranks"] for item in parsed.observed_hosts)
        != parsed.observed_nprocs
    )
