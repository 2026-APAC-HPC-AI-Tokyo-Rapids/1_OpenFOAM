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

from .artifact_store import MetricRow, read_artifact_members, validate_artifact_set
from .projections import project_artifact_set, resolve_projection_batches
from .protocol import RunProtocol
from .registry import Registry

GOOGLE_CREDENTIALS_ENV = "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON"
BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery"


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
    registry_path: Path | None = None,
    protocol_path: Path | None = None,
    schema_sql_path: Path | None = None,
    request: Callable[[urllib.request.Request], bytes] | None = None,
) -> int:
    """Validate and publish one immutable artifact set from the runner boundary."""

    artifact_set = validate_artifact_set(manifest_path, artifact_manifest_path)
    rows = tuple(RawRow.from_metric(row) for row in artifact_set.metrics_rows)
    projection_batches = ()
    if (registry_path is None) != (protocol_path is None):
        raise ValueError("registry and protocol must be supplied together")
    if registry_path is not None and protocol_path is not None:
        registry = Registry.load(registry_path)
        protocol = RunProtocol.load(protocol_path, artifact_set.manifest.purpose)
        projection_batches = project_artifact_set(
            artifact_set,
            read_artifact_members(artifact_set),
            registry,
            protocol,
        )
        by_projection: dict[str, list[object]] = {}
        for batch in projection_batches:
            by_projection.setdefault(batch.spec.identifier, []).append(batch)
        for identifier, batches in by_projection.items():
            resolution = resolve_projection_batches(tuple(batches))  # type: ignore[arg-type]
            if resolution.conflicts:
                raise ValueError(
                    f"projection {identifier} has local source/grain conflicts"
                )
    token = None if request is not None else _access_token()
    sender = request or _urlopen
    if schema_sql_path is not None:
        _apply_schema(config, schema_sql_path, sender, token)
    published = 0
    for batch in projection_batches:
        insert_rows = tuple(
            {
                "insertId": _projection_insert_id(batch.spec.base_table_id, row),
                "json": row,
            }
            for row in batch.insert_rows()
        )
        # One registry source instance maps to exactly one physical append call.
        _insert_all(
            config,
            batch.spec.base_table_id,
            insert_rows,
            sender,
            token,
        )
        published += len(insert_rows)
    # Publish collection_complete and the rest of the raw Fact table only
    # after every purpose-applicable physical projection append succeeded.
    for chunk in _chunks(rows, 500):
        _insert_all(
            config,
            config.table,
            tuple(row.insert_row() for row in chunk),
            sender,
            token,
        )
        published += len(chunk)
    return published


def publish_metrics(
    manifest_path: Path,
    artifact_manifest_path: Path,
    config: BigQueryConfig,
    *,
    registry_path: Path | None = None,
    protocol_path: Path | None = None,
    schema_sql_path: Path | None = None,
    request: Callable[[urllib.request.Request], bytes] | None = None,
) -> int:
    """Compatibility name for the artifact-set-only publication boundary."""

    return publish_artifact_set(
        manifest_path,
        artifact_manifest_path,
        config,
        registry_path=registry_path,
        protocol_path=protocol_path,
        schema_sql_path=schema_sql_path,
        request=request,
    )


def _apply_schema(
    config: BigQueryConfig,
    schema_sql_path: Path,
    sender: Callable[[urllib.request.Request], bytes],
    token: str | None,
) -> None:
    if schema_sql_path.is_symlink():
        raise ValueError("BigQuery schema SQL must be a regular file")
    path = schema_sql_path.resolve(strict=True)
    if not path.is_file():
        raise ValueError("BigQuery schema SQL must be a regular file")
    query = path.read_text(encoding="utf-8")
    if not query.strip():
        raise ValueError("BigQuery schema SQL is empty")
    endpoint = (
        "https://bigquery.googleapis.com/bigquery/v2/projects/"
        f"{urllib.parse.quote(config.project, safe='')}/queries"
    )
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(
        {
            "query": query,
            "useLegacySql": False,
            "location": config.location,
            "timeoutMs": 200000,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    response = sender(
        urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    )
    payload = _bigquery_payload(response, "schema query")
    for _ in range(20):
        if payload.get("jobComplete") is True:
            return
        reference = payload.get("jobReference")
        if not isinstance(reference, dict) or not isinstance(
            reference.get("jobId"), str
        ):
            raise RuntimeError("BigQuery schema query returned no job reference")
        job_id = urllib.parse.quote(reference["jobId"], safe="")
        poll_endpoint = (
            "https://bigquery.googleapis.com/bigquery/v2/projects/"
            f"{urllib.parse.quote(config.project, safe='')}/queries/{job_id}?"
            + urllib.parse.urlencode(
                {"location": config.location, "timeoutMs": "200000"}
            )
        )
        payload = _bigquery_payload(
            sender(
                urllib.request.Request(poll_endpoint, headers=headers, method="GET")
            ),
            "schema query poll",
        )
    raise RuntimeError("BigQuery schema query did not complete")


def _bigquery_payload(response: bytes, label: str) -> dict[str, object]:
    value = json.loads(response or b"{}")
    if not isinstance(value, dict):
        raise RuntimeError(f"BigQuery {label} response is not an object")
    errors = value.get("errors") or value.get("errorResult")
    if errors:
        raise RuntimeError(
            f"BigQuery {label} failed: " + json.dumps(errors, ensure_ascii=False)
        )
    return value


def _insert_all(
    config: BigQueryConfig,
    table: str,
    rows: tuple[dict[str, object], ...],
    sender: Callable[[urllib.request.Request], bytes],
    token: str | None,
) -> None:
    if not rows:
        raise ValueError("BigQuery source-instance append cannot be empty")
    endpoint = (
        "https://bigquery.googleapis.com/bigquery/v2/projects/"
        f"{urllib.parse.quote(config.project, safe='')}/datasets/"
        f"{urllib.parse.quote(config.dataset, safe='')}/tables/"
        f"{urllib.parse.quote(table, safe='')}/insertAll"
    )
    body = json.dumps(
        {
            "skipInvalidRows": False,
            "ignoreUnknownValues": False,
            "rows": rows,
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


def _projection_insert_id(table: str, row: dict[str, object]) -> str:
    payload = json.dumps(
        row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(table.encode() + b"\0" + payload).hexdigest()


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
            info, scopes=[BIGQUERY_SCOPE]
        )
    else:
        credentials, _ = google.auth.default(scopes=[BIGQUERY_SCOPE])
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
