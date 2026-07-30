from __future__ import annotations

from ..context import Context
from ..model import Metric
from ..readers.dictionary import read_entry, vector_components
from ..readers.files import manifest_sha256, sha256_file, tree_files

DICTIONARY_SPECS = {
    "case.application": ("system/controlDict", "application"),
    "case.start_time": ("system/controlDict", "startTime"),
    "case.end_time": ("system/controlDict", "endTime"),
    "case.delta_t": ("system/controlDict", "deltaT"),
    "case.write_interval": ("system/controlDict", "writeInterval"),
    "case.write_precision": ("system/controlDict", "writePrecision"),
    "case.initial.kinematic_pressure_m2_per_sec2": (
        "0.orig/include/initialConditions",
        "pressure",
    ),
    "case.initial.turbulent_kinetic_energy_m2_per_sec2": (
        "0.orig/include/initialConditions",
        "turbulentKE",
    ),
    "case.initial.specific_dissipation_rate_per_sec": (
        "0.orig/include/initialConditions",
        "turbulentOmega",
    ),
    "case.transport.model": ("constant/transportProperties", "transportModel"),
    "case.transport.kinematic_viscosity_m2_per_sec": (
        "constant/transportProperties",
        "nu",
    ),
    "case.turbulence.simulation_type": (
        "constant/turbulenceProperties",
        "simulationType",
    ),
    "case.turbulence.ras_model": (
        "constant/turbulenceProperties",
        "RAS/RASModel",
    ),
    "case.force_coefficients.reference_velocity_m_per_sec": (
        "system/forceCoeffs",
        "forceCoeffs1/magUInf",
    ),
    "case.force_coefficients.reference_length_m": (
        "system/forceCoeffs",
        "forceCoeffs1/lRef",
    ),
    "case.force_coefficients.reference_area_m2": (
        "system/forceCoeffs",
        "forceCoeffs1/Aref",
    ),
    "case.force_coefficients.reference_density_kg_per_m3": (
        "system/forceCoeffs",
        "forceCoeffs1/rhoInf",
    ),
}

HASH_SPECS = {
    "case.control_dict.sha256": "system/controlDict",
    "case.fv_schemes.sha256": "system/fvSchemes",
    "case.fv_solution.sha256": "system/fvSolution",
    "case.decompose_par_dict.sha256": "system/decomposeParDict.6",
    "case.force_coefficients.sha256": "system/forceCoeffs",
    "case.solver_info.sha256": "system/solverInfo",
    "case.metrics_functions.sha256": "system/metricsFunctions",
    "case.geometry.motorbike_obj_gz.sha256": "constant/triSurface/motorBike.obj.gz",
}


def collect(context: Context) -> list[Metric]:
    case_dir = context.case_dir
    result = [Metric("case.name", case_dir.name)]
    result.extend(
        Metric(key, read_entry(case_dir, path, entry))
        for key, (path, entry) in DICTIONARY_SPECS.items()
    )

    velocity = vector_components(
        read_entry(case_dir, "0.orig/include/initialConditions", "flowVelocity")
    )
    result.extend(
        Metric(f"case.freestream_velocity_m_per_sec.{index}", value)
        for index, value in enumerate(velocity)
    )
    result.append(
        Metric(
            "case.input_manifest.sha256",
            manifest_sha256(
                case_dir,
                tree_files(case_dir, ["0.orig", "constant", "system"]),
            ),
        )
    )
    result.extend(
        Metric(key, sha256_file(case_dir / path)) for key, path in HASH_SPECS.items()
    )
    return result
