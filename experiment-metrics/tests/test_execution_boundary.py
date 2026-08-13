from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_commands_do_not_use_line_continuations() -> None:
    paths = [ROOT / ".github/workflows/genkai.yml"]
    paths.extend((ROOT / "scripts").glob("*.sh"))
    paths.extend((ROOT / "scripts").glob("*.pjm"))
    paths.extend((ROOT / "benchmark").glob("*.sh"))
    paths.extend((ROOT / "research").rglob("*.md"))

    for path in paths:
        continued = [number for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if line.endswith("\\")]
        assert not continued, f"{path}: command continuation at lines {continued}"


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
    assert "stage_at case_prepare" in text
    assert "prepare-openfoam-case.sh" in text
    assert "--require-cache" in text
    assert "stage mesh_facts" not in text
    assert "stage partition_audit" not in text
    assert 'stage mesh_facts "${LOG_DIR}/mesh-facts.log"' not in text
    assert 'stage partition_audit "${LOG_DIR}/partition-audit.log"' not in text
    assert "stage check_mesh" not in text
    assert "native tool is not provisioned" not in text
    assert "-fileHandler uncollated" in text
    assert "OPENFOAM_METRICS_PSTREAM_DIR" in text
    assert "OPENFOAM_METRICS_RUN_ID" in text
    assert "OPENFOAM_RANKS" not in text
    assert "OPENFOAM_MPI_PPN" not in text
    assert "scheduler-selected VTune rank is required" in text
    assert "if (( ranks_per_node == 112 )); then" in text
    assert (
        'I_MPI_PIN_PROCESSOR_LIST="0-13,15-28,30-43,45-58,'
        '60-73,75-88,90-103,105-118"'
    ) in text
    assert "OPENFOAM_PROFILE_DIR" not in text
    assert 'vtune_root="/home/pj26000080/share/openfoam-vtune/${profile_run_id}"' in text
    assert 'WM_COMPILE_OPTION="${build_environment[0]}"' in text
    assert 'test "${WM_OPTIONS}" = "${build_environment[1]}"' in text
    assert "capture-workload" in text
    assert '--expected-nodes "${OPENFOAM_NODES}"' in text
    assert '--stderr-path "${IMB_STDERR}" --timeout-sec 600' in text
    assert '--profile-rank "${OPENFOAM_VTUNE_RANK}"' in text
    assert '--profile-wrapper "${PROVISION_DIR}/scripts/exec-profiler.sh"' in text
    assert '"${PROVISION_DIR}/scripts/allow-vtune-attach.py"' in (
        (ROOT / "scripts/exec-profiler.sh").read_text()
    )
    assert '"${PROVISION_DIR}/scripts/export-vtune-hotspots.sh"' in text
    assert "record-build-provision" in text
    assert "record-minimal-hardware" in text
    assert "record-mesh" in text
    assert '--block-mesh-log "${LOG_DIR}/blockMesh.log"' in text
    assert '--decompose-log "${LOG_DIR}/decomposePar.log"' in text

    prepare = ROOT / "scripts/prepare-openfoam-case.pjm"
    subprocess.run(["bash", "-n", str(prepare)], check=True)
    assert "blockMesh" in prepare.read_text(encoding="utf-8")
    assert "decomposePar" in prepare.read_text(encoding="utf-8")
    # The installed hardware probe has an env python3 shebang.  Genkai's
    # system Python is too old, so every direct or MPI-launched probe must
    # inherit the provisioned interpreter without changing the probe argv.
    python_path = 'probe_python_dir="${PROVISION_DIR}/experiment-metrics/.venv/bin"'
    export_path = 'export PATH="${probe_python_dir}:${PATH}"'
    assert python_path in text
    assert '[[ -x "${probe_python_dir}/python3" ]]' in text
    assert export_path in text
    assert text.index('source "${PROVISION_DIR}/OpenFOAM/etc/bashrc"') < text.index(
        python_path
    )
    assert text.index(export_path) < text.index("CAPTURE_HARDWARE=$(command -v")
    assert text.index(export_path) < text.index("stage minimal_hardware_capture")
    assert text.index(export_path) < text.index("stage profile_hardware_capture")


def test_workflow_uses_mode_0600_credential_path_for_direct_sends() -> None:
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")

    assert "submit-run" in workflow
    assert '--manifest "${RUN_MANIFEST}"' in workflow
    assert "--pjm-script-repository-path scripts/run-openfoam.pjm" in workflow
    assert "record-scheduler-terminal --manifest" in workflow
    assert "record-execution-context --manifest" in workflow
    assert "record-profile-vtune" not in workflow
    assert "Publish VTune hotspots to Actions summary" in workflow
    assert 'purpose=\'${{ github.event_name == \'push\' && \'bench\' || inputs.run_purpose }}\'' in workflow
    assert "github.event_name == 'push' && 'bench'" in workflow
    assert "run_purpose:" in workflow
    assert "build_preset:" not in workflow
    assert "profile_rank:" in workflow
    assert "profile_analysis:" in workflow
    assert "OPENFOAM_PROFILE_RANK" not in workflow
    assert "OPENFOAM_PROFILE_ANALYSIS" not in workflow
    assert "OPENFOAM_EXPERIMENT_PRESET" not in workflow
    assert """--profile-rank '${{ github.event_name == 'push' && '0' || inputs.profile_rank }}'""" in workflow
    assert """--profile-analysis '${{ github.event_name == 'push' && 'hotspots' || inputs.profile_analysis }}'""" in workflow
    assert "- bench" in workflow
    assert "- profile" in workflow
    assert "openfoam-profile-vtune-hotspots-v1.json" in workflow
    assert "profile_mode" not in workflow
    assert "perf-stat" not in workflow
    assert "Perfetto" not in workflow
    assert "Merge terminal fragments" not in workflow
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64" not in workflow
    assert "record-pstream --manifest" in workflow
    assert "Publish v2 raw facts to BigQuery" not in workflow
    assert "install -m 0600" in workflow
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE" in workflow
    assert 'smoke-send --run "${RUN_ID}" --source runner' in workflow
    assert "Prepare OpenFOAM case cache" in workflow
    prepare_concurrency = (
        "genkai-openfoam-case-${{ needs.select-build.outputs.prepare_script_sha256 }}"
    )
    assert prepare_concurrency in workflow
    assert workflow.count("queue: max") == 2
    assert "queue: single" not in workflow
    assert workflow.count("- name: Record v2 terminal sources") == 1
    assert "metrics.jsonl" not in workflow
    assert "-name 'node-*.json'" in workflow
    assert "! -name 'node-*.json'" in workflow


def test_partition_audit_uses_json_writer_for_std_string_digest() -> None:
    source = (
        ROOT / "experiment-metrics/native/partition-audit/partition-audit.C"
    ).read_text(encoding="utf-8")

    assert "writeJsonString(output, locator.sha256);" in source
    assert '<< locator.sha256 << "\\"}"' not in source


def test_builder_verifies_only_upstream_in_process_sources() -> None:
    script = (ROOT / "scripts/build-openfoam.sh").read_text(encoding="utf-8")

    assert 'select(.kind == "in_process_hook")' in script
    assert "| .source_path" in script
    assert "jq -r '.source_paths[]'" not in script
    assert "OPENFOAM_BUILD_PARALLELISM" not in script
    assert "EXPERIMENT_METRICS_NATIVE_ROOT" not in script
    assert "build_condition=opt-avx512-zmm-high" in script
    assert "build_compile_option=OptAVX512" in script
    assert "build_tuning_flags=-qopt-zmm-usage=high" in script
    assert "-qopt-report-phase=loop,vec,cg" in script
    assert 'export FOAM_EXTRA_CXXFLAGS="${build_extra_cxxflags}"' in script
    assert 'test "${FOAM_EXTRA_CXXFLAGS}" = "${build_extra_cxxflags}"' in script
    assert "WM_COMPILE_CONTROL=+ccache" not in script
    assert "CMAKE_CXX_COMPILER_LAUNCHER" not in script


def test_ruff_does_not_enforce_code_width() -> None:
    config = (ROOT / "experiment-metrics/pyproject.toml").read_text(encoding="utf-8")
    assert "line-length" not in config
    assert 'ignore = ["E501"]' in config
