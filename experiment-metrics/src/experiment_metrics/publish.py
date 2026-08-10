from __future__ import annotations

import hashlib
import json
import os
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .artifact_store import MetricRow, validate_artifact_set

GOOGLE_CREDENTIALS_ENV = "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON"
BIGQUERY_INSERT_SCOPE = "https://www.googleapis.com/auth/bigquery.insertdata"


@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    project: str
    dataset: str
    table: str
    location: str

    @classmethod
    def load(cls, pyproject: Path) -> BigQueryConfig:
        with pyproject.open("rb") as stream:
            document = tomllib.load(stream)
        section = document["tool"]["experiment-metrics"]["bigquery"]
        values = tuple(
            section[name] for name in ("project", "dataset", "table", "location")
        )
        if not all(isinstance(value, str) and value for value in values):
            raise ValueError("BigQuery configuration values must be non-empty strings")
        return cls(*values)


@dataclass(frozen=True, slots=True)
class RawRow:
    run: str
    key: str
    value: str

    @classmethod
    def from_metric(cls, row: MetricRow) -> RawRow:
        return cls(row.run, row.key, row.value)

    def insert_row(self) -> dict[str, object]:
        identity = b"\0".join(
            (self.run.encode(), self.key.encode(), self.value.encode())
        )
        return {
            "insertId": hashlib.sha256(identity).hexdigest(),
            "json": {"run": self.run, "key": self.key, "value": self.value},
        }


def publish_artifact_set(
    manifest_path: Path,
    artifact_manifest_path: Path,
    config: BigQueryConfig,
    *,
    request: Callable[[urllib.request.Request], bytes] | None = None,
) -> int:
    """Validate and publish one immutable artifact set from the runner boundary."""

    artifact_set = validate_artifact_set(manifest_path, artifact_manifest_path)
    rows = tuple(RawRow.from_metric(row) for row in artifact_set.metrics_rows)
    token = None if request is not None else _access_token()
    endpoint = (
        "https://bigquery.googleapis.com/bigquery/v2/projects/"
        f"{urllib.parse.quote(config.project, safe='')}/datasets/"
        f"{urllib.parse.quote(config.dataset, safe='')}/tables/"
        f"{urllib.parse.quote(config.table, safe='')}/insertAll"
    )
    sender = request or _urlopen
    published = 0
    for chunk in _chunks(rows, 500):
        body = json.dumps(
            {
                "skipInvalidRows": False,
                "ignoreUnknownValues": False,
                "rows": [row.insert_row() for row in chunk],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        response = sender(
            urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        )
        payload = json.loads(response or b"{}")
        if payload.get("insertErrors"):
            raise RuntimeError(
                "BigQuery rejected rows: "
                + json.dumps(payload["insertErrors"], ensure_ascii=False)
            )
        published += len(chunk)
    return published


def publish_metrics(
    manifest_path: Path,
    artifact_manifest_path: Path,
    config: BigQueryConfig,
    *,
    request: Callable[[urllib.request.Request], bytes] | None = None,
) -> int:
    """Compatibility name for the artifact-set-only publication boundary."""

    return publish_artifact_set(
        manifest_path, artifact_manifest_path, config, request=request
    )


def _access_token() -> str:
    # Credential and HTTP-client imports remain confined to the runner-only path.
    import google.auth
    import google.auth.transport.requests
    from google.oauth2 import service_account

    raw = os.environ.pop(GOOGLE_CREDENTIALS_ENV, None)
    if raw is not None:
        info = json.loads(raw)
        if not isinstance(info, dict):
            raise ValueError("Google credentials JSON must be an object")
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=[BIGQUERY_INSERT_SCOPE]
        )
    else:
        credentials, _ = google.auth.default(scopes=[BIGQUERY_INSERT_SCOPE])
    credentials.refresh(google.auth.transport.requests.Request())
    if not credentials.token:
        raise RuntimeError("Google credentials returned no access token")
    return credentials.token


def _urlopen(request: urllib.request.Request) -> bytes:
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _chunks(rows: Iterable[RawRow], size: int) -> Iterator[tuple[RawRow, ...]]:
    chunk: list[RawRow] = []
    for row in rows:
        chunk.append(row)
        if len(chunk) == size:
            yield tuple(chunk)
            chunk.clear()
    if chunk:
        yield tuple(chunk)
