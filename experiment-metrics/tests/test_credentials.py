import base64
import importlib
import json
import os

from experiment_metrics import credentials


def test_capture_reads_json_and_removes_transport_environment(monkeypatch) -> None:
    module = importlib.reload(credentials)
    raw = json.dumps({"type": "service_account", "project_id": "example"})
    monkeypatch.setenv(module.JSON_ENV, raw)
    monkeypatch.setattr(
        module.service_account.Credentials,
        "from_service_account_info",
        lambda info, scopes: (info, scopes),
    )

    module.capture_from_environment()
    loaded, project = module.load(["scope"])

    assert loaded[0]["project_id"] == "example"
    assert loaded[1] == ["scope"]
    assert project == "example"
    assert module.JSON_ENV not in os.environ


def test_capture_decodes_pjm_base64_and_removes_transport_environment(
    monkeypatch,
) -> None:
    module = importlib.reload(credentials)
    raw = json.dumps({"type": "service_account", "project_id": "example"})
    encoded = base64.b64encode(raw.encode()).decode()
    monkeypatch.setenv(module.BASE64_ENV, encoded)
    monkeypatch.setattr(
        module.service_account.Credentials,
        "from_service_account_info",
        lambda info, scopes: (info, scopes),
    )

    module.capture_from_environment()
    loaded, project = module.load(["scope"])

    assert loaded[0]["project_id"] == "example"
    assert project == "example"
    assert module.BASE64_ENV not in os.environ
