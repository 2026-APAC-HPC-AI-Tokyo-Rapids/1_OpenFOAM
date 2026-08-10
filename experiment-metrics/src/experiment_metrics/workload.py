from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath

from .fact import canonical_json
from .manifest import RunManifest

WORKLOAD_MEMBERS = (
    "0/U",
    "0/p",
    "constant/transportProperties",
    "system/blockMeshDict",
    "system/controlDict",
    "system/fvSchemes",
    "system/fvSolution",
)


def capture_workload(
    manifest_path: Path, case_root: Path, output_root: Path
) -> Path:
    """Copy and seal the exact workload-defining case members.

    Member copies are completed before the manifest is atomically published, so
    the manifest is the completion sentinel for this source family.
    """

    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    case = case_root.resolve(strict=True)
    output = output_root.resolve()
    expected_output = (run_dir / "source/workload").resolve()
    if output != expected_output:
        raise ValueError("workload output root is outside the bound run")
    output.mkdir(parents=True, exist_ok=True)

    members: list[dict[str, object]] = []
    for relative in WORKLOAD_MEMBERS:
        member = PurePosixPath(relative)
        source = (case / Path(*member.parts)).resolve(strict=True)
        if not source.is_file() or not source.is_relative_to(case):
            raise ValueError(f"invalid workload member: {relative}")
        raw = source.read_bytes()
        target = output / Path(*member.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_bytes(target, raw)
        members.append(
            {
                "path": relative,
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )

    manifest_path = run_dir / "source/workload-manifest.json"
    _atomic_bytes(
        manifest_path,
        (
            canonical_json(
                {
                    "schema_version": "workload-manifest/v1",
                    "members": members,
                }
            )
            + "\n"
        ).encode("utf-8"),
    )
    return manifest_path


def _atomic_bytes(path: Path, content: bytes) -> None:
    if path.exists():
        raise FileExistsError(path)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)
