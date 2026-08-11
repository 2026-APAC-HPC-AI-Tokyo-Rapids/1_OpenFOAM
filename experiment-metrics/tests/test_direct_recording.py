from __future__ import annotations

import json
from pathlib import Path

from experiment_metrics.environment import snapshot_bytes
from experiment_metrics.fact import Fact
from experiment_metrics.manifest import init_run
from experiment_metrics.recording import Recorder


def test_atomic_fragment_rows_are_sent_unchanged(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: object,
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=registry_path)
    sent = []
    monkeypatch.setenv("EXPERIMENT_METRICS_DIRECT_SEND", "1")
    monkeypatch.setattr(
        "experiment_metrics.publish.send_raw",
        lambda run, rows: sent.append((run, list(rows))) or True,
    )
    with Recorder.open(
        manifest, registry_path, "arbitrary-producer", manifest.parents[1]
    ) as recorder:
        recorder.record(Fact("arbitrary.key", {"b": 2, "a": 1}))
    persisted = [
        json.loads(line) for line in recorder.fragment_path.read_text().splitlines()
    ]
    assert sent == [(recorder.manifest.run_id, persisted)]


def test_credential_transport_variables_are_not_snapshotted() -> None:
    payload = snapshot_bytes(
        {
            b"SAFE": b"yes",
            b"EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE": b"/secret/path",
            b"EXPERIMENT_METRICS_BIGQUERY_CONFIG": b"/config/path",
            b"EXPERIMENT_METRICS_DIRECT_SEND": b"1",
        }
    )
    assert payload == b"SAFE\0yes\0"
