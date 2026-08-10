from __future__ import annotations

import json
from pathlib import Path

from experiment_metrics import Recorder, init_run, merge_run, run_stage


def test_merge_deduplicates_identical_rows_retains_conflict_and_preserves_fragments(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    protocol = _protocol(tmp_path, "one")
    with Recorder.open(
        manifest_path,
        registry_path,
        "stage.runner",
        runtime_dir,
        fragment_id="stage.one",
    ) as recorder:
        run_stage(
            "one", ["true"], cwd=tmp_path, stderr_mode="separate", recorder=recorder
        )
    fragment = runtime_dir / "domain/fragments/stage.runner--stage.one.jsonl"
    first = json.loads(fragment.read_text().splitlines()[0])
    conflicting = dict(first)
    conflicting["value"] = '{"argv":["changed"],"cwd":"x","stderr_mode":"separate"}'
    fragment.write_text(
        fragment.read_text()
        + json.dumps(first, separators=(",", ":"))
        + "\n"
        + json.dumps(conflicting)
        + "\n",
        encoding="utf-8",
    )

    outcome = merge_run(
        manifest_path, runtime_dir, registry_path=registry_path, protocol_path=protocol
    )
    rows = [json.loads(line) for line in outcome.metrics_path.read_text().splitlines()]

    assert not outcome.collection_complete
    assert outcome.conflicts == ("run.stage.one.launch",)
    assert len([row for row in rows if row["key"] == "run.stage.one.launch"]) == 2
    assert {row["value"] for row in rows if row["key"] == "collection_complete"} == {
        "false"
    }
    assert list((runtime_dir / "domain/fragments").glob("*.jsonl")) == [fragment]


def test_merge_marks_required_stage_producer_missing(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]

    outcome = merge_run(manifest_path, runtime_dir, registry_path=registry_path)

    assert not outcome.collection_complete
    assert outcome.missing_producers == ("stage.runner",)


def test_missing_protocol_is_fail_closed(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    outcome = merge_run(
        manifest_path,
        manifest_path.parents[1],
        registry_path=registry_path,
        protocol_path=tmp_path / "missing-protocol.toml",
    )

    assert not outcome.collection_complete
    assert outcome.protocol_invalid


def test_invalid_fragment_is_preserved_and_its_partial_rows_are_not_adopted(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    fragment = runtime_dir / "domain/fragments/stage.runner--invalid.jsonl"
    fragment.parent.mkdir(parents=True, exist_ok=True)
    launch = {
        "schema_version": "stage-launch/v1",
        "argv": ["true"],
        "cwd": "/tmp",
        "stderr_mode": "separate",
    }
    fragment.write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "run": manifest_path.parents[1].name,
                        "key": "run.stage.solver.launch",
                        "value": json.dumps(launch, separators=(",", ":")),
                    }
                ),
                "not-json",
            )
        )
        + "\n"
    )

    outcome = merge_run(manifest_path, runtime_dir, registry_path=registry_path)
    values = [
        json.loads(line) for line in outcome.metrics_path.read_text().splitlines()
    ]

    assert outcome.invalid_fragments == (fragment.name,)
    assert fragment.exists()
    assert "run.stage.solver.launch" not in {row["key"] for row in values}


def test_stage_fragment_instance_must_match_protocol_stage_axis(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest_path.parents[1]
    protocol = _protocol(tmp_path, "solver")
    with Recorder.open(
        manifest_path,
        registry_path,
        "stage.runner",
        runtime_dir,
        fragment_id="stage.other",
    ) as recorder:
        run_stage(
            "other", ["true"], cwd=tmp_path, stderr_mode="separate", recorder=recorder
        )

    outcome = merge_run(
        manifest_path, runtime_dir, registry_path=registry_path, protocol_path=protocol
    )
    assert outcome.invalid_fragments == ("stage.runner--stage.other.jsonl",)
    assert (runtime_dir / "domain/fragments/stage.runner--stage.other.jsonl").exists()


def _protocol(tmp_path: Path, stage: str) -> Path:
    path = tmp_path / f"{stage}.toml"
    path.write_text(
        f'''[protocol]
schema_version = "openfoam-v2-run-protocol/v1"

[variant.bench]
expected_stages = ["{stage}"]
nodes = 1
ranks = 1
resource_group = "test"
transport_policy = "shm"
workload_id = "test"
expected_workload_identity = "{"a" * 64}"

[variant.profile]
expected_stages = ["{stage}"]
nodes = 1
ranks = 1
resource_group = "test"
transport_policy = "shm"
workload_id = "test"
expected_workload_identity = "{"a" * 64}"
''',
        encoding="utf-8",
    )
    return path
