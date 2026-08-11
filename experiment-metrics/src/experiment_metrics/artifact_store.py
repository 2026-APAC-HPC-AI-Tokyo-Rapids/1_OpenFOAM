from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .fact import canonical_json
from .manifest import SHA256, RunManifest
from .registry import Registry

_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "registry/openfoam-v2.toml"
_REGISTRY = Registry.load(_REGISTRY_PATH)
if _REGISTRY.artifact_roles is None:  # pragma: no cover - import-time invariant
    raise RuntimeError("default registry has no artifact role contract")
ROLE_FILENAMES = {
    role: _REGISTRY.artifact_roles.filename(role)
    for role in ("run_bundle", "profile_raw")
}
ARTIFACT_MANIFEST_FILENAME = _REGISTRY.artifact_roles.filename("artifact_manifest")
RUN_BUNDLE_SOURCE_ROLES = frozenset(_REGISTRY.artifact_roles.run_bundle_source_roles)
_RUN_MEMBER_ROOTS = frozenset(
    {"control", "source", "domain", "logs", "result", "results"}
)


@dataclass(frozen=True, slots=True)
class Member:
    path: str
    size_bytes: int
    sha256: str
    role: str

    @classmethod
    def from_file(cls, run_dir: Path, relative: str, role: str) -> Member:
        path = _member_path(run_dir, relative)
        _validate_role(role)
        return cls(relative, path.stat().st_size, _sha256(path), role)

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class ArtifactSet:
    manifest_path: Path
    files: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class ValidatedArtifactSet:
    manifest: RunManifest
    artifact_manifest_path: Path
    files: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class ArchivedMember:
    path: str
    size_bytes: int
    sha256: str
    role: str | None
    content: bytes


@dataclass(frozen=True, slots=True)
class ArtifactMembers:
    run_bundle: tuple[ArchivedMember, ...]
    profile_raw: tuple[ArchivedMember, ...]

    def run(self, path: str, *, role: str | None = None) -> ArchivedMember:
        return _unique_archived_member(self.run_bundle, path, role)

    def profile(self, path: str) -> ArchivedMember:
        return _unique_archived_member(self.profile_raw, path, None)

    def run_by_role(self, role: str) -> tuple[ArchivedMember, ...]:
        return tuple(member for member in self.run_bundle if member.role == role)


class RunPackager:
    """Create and verify the closed v2 artifact set for one persisted run."""

    def package(
        self,
        manifest_path: Path,
        *,
        run_members: tuple[tuple[str, str], ...],
        profile_members: tuple[str, ...] = (),
    ) -> ArtifactSet:
        manifest = _load_bound_manifest(manifest_path)
        run_dir = manifest.path.parents[1]
        members = _run_members(run_dir, run_members)
        profile_paths: tuple[str, ...] = ()
        if manifest.purpose == "profile":
            profile_paths = _profile_members(run_dir, profile_members)
        elif profile_members:
            raise ValueError("bench runs cannot contain profile raw members")

        staging = run_dir / "archive-staging"
        staging.mkdir(exist_ok=True)
        bundle_manifest = staging / "bundle.manifest.json"
        bundle_document = {
            "schema_version": "bundle-manifest/v1",
            "subject_kind": "regular_run",
            "run_id": manifest.run_id,
            "members": [member.as_json() for member in members],
        }
        _atomic_text(bundle_manifest, canonical_json(bundle_document) + "\n")

        run_bundle = run_dir / ROLE_FILENAMES["run_bundle"]
        _tar_zstd(
            run_dir,
            tuple(member.path for member in members),
            bundle_manifest,
            run_bundle,
        )
        _validate_run_bundle(run_bundle, manifest.run_id)

        outputs: list[tuple[str, Path]] = [
            ("run_bundle", run_bundle),
        ]
        if manifest.purpose == "profile":
            profile_archive = run_dir / ROLE_FILENAMES["profile_raw"]
            _tar_zstd(run_dir, profile_paths, None, profile_archive)
            _validate_archive_members(profile_archive, profile_paths)
            outputs.append(("profile_raw", profile_archive))

        artifact_manifest = run_dir / ARTIFACT_MANIFEST_FILENAME
        if artifact_manifest.exists():
            raise FileExistsError(artifact_manifest)
        artifact_document = {
            "schema_version": "artifact-manifest/v1",
            "logical_artifact_name": manifest.run_id,
            "files": [
                {
                    "role": role,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for role, path in outputs
            ],
        }
        _atomic_text(artifact_manifest, canonical_json(artifact_document) + "\n")
        validated = validate_artifact_set(manifest.path, artifact_manifest)
        return ArtifactSet(validated.artifact_manifest_path, validated.files)


def validate_artifact_set(
    manifest_path: Path, artifact_manifest_path: Path
) -> ValidatedArtifactSet:
    """Validate a local/GitHub artifact set before any external publication."""

    manifest = _load_bound_manifest(manifest_path)
    run_dir = manifest.path.parents[1]
    expected_artifact_manifest = run_dir / ARTIFACT_MANIFEST_FILENAME
    artifact_manifest = _regular_file(artifact_manifest_path)
    if artifact_manifest != expected_artifact_manifest:
        raise ValueError("artifact manifest must have its fixed run-root filename")
    document = _load_json_strict(artifact_manifest.read_bytes(), "artifact manifest")
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "logical_artifact_name",
        "files",
    }:
        raise ValueError("artifact manifest must be a closed v1 object")
    if document["schema_version"] != "artifact-manifest/v1":
        raise ValueError("unsupported artifact manifest schema")
    if document["logical_artifact_name"] != manifest.run_id:
        raise ValueError("artifact manifest belongs to a different run")

    expected_roles = _expected_roles(manifest.purpose)
    rows = document["files"]
    if not isinstance(rows, list) or len(rows) != len(expected_roles):
        raise ValueError("artifact manifest has the wrong purpose-specific file set")
    files: list[Path] = []
    for role, row in zip(expected_roles, rows, strict=True):
        if not isinstance(row, dict) or set(row) != {"role", "size_bytes", "sha256"}:
            raise ValueError("artifact file entry must be a closed object")
        if row["role"] != role:
            raise ValueError("artifact files are not in the required role order")
        size = row["size_bytes"]
        digest = row["sha256"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("artifact file size must be an unsigned integer")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError("artifact file hash must be a lowercase SHA-256")
        path = _regular_file(run_dir / ROLE_FILENAMES[role])
        if path.parent != run_dir:
            raise ValueError("artifact file is outside the run root")
        if path.stat().st_size != size or _sha256(path) != digest:
            raise ValueError(f"artifact file identity mismatch: {role}")
        files.append(path)

    _validate_run_bundle(files[0], manifest.run_id)
    return ValidatedArtifactSet(
        manifest=manifest,
        artifact_manifest_path=artifact_manifest,
        files=tuple(files),
    )


def read_artifact_members(artifact_set: ValidatedArtifactSet) -> ArtifactMembers:
    """Read the already validated archives without extracting mutable files.

    The run bundle's own manifest supplies per-member roles and identities.  A
    profile archive is sealed by the outer artifact manifest, so member hashes
    are computed over the bytes from that validated archive.
    """

    run_archive = artifact_set.files[0]
    document = _load_json_strict(
        _read_archive_member(run_archive, "bundle.manifest.json"),
        "bundle manifest",
    )
    if not isinstance(document, dict) or not isinstance(document.get("members"), list):
        raise ValueError("validated run bundle has no member index")
    run_members: list[ArchivedMember] = []
    for row in document["members"]:
        if not isinstance(row, dict):  # pragma: no cover - validation invariant
            raise ValueError("validated run bundle member is invalid")
        content = _read_archive_member(run_archive, row["path"])
        run_members.append(
            ArchivedMember(
                row["path"],
                row["size_bytes"],
                row["sha256"],
                row["role"],
                content,
            )
        )
    profile_members: list[ArchivedMember] = []
    if artifact_set.manifest.purpose == "profile":
        profile_archive = artifact_set.files[1]
        for relative in _archive_members(profile_archive):
            _validate_relative_path(relative)
            content = _read_archive_member(profile_archive, relative)
            profile_members.append(
                ArchivedMember(
                    relative,
                    len(content),
                    hashlib.sha256(content).hexdigest(),
                    None,
                    content,
                )
            )
    return ArtifactMembers(tuple(run_members), tuple(profile_members))


def _unique_archived_member(
    members: tuple[ArchivedMember, ...], path: str, role: str | None
) -> ArchivedMember:
    _validate_relative_path(path)
    matches = [
        member
        for member in members
        if member.path == path and (role is None or member.role == role)
    ]
    if len(matches) != 1:
        qualifier = "" if role is None else f" with role {role}"
        raise ValueError(f"artifact requires exactly one {path}{qualifier}")
    return matches[0]


def _run_members(
    run_dir: Path, supplied: tuple[tuple[str, str], ...]
) -> tuple[Member, ...]:
    declared = list(supplied)
    manifest_entries = [
        item for item in declared if item[0] == "control/run-manifest.json"
    ]
    if not manifest_entries:
        declared.append(("control/run-manifest.json", "run_manifest"))
    elif manifest_entries != [("control/run-manifest.json", "run_manifest")]:
        raise ValueError("run bundle has an invalid run_manifest declaration")
    if len({relative for relative, _ in declared}) != len(declared):
        raise ValueError("run bundle members must be path-unique")
    members = tuple(
        sorted(
            (Member.from_file(run_dir, relative, role) for relative, role in declared),
            key=lambda item: item.path.encode(),
        )
    )
    for member in members:
        root = PurePosixPath(member.path).parts[0]
        if root not in _RUN_MEMBER_ROOTS or member.path.startswith("profile/raw/"):
            raise ValueError(
                f"run bundle member is outside its closed roots: {member.path}"
            )
    return members


def _profile_members(run_dir: Path, supplied: tuple[str, ...]) -> tuple[str, ...]:
    if not supplied:
        raise ValueError("profile runs require profile raw members")
    if len(set(supplied)) != len(supplied):
        raise ValueError("profile raw members must be path-unique")
    ordered = tuple(sorted(supplied, key=lambda item: item.encode()))
    for relative in ordered:
        if not relative.startswith("profile/raw/"):
            raise ValueError("profile raw member is outside profile/raw")
        _member_path(run_dir, relative)
    return ordered


def _load_bound_manifest(path: Path) -> RunManifest:
    resolved = _regular_file(path)
    document = _load_json_strict(resolved.read_bytes(), "run manifest")
    if not isinstance(document, dict):
        raise ValueError("run manifest must be a JSON object")
    manifest = RunManifest.load(resolved)
    expected = manifest.path.parents[1] / "control/run-manifest.json"
    if manifest.path != expected:
        raise ValueError("manifest must have its fixed run-root path")
    return manifest


def _expected_roles(purpose: str) -> tuple[str, ...]:
    if purpose == "bench":
        return ("run_bundle",)
    if purpose == "profile":
        return ("run_bundle", "profile_raw")
    raise ValueError(f"unsupported run purpose: {purpose}")


def _validate_run_bundle(path: Path, run_id: str) -> None:
    names = _archive_members(path)
    if not names or names[-1] != "bundle.manifest.json":
        raise ValueError("run bundle must end with bundle.manifest.json")
    if len(names) != len(set(names)):
        raise ValueError("run bundle contains duplicate member paths")
    document = _load_json_strict(
        _read_archive_member(path, "bundle.manifest.json"), "bundle manifest"
    )
    if not isinstance(document, dict) or set(document) != {
        "schema_version",
        "subject_kind",
        "run_id",
        "members",
    }:
        raise ValueError("bundle manifest must be a closed v1 object")
    if (
        document["schema_version"] != "bundle-manifest/v1"
        or document["subject_kind"] != "regular_run"
        or document["run_id"] != run_id
    ):
        raise ValueError("run bundle manifest identity mismatch")
    members = document["members"]
    if not isinstance(members, list) or len(members) != len(names) - 1:
        raise ValueError("run bundle member set differs from its manifest")
    expected_names: list[str] = []
    for row in members:
        if not isinstance(row, dict) or set(row) != {
            "path",
            "size_bytes",
            "sha256",
            "role",
        }:
            raise ValueError("bundle member entry must be a closed object")
        relative, size, digest, role = (
            row["path"],
            row["size_bytes"],
            row["sha256"],
            row["role"],
        )
        if not isinstance(relative, str):
            raise ValueError("bundle member path must be a string")
        _validate_relative_path(relative)
        _validate_role(role)
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("bundle member size must be an unsigned integer")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError("bundle member hash must be a lowercase SHA-256")
        payload = _read_archive_member(path, relative)
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise ValueError(f"run bundle member identity mismatch: {relative}")
        expected_names.append(relative)
    if expected_names != sorted(expected_names, key=lambda item: item.encode()):
        raise ValueError("bundle manifest members are not in path byte order")
    if names[:-1] != expected_names:
        raise ValueError("run bundle archive order differs from its manifest")


def _validate_archive_members(path: Path, expected: tuple[str, ...]) -> None:
    if _archive_members(path) != list(expected):
        raise ValueError("archive members differ from the closed expected set")


def _archive_members(path: Path) -> list[str]:
    result = subprocess.run(
        ["tar", "-I", "zstd", "-tf", path],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.splitlines()


def _read_archive_member(path: Path, relative: str) -> bytes:
    result = subprocess.run(
        ["tar", "-I", "zstd", "-xOf", path, "--", relative],
        check=True,
        capture_output=True,
    )
    return result.stdout


def _member_path(root: Path, relative: str) -> Path:
    _validate_relative_path(relative)
    root = root.resolve()
    lexical = root / Path(*PurePosixPath(relative).parts)
    if any(path.is_symlink() for path in (lexical, *lexical.parents) if path != root):
        raise ValueError(f"artifact member cannot traverse a symlink: {relative!r}")
    path = lexical.resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"artifact member escapes run root: {relative!r}")
    return path


def _validate_relative_path(relative: str) -> None:
    posix = PurePosixPath(relative)
    if (
        not relative
        or posix.is_absolute()
        or ".." in posix.parts
        or any(not part or part in {".", ".."} for part in posix.parts)
        or str(posix) != relative
        or any(ord(character) < 32 or ord(character) == 127 for character in relative)
    ):
        raise ValueError(f"unsafe artifact member path: {relative!r}")


def _validate_role(role: object) -> None:
    if (
        not isinstance(role, str)
        or not role
        or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789_"
            for character in role
        )
    ):
        raise ValueError("artifact member role must be a lowercase registry token")
    if role not in RUN_BUNDLE_SOURCE_ROLES:
        raise ValueError(f"artifact member role is absent from the registry: {role}")


def _regular_file(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"artifact boundary rejects symlink: {path}")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"artifact boundary requires a regular file: {path}")
    return resolved


def _tar_zstd(
    root: Path,
    members: tuple[str, ...],
    bundle_manifest: Path | None,
    output: Path,
) -> None:
    if output.exists():
        raise FileExistsError(output)
    with tempfile.NamedTemporaryFile(
        dir=output.parent, prefix=f".{output.name}.", delete=False
    ) as stream:
        temporary = Path(stream.name)
    temporary.unlink()
    argv = ["tar", "-I", "zstd", "-cf", str(temporary), "-C", str(root)]
    if bundle_manifest is not None:
        argv.extend(["--transform", "s|^archive-staging/||"])
    argv.extend(["--", *members])
    if bundle_manifest is not None:
        argv.append("archive-staging/bundle.manifest.json")
    try:
        subprocess.run(argv, check=True)
        os.replace(temporary, output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json_strict(data: bytes, label: str) -> Any:
    def closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} has duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(data, object_pairs_hook=closed_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid {label}") from error


def _atomic_text(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        stream.write(text)
        temporary = Path(stream.name)
    os.replace(temporary, path)
