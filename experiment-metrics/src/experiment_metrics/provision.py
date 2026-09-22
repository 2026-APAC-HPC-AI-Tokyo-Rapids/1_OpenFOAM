from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .build_provenance import ELF_ROLES, EXECUTABLE_ROLES, validate_build_sidecar
from .fact import canonical_json
from .manifest import SHA256, RunManifest

BASE_ROLES = (*EXECUTABLE_ROLES, "mpirun")
PROFILE_ROLES = {"craypat": "-V", "vtune": "--version", "uprof": "--version"}


def validate_provision(
    *,
    manifest_path: Path,
    build_sidecar_path: Path,
    provision_root: Path,
    output: Path,
    executable_paths: dict[str, Path],
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    expected_output = run_dir / "control/build-provision-validation.json"
    if output.resolve() != expected_output.resolve():
        raise ValueError("provision validation output is outside the bound run")
    sidecar_bytes = build_sidecar_path.read_bytes()
    sidecar = json.loads(sidecar_bytes)
    validate_build_sidecar(sidecar)
    if manifest.purpose == "profile":
        selected = tuple(role for role in PROFILE_ROLES if role in executable_paths)
        if len(selected) != 1:
            raise ValueError("profile provision requires exactly one supported profiler")
        profile_role = selected[0]
        expected_roles = BASE_ROLES + (profile_role,)
    else:
        profile_role = None
        expected_roles = BASE_ROLES
    if tuple(executable_paths) != expected_roles:
        raise ValueError("provision executable roles are incomplete or unordered")

    build_objects = {
        item["role"]: item
        for item in sidecar["runtime_objects"]
        if item["kind"] == "executable"
    }
    executables: list[dict[str, object]] = []
    resolved: dict[str, Path] = {}
    provision = provision_root.resolve(strict=True)
    for role in expected_roles:
        requested = executable_paths[role]
        real = requested.resolve(strict=True)
        if not real.is_file():
            raise ValueError(f"provision executable is not a file: {role}")
        identity = _identity(real)
        if role in build_objects and (
            identity["size_bytes"] != build_objects[role]["size_bytes"]
            or identity["sha256"] != build_objects[role]["sha256"]
        ):
            raise ValueError(f"provision executable differs from build sidecar: {role}")
        if role in build_objects:
            expected_real = (provision / build_objects[role]["path"]).resolve(
                strict=True
            )
            if real != expected_real:
                raise ValueError(
                    f"provision executable path differs from build sidecar: {role}"
                )
        executables.append(
            {
                "role": role,
                "requested_path": str(requested),
                "resolved_realpath": str(real),
                **identity,
            }
        )
        resolved[role] = real

    source_root = run_dir / "source/build-provision"
    source_root.mkdir(parents=True, exist_ok=True)
    ldd_raw: list[dict[str, object]] = []
    provision_libraries: set[Path] = set()
    mpi_pairs: set[tuple[str, str]] = set()
    mpi_companions: set[Path] = set()
    for role in ELF_ROLES:
        completed = subprocess.run(
            ["ldd", str(resolved[role])], check=False, capture_output=True
        )
        source = source_root / f"ldd-{role}.txt"
        source.write_bytes(completed.stdout + completed.stderr)
        if completed.returncode != 0 or b"not found" in completed.stdout:
            raise ValueError(f"ldd validation failed for {role}")
        ldd_raw.append({"role": role, "source": _member(source, run_dir)})
        for path in _ldd_paths(completed.stdout.decode("utf-8", errors="replace")):
            real = path.resolve(strict=True)
            if real.is_relative_to(provision):
                provision_libraries.add(real)
            if _is_canonical_libmpi(path):
                mpi_pairs.add((str(real), _sha256(real)))
            elif _is_mpi_companion(path):
                mpi_companions.add(real)

    expected_libraries = {
        (provision / item["path"]).resolve(strict=True): item
        for item in sidecar["runtime_objects"]
        if item["kind"] == "shared_library"
    }
    if set(expected_libraries) != provision_libraries:
        raise ValueError("provision shared-library closure differs from build sidecar")
    for path, expected in expected_libraries.items():
        identity = _identity(path)
        if (
            identity["size_bytes"] != expected["size_bytes"]
            or identity["sha256"] != expected["sha256"]
        ):
            raise ValueError(f"provision shared library identity differs: {path}")
    if len(mpi_pairs) != 1:
        raise ValueError("provision must resolve exactly one libmpi identity")
    path, digest = next(iter(mpi_pairs))
    libmpi_parent = Path(path).parent
    if any(item.parent != libmpi_parent for item in mpi_companions):
        raise ValueError("MPI companion libraries resolve outside the libmpi root")
    resolved_libmpi = {"path": path, "sha256": digest}

    launcher_version = _capture_version(
        [str(resolved["mpirun"]), "--version"],
        source_root / "mpirun-version.stdout",
        source_root / "mpirun-version.stderr",
        run_dir,
    )
    profiler_version = None
    if manifest.purpose == "profile":
        assert profile_role is not None
        profiler_version = _capture_version(
            [str(resolved[profile_role]), PROFILE_ROLES[profile_role]],
            source_root / f"{profile_role}-version.stdout",
            source_root / f"{profile_role}-version.stderr",
            run_dir,
        )
    document = {
        "schema_version": "build-provision-validation/v1",
        "build_sidecar_sha256": hashlib.sha256(sidecar_bytes).hexdigest(),
        "run_variant": manifest.purpose,
        "executables": executables,
        "ldd_raw": ldd_raw,
        "launcher_version": launcher_version,
        **({"profiler_version": profiler_version} if profiler_version else {}),
        "resolved_libmpi": resolved_libmpi,
    }
    validate_provision_document(document, purpose=manifest.purpose)
    _atomic_json(output, document)
    return output


def validate_provision_document(document: object, *, purpose: str) -> None:
    required = {
        "schema_version",
        "build_sidecar_sha256",
        "run_variant",
        "executables",
        "ldd_raw",
        "launcher_version",
        "resolved_libmpi",
    }
    if purpose == "profile":
        required.add("profiler_version")
    if (
        not isinstance(document, dict)
        or set(document) != required
        or document.get("schema_version") != "build-provision-validation/v1"
        or document.get("run_variant") != purpose
        or not isinstance(document.get("build_sidecar_sha256"), str)
        or SHA256.fullmatch(document["build_sidecar_sha256"]) is None
    ):
        raise ValueError("build provision validation is not a closed v1 object")
    executables = document["executables"]
    actual_roles = [
        item.get("role") if isinstance(item, dict) else None for item in executables
    ] if isinstance(executables, list) else []
    expected_roles = BASE_ROLES
    if purpose == "profile" and actual_roles:
        profile_role = actual_roles[-1]
        if profile_role not in PROFILE_ROLES:
            raise ValueError("provision profiler role is unsupported")
        expected_roles += (profile_role,)
    if not isinstance(executables, list) or actual_roles != list(expected_roles):
        raise ValueError("provision executable roles are incomplete")
    for item in executables:
        if not isinstance(item, dict) or set(item) != {
            "role",
            "requested_path",
            "resolved_realpath",
            "size_bytes",
            "sha256",
        }:
            raise ValueError("provision executable entry is not closed")
        _validate_identity(item)
        if not all(
            isinstance(item[name], str) and item[name]
            for name in ("requested_path", "resolved_realpath")
        ):
            raise ValueError("provision executable path is invalid")
    ldd_raw = document["ldd_raw"]
    if not isinstance(ldd_raw, list) or [
        item.get("role") if isinstance(item, dict) else None for item in ldd_raw
    ] != list(ELF_ROLES):
        raise ValueError("provision ldd source roles are incomplete")
    for item in ldd_raw:
        if not isinstance(item, dict) or set(item) != {"role", "source"}:
            raise ValueError("provision ldd source is not closed")
        _validate_member(item["source"])
    _validate_version(document["launcher_version"])
    if purpose == "profile":
        _validate_version(document["profiler_version"])
    libmpi = document["resolved_libmpi"]
    if not isinstance(libmpi, dict) or set(libmpi) != {"path", "sha256"}:
        raise ValueError("provision libmpi identity is required")
    if (
        not isinstance(libmpi["path"], str)
        or not libmpi["path"]
        or not isinstance(libmpi["sha256"], str)
        or SHA256.fullmatch(libmpi["sha256"]) is None
    ):
        raise ValueError("provision libmpi identity is invalid")


def _validate_version(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {
        "argv",
        "outcome",
        "stdout",
        "stderr",
    }:
        raise ValueError("provision version observation is not closed")
    if (
        not isinstance(value["argv"], list)
        or len(value["argv"]) != 2
        or value["argv"][1] not in PROFILE_ROLES.values()
        or not isinstance(value["argv"][0], str)
        or not value["argv"][0]
        or value["outcome"] != {"kind": "exit", "code": 0}
    ):
        raise ValueError("provision version observation is invalid")
    _validate_member(value["stdout"])
    _validate_member(value["stderr"])


def _validate_member(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"path", "size_bytes", "sha256"}:
        raise ValueError("provision source member is not closed")
    if not isinstance(value["path"], str) or not value["path"]:
        raise ValueError("provision source member path is invalid")
    _validate_identity(value)


def _validate_identity(value: dict[str, object]) -> None:
    if (
        not isinstance(value["size_bytes"], int)
        or isinstance(value["size_bytes"], bool)
        or value["size_bytes"] < 0
        or not isinstance(value["sha256"], str)
        or SHA256.fullmatch(value["sha256"]) is None
    ):
        raise ValueError("provision member identity is invalid")


def _capture_version(
    argv: list[str], stdout: Path, stderr: Path, run_dir: Path
) -> dict[str, object]:
    completed = subprocess.run(argv, check=False, capture_output=True)
    stdout.write_bytes(completed.stdout)
    stderr.write_bytes(completed.stderr)
    outcome = {"kind": "exit", "code": completed.returncode}
    if completed.returncode != 0:
        raise ValueError(f"version command failed: {argv[0]}")
    return {
        "argv": argv,
        "outcome": outcome,
        "stdout": _member(stdout, run_dir),
        "stderr": _member(stderr, run_dir),
    }


def _ldd_paths(text: str) -> tuple[Path, ...]:
    paths: list[Path] = []
    for line in text.splitlines():
        match = re.search(r"=>\s+(/\S+)\s+\(", line)
        if match is None:
            match = re.match(r"\s*(/\S+)\s+\(", line)
        if match is not None:
            paths.append(Path(match.group(1)))
    return tuple(paths)


def _is_canonical_libmpi(path: Path) -> bool:
    if re.fullmatch(r"libmpi\.so(?:\.[0-9]+)*", path.name) is not None:
        return True
    generic_alias = path.parent / "libmpi.so"
    return generic_alias.exists() and generic_alias.resolve() == path.resolve()


def _is_mpi_companion(path: Path) -> bool:
    return path.name.startswith(("libmpi_", "libmpifort"))


def _member(path: Path, run_dir: Path) -> dict[str, object]:
    return {"path": path.relative_to(run_dir).as_posix(), **_identity(path)}


def _identity(path: Path) -> dict[str, object]:
    return {"size_bytes": path.stat().st_size, "sha256": _sha256(path)}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, document: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".provision-", delete=False
    ) as stream:
        stream.write(canonical_json(document) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)
