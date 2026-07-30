from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from .logging import warning


def prepare_case(case_dir: Path) -> None:
    system = case_dir / "system"
    control_dict = system / "controlDict"
    metrics_functions = system / "metricsFunctions"
    try:
        source = (
            files("experiment_metrics.assets").joinpath("metricsFunctions").read_text()
        )
        metrics_functions.write_text(source, encoding="utf-8", newline="\n")
        control = control_dict.read_text(encoding="utf-8")
        includes = (
            '    #include "forceCoeffs"',
            '    #include "solverInfo"',
            '    #include "metricsFunctions"',
        )
        missing = [include for include in includes if include not in control]
        if missing:
            marker = "functions\n{"
            insertion = "\n".join(missing)
            if marker in control:
                control = control.replace(marker, f"{marker}\n{insertion}", 1)
            else:
                control = f"{control.rstrip()}\n\nfunctions\n{{\n{insertion}\n}}\n"
            control_dict.write_text(control, encoding="utf-8", newline="\n")
        _add_block_entries(
            system / "forceCoeffs",
            "forceCoeffs1",
            (
                "    coefficients    (Cd Cl CmPitch);",
                "    writePrecision  17;",
            ),
        )
        _add_block_entries(
            system / "solverInfo",
            "solverInfo1",
            (
                "    writePrecision  17;",
                "    executeControl  timeStep;",
                "    executeInterval 1;",
            ),
        )
    except OSError as error:
        warning(f"case metric function setup failed: {error}")


def _add_block_entries(path: Path, block: str, entries: tuple[str, ...]) -> None:
    content = path.read_text(encoding="utf-8")
    missing = [entry for entry in entries if entry not in content]
    if not missing:
        return
    marker = f"{block}\n{{"
    if marker not in content:
        warning(f"{path.name} block {block} was not found")
        return
    insertion = "\n".join(missing)
    path.write_text(
        content.replace(marker, f"{marker}\n{insertion}", 1),
        encoding="utf-8",
        newline="\n",
    )
