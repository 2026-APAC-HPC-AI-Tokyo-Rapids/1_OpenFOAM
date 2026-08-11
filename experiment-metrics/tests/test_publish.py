from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

import pytest

from experiment_metrics import RunManifest, init_run
from experiment_metrics.artifact_store import RunPackager, read_metrics
from experiment_metrics.publish import (
    BigQueryConfig,
    _bigquery_projection_row,
    publish_artifact_set,
    publish_metrics,
)


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _artifact_set(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    *,
    row_count: int = 1,
) -> tuple[Path, Path, RunManifest]:
    manifest_path = init_run(
        None,
        tmp_path,
        identities,
        registry_path=registry_path,
    )
    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    rows = [
        {"run": manifest.run_id, "key": f"key.{index:03d}", "value": str(index)}
        for index in range(row_count)
    ]
    _write(run_dir / "metrics.jsonl", rows)
    (run_dir / "logs/solver.log").write_text("complete\n", encoding="utf-8")
    result = RunPackager().package(
        manifest_path,
        run_members=(
            ("control/run-manifest.json", "run_manifest"),
            ("logs/solver.log", "solver_log"),
        ),
    )
    return manifest_path, result.manifest_path, manifest


def test_read_metrics_requires_bound_run_ordered_columns_and_sorted_rows(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metrics.jsonl"
    _write(path, [{"run": "r-1", "key": "a", "value": "0"}])
    assert read_metrics(path, expected_run="r-1")[0].value == "0"

    _write(path, [{"key": "a", "run": "r-1", "value": "0"}])
    with pytest.raises(ValueError, match="ordered run/key/value"):
        read_metrics(path, expected_run="r-1")

    _write(path, [{"run": "r-2", "key": "a", "value": "0"}])
    with pytest.raises(ValueError, match="foreign run"):
        read_metrics(path, expected_run="r-1")

    _write(
        path,
        [
            {"run": "r-1", "key": "b", "value": "0"},
            {"run": "r-1", "key": "a", "value": "0"},
        ],
    )
    with pytest.raises(ValueError, match="key/value byte order"):
        read_metrics(path, expected_run="r-1")


def test_publish_validates_artifact_set_then_chunks_stable_rows(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, artifact_manifest, manifest = _artifact_set(
        tmp_path, registry_path, identities, row_count=501
    )
    requests: list[Request] = []

    def send(request: Request) -> bytes:
        requests.append(request)
        return b"{}"

    count = publish_artifact_set(
        manifest_path,
        artifact_manifest,
        BigQueryConfig("project", "dataset", "table", "asia-northeast1"),
        request=send,
    )

    assert count == 501
    assert len(requests) == 2
    first = json.loads(requests[0].data or b"{}")
    assert len(first["rows"]) == 500
    assert first["rows"][0]["json"]["run"] == manifest.run_id
    assert list(first["rows"][0]["json"]) == ["run", "key", "value"]
    assert len(first["rows"][0]["insertId"]) == 64


def test_publish_compatibility_name_still_requires_whole_artifact_set(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, artifact_manifest, _ = _artifact_set(
        tmp_path, registry_path, identities
    )
    assert (
        publish_metrics(
            manifest_path,
            artifact_manifest,
            BigQueryConfig("project", "dataset", "table", "asia-northeast1"),
            request=lambda _: b"{}",
        )
        == 1
    )


def test_publish_rejects_tampered_artifact_before_any_request(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, artifact_manifest, manifest = _artifact_set(
        tmp_path, registry_path, identities
    )
    run_dir = manifest.path.parents[1]
    with (run_dir / "metrics.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {"run": manifest.run_id, "key": "tampered", "value": "1"},
                separators=(",", ":"),
            )
            + "\n"
        )
    requests: list[Request] = []
    with pytest.raises(ValueError, match="identity mismatch"):
        publish_artifact_set(
            manifest_path,
            artifact_manifest,
            BigQueryConfig("project", "dataset", "table", "asia-northeast1"),
            request=lambda request: requests.append(request) or b"{}",
        )
    assert requests == []


def test_publish_propagates_bigquery_row_rejection(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, artifact_manifest, _ = _artifact_set(
        tmp_path, registry_path, identities
    )
    with pytest.raises(RuntimeError, match="rejected rows"):
        publish_artifact_set(
            manifest_path,
            artifact_manifest,
            BigQueryConfig("project", "dataset", "table", "asia-northeast1"),
            request=lambda _: b'{"insertErrors":[{"index":0}]}',
        )


def test_bigquery_projection_row_encodes_scalar_json_columns() -> None:
    row = {
        "_source_instance_key": '["r-1","source.json"]',
        "compile_flags": {"cxx": ["-O3"], "cc": ["-O2"]},
        "runtime_objects": [{"path": "lib.so", "kind": "shared_library"}],
        "label_bits": 64,
        "resolved_libmpi_path": None,
    }

    encoded = _bigquery_projection_row(row)

    assert encoded == {
        "_source_instance_key": '["r-1","source.json"]',
        "compile_flags": '{"cc":["-O2"],"cxx":["-O3"]}',
        "runtime_objects": '[{"kind":"shared_library","path":"lib.so"}]',
        "label_bits": 64,
        "resolved_libmpi_path": None,
    }


def test_publish_applies_and_waits_for_idempotent_schema_job_before_rows(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path, artifact_manifest, _ = _artifact_set(
        tmp_path, registry_path, identities
    )
    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE IF NOT EXISTS `p.d.t` (x STRING);\n")
    requests: list[Request] = []
    responses = iter(
        (
            b'{"jobComplete":false,"jobReference":{"jobId":"schema-job"}}',
            b'{"jobComplete":true}',
            b"{}",
        )
    )

    def send(request: Request) -> bytes:
        requests.append(request)
        return next(responses)

    count = publish_artifact_set(
        manifest_path,
        artifact_manifest,
        BigQueryConfig("project", "dataset", "table", "asia-northeast1"),
        schema_sql_path=schema,
        request=send,
    )

    assert count == 1
    assert requests[0].method == "POST"
    assert requests[0].full_url.endswith("/projects/project/queries")
    assert json.loads(requests[0].data or b"{}")["useLegacySql"] is False
    assert requests[1].method == "GET"
    assert "/queries/schema-job?" in requests[1].full_url
    assert requests[2].full_url.endswith("/tables/table/insertAll")
