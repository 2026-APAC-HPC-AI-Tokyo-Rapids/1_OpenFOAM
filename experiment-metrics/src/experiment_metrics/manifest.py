from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .fact import canonical_json

RUN_ID = re.compile(r"^r-[a-f0-9]{32}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
PURPOSES = frozenset({"bench", "profile"})
REPOSITORY_ID = "apac2026-openfoam"


@dataclass(frozen=True, slots=True)
class RunManifest:
    path: Path
    run_id: str
    purpose: str
    repository_id: str
    source_track: Mapping[str, object]
    observed_control_plane_sha256: str
    instrumentation_bundle_sha256: str

    @classmethod
    def load(cls, path: Path) -> RunManifest:
        import json

        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("run manifest must be a JSON object")
        expected_fields = {
            "schema_version",
            "subject_kind",
            "run_id",
            "run_purpose",
            "repository_id",
            "source_track",
            "observed_control_plane_sha256",
            "instrumentation_bundle_sha256",
        }
        if set(document) != expected_fields:
            raise ValueError("run manifest must contain exactly its v1 fields")
        if document.get("schema_version") != "run-manifest/v1":
            raise ValueError("unsupported run manifest schema")
        if document.get("subject_kind") != "regular_run":
            raise ValueError("unsupported run manifest subject_kind")
        run_id = document.get("run_id")
        purpose = document.get("run_purpose")
        repository_id = document.get("repository_id")
        source_track = document.get("source_track")
        observed_control_plane_sha256 = document.get("observed_control_plane_sha256")
        instrumentation_bundle_sha256 = document.get("instrumentation_bundle_sha256")
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise ValueError("invalid run ID")
        if purpose not in PURPOSES:
            raise ValueError("run purpose must be bench or profile")
        if repository_id != REPOSITORY_ID:
            raise ValueError("repository_id must be apac2026-openfoam")
        if not isinstance(source_track, dict):
            raise ValueError("source_track must be an object")
        _validate_source_track(source_track, purpose)
        if not isinstance(observed_control_plane_sha256, str) or not SHA256.fullmatch(
            observed_control_plane_sha256
        ):
            raise ValueError("observed_control_plane_sha256 must be a SHA-256")
        if not isinstance(instrumentation_bundle_sha256, str) or not SHA256.fullmatch(
            instrumentation_bundle_sha256
        ):
            raise ValueError("instrumentation_bundle_sha256 must be a SHA-256")
        return cls(
            path.resolve(),
            run_id,
            purpose,
            repository_id,
            source_track,
            observed_control_plane_sha256,
            instrumentation_bundle_sha256,
        )


def init_run(
    settings_path: Path | None,
    runtime_root: Path,
    identities: Mapping[str, object],
    *,
    purpose: str = "bench",
    repository_id: str = REPOSITORY_ID,
    registry_path: Path | None = None,
    instrumentation_bundle_path: Path | None = None,
) -> Path:
    """Create a persisted manifest before any producer starts.

    The supplied identities are the closed v2 manifest identity fields.  The
    optional settings path is a runner input and is intentionally not copied
    into the manifest.
    """

    if purpose not in PURPOSES:
        raise ValueError("purpose must be bench or profile")
    if repository_id != REPOSITORY_ID:
        raise ValueError("repository_id must be apac2026-openfoam")
    _validate_identities(identities, purpose)
    run_id = "r-" + os.urandom(16).hex()
    run_dir = runtime_root.resolve() / "runs" / run_id
    for name in (
        "control",
        "domain",
        "source",
        "logs",
        "profile/raw",
        "archive-staging",
    ):
        (run_dir / name).mkdir(
            parents=True, exist_ok=False if name == "control" else True
        )
    _ = settings_path
    document = {
        "schema_version": "run-manifest/v1",
        "subject_kind": "regular_run",
        "run_id": run_id,
        "run_purpose": purpose,
        "repository_id": repository_id,
        "source_track": identities["source_track"],
        "observed_control_plane_sha256": identities["observed_control_plane_sha256"],
        "instrumentation_bundle_sha256": identities["instrumentation_bundle_sha256"],
    }
    path = run_dir / "control/run-manifest.json"
    if instrumentation_bundle_path is not None:
        from .instrumentation import bundle_identity, install_bundle

        installed_identity = bundle_identity(
            instrumentation_bundle_path,
            purpose=purpose,
            registry_path=registry_path,
        )
        if installed_identity != identities["instrumentation_bundle_sha256"]:
            raise ValueError("instrumentation bundle identity does not match manifest")
        install_bundle(
            instrumentation_bundle_path,
            run_dir / "control/instrumentation-bundle.json",
            purpose=purpose,
            registry_path=registry_path,
        )
    _atomic_write(path, canonical_json(document) + "\n")
    RunManifest.load(path)
    # The persisted manifest is itself an owned required observation.  This
    # keeps finalization from accepting an orphaned directory as a run.
    from .recording import Recorder

    registry = (
        registry_path
        or Path(__file__).resolve().parents[2] / "registry/openfoam-v2.toml"
    )
    with Recorder.open(
        path,
        registry,
        "runner.manifest",
        run_dir,
        fragment_id="initial",
    ) as recorder:
        for fact in manifest_facts(RunManifest.load(path)):
            recorder.record(fact)
    return path


def manifest_facts(manifest: RunManifest) -> tuple[object, ...]:
    """Project the closed manifest fields that are raw fact leaves."""

    from .fact import Fact

    return (
        Fact("run.identity.run_id", manifest.run_id),
        Fact("run.identity.run_purpose", manifest.purpose),
        Fact("run.identity.repository_id", manifest.repository_id),
        Fact(
            "run.instrumentation_bundle_sha256",
            manifest.instrumentation_bundle_sha256,
        ),
    )


def _atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".tmp-", delete=False
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(path)


def _validate_source_track(source_track: Mapping[str, object], purpose: str) -> None:
    expected = {"object_hash_algorithm", "base_role", "base_commit", "head_commit"}
    if set(source_track) != expected:
        raise ValueError("source_track must contain exactly its v1 fields")
    algorithm = source_track["object_hash_algorithm"]
    base_role = source_track["base_role"]
    base_commit = source_track["base_commit"]
    head_commit = source_track["head_commit"]
    width = 40 if algorithm == "sha1" else 64 if algorithm == "sha256" else 0
    expected_role = "score_reference" if purpose == "bench" else "profile_base"
    if base_role != expected_role:
        raise ValueError("source_track base_role does not match run purpose")
    if not all(
        isinstance(value, str)
        and len(value) == width
        and all(character in "0123456789abcdef" for character in value)
        for value in (base_commit, head_commit)
    ):
        raise ValueError("source_track commits do not match the Git object algorithm")


def _validate_identities(identities: Mapping[str, object], purpose: str) -> None:
    expected = {
        "source_track",
        "observed_control_plane_sha256",
        "instrumentation_bundle_sha256",
    }
    if set(identities) != expected:
        raise ValueError(
            "identities must contain exactly the v2 manifest identity fields"
        )
    source_track = identities["source_track"]
    if not isinstance(source_track, Mapping):
        raise ValueError("source_track must be an object")
    _validate_source_track(source_track, purpose)
    for name in (
        "observed_control_plane_sha256",
        "instrumentation_bundle_sha256",
    ):
        value = identities[name]
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            raise ValueError(f"{name} must be a SHA-256")
