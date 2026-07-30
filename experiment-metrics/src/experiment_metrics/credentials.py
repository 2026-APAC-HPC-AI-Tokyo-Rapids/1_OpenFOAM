from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

import google.auth
from google.oauth2 import service_account

JSON_ENV = "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON"
BASE64_ENV = "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64"


@dataclass(frozen=True, slots=True)
class CapturedCredentials:
    info: dict[str, Any] | None
    error: Exception | None


_captured: CapturedCredentials | None = None


def capture_from_environment() -> None:
    """Move transport credentials out of the metric-visible environment."""
    global _captured
    if _captured is not None:
        return

    raw_json = os.environ.pop(JSON_ENV, None)
    raw_base64 = os.environ.pop(BASE64_ENV, None)
    try:
        if raw_json is None and raw_base64 is not None:
            raw_json = base64.b64decode(raw_base64, validate=True).decode("utf-8")
        if raw_json is None:
            _captured = CapturedCredentials(None, None)
            return
        decoded = json.loads(raw_json)
        if not isinstance(decoded, dict):
            raise TypeError("Google credentials JSON must be an object")
        _captured = CapturedCredentials(decoded, None)
    except Exception as error:  # noqa: BLE001 - report it only when a send is attempted
        _captured = CapturedCredentials(None, error)


def load(scopes: list[str]) -> tuple[object, str | None]:
    capture_from_environment()
    assert _captured is not None
    if _captured.error is not None:
        raise ValueError("invalid Google credentials environment variable") from (
            _captured.error
        )
    if _captured.info is not None:
        credentials = service_account.Credentials.from_service_account_info(
            _captured.info, scopes=scopes
        )
        project = _captured.info.get("project_id")
        return credentials, project if isinstance(project, str) else None
    return google.auth.default(scopes=scopes)
