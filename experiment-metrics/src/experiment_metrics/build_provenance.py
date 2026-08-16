from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import deque
from pathlib import Path, PurePosixPath

from .fact import Fact, canonical_json
from .manifest import SHA256, RunManifest

EXECUTABLE_ROLES = (
    "icoFoam",
    "blockMesh",
    "decomposePar",
    "checkMesh",
    "mesh-facts",
    "partition-audit",
    "capture-hardware",
)
ELF_ROLES = EXECUTABLE_ROLES[:-1]
TOOLCHAIN_ROLES = (
    "compiler_c_version",
    "compiler_cxx_version",
    "mpirun_version",
    "icofoam_dynamic",
)
PARTITION_SOURCE_PATHS = (
    "experiment-metrics/native/partition-audit/Make/files",
    "experiment-metrics/native/partition-audit/Make/options",
    "experiment-metrics/native/partition-audit/partition-audit.C",
)
def capture_build_state(
    *,
    output: Path,
    build_tree: Path,
    build_definition_repo: Path,
    openfoam_oid: str,
    openfoam_algorithm: str,
    thirdparty_oid: str,
    thirdparty_algorithm: str,
    executable_paths: dict[str, Path],
    compile_flags: list[str],
    compiler_c: Path,
    compiler_cxx: Path,
    mpi_launcher: Path,
    precision: str,
    label_bits: int,
) -> Path:
    root = build_tree.resolve(strict=True)
    definition = build_definition_repo.resolve(strict=True)
    if set(executable_paths) != set(EXECUTABLE_ROLES):
        raise ValueError("build state requires the task executable roles")
    if _git(definition, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("build provenance requires a clean definition checkout")
    definition_algorithm = _git(definition, "rev-parse", "--show-object-format")
    definition_oid = _git(definition, "rev-parse", "HEAD")
    if not _git(
        definition,
        "for-each-ref",
        "--format=%(refname)",
        "--contains",
        definition_oid,
        "refs/remotes/origin",
    ):
        raise ValueError("build definition is not reachable from origin")
    source_commits = [
        _commit(
            "build_definition",
            "apac2026-openfoam",
            definition_algorithm,
            definition_oid,
        ),
        _commit("openfoam_source", "openfoam-source", openfoam_algorithm, openfoam_oid),
        _commit(
            "thirdparty_source",
            "openfoam-thirdparty-source",
            thirdparty_algorithm,
            thirdparty_oid,
        ),
    ]

    resolved = {
        role: _inside(root, path.resolve(strict=True))
        for role, path in executable_paths.items()
    }
    raw_root = root / "control/build-raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    compiler_c = compiler_c.resolve(strict=True)
    compiler_cxx = compiler_cxx.resolve(strict=True)
    launcher = mpi_launcher.resolve(strict=True)
    if not all(os.access(path, os.X_OK) for path in (compiler_c, compiler_cxx, launcher)) or precision not in {"SP", "DP"} or label_bits not in {32, 64}:
        raise ValueError("build toolchain selection is invalid")
    readelf = _which("readelf")
    commands = (
        ("compiler_c_version", [str(compiler_c), "--version"]),
        ("compiler_cxx_version", [str(compiler_cxx), "--version"]),
        ("mpirun_version", [str(launcher), "--version"]),
        ("icofoam_dynamic", [str(readelf), "--dynamic", str(resolved["icoFoam"])]),
    )
    observations = [
        _capture_command(role, argv, raw_root, root) for role, argv in commands
    ]
    if any(item["outcome"] != {"kind": "exit", "code": 0} for item in observations):
        raise ValueError("toolchain observation command failed")

    runtime_objects = [
        _runtime_executable(role, resolved[role], root) for role in EXECUTABLE_ROLES
    ]
    runtime_objects.extend(
        _shared_library_closure(tuple(resolved[r] for r in ELF_ROLES), root, readelf)
    )
    runtime_objects.sort(key=lambda item: str(item["path"]).encode())
    if len({item["path"] for item in runtime_objects}) != len(runtime_objects):
        raise ValueError("runtime object paths are not unique")

    state = {
        "schema_version": "build-state/v1",
        "source_commits": source_commits,
        "toolchain_commands": observations,
        "compile_flags": compile_flags,
        "precision": precision,
        "label_bits": label_bits,
        "runtime_objects": runtime_objects,
        "partition_audit_source": {
            "source_commit_role": "build_definition",
            "repository_paths": list(PARTITION_SOURCE_PATHS),
            "git_blob_oids": [
                _git(definition, "rev-parse", f"HEAD:{path}")
                for path in PARTITION_SOURCE_PATHS
            ],
        },
    }
    _atomic_json(output, state)
    return output


def finalize_build_sidecar(state_path: Path, archive: Path, output: Path) -> Path:
    state = _json(state_path)
    if not isinstance(state, dict) or state.get("schema_version") != "build-state/v1":
        raise ValueError("build state has an invalid schema")
    archive = archive.resolve(strict=True)
    document = {
        "schema_version": "build-sidecar/v1",
        "source_commits": state["source_commits"],
        "toolchain_commands": state["toolchain_commands"],
        "compile_flags": state["compile_flags"],
        "precision": state["precision"],
        "label_bits": state["label_bits"],
        "build_archive": {
            "path": "build.tar.zst",
            "size_bytes": archive.stat().st_size,
            "sha256": _sha256(archive),
        },
        "runtime_objects": state["runtime_objects"],
        "partition_audit_source": state["partition_audit_source"],
    }
    validate_build_sidecar(document)
    _atomic_json(output, document)
    return output


def verify_build_pair(sidecar: Path, archive: Path) -> dict[str, object]:
    document = _json(sidecar)
    validate_build_sidecar(document)
    member = document["build_archive"]
    assert isinstance(member, dict)
    archive = archive.resolve(strict=True)
    if (
        archive.stat().st_size != member["size_bytes"]
        or _sha256(archive) != member["sha256"]
    ):
        raise ValueError("build archive does not match its sidecar")
    return document


def build_artifact_facts(
    manifest_path: Path, build_sidecar_path: Path
) -> tuple[Fact, Fact]:
    """Expose the complete validated build provenance without a projection table."""

    manifest = RunManifest.load(manifest_path)
    expected = manifest.path.parents[1] / "control/build-sidecar.json"
    if build_sidecar_path.is_symlink() or build_sidecar_path.resolve(strict=True) != (
        expected.resolve(strict=True)
    ):
        raise ValueError("build artifact index source is outside the bound run")
    content = build_sidecar_path.read_bytes()
    document = json.loads(content)
    validate_build_sidecar(document)
    run_dir = manifest_path.parents[1]
    observations: list[dict[str, object]] = []
    for command in document["toolchain_commands"]:
        observations.append(
            {
                "role": command["role"],
                "argv": command["argv"],
                "outcome": command["outcome"],
                "stdout": _expanded_member(command["stdout"], run_dir),
                "stderr": _expanded_member(command["stderr"], run_dir),
            }
        )
    provenance = {
        **document,
        "toolchain_commands": observations,
    }
    return (
        Fact("artifact.build_manifest_sha256", hashlib.sha256(content).hexdigest()),
        Fact("build.provenance", provenance),
    )


def build_artifact_index_fact(manifest_path: Path, build_sidecar_path: Path) -> Fact:
    """Compatibility helper for callers that only need the sidecar identity."""

    return build_artifact_facts(manifest_path, build_sidecar_path)[0]


def _expanded_member(value: object, root: Path) -> dict[str, object]:
    _validate_member(value)
    assert isinstance(value, dict)
    path = (root / str(value["path"])).resolve(strict=True)
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("build raw member is outside the bound run")
    raw = path.read_bytes()
    if (
        len(raw) != value["size_bytes"]
        or hashlib.sha256(raw).hexdigest() != value["sha256"]
    ):
        raise ValueError("build raw member differs from its sidecar")
    return {**value, "content_b64": base64.b64encode(raw).decode("ascii")}


def validate_build_sidecar(document: object) -> None:
    fields = {
        "schema_version",
        "source_commits",
        "toolchain_commands",
        "compile_flags",
        "precision",
        "label_bits",
        "build_archive",
        "runtime_objects",
        "partition_audit_source",
    }
    if (
        not isinstance(document, dict)
        or set(document) != fields
        or document["schema_version"] != "build-sidecar/v1"
        or document["precision"] not in {"SP", "DP"}
        or document["label_bits"] not in {32, 64}
    ):
        raise ValueError("build sidecar is not a closed v1 object")
    commits = document["source_commits"]
    commands = document["toolchain_commands"]
    objects = document["runtime_objects"]
    if (
        not isinstance(commits, list)
        or not all(isinstance(item, dict) for item in commits)
        or [item.get("commit_role") for item in commits]
        != [
            "build_definition",
            "openfoam_source",
            "thirdparty_source",
        ]
    ):
        raise ValueError("build source commit roles are incomplete")
    for item in commits:
        _validate_commit(item)
    if [item["repository_id"] for item in commits] != [
        "apac2026-openfoam",
        "openfoam-source",
        "openfoam-thirdparty-source",
    ]:
        raise ValueError("build source repository identities are invalid")
    if (
        not isinstance(commands, list)
        or not all(isinstance(item, dict) for item in commands)
        or tuple(item.get("role") for item in commands) != TOOLCHAIN_ROLES
    ):
        raise ValueError("build toolchain observations are incomplete")
    for item in commands:
        _validate_command(item)
    if not isinstance(document["compile_flags"], list) or not all(
        isinstance(item, str) for item in document["compile_flags"]
    ):
        raise ValueError("build compile flags must be strings")
    _validate_member(document["build_archive"])
    if not isinstance(objects, list):
        raise ValueError("build runtime objects must be an array")
    if not all(isinstance(item, dict) for item in objects):
        raise ValueError("build runtime object is invalid")
    executable_roles = [
        item.get("role") for item in objects if item.get("kind") == "executable"
    ]
    if len(executable_roles) != len(EXECUTABLE_ROLES) or set(executable_roles) != set(
        EXECUTABLE_ROLES
    ):
        raise ValueError("build runtime executable roles are incomplete")
    paths: list[str] = []
    for item in objects:
        if not isinstance(item, dict) or item.get("kind") not in {
            "executable",
            "shared_library",
        }:
            raise ValueError("build runtime object is invalid")
        expected = {"kind", "role", "path", "size_bytes", "sha256"}
        if item["kind"] == "shared_library":
            expected = {"kind", "path", "soname", "size_bytes", "sha256"}
        if set(item) != expected:
            raise ValueError("build runtime object is not closed")
        if item["kind"] == "executable" and item["role"] not in EXECUTABLE_ROLES:
            raise ValueError("build runtime executable role is invalid")
        if item["kind"] == "shared_library" and (
            not isinstance(item["soname"], str) or not item["soname"]
        ):
            raise ValueError("build shared-library SONAME is invalid")
        _relative(str(item["path"]))
        _size_hash(item)
        paths.append(str(item["path"]))
    if paths != sorted(set(paths), key=str.encode):
        raise ValueError("build runtime objects must be path-sorted and unique")
    _validate_sources(document, commits[0]["object_hash_algorithm"])


def _shared_library_closure(
    roots: tuple[Path, ...], build_tree: Path, readelf: Path
) -> list[dict[str, object]]:
    pending: deque[Path] = deque(roots)
    visited: set[Path] = set()
    libraries: set[Path] = set()
    while pending:
        binary = pending.popleft().resolve(strict=True)
        if binary in visited:
            continue
        visited.add(binary)
        completed = subprocess.run(
            ["ldd", str(binary)], check=True, capture_output=True, text=True
        )
        for line in completed.stdout.splitlines():
            match = re.search(r"=>\s+(/\S+)\s+\(", line)
            if match is None:
                match = re.match(r"\s*(/\S+)\s+\(", line)
            if match is None:
                if "not found" in line:
                    raise ValueError(f"unresolved runtime dependency: {line.strip()}")
                continue
            path = Path(match.group(1)).resolve(strict=True)
            if path.is_relative_to(build_tree) and path not in libraries:
                libraries.add(path)
                pending.append(path)
    return [_runtime_library(path, build_tree, readelf) for path in libraries]


def _capture_command(
    role: str, argv: list[str], raw_root: Path, root: Path
) -> dict[str, object]:
    completed = subprocess.run(argv, check=False, capture_output=True)
    stdout = raw_root / f"{role}.stdout"
    stderr = raw_root / f"{role}.stderr"
    stdout.write_bytes(completed.stdout)
    stderr.write_bytes(completed.stderr)
    return {
        "role": role,
        "argv": argv,
        "stdout": _member(stdout, root),
        "stderr": _member(stderr, root),
        "outcome": {"kind": "exit", "code": completed.returncode},
    }


def _runtime_executable(role: str, path: Path, root: Path) -> dict[str, object]:
    value = {
        "kind": "executable",
        "role": role,
        "path": path.relative_to(root).as_posix(),
    }
    value.update(_size_hash_value(path))
    return value


def _runtime_library(path: Path, root: Path, readelf: Path) -> dict[str, object]:
    completed = subprocess.run(
        [str(readelf), "--dynamic", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"\(SONAME\).*\[([^]]+)\]", completed.stdout)
    value = {
        "kind": "shared_library",
        "path": path.relative_to(root).as_posix(),
        "soname": match.group(1) if match else path.name,
    }
    value.update(_size_hash_value(path))
    return value


def _commit(role: str, repository: str, algorithm: str, oid: str) -> dict[str, str]:
    item = {
        "repository_id": repository,
        "commit_role": role,
        "object_hash_algorithm": algorithm,
        "oid": oid,
    }
    _validate_commit(item)
    return item


def _validate_commit(item: object) -> None:
    if not isinstance(item, dict) or set(item) != {
        "repository_id",
        "commit_role",
        "object_hash_algorithm",
        "oid",
    }:
        raise ValueError("source commit is not closed")
    width = (
        40
        if item["object_hash_algorithm"] == "sha1"
        else 64
        if item["object_hash_algorithm"] == "sha256"
        else 0
    )
    if not isinstance(item["oid"], str) or not re.fullmatch(
        rf"[a-f0-9]{{{width}}}", item["oid"]
    ):
        raise ValueError("source commit OID does not match its algorithm")
    if (
        item["commit_role"]
        not in {
            "build_definition",
            "openfoam_source",
            "thirdparty_source",
        }
        or not isinstance(item["repository_id"], str)
        or not item["repository_id"]
    ):
        raise ValueError("source commit identity is invalid")


def _validate_command(item: object) -> None:
    if not isinstance(item, dict) or set(item) != {
        "role",
        "argv",
        "stdout",
        "stderr",
        "outcome",
    }:
        raise ValueError("toolchain command is not closed")
    if (
        not isinstance(item["argv"], list)
        or not item["argv"]
        or not all(isinstance(arg, str) and arg for arg in item["argv"])
    ):
        raise ValueError("toolchain argv is invalid")
    _validate_member(item["stdout"])
    _validate_member(item["stderr"])
    if item["outcome"] != {"kind": "exit", "code": 0}:
        raise ValueError("toolchain command was not successful")


def _validate_sources(document: dict[str, object], algorithm: object) -> None:
    partition = document["partition_audit_source"]
    width = 40 if algorithm == "sha1" else 64
    if not isinstance(partition, dict) or set(partition) != {
        "source_commit_role",
        "repository_paths",
        "git_blob_oids",
    }:
        raise ValueError("partition audit source is not closed")
    if partition["source_commit_role"] != "build_definition" or partition[
        "repository_paths"
    ] != list(PARTITION_SOURCE_PATHS):
        raise ValueError("partition audit paths are invalid")
    if (
        not isinstance(partition["git_blob_oids"], list)
        or len(partition["git_blob_oids"]) != len(PARTITION_SOURCE_PATHS)
        or not all(
            re.fullmatch(rf"[a-f0-9]{{{width}}}", str(oid))
            for oid in partition["git_blob_oids"]
        )
    ):
        raise ValueError("partition audit blob OIDs are invalid")


def _member(path: Path, root: Path) -> dict[str, object]:
    value = {"path": path.relative_to(root).as_posix()}
    value.update(_size_hash_value(path))
    return value


def _validate_member(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"path", "size_bytes", "sha256"}:
        raise ValueError("member is not closed")
    _relative(str(value["path"]))
    _size_hash(value)


def _size_hash(value: dict[str, object]) -> None:
    if (
        not isinstance(value["size_bytes"], int)
        or isinstance(value["size_bytes"], bool)
        or value["size_bytes"] < 0
    ):
        raise ValueError("member size is invalid")
    if not isinstance(value["sha256"], str) or not SHA256.fullmatch(value["sha256"]):
        raise ValueError("member SHA-256 is invalid")


def _size_hash_value(path: Path) -> dict[str, object]:
    return {"size_bytes": path.stat().st_size, "sha256": _sha256(path)}


def _inside(root: Path, path: Path) -> Path:
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"runtime object is outside build tree: {path}")
    return path


def _relative(value: str) -> None:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError("member path is not relative-safe")


def _which(name: str) -> Path:
    path = shutil.which(name)
    if path is None:
        raise FileNotFoundError(name)
    return Path(path).resolve(strict=True)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        stream.write(canonical_json(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
