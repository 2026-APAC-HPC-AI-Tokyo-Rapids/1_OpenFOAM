from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_pjm_compute_boundary_is_credential_free_and_uses_exact_stages() -> None:
    script = ROOT / "scripts/run-openfoam.pjm"
    text = script.read_text(encoding="utf-8")

    subprocess.run(["bash", "-n", str(script)], check=True)
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS" not in text
    assert "stage solver" in text
    assert "stage minimal_hardware_capture" in text
    assert "stage mesh_facts" in text
    assert "stage partition_audit" in text
    assert "native tool is not provisioned" not in text
    assert "-fileHandler uncollated" in text
    assert "OPENFOAM_METRICS_PSTREAM_DIR" in text
    assert "OPENFOAM_METRICS_RUN_ID" in text


def test_workflow_keeps_credentials_at_runner_publish_boundary_only() -> None:
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")

    assert (
        'job_environment="RUN_ID=${RUN_ID},RUN_MANIFEST=${RUN_MANIFEST},RUN_DIR=${RUN_DIR}"'
        in workflow
    )
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64" not in workflow
    assert "record-pstream --manifest" in workflow
    assert "Publish v2 raw facts to BigQuery" in workflow
    publish = workflow.index("Publish v2 raw facts to BigQuery")
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON" in workflow[publish:]
