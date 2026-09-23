from __future__ import annotations

import hashlib
import json
import shutil
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .fact import Fact


def parse_coefficient(path: Path, iterations: int) -> dict[str, object]:
    return parse_coefficient_text(path.read_text(encoding="utf-8"), iterations)


def parse_coefficient_text(text: str, iterations: int) -> dict[str, object]:
    """Read the final Cd observation; the published references are not gates."""
    references = {10: "not_applicable", 40: "~0.43", 80: "~0.34", 150: "~0.28–0.29"}
    if iterations not in references:
        raise ValueError("Cd requires 10, 40, 80, or 150 configured iterations")
    header: list[str] | None = None
    final: tuple[Decimal, Decimal] | None = None
    for line in text.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0].startswith("#"):
            columns = line.lstrip().lstrip("#").split()
            if columns and columns[0] == "Time":
                if header is not None or columns.count("Time") != 1 or columns.count("Cd") != 1:
                    raise ValueError("coefficient.dat has an ambiguous Time/Cd header")
                header = columns
            continue
        if header is None or len(tokens) != len(header):
            raise ValueError("coefficient.dat has no header or a malformed data row")
        try:
            step = Decimal(tokens[header.index("Time")])
            cd = Decimal(tokens[header.index("Cd")])
        except InvalidOperation as error:
            raise ValueError("coefficient.dat has a non-numeric Time/Cd value") from error
        if not step.is_finite() or not cd.is_finite():
            raise ValueError("coefficient.dat has a non-finite Time/Cd value")
        if final is not None and step <= final[0]:
            raise ValueError("coefficient.dat steps are not strictly increasing")
        final = step, cd
    if final is None or final[0] != iterations:
        raise ValueError("coefficient.dat final step differs from configured iterations")
    return {"step": iterations, "cd": format(final[1], "f"), "reference": references[iterations]}


def collect_coefficient(case_root: Path, output_root: Path, iterations: int) -> Path:
    """Persist the master rank's output before its node-local case disappears."""
    candidates = sorted(case_root.glob("postProcessing/forceCoeffsAll/*/coefficient.dat"))
    if len(candidates) != 1:
        raise ValueError(f"expected one forceCoeffsAll/coefficient.dat, found {len(candidates)}")
    source = candidates[0]
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / "coefficient.dat"
    shutil.copyfile(source, target)
    raw = target.read_bytes()
    provenance = {"source_path": str(source), "case_member": source.relative_to(case_root).as_posix(), "source_member": "results/coefficient.dat", "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    (output_root / "coefficient-source.json").write_text(json.dumps(provenance, sort_keys=True) + "\n", encoding="utf-8")
    # Preserve even malformed output for diagnosis, but fail the submission path.
    parse_coefficient(target, iterations)
    return target


def coefficient_fact(path: Path, iterations: int) -> Fact:
    return Fact("result.aero_sanity", {"schema_version": "openfoam-aero-sanity/v1", **parse_coefficient(path, iterations), "source_member": "results/coefficient.dat"})
