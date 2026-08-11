from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_pjm_compute_boundary_is_credential_free_and_uses_exact_stages() -> None:
    script = ROOT / "scripts/run-openfoam.pjm"
    text = script.read_text(encoding="utf-8")

    subprocess.run(["bash", "-n", str(script)], check=True)
    assert "#PJM -L elapse=01:00:00" in text
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

    # The installed hardware probe has an env python3 shebang.  Genkai's
    # system Python is too old, so every direct or MPI-launched probe must
    # inherit the provisioned interpreter without changing the probe argv.
    python_path = 'PROBE_PYTHON_DIR="${PROVISION_DIR}/experiment-metrics/.venv/bin"'
    export_path = 'export PATH="${PROBE_PYTHON_DIR}:${PATH}"'
    assert python_path in text
    assert '[[ -x "${PROBE_PYTHON_DIR}/python3" ]]' in text
    assert export_path in text
    assert text.index('source "${PROVISION_DIR}/OpenFOAM/etc/bashrc"') < text.index(
        python_path
    )
    assert text.index(export_path) < text.index("CAPTURE_HARDWARE=$(command -v")
    assert text.index(export_path) < text.index("stage minimal_hardware_capture")
    assert text.index(export_path) < text.index("stage profile_hardware_capture")


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
    # Schema deployment is an explicit control-plane operation.  Steady-state
    # publication must need only insertAll permissions, not query-job creation.
    publish_step = workflow[publish : workflow.index("Upload cavity3D result")]
    assert "--schema-sql" not in publish_step
    assert "-name 'node-*.json'" in workflow
    assert "! -name 'node-*.json'" in workflow


def test_partition_audit_uses_json_writer_for_std_string_digest() -> None:
    source = (
        ROOT / "experiment-metrics/native/partition-audit/partition-audit.C"
    ).read_text(encoding="utf-8")

    assert "writeJsonString(output, locator.sha256);" in source
    assert '<< locator.sha256 << "\\\"}"' not in source


def test_builder_verifies_only_upstream_in_process_sources() -> None:
    script = (ROOT / "scripts/build-openfoam.sh").read_text(encoding="utf-8")

    assert 'select(.kind == "in_process_hook")' in script
    assert "| .source_path" in script
    assert "jq -r '.source_paths[]'" not in script


def test_overhead_check_repeats_primary_solver_and_keeps_diagnostics() -> None:
    script_path = ROOT / "scripts/v2-overhead-check.pjm"
    script = script_path.read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/v2-overhead-check.yml").read_text(
        encoding="utf-8"
    )

    subprocess.run(["bash", "-n", str(script_path)], check=True)
    order = [
        script.index("run_arm off 1"),
        script.index("run_arm on 1"),
        script.index("run_arm off 2"),
        script.index("run_arm on 2"),
    ]
    assert order == sorted(order)
    assert "primary_on_over_off_trim_ratio" in script
    assert '(on1 + on2) / (off1 + off2)' in script
    assert 'ratio <= 1.05' in script
    assert "sha256sum --check" in script
    assert "markers_equal=true" in script
    assert "for rank in $(seq 0 119)" in script
    assert "diagnostic-status.txt" in script

    upload = workflow.index("Upload comparison diagnostics")
    cleanup = workflow.index("Discard comparison data")
    assert upload < cleanup
    assert "if: always() && steps.provision.outputs.check_dir != ''" in workflow
    assert "archive_sha256=" in workflow
    assert "bigquery" not in workflow.lower()
    assert "GOOGLE_CREDENTIALS" not in workflow
