from __future__ import annotations

import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .config import load_bigquery_config
from .credentials import load as load_credentials
from .logging import warning
from .model import Metric

INSERT_SCOPE = "https://www.googleapis.com/auth/bigquery.insertdata"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    data: bytes
    headers: Mapping[str, str]


class UrllibAuthRequest:
    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
        **_: object,
    ) -> HttpResponse:
        request = urllib.request.Request(
            url, data=body, headers=dict(headers or {}), method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return HttpResponse(
                    response.status, response.read(), dict(response.headers)
                )
        except urllib.error.HTTPError as error:
            return HttpResponse(error.code, error.read(), dict(error.headers))


def _insert_id(run: str, metric: Metric) -> str:
    payload = b"\0".join((run.encode(), metric.key.encode(), metric.value.encode()))
    return hashlib.sha256(payload).hexdigest()


def _rows(run: str, batch: Iterable[Metric]) -> list[dict[str, object]]:
    return [
        {
            "insertId": _insert_id(run, metric),
            "json": {"run": run, "key": metric.key, "value": metric.value},
        }
        for metric in batch
    ]


def _chunks(items: list[Metric], size: int = 500) -> Iterable[list[Metric]]:
    for offset in range(0, len(items), size):
        yield items[offset : offset + size]


def _stdout_sink(run: str, batch: list[Metric]) -> bool:
    for metric in batch:
        print(
            json.dumps(
                {"run": run, "key": metric.key, "value": metric.value},
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    return True


def send(run: str, batch: list[Metric]) -> bool:
    if not batch:
        return True
    if os.environ.get("EXPERIMENT_METRICS_SINK") == "stdout":
        return _stdout_sink(run, batch)

    try:
        config = load_bigquery_config()
        credentials, credential_project = load_credentials([INSERT_SCOPE])
        project = config.project or credential_project
        auth_request = UrllibAuthRequest()
        url = (
            "https://bigquery.googleapis.com/bigquery/v2/projects/"
            f"{urllib.parse.quote(project, safe='')}/datasets/"
            f"{urllib.parse.quote(config.dataset, safe='')}/tables/"
            f"{urllib.parse.quote(config.table, safe='')}/insertAll"
        )
        for chunk in _chunks(batch):
            if not _send_chunk(credentials, auth_request, url, run, chunk):
                return False
        return True
    except Exception as error:  # noqa: BLE001 - send errors must not alter the experiment
        warning(f"BigQuery send failed: {error}")
        return False


def _send_chunk(
    credentials: object,
    auth_request: UrllibAuthRequest,
    url: str,
    run: str,
    batch: list[Metric],
) -> bool:
    body = json.dumps(
        {
            "skipInvalidRows": False,
            "ignoreUnknownValues": False,
            "rows": _rows(run, batch),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()

    for attempt in range(4):
        headers = {"Content-Type": "application/json; charset=utf-8"}
        credentials.before_request(auth_request, "POST", url, headers)
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
            response_body = error.read()
        except (OSError, TimeoutError) as error:
            if attempt == 3:
                warning(f"BigQuery request failed: {error}")
                return False
            _backoff(attempt)
            continue

        if status in RETRYABLE_STATUS and attempt < 3:
            _backoff(attempt)
            continue
        if status < 200 or status >= 300:
            warning(
                f"BigQuery returned HTTP {status}: {response_body.decode(errors='replace')}"
            )
            return False

        response_json = json.loads(response_body or b"{}")
        if response_json.get("insertErrors"):
            warning(
                f"BigQuery rejected rows: {json.dumps(response_json['insertErrors'])}"
            )
            return False
        return True
    return False


def _backoff(attempt: int) -> None:
    time.sleep((2**attempt) * random.uniform(0.5, 1.0))
