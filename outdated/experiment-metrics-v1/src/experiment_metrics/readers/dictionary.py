from __future__ import annotations

from pathlib import Path

from ..command import run


def read_entry(case_dir: Path, path: str, entry: str) -> str:
    result = run(
        ["foamDictionary", "-entry", entry, "-value", path],
        cwd=case_dir,
    )
    if result.returncode != 0:
        return ""
    lines = result.stdout.strip().splitlines()
    return lines[0].strip() if lines else ""


def vector_components(value: str) -> list[str]:
    text = value.strip()
    if text.startswith("(") and text.endswith(")"):
        parts = text[1:-1].split()
        if len(parts) == 3:
            return parts
    return ["", "", ""]
