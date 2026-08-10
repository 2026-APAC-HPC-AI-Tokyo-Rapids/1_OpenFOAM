from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_pjm_compute_boundary_is_credential_free_and_uses_exact_stages() -> None:
    script = ROOT / "scripts/run-openfoam.pjm"
    text = script.read_text(encoding="utf-8")

    subprocess.run(["bash", "-n", str(script)], check=True)
    assert "#PJM -L elapse=00:50:00" in text
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS" not in text
    assert "stage solver" in text
    assert "stage minimal_hardware_capture" in text
    assert "if (( OPENFOAM_NODES == 1 )); then" in text
    assert "minimal_hardware_argv+=(--node-ordinal 0)" in text
    assert '"${MPIEXEC}" -np "${OPENFOAM_NODES}" -ppn 1' in text
    assert "--node-ordinal-from-env PMI_RANK" in text
    assert "stage mesh_facts" in text
    assert "stage partition_audit" in text
    assert "native tool is not provisioned" not in text
    assert "-fileHandler uncollated" in text
    assert "OPENFOAM_METRICS_PSTREAM_DIR" in text
    assert "OPENFOAM_METRICS_RUN_ID" in text
    assert "export OPENFOAM_PROFILE_DIR PROFILE_RUN_ID" in text
    assert text.index("export OPENFOAM_PROFILE_DIR PROFILE_RUN_ID") < text.index(
        "stage solver"
    )
    assert "capture-workload" in text
    assert '--expected-nodes "${OPENFOAM_NODES}"' in text
    assert '--stderr-path "${IMB_STDERR}" --timeout-sec 600' in text
    assert '"${PROVISION_DIR}/scripts/openfoam-rank-wrapper.py"' in text


def test_workflow_keeps_credentials_at_runner_publish_boundary_only() -> None:
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")

    assert "submit-run --manifest" in workflow
    assert "--pjm-script-repository-path scripts/run-openfoam.pjm" in workflow
    assert "record-scheduler-terminal --manifest" in workflow
    assert "record-execution-context --manifest" in workflow
    assert "record-profile-perf --manifest" in workflow
    assert "env.MERGE_STATUS == '0'" in workflow
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64" not in workflow
    assert "record-pstream --manifest" in workflow
    assert "Publish v2 raw facts to BigQuery" in workflow
    assert "steps.upload_v2.outcome == 'success'" in workflow
    publish = workflow.index("Publish v2 raw facts to BigQuery")
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON" in workflow[publish:]
