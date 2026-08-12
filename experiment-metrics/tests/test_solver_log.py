from __future__ import annotations

import re
import subprocess
from decimal import Decimal
from pathlib import Path

from experiment_metrics.fact import encode_value
from experiment_metrics.reducers import solver_log_facts
from experiment_metrics.registry import Registry
from experiment_metrics.solver_log import evaluate_official, parse_solver_log

FIXTURES = Path(__file__).parent / "fixtures"


def test_solver_log_parser_and_reducer_preserve_complete_records() -> None:
    parsed = parse_solver_log((FIXTURES / "solver-valid.log").read_text())

    assert parsed.runtime_header is not None
    assert parsed.runtime_header["hosts"] == [
        {"hostname": "node-a", "ranks": 1},
        {"hostname": "node-b", "ranks": 1},
    ]
    assert len(parsed.step_timings) == 5
    assert parsed.step_timings[0]["execution_lexeme"] == "10.0"
    assert parsed.step_timings[0]["execution_sec"] == Decimal("10.0")
    assert len(parsed.pressure_solves) == 10
    assert parsed.pressure_solves[0]["final_residual_lexeme"] == "1.0e-1"
    assert parsed.log_markers == {
        "schema_version": "official-marker/v1",
        "end_count": 1,
        "badnum_line_count": 0,
        "log_ncells": None,
    }
    facts = solver_log_facts(parsed)
    assert {fact.key for fact in facts} == {
        "solver.runtime_header",
        "solver.step_timings",
        "solver.pressure_solves",
        "solver.log_markers",
        "result.official",
    }
    assert "10" in encode_value(facts[1].logical_value, "json")


def test_official_evaluator_matches_existing_shell_golden() -> None:
    root = Path(__file__).parents[2]
    log = root / "tasks/baseline_logs/gadi/gadi-1n-175550866.log"
    shell = subprocess.run(
        ["bash", str(root / "tasks/parse_result.sh"), str(log)],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    parsed = parse_solver_log(log.read_text())
    evaluation = evaluate_official(parsed)
    expected = re.search(r"FVOPS_trim=([0-9.]+)M", shell)

    assert "STATUS: VALID" in shell
    assert evaluation.valid
    assert evaluation.fvops_trim_m == Decimal(expected.group(1))


def test_official_evaluator_rejects_badnum_but_retains_lexemes() -> None:
    text = (
        (FIXTURES / "solver-valid.log")
        .read_text()
        .replace("Final residual = 0.1", "Final residual = NaN", 1)
    )
    parsed = parse_solver_log(text)

    assert parsed.pressure_solves[2]["final_residual_lexeme"] == "NaN"
    assert parsed.pressure_solves[2]["final_residual"] is None
    assert parsed.log_markers["badnum_line_count"] == 1
    assert not evaluate_official(parsed).valid


def test_malformed_timing_is_retained_with_nullable_numeric() -> None:
    parsed = parse_solver_log("ExecutionTime = 1.2.3 s  ClockTime = Infinity s\n")

    assert parsed.step_timings == (
        {
            "simulation_time_lexeme": None,
            "simulation_time": None,
            "execution_lexeme": "1.2.3",
            "execution_sec": None,
            "clock_lexeme": "Infinity",
            "clock_sec": None,
        },
    )


def test_malformed_hosts_do_not_form_a_canonical_runtime_header() -> None:
    text = (
        (FIXTURES / "solver-valid.log")
        .read_text()
        .replace("(node-a 1)", "not-a-host-entry")
    )

    assert parse_solver_log(text).runtime_header is None


def test_solver_fact_keys_are_owned_by_the_log_parser() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")

    assert {
        registry.spec_for(key).owner
        for key in (
            "solver.runtime_header",
            "solver.step_timings",
            "solver.pressure_solves",
            "solver.log_markers",
        )
    } == {"runner.log_parser"}
