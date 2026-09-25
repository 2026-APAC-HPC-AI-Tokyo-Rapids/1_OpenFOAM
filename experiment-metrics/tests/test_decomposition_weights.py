from __future__ import annotations

import struct
import subprocess
from pathlib import Path


SOURCE = Path(__file__).parents[2] / "platforms/aspire2a/write-decomposition-weights.c"


def test_weight_generator_marks_unique_target_owner_cells(tmp_path: Path) -> None:
    binary = tmp_path / "write-decomposition-weights"
    subprocess.run(["cc", "-O2", "-Wall", "-Wextra", "-Werror", "-std=c11", "-o", str(binary), str(SOURCE)], check=True)
    boundary = tmp_path / "boundary"
    boundary.write_text(
        "FoamFile\n{\n format binary;\n}\n3\n(\n"
        " inlet\n {\n type patch;\n nFaces 2;\n startFace 3;\n }\n"
        " Tiresfront\n {\n type wall;\n nFaces 2;\n startFace 5;\n }\n"
        " OCDADetailedUnderbody\n {\n type wall;\n nFaces 1;\n startFace 7;\n }\n)\n"
    )
    owner = tmp_path / "owner"
    owner.write_bytes(
        b'FoamFile\n{\n format binary;\n arch "LSB;label=32;scalar=64";\n'
        b' note "nPoints:8 nCells:4 nFaces:8 nInternalFaces:3";\n}\n8\n('
        + struct.pack("<8I", 0, 0, 1, 0, 1, 2, 2, 2)
        + b"\n)\n"
    )
    output = tmp_path / "costWeight"
    completed = subprocess.run([binary, boundary, owner, output], check=True, capture_output=True, text=True)
    assert "selected_patches=2\n" in completed.stdout
    assert "selected_faces=3\n" in completed.stdout
    assert "selected_cells=1\n" in completed.stdout
    text = output.read_text()
    assert "internalField nonuniform List<scalar>\n4\n(\n1\n1\n3\n1\n)" in text
    assert "object costWeight;" in text
    assert "type calculated;" in text
