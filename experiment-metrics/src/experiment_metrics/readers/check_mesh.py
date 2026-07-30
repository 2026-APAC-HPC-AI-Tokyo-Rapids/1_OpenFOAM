from __future__ import annotations

from pathlib import Path

from ..command import CommandResult, run

LABELS = {
    "mesh.point_count": "points:",
    "mesh.face_count": "faces:",
    "mesh.cell_count": "cells:",
    "mesh.patch_count": "boundary patches:",
    "mesh.region_count": "Number of regions:",
    "mesh.quality.max_aspect_ratio": "Max aspect ratio =",
    "mesh.quality.max_non_orthogonality_deg": "Mesh non-orthogonality Max:",
    "mesh.quality.max_skewness": "Max skewness =",
    "mesh.quality.min_cell_volume_m3": "Min volume =",
}


def execute(case_dir: Path, mpi_procs: str, dictionary: str) -> CommandResult:
    return run(
        [
            "mpirun",
            "-np",
            mpi_procs,
            "checkMesh",
            "-parallel",
            "-constant",
            "-allTopology",
            "-allGeometry",
            "-decomposeParDict",
            dictionary,
        ],
        cwd=case_dir,
        timeout=None,
    )


def parse(output: str) -> dict[str, str]:
    values = {key: "" for key in LABELS}
    for line in output.splitlines():
        stripped = line.strip()
        for key, label in LABELS.items():
            if not stripped.startswith(label):
                continue
            remainder = stripped[len(label) :].strip()
            values[key] = _first_number(remainder)
    values["mesh.quality.valid"] = (
        "true" if "Mesh OK." in output else "false" if "Failed" in output else ""
    )
    return values


def _first_number(text: str) -> str:
    for token in text.replace("(", " ").replace(")", " ").split():
        candidate = token.rstrip(".,;")
        try:
            float(candidate)
        except ValueError:
            continue
        return candidate
    return ""
