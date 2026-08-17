from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .fact import Fact, canonical_json
from .manifest import SHA256, RunManifest
from .recording import Recorder


@dataclass(frozen=True, slots=True)
class WorkloadDefinition:
    workload_id: str
    solver: str
    distribution: str
    release: str
    case_identity: str
    case_members: tuple[str, ...]
    expected_cells: int
    mesh_url: str
    mesh_size_bytes: int
    mesh_md5: str
    mesh_sha256: str
    iteration_by_nodes: dict[int, int]

    def iteration_for(self, nodes: int) -> int:
        try:
            return self.iteration_by_nodes[nodes]
        except KeyError as error:
            raise ValueError(f"unsupported OpenFOAM node count: {nodes}") from error


def load_workload_definition(path: Path) -> WorkloadDefinition:
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document)
        != {
            "schema_version",
            "workload_id",
            "solver",
            "distribution",
            "release",
            "case",
            "mesh",
            "iteration_by_nodes",
        }
        or document["schema_version"] != "openfoam-workload/v1"
        or document["workload_id"] != "occDrivAerStaticMesh-65M"
        or document["solver"] != "simpleFoam"
        or document["distribution"] != "OpenFOAM.com"
        or document["release"] != "v2512"
    ):
        raise ValueError("workload definition is not the selected official task")
    case = document["case"]
    mesh = document["mesh"]
    iterations = document["iteration_by_nodes"]
    if (
        not isinstance(case, dict)
        or set(case) != {"repository", "commit", "path", "identity_sha256", "members"}
        or not isinstance(case["members"], list)
        or not case["members"]
        or len(set(case["members"])) != len(case["members"])
        or case["members"] != sorted(case["members"], key=lambda item: item.encode())
        or not all(_relative_member(item) for item in case["members"])
        or not isinstance(case["identity_sha256"], str)
        or SHA256.fullmatch(case["identity_sha256"]) is None
        or not isinstance(mesh, dict)
        or set(mesh) != {"url", "size_bytes", "md5", "sha256", "cells"}
        or not isinstance(mesh["size_bytes"], int)
        or isinstance(mesh["size_bytes"], bool)
        or mesh["size_bytes"] <= 0
        or not isinstance(mesh["cells"], int)
        or isinstance(mesh["cells"], bool)
        or mesh["cells"] <= 0
        or not isinstance(mesh["md5"], str)
        or len(mesh["md5"]) != 32
        or not isinstance(mesh["sha256"], str)
        or SHA256.fullmatch(mesh["sha256"]) is None
        or not isinstance(iterations, dict)
        or set(iterations) != {"1", "2", "4"}
        or iterations != {"1": 40, "2": 80, "4": 150}
    ):
        raise ValueError("workload definition has invalid provenance or protocol")
    return WorkloadDefinition(
        document["workload_id"],
        document["solver"],
        document["distribution"],
        document["release"],
        case["identity_sha256"],
        tuple(case["members"]),
        mesh["cells"],
        mesh["url"],
        mesh["size_bytes"],
        mesh["md5"],
        mesh["sha256"],
        {int(key): value for key, value in iterations.items()},
    )


def capture_workload(
    manifest_path: Path,
    case_root: Path,
    output_root: Path,
    definition_path: Path,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    definition = load_workload_definition(definition_path)
    run_dir = manifest.path.parents[1]
    case = case_root.resolve(strict=True)
    output = output_root.resolve()
    expected_output = (run_dir / "source/workload").resolve()
    if output != expected_output:
        raise ValueError("workload output root is outside the bound run")
    output.mkdir(parents=True, exist_ok=True)

    members: list[dict[str, object]] = []
    for relative in definition.case_members:
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

    identity = hashlib.sha256(canonical_json(members).encode()).hexdigest()
    if identity != definition.case_identity:
        raise ValueError("case files differ from the pinned workload identity")
    output_manifest = run_dir / "source/workload-manifest.json"
    document = {
        "schema_version": "workload-manifest/v2",
        "workload_id": definition.workload_id,
        "workload_identity": identity,
        "members": members,
    }
    _atomic_bytes(output_manifest, (canonical_json(document) + "\n").encode())
    with Recorder.open(
        manifest.path,
        "runner.workload_manifest",
        run_dir,
        fragment_id="workload",
    ) as recorder:
        recorder.record(Fact("workload.manifest", document))
    return output_manifest


def _relative_member(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


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
