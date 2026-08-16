from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics import Fact, Recorder, RunManifest, init_run, manifest_facts


def test_init_persists_closed_manifest_and_manifest_fragment(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(
        None, tmp_path, identities, purpose="bench", registry_path=registry_path
    )
    manifest = json.loads(manifest_path.read_text())

    assert set(manifest) == {
        "schema_version",
        "subject_kind",
        "run_id",
        "run_purpose",
        "repository_id",
        "source_track",
        "observed_control_plane_sha256",
        "instrumentation_bundle_sha256",
    }
    assert manifest["run_id"].startswith("r-")
    facts = manifest_facts(RunManifest.load(manifest_path))
    assert {fact.key for fact in facts} == {
        "run.identity.run_id",
        "run.identity.run_purpose",
        "run.identity.repository_id",
        "run.instrumentation_bundle_sha256",
        "source.track.head_commit",
    }


def test_recorder_closes_only_by_atomic_rename(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    recorder = Recorder.open(
        manifest_path,
        "arbitrary-producer",
        runtime_dir,
        fragment_id="one",
    )
    recorder.record(Fact("arbitrary.key", False))

    assert not list(
        (runtime_dir / "domain/fragments").glob("arbitrary-producer--one.jsonl")
    )
    assert list((runtime_dir / "domain/fragments").glob("*.tmp"))
    fragment = recorder.close()
    assert fragment.is_file()
    assert not list((runtime_dir / "domain/fragments").glob("*.tmp"))


def test_manifest_rejects_open_identity_or_source_track_shape(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    extra_identity = {**identities, "unexpected": "no"}
    with pytest.raises(ValueError, match="exactly the v2 manifest identity"):
        init_run(None, tmp_path, extra_identity, registry_path=registry_path)

    malformed = {**identities, "source_track": {"head_commit": "b" * 40}}
    with pytest.raises(ValueError, match="source_track must contain exactly"):
        init_run(None, tmp_path, malformed, registry_path=registry_path)


def test_manifest_load_rejects_extra_closed_field(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    document = json.loads(manifest_path.read_text())
    document["unexpected"] = True
    manifest_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="exactly its v1 fields"):
        RunManifest.load(manifest_path)


def test_recorder_allows_unregistered_keys_but_rejects_duplicate_keys(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    with Recorder.open(manifest_path, "arbitrary-producer") as recorder:
        recorder.record(Fact("arbitrary.key", False))
        with pytest.raises(ValueError, match="duplicate"):
            recorder.record(Fact("arbitrary.key", True))
        recorder.record(Fact("unregistered.producer.key", "value"))
