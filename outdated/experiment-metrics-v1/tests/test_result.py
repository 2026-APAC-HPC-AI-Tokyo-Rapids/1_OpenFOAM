from pathlib import Path

from experiment_metrics.collectors.result import collect
from experiment_metrics.context import Context


def test_aero_collector_uses_available_tail_rows(tmp_path: Path) -> None:
    output = tmp_path / "postProcessing/forceCoeffs1/0"
    output.mkdir(parents=True)
    (output / "coefficient.dat").write_text(
        "# Time Cd Cl CmPitch\n1 1.0 2.0 3.0\n2 3.0 4.0 5.0\n",
        encoding="utf-8",
    )
    context = Context("run", tmp_path, None)
    values = {metric.key: metric.value for metric in collect(context)}

    assert values["result.aero.tail.window_size"] == "2"
    assert values["result.aero.cd.tail.mean"] == "2.0"
    assert values["result.aero.cd.tail.population_stddev"] == "1.0"
    assert values["result.flux.inlet.final_m3_per_sec"] == ""


def test_vector_results_are_each_stored_as_one_string_value(tmp_path: Path) -> None:
    solver = tmp_path / "postProcessing/solverInfo1/0"
    solver.mkdir(parents=True)
    (solver / "solverInfo.dat").write_text(
        "# Time Ux_initial Ux_final Ux_iters Uy_initial Uy_final Uy_iters "
        "Uz_initial Uz_final Uz_iters U_converged p_initial p_final p_iters "
        "p_converged\n"
        "1 0.1 0.01 2 0.2 0.02 3 0.3 0.03 4 1 0.4 0.04 5 1\n",
        encoding="utf-8",
    )
    probes = tmp_path / "postProcessing/wakeProbeMetrics/0"
    probes.mkdir(parents=True)
    (probes / "U").write_text(
        "# Time 0 1 2\n1 (1 2 3) (4 5 6) (7 8 9)\n",
        encoding="utf-8",
    )
    (probes / "p").write_text("# Time 0 1 2\n1 10 11 12\n", encoding="utf-8")

    values = {
        metric.key: metric.value
        for metric in collect(Context("run", tmp_path, None))
    }

    assert values["solver.linear.u.initial_residual"] == "['0.1', '0.2', '0.3']"
    assert values["solver.linear.u.final_residual"] == "['0.01', '0.02', '0.03']"
    assert values["solver.linear.u.iterations"] == "['2', '3', '4']"
    assert values["result.probe.wake_near.u.final_m_per_sec"] == "['1', '2', '3']"
    assert not any(key.startswith("solver.linear.u.0.") for key in values)
    assert not any(key.endswith(".u.final_m_per_sec.0") for key in values)
