from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

import experiment_metrics.provision as provision_module
from experiment_metrics import init_run
from experiment_metrics.build_provenance import (
    EXECUTABLE_ROLES,
    PARTITION_SOURCE_PATHS,
    TOOLCHAIN_ROLES,
)
from experiment_metrics.fact import canonical_json
from experiment_metrics.provision import BASE_ROLES, validate_provision


def _identity(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def test_intel_mpi_ldd_fixture_selects_only_libmpi_as_identity() -> None:
    root = "/home/app/inteloneapi/2025.1.3/mpi/2021.15/lib/release"
    paths = provision_module._ldd_paths(
        f"""
        libmpi.so.12 => {root}/libmpi.so.12 (0x00007f00)
        libmpifort.so.12 => {root}/libmpifort.so.12 (0x00007e00)
        """
    )

    assert [path.name for path in paths] == ["libmpi.so.12", "libmpifort.so.12"]
    assert [
        path.name for path in paths if provision_module._is_canonical_libmpi(path)
    ] == ["libmpi.so.12"]
    assert provision_module._is_mpi_companion(paths[1])


def _sidecar(path: Path, executables: dict[str, Path]) -> Path:
    empty_sha = hashlib.sha256(b"").hexdigest()
    document = {
        "schema_version": "build-sidecar/v1",
        "source_commits": [
            {
                "repository_id": repository,
                "commit_role": role,
                "object_hash_algorithm": "sha1",
                "oid": token * 40,
            }
            for repository, role, token in (
                ("apac2026-openfoam", "build_definition", "a"),
                ("openfoam-source", "openfoam_source", "b"),
                ("openfoam-thirdparty-source", "thirdparty_source", "c"),
            )
        ],
        "toolchain_commands": [
            {
                "role": role,
                "argv": ["/bin/true", "--version"],
                "stdout": {
                    "path": f"control/build-raw/{role}.stdout",
                    "size_bytes": 0,
                    "sha256": empty_sha,
                },
                "stderr": {
                    "path": f"control/build-raw/{role}.stderr",
                    "size_bytes": 0,
                    "sha256": empty_sha,
                },
                "outcome": {"kind": "exit", "code": 0},
            }
            for role in TOOLCHAIN_ROLES
        ],
        "compile_flags": ["WM_PRECISION_OPTION=DP"],
        "precision": "DP",
        "label_bits": 64,
        "build_archive": {
            "path": "build.tar.zst",
            "size_bytes": 1,
            "sha256": hashlib.sha256(b"x").hexdigest(),
        },
        "runtime_objects": sorted(
            [
                {
                    "kind": "executable",
                    "role": role,
                    "path": f"bin/{role}",
                    **_identity(executables[role]),
                }
                for role in EXECUTABLE_ROLES
            ],
            key=lambda item: item["path"].encode(),
        ),
        "partition_audit_source": {
            "source_commit_role": "build_definition",
            "repository_paths": list(PARTITION_SOURCE_PATHS),
            "git_blob_oids": ["e" * 40] * 3,
        },
    }
    path.write_text(canonical_json(document) + "\n")
    return path


def test_provision_validation_binds_resolved_executables_and_ldd_sources(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    bin_dir = provision / "bin"
    bin_dir.mkdir(parents=True)
    build_executables = {}
    for role in EXECUTABLE_ROLES:
        target = bin_dir / role
        shutil.copy2("/bin/true", target)
        build_executables[role] = target
    sidecar = _sidecar(run_dir / "control/build-sidecar.json", build_executables)
    role_paths = {role: build_executables[role] for role in EXECUTABLE_ROLES}
    role_paths["mpirun"] = Path("/bin/true")
    libmpi = tmp_path / "libmpi.so.12"
    libmpi.write_bytes(b"fixture mpi")
    libmpifort = tmp_path / "libmpifort.so.12"
    libmpifort.write_bytes(b"fixture mpifort")
    monkeypatch.setattr(
        provision_module, "_ldd_paths", lambda _text: (libmpi, libmpifort)
    )

    output = validate_provision(
        manifest_path=manifest,
        build_sidecar_path=sidecar,
        provision_root=provision,
        output=run_dir / "control/build-provision-validation.json",
        executable_paths=role_paths,
    )
    document = json.loads(output.read_text())
    assert [item["role"] for item in document["executables"]] == list(BASE_ROLES)
    assert [item["role"] for item in document["ldd_raw"]] == list(EXECUTABLE_ROLES[:-1])
    assert document["resolved_libmpi"]["path"] == str(libmpi)


def test_provision_validation_rejects_changed_build_executable(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    bin_dir = provision / "bin"
    bin_dir.mkdir(parents=True)
    executables = {}
    for role in EXECUTABLE_ROLES:
        target = bin_dir / role
        shutil.copy2("/bin/true", target)
        executables[role] = target
    sidecar = _sidecar(run_dir / "control/build-sidecar.json", executables)
    executables["simpleFoam"].write_bytes(b"changed")
    role_paths = {role: executables[role] for role in EXECUTABLE_ROLES}
    role_paths["mpirun"] = Path("/bin/true")
    libmpi = tmp_path / "libmpi.so.12"
    libmpi.write_bytes(b"fixture mpi")
    monkeypatch.setattr(provision_module, "_ldd_paths", lambda _text: (libmpi,))

    with pytest.raises(ValueError, match="differs from build sidecar"):
        validate_provision(
            manifest_path=manifest,
            build_sidecar_path=sidecar,
            provision_root=provision,
            output=run_dir / "control/build-provision-validation.json",
            executable_paths=role_paths,
        )


def test_profile_provision_records_vtune_identity_and_version(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(
        None,
        tmp_path,
        profile_identities,
        purpose="profile",
        registry_path=registry_path,
    )
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    bin_dir = provision / "bin"
    bin_dir.mkdir(parents=True)
    executables = {}
    for role in EXECUTABLE_ROLES:
        target = bin_dir / role
        shutil.copy2("/bin/true", target)
        executables[role] = target
    sidecar = _sidecar(run_dir / "control/build-sidecar.json", executables)
    role_paths = {role: executables[role] for role in EXECUTABLE_ROLES}
    role_paths["mpirun"] = Path("/bin/true")
    role_paths["vtune"] = Path("/bin/true")
    libmpi = tmp_path / "libmpi.so.12"
    libmpi.write_bytes(b"fixture mpi")
    monkeypatch.setattr(provision_module, "_ldd_paths", lambda _text: (libmpi,))

    output = validate_provision(
        manifest_path=manifest,
        build_sidecar_path=sidecar,
        provision_root=provision,
        output=run_dir / "control/build-provision-validation.json",
        executable_paths=role_paths,
    )

    document = json.loads(output.read_text())
    assert [item["role"] for item in document["executables"]][-1] == "vtune"
    assert document["profiler_version"]["argv"] == [
        str(Path("/bin/true").resolve()),
        "--version",
    ]
    assert document["profiler_version"]["stdout"]["path"].endswith(
        "vtune-version.stdout"
    )


def test_profile_provision_records_craypat_identity_and_version(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    manifest = init_run(
        None,
        tmp_path,
        profile_identities,
        purpose="profile",
        registry_path=registry_path,
    )
    run_dir = manifest.parents[1]
    provision = tmp_path / "provision"
    bin_dir = provision / "bin"
    bin_dir.mkdir(parents=True)
    executables = {}
    for role in EXECUTABLE_ROLES:
        target = bin_dir / role
        shutil.copy2("/bin/true", target)
        executables[role] = target
    sidecar = _sidecar(run_dir / "control/build-sidecar.json", executables)
    role_paths = {role: executables[role] for role in EXECUTABLE_ROLES}
    role_paths["mpirun"] = Path("/bin/true")
    role_paths["craypat"] = Path("/bin/true")
    libmpi = tmp_path / "libmpi.so.12"
    libmpi.write_bytes(b"fixture mpi")
    monkeypatch.setattr(provision_module, "_ldd_paths", lambda _text: (libmpi,))

    output = validate_provision(
        manifest_path=manifest,
        build_sidecar_path=sidecar,
        provision_root=provision,
        output=run_dir / "control/build-provision-validation.json",
        executable_paths=role_paths,
    )

    document = json.loads(output.read_text())
    assert [item["role"] for item in document["executables"]][-1] == "craypat"
    assert document["profiler_version"]["argv"] == [
        str(Path("/bin/true").resolve()),
        "-V",
    ]
    assert document["profiler_version"]["stdout"]["path"].endswith(
        "craypat-version.stdout"
    )
