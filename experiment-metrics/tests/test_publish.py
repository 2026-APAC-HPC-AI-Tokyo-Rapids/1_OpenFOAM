from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics import init_run
from experiment_metrics.publish import (
    BigQueryConfig,
    _access_token,
    send_fragments,
    send_raw,
)

CONFIG = BigQueryConfig("project", "dataset", "table", "location")


def test_send_raw_validates_chunks_and_allows_duplicates() -> None:
    requests = []
    rows = [{"run": "r", "key": "same", "value": "value"}] * 501
    assert send_raw(
        "r",
        rows,
        config=CONFIG,
        request=lambda request: requests.append(request) or b"{}",
    )
    bodies = [json.loads(request.data) for request in requests]
    assert [len(body["rows"]) for body in bodies] == [500, 1]
    assert set(bodies[0]["rows"][0]) == {"json"}
    assert bodies[0]["rows"][0] == bodies[0]["rows"][1]


@pytest.mark.parametrize(
    "row",
    [
        {"run": "", "key": "key", "value": "value"},
        {"run": "r", "key": "", "value": "value"},
        {"run": "r", "key": "key", "value": 1},
        {"run": "r", "key": "key", "value": "value", "extra": "x"},
    ],
)
def test_send_raw_rejects_invalid_rows_as_warning(row: dict[str, object]) -> None:
    with pytest.warns(RuntimeWarning):
        assert not send_raw("r", [row], config=CONFIG, request=lambda _: b"{}")


def test_send_raw_does_not_retry_or_raise_on_bigquery_error() -> None:
    calls = 0

    def reject(_request: object) -> bytes:
        nonlocal calls
        calls += 1
        return b'{"insertErrors":[{"index":0}]}'

    with pytest.warns(RuntimeWarning):
        assert not send_raw(
            "r", [{"run": "r", "key": "k", "value": "v"}], config=CONFIG, request=reject
        )
    assert calls == 1


def test_send_fragments_sends_closed_run_fragments_once(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    runtime_dir = manifest.parents[1]
    run_id = json.loads(manifest.read_text(encoding="utf-8"))["run_id"]
    extra = runtime_dir / "domain/fragments/stage.runner--extra.jsonl"
    extra.write_text(
        json.dumps({"run": run_id, "key": "extra", "value": "true"}) + "\n",
        encoding="utf-8",
    )
    requests = []

    assert send_fragments(
        manifest,
        runtime_dir,
        config=CONFIG,
        request=lambda request: requests.append(request) or b"{}",
    )
    rows = json.loads(requests[0].data)["rows"]
    assert any(row["json"]["key"] == "extra" for row in rows)


def test_credentials_file_must_be_mode_0600(tmp_path) -> None:
    path = tmp_path / "credential.json"
    path.write_text("{}")
    path.chmod(0o644)
    with pytest.raises(ValueError, match="mode-0600"):
        _access_token(path)
