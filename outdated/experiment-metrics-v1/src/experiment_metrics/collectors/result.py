from __future__ import annotations

import math
from pathlib import Path

from ..context import Context
from ..model import Metric
from ..readers.openfoam_table import read_table, vector

AERO_KEYS = [
    "result.aero.tail.window_size",
    *[
        f"result.aero.{coefficient}.tail.{statistic}"
        for coefficient in ("cd", "cl", "cm_pitch")
        for statistic in ("final", "min", "max", "mean", "population_stddev")
    ],
]

SOLVER_KEYS = [
    "solver.linear.u.initial_residual",
    "solver.linear.u.final_residual",
    "solver.linear.u.iterations",
    "solver.linear.u.converged",
    "solver.linear.p.initial_residual",
    "solver.linear.p.final_residual",
    "solver.linear.p.iterations",
    "solver.linear.p.converged",
    "solver.continuity.final.local",
    "solver.continuity.final.global",
    "solver.continuity.cumulative",
]

FIELD_KEYS = [
    "result.field.u_magnitude.final.min_m_per_sec",
    "result.field.u_magnitude.final.max_m_per_sec",
    "result.field.kinematic_pressure.final.min_m2_per_sec2",
    "result.field.kinematic_pressure.final.max_m2_per_sec2",
    "result.field.k.final.min_m2_per_sec2",
    "result.field.k.final.max_m2_per_sec2",
    "result.field.omega.final.min_per_sec",
    "result.field.omega.final.max_per_sec",
    "result.flux.inlet.final_m3_per_sec",
    "result.flux.outlet.final_m3_per_sec",
    *[
        f"result.probe.{probe}.u.final_m_per_sec"
        for probe in ("wake_near", "wake_upper", "wake_far")
    ],
    *[
        f"result.probe.{probe}.kinematic_pressure.final_m2_per_sec2"
        for probe in ("wake_near", "wake_upper", "wake_far")
    ],
]

ALL_RESULT_KEYS = [*AERO_KEYS, *SOLVER_KEYS, *FIELD_KEYS]


def collect(context: Context) -> list[Metric]:
    values = {key: "" for key in ALL_RESULT_KEYS}
    _aero(context.case_dir, values)
    _solver(context.case_dir, values)
    _fields(context.case_dir, values)
    return [Metric(key, values[key]) for key in ALL_RESULT_KEYS]


def collect_status(context: Context, exit_code: int) -> list[Metric]:
    solver_info = read_table(
        context.case_dir / "postProcessing/solverInfo1/0/solverInfo.dat"
    )
    final_time = solver_info.last().get("Time", "")
    return [
        Metric("solver.completed", str(exit_code == 0).lower()),
        Metric("solver.final_simulation_time", final_time),
    ]


def _aero(case_dir: Path, values: dict[str, str]) -> None:
    table = read_table(case_dir / "postProcessing/forceCoeffs1/0/coefficient.dat")
    rows = table.tail(100)
    if not rows:
        return
    values["result.aero.tail.window_size"] = str(len(rows))
    for source, target in (("Cd", "cd"), ("Cl", "cl"), ("CmPitch", "cm_pitch")):
        try:
            samples = [float(row[source]) for row in rows]
        except (KeyError, ValueError):
            continue
        mean = math.fsum(samples) / len(samples)
        statistics = {
            "final": samples[-1],
            "min": min(samples),
            "max": max(samples),
            "mean": mean,
            "population_stddev": math.sqrt(
                math.fsum((sample - mean) ** 2 for sample in samples) / len(samples)
            ),
        }
        for statistic, value in statistics.items():
            values[f"result.aero.{target}.tail.{statistic}"] = repr(value)


def _solver(case_dir: Path, values: dict[str, str]) -> None:
    row = read_table(case_dir / "postProcessing/solverInfo1/0/solverInfo.dat").last()
    vector_columns = {
        "solver.linear.u.initial_residual": (
            "Ux_initial",
            "Uy_initial",
            "Uz_initial",
        ),
        "solver.linear.u.final_residual": ("Ux_final", "Uy_final", "Uz_final"),
        "solver.linear.u.iterations": ("Ux_iters", "Uy_iters", "Uz_iters"),
    }
    for key, columns in vector_columns.items():
        components = [row.get(column, "") for column in columns]
        values[key] = str(components) if all(components) else ""

    columns = {
        "solver.linear.u.converged": "U_converged",
        "solver.linear.p.initial_residual": "p_initial",
        "solver.linear.p.final_residual": "p_final",
        "solver.linear.p.iterations": "p_iters",
        "solver.linear.p.converged": "p_converged",
    }
    for key, column in columns.items():
        raw = row.get(column, "")
        values[key] = _bool_string(raw) if column.endswith("converged") else raw

    continuity = read_table(
        case_dir / "postProcessing/continuityErrorMetrics/0/continuityError.dat"
    ).last()
    values["solver.continuity.final.local"] = continuity.get("Local", "")
    values["solver.continuity.final.global"] = continuity.get("Global", "")
    values["solver.continuity.cumulative"] = continuity.get("Cumulative", "")


def _fields(case_dir: Path, values: dict[str, str]) -> None:
    velocity = read_table(
        case_dir / "postProcessing/velocityRangeMetrics/0/fieldMinMax.dat"
    ).last()
    values["result.field.u_magnitude.final.min_m_per_sec"] = velocity.get(
        "min(mag(U))", ""
    )
    values["result.field.u_magnitude.final.max_m_per_sec"] = velocity.get(
        "max(mag(U))", ""
    )

    scalar = read_table(
        case_dir / "postProcessing/scalarRangeMetrics/0/fieldMinMax.dat"
    ).last()
    scalar_columns = {
        "result.field.kinematic_pressure.final.min_m2_per_sec2": "min(p)",
        "result.field.kinematic_pressure.final.max_m2_per_sec2": "max(p)",
        "result.field.k.final.min_m2_per_sec2": "min(k)",
        "result.field.k.final.max_m2_per_sec2": "max(k)",
        "result.field.omega.final.min_per_sec": "min(omega)",
        "result.field.omega.final.max_per_sec": "max(omega)",
    }
    for key, column in scalar_columns.items():
        values[key] = scalar.get(column, "")

    for boundary in ("inlet", "outlet"):
        row = read_table(
            case_dir / f"postProcessing/{boundary}FluxMetrics/0/surfaceFieldValue.dat"
        ).last()
        values[f"result.flux.{boundary}.final_m3_per_sec"] = row.get("sum(phi)", "")

    probe_names = ("wake_near", "wake_upper", "wake_far")
    u_row = read_table(case_dir / "postProcessing/wakeProbeMetrics/0/U").last()
    p_row = read_table(case_dir / "postProcessing/wakeProbeMetrics/0/p").last()
    for index, probe in enumerate(probe_names):
        raw_velocity = u_row.get(str(index), "")
        velocity = vector(raw_velocity)
        if velocity:
            values[f"result.probe.{probe}.u.final_m_per_sec"] = str(velocity)
        values[f"result.probe.{probe}.kinematic_pressure.final_m2_per_sec2"] = (
            p_row.get(str(index), "")
        )


def _bool_string(value: str) -> str:
    if value == "1":
        return "true"
    if value == "0":
        return "false"
    return ""
