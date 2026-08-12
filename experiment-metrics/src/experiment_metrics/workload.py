from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath

from .fact import Fact, canonical_json
from .manifest import RunManifest
from .recording import Recorder

WORKLOAD_MEMBERS = (
    "0/U",
    "0/p",
    "constant/transportProperties",
    "system/blockMeshDict",
    "system/controlDict",
    "system/fvSchemes",
    "system/fvSolution",
)

_MEMBER_KEYS = {
    "0/U": "initial_u",
    "0/p": "initial_p",
    "constant/transportProperties": "transport_properties",
    "system/blockMeshDict": "block_mesh_dict",
    "system/controlDict": "control_dict",
    "system/fvSchemes": "fv_schemes",
    "system/fvSolution": "fv_solution",
}


def capture_workload(
    manifest_path: Path,
    case_root: Path,
    output_root: Path,
    *,
    registry_path: Path | None = None,
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
    contents: dict[str, bytes] = {}
    for relative in WORKLOAD_MEMBERS:
        member = PurePosixPath(relative)
        source = (case / Path(*member.parts)).resolve(strict=True)
        if not source.is_file() or not source.is_relative_to(case):
            raise ValueError(f"invalid workload member: {relative}")
        raw = source.read_bytes()
        contents[relative] = raw
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
    identity = hashlib.sha256(canonical_json(members).encode()).hexdigest()
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
    if registry_path is not None:
        with Recorder.open(
            manifest.path,
            registry_path,
            "runner.workload_manifest",
            run_dir,
            fragment_id="workload",
        ) as recorder:
            recorder.record(
                Fact(
                    "workload.manifest",
                    {
                        "schema_version": "workload-manifest-fact/v1",
                        "workload_identity": identity,
                        "members": members,
                    },
                )
            )
            for relative in WORKLOAD_MEMBERS:
                recorder.record(
                    Fact(
                        f"workload.member.{_MEMBER_KEYS[relative]}", contents[relative]
                    )
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
