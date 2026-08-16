from __future__ import annotations

import json
import os
import stat
import tomllib
import urllib.parse
import urllib.request
import warnings
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from .manifest import RunManifest

BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery.insertdata"
CONFIG_ENV = "EXPERIMENT_METRICS_BIGQUERY_CONFIG"
CREDENTIALS_FILE_ENV = "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE"


@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    project: str
    dataset: str
    table: str
    location: str

    @classmethod
    def load(cls, pyproject: Path) -> BigQueryConfig:
        with pyproject.open("rb") as stream:
            section = tomllib.load(stream)["tool"]["experiment-metrics"]["bigquery"]
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
    def from_mapping(cls, row: Mapping[str, object]) -> RawRow:
        if set(row) != {"run", "key", "value"}:
            raise ValueError("raw row must contain only run, key, value")
        values = tuple(row[name] for name in ("run", "key", "value"))
        if not all(isinstance(value, str) for value in values):
            raise TypeError("raw row fields must be strings")
        run, key, value = values
        if not run or not key:
            raise ValueError("raw row run and key must be non-empty")
        return cls(run, key, value)

    def insert_row(self) -> dict[str, object]:
        # Deliberately omit insertId: duplicates are valid observations.
        return {"json": {"run": self.run, "key": self.key, "value": self.value}}


def send_raw(
    run_id: str,
    rows: Iterable[RawRow | Mapping[str, object]],
    *,
    config: BigQueryConfig | None = None,
    credentials_file: Path | None = None,
    request: Callable[[urllib.request.Request], bytes] | None = None,
) -> bool:
    """Append producer rows once; transport failures never fail the workload."""

    try:
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be a non-empty string")
        normalized = tuple(
            row if isinstance(row, RawRow) else RawRow.from_mapping(row) for row in rows
        )
        if any(row.run != run_id for row in normalized):
            raise ValueError("raw row belongs to a different run")
        if not normalized:
            return True
        config = config or BigQueryConfig.load(Path(os.environ[CONFIG_ENV]))
        token = (
            None
            if request is not None
            else _access_token(
                credentials_file or Path(os.environ[CREDENTIALS_FILE_ENV])
            )
        )
        sender = request or _urlopen
        endpoint = (
            "https://bigquery.googleapis.com/bigquery/v2/projects/"
            f"{urllib.parse.quote(config.project, safe='')}/datasets/"
            f"{urllib.parse.quote(config.dataset, safe='')}/tables/"
            f"{urllib.parse.quote(config.table, safe='')}/insertAll"
        )
        for chunk in _chunks(normalized, 500):
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
            payload = json.loads(
                sender(
                    urllib.request.Request(
                        endpoint, data=body, headers=headers, method="POST"
                    )
                )
                or b"{}"
            )
            if payload.get("insertErrors"):
                raise RuntimeError(
                    "BigQuery rejected rows: "
                    + json.dumps(payload["insertErrors"], ensure_ascii=False)
                )
        return True
    except Exception as error:
        warnings.warn(
            f"experiment metrics BigQuery append failed: {error}", RuntimeWarning
        )
        return False


def send_fragments(
    manifest_path: Path,
    runtime_dir: Path,
    *,
    config: BigQueryConfig | None = None,
    credentials_file: Path | None = None,
    request: Callable[[urllib.request.Request], bytes] | None = None,
) -> bool:
    """Send every closed fragment once from a network-capable runner."""

    manifest = RunManifest.load(manifest_path)
    root = runtime_dir.resolve(strict=True)
    if manifest.path.parents[1] != root:
        raise ValueError("fragment runtime does not own the run manifest")
    fragments = sorted(
        (root / "domain/fragments").glob("*.jsonl"), key=lambda path: path.name.encode()
    )
    if not fragments:
        raise ValueError("run has no closed metric fragments")
    rows: list[RawRow] = []
    for fragment in fragments:
        for line in fragment.read_text(encoding="utf-8").splitlines():
            rows.append(RawRow.from_mapping(json.loads(line)))
    return send_raw(
        manifest.run_id,
        rows,
        config=config,
        credentials_file=credentials_file,
        request=request,
    )


def _access_token(credentials_file: Path) -> str:
    path = credentials_file.resolve(strict=True)
    if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ValueError("Google credentials file must be a regular mode-0600 file")
    import google.auth.transport.requests
    from google.oauth2 import service_account

    info = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(info, dict):
        raise ValueError("Google credentials JSON must be an object")
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=[BIGQUERY_SCOPE]
    )
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
