#!/usr/bin/env python3
"""Install bounded VTune/Chrome-trace task instrumentation into OpenFOAM."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{path}: expected one instrumentation anchor, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def add_scope(
    path: Path,
    *,
    function_name: str,
    task_kind: str,
    expected_occurrences: int = 1,
    occurrence: int = 0,
) -> None:
    text = path.read_text(encoding="utf-8")
    positions: list[int] = []
    position = text.find(function_name)
    while position >= 0:
        positions.append(position)
        position = text.find(function_name, position + len(function_name))
    if len(positions) != expected_occurrences:
        raise ValueError(
            f"{path}: expected {expected_occurrences} definitions of "
            f"{function_name!r}, found {len(positions)}"
        )
    brace = text.find("\n{\n", positions[occurrence] + len(function_name))
    if brace < 0:
        raise ValueError(f"{path}: opening brace for {function_name!r} not found")
    insertion = brace + len("\n{\n")
    scope = f"    FOAM_VTUNE_TASK_SCOPE(Foam::vtuneTaskKind::{task_kind});\n"
    path.write_text(
        text[:insertion] + scope + text[insertion:],
        encoding="utf-8",
    )


def instrument(source: Path, assets: Path) -> None:
    profiling = source / "src/OpenFOAM/global/profiling"
    for name in ("vtuneTaskTrace.H", "vtuneTaskTrace.C"):
        shutil.copy2(assets / name, profiling / name)

    replace_once(
        source / "src/OpenFOAM/Make/files",
        "global/profiling/profilingPstream.C\n",
        (
            "global/profiling/profilingPstream.C\n"
            "global/profiling/vtuneTaskTrace.C\n"
        ),
    )
    options = source / "src/OpenFOAM/Make/options"
    options.write_text(
        options.read_text(encoding="utf-8")
        + (
            "\n/* Selected OpenFOAM regions exported as Intel ITT tasks. */\n"
            "EXE_INC += -I$(VTUNE_PROFILER_DIR)/include\n"
            "LIB_LIBS += -L$(VTUNE_PROFILER_DIR)/lib64 -littnotify -ldl\n"
        ),
        encoding="utf-8",
    )

    gauss_seidel = source / (
            "src/OpenFOAM/matrices/LduMatrix/Smoothers/GaussSeidel/"
            "GaussSeidelSmoother.C"
        )
    replace_once(
        gauss_seidel,
        '#include "PrecisionAdaptor.H"\n',
        '#include "PrecisionAdaptor.H"\n#include "vtuneTaskTrace.H"\n',
    )
    add_scope(
        gauss_seidel,
        function_name="void Foam::GaussSeidelSmoother::smooth",
        task_kind="gaussSeidelSmooth",
        expected_occurrences=2,
    )
    matrix_path = (
        source / "src/OpenFOAM/matrices/LduMatrix/LduMatrix/lduMatrixATmul.C"
    )
    replace_once(
        matrix_path,
        '#include "lduMatrix.H"\n',
        '#include "lduMatrix.H"\n#include "vtuneTaskTrace.H"\n',
    )
    add_scope(
        matrix_path,
        function_name="void Foam::lduMatrix::Amul",
        task_kind="lduMatrixAmul",
    )
    add_scope(
        matrix_path,
        function_name="void Foam::lduMatrix::residual",
        task_kind="lduMatrixResidual",
    )

    cell_limited = source / (
            "src/finiteVolume/finiteVolume/gradSchemes/limitedGradSchemes/"
            "cellLimitedGrad/cellLimitedGrad.C"
        )
    replace_once(
        cell_limited,
        '#include "cellLimitedGrad.H"\n',
        '#include "cellLimitedGrad.H"\n#include "vtuneTaskTrace.H"\n',
    )
    add_scope(
        cell_limited,
        function_name="void Foam::fv::cellLimitedGrad<Type, Limiter>::calcGrad",
        task_kind="cellLimitedGradCalcGrad",
    )
    gauss_grad = (
        source / "src/finiteVolume/finiteVolume/gradSchemes/gaussGrad/gaussGrad.C"
    )
    replace_once(
        gauss_grad,
        '#include "gaussGrad.H"\n',
        '#include "gaussGrad.H"\n#include "vtuneTaskTrace.H"\n',
    )
    add_scope(
        gauss_grad,
        function_name="Foam::fv::gaussGrad<Type>::gradf",
        task_kind="gaussGradGradf",
    )
    linear_upwind = source / (
            "src/finiteVolume/interpolation/surfaceInterpolation/schemes/"
            "linearUpwind/linearUpwindV.C"
        )
    replace_once(
        linear_upwind,
        '#include "linearUpwindV.H"\n',
        '#include "linearUpwindV.H"\n#include "vtuneTaskTrace.H"\n',
    )
    add_scope(
        linear_upwind,
        function_name="Foam::linearUpwindV<Type>::correction",
        task_kind="linearUpwindVCorrection",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    arguments = parser.parse_args()
    instrument(arguments.source.resolve(), arguments.assets.resolve())


if __name__ == "__main__":
    main()
