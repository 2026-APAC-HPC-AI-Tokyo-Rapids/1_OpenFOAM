from __future__ import annotations

import os
import sys
import time

from ..context import Context
from ..model import Metric
from ..readers.check_mesh import LABELS, execute, parse
from ..readers.files import manifest_sha256

POLYMESH_BASENAMES = {
    "boundary",
    "cellZones",
    "faceZones",
    "faces",
    "neighbour",
    "owner",
    "pointZones",
    "points",
}


def collect(context: Context) -> list[Metric]:
    relative_files = []
    for processor in context.case_dir.glob("processor*"):
        suffix = processor.name.removeprefix("processor")
        if not processor.is_dir() or not suffix.isdigit():
            continue
        poly_mesh = processor / "constant/polyMesh"
        relative_files.extend(
            path.relative_to(context.case_dir)
            for path in poly_mesh.iterdir()
            if path.name in POLYMESH_BASENAMES and path.is_file()
        )

    result = [
        Metric(
            "mesh.partitioned.sha256",
            manifest_sha256(context.case_dir, relative_files),
        )
    ]
    started = time.monotonic_ns()
    command = execute(
        context.case_dir,
        os.environ.get("OPENFOAM_MPI_PROCS", "1"),
        os.environ.get("DECOMPOSE_PAR_DICT", "system/decomposeParDict.6"),
    )
    elapsed = (time.monotonic_ns() - started) / 1_000_000_000
    if command.stdout:
        print(command.stdout, end="")
    if command.stderr:
        print(command.stderr, file=sys.stderr, end="")
    parsed = parse(command.stdout)
    result.extend(
        Metric(key, parsed.get(key, "")) for key in [*LABELS, "mesh.quality.valid"]
    )
    result.extend(
        [
            Metric("perf.stage.check_mesh.wall_time_sec", repr(elapsed)),
            Metric("run.stage.check_mesh.exit_code", str(command.returncode)),
        ]
    )
    return result
