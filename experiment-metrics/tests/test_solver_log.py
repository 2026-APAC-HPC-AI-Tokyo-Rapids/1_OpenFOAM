from __future__ import annotations

import subprocess
from decimal import Decimal
from pathlib import Path

from experiment_metrics.fact import encode_value
from experiment_metrics.protocol import RunProtocol
from experiment_metrics.reducers import solver_log_facts
from experiment_metrics.registry import Registry
from experiment_metrics.solver_log import evaluate_official, parse_solver_log

FIXTURES = Path(__file__).parent / "fixtures"


def _protocol() -> RunProtocol:
    return RunProtocol(("solver",), 1, 2, "test", "shm", {}, "occDrivAerStaticMesh-65M", "a" * 64, 5, 65_334_765, "simpleFoam", "OpenFOAM.com", "v2512")


def test_solver_log_parser_and_reducer_preserve_complete_records() -> None:
    parsed = parse_solver_log((FIXTURES / "solver-valid.log").read_text())
    assert parsed.runtime_header is not None
    assert parsed.runtime_header["hosts"] == [{"hostname": "node-a", "ranks": 1}, {"hostname": "node-b", "ranks": 1}]
    assert len(parsed.step_timings) == 5
    assert parsed.step_timings[0]["execution_sec"] == Decimal("10.0")
    assert len(parsed.pressure_solves) == 5
    assert parsed.log_markers["measured_iterations"] == 4
    assert parsed.log_markers["average_wall_clock_sec"] == Decimal("10.25")
    facts = solver_log_facts(parsed, _protocol())
    assert {fact.key for fact in facts} == {"solver.runtime_header", "solver.step_timings", "solver.pressure_solves", "solver.log_markers", "result.official"}
    assert "10" in encode_value(facts[1].logical_value, "json")


def test_official_evaluator_accepts_pinned_simplefoam_run() -> None:
    parsed = parse_solver_log((FIXTURES / "solver-valid.log").read_text())
    evaluation = evaluate_official(parsed, iterations=5, expected_cells=65_334_765, ranks=2, release="v2512", solver="simpleFoam")
    assert evaluation.valid
    assert evaluation.average_wall_clock_sec == Decimal("10.25")
    assert evaluation.measured_iterations == 4


def test_official_shell_parser_accepts_simplefoam_statistics(tmp_path: Path) -> None:
    check_mesh = tmp_path / "checkMesh.log"
    check_mesh.write_text("    cells: 65334765\nFailed 2 mesh checks.\n\nEnd\n")
    solver = tmp_path / "solver.log"
    solver.write_text("Build  : test OPENFOAM=2512\nExec   : simpleFoam -parallel\nnProcs : 2\ntrapFpe: Floating point exception trapping enabled (FOAM_SIGFPE).\n" + "".join(f"Time = {iteration}\n" for iteration in range(1, 41)) + "    Number of measured time steps = 39\n    Average wall-clock time per time step = 10.25\n    Standard deviation of wall-clock time per time step = 0.25\nEnd\n")
    coefficient = tmp_path / "coefficient.dat"
    coefficient.write_text("# Time Cd Cl\n40 0.435 0.01\n")
    command = [Path(__file__).parents[2] / "benchmark/parse_result.sh", solver, check_mesh, "2", "1", "40", "65334765", "v2512", "occDrivAerStaticMesh-65M", "OpenFOAM.com", coefficient]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    assert "STATUS: VALID" in completed.stdout
    assert "average_wall_clock_seconds_per_iteration=10.25" in completed.stdout
    assert "nodes=1 workload_id=occDrivAerStaticMesh-65M distribution=OpenFOAM.com" in completed.stdout
    assert "CD_SANITY: cd=0.435 step=40" in completed.stdout
    coefficient.write_text("# Time Cd Cl\n40 9.5 0.01\n")
    outlier = subprocess.run(command, check=True, capture_output=True, text=True)
    assert "STATUS: VALID" in outlier.stdout
    assert "CD_SANITY: cd=9.5 step=40" in outlier.stdout
    coefficient.write_text("# Time Cd Cl\n39 0.435 0.01\n")
    assert subprocess.run(command, capture_output=True).returncode != 0
    coefficient.write_text("# Time Cd Cl\n40 0.435 0.01\n")
    assert subprocess.run([*command[:4], "2", *command[5:]], capture_output=True).returncode != 0

    solver.write_text(solver.read_text().replace("Average wall-clock time per time step = 10.25", "Average wall-clock time per time step = NaN"))
    assert subprocess.run(command, capture_output=True).returncode != 0


def test_official_evaluator_rejects_badnum_but_retains_lexemes() -> None:
    text = (FIXTURES / "solver-valid.log").read_text().replace("Final residual = 0.04", "Final residual = NaN", 1)
    parsed = parse_solver_log(text)
    assert parsed.pressure_solves[2]["final_residual"] is None
    assert not evaluate_official(parsed, iterations=5, expected_cells=65_334_765, ranks=2, release="v2512", solver="simpleFoam").valid


def test_solver_fact_keys_are_owned_by_the_log_parser() -> None:
    registry = Registry.load(Path(__file__).parents[1] / "registry/openfoam-v2.toml")
    assert {registry.spec_for(key).owner for key in ("solver.runtime_header", "solver.step_timings", "solver.pressure_solves", "solver.log_markers")} == {"runner.log_parser"}
