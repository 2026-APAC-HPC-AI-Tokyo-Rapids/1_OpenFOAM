from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_commands_do_not_use_line_continuations() -> None:
    paths = list((ROOT / ".github/workflows").glob("*.yml"))
    paths.extend((ROOT / "scripts").glob("*.sh"))
    paths.extend((ROOT / "scripts").glob("*.pjm"))
    paths.extend((ROOT / "platforms").rglob("*.sh"))
    paths.extend((ROOT / "platforms").rglob("*.pjm"))
    paths.extend((ROOT / "platforms").rglob("*.pbs"))
    paths.extend((ROOT / "benchmark").glob("*.sh"))
    paths.extend((ROOT / "research").rglob("*.md"))

    for path in paths:
        continued = [number for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if line.endswith("\\")]
        assert not continued, f"{path}: command continuation at lines {continued}"


def test_pjm_compute_boundary_is_credential_free_and_uses_exact_stages() -> None:
    script = ROOT / "scripts/run-openfoam.sh"
    text = script.read_text(encoding="utf-8")
    wrapper = ROOT / "platforms/genkai/run-openfoam.pjm"
    wrapper_text = wrapper.read_text(encoding="utf-8")

    subprocess.run(["bash", "-n", str(script)], check=True)
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    assert "#PJM -L elapse=01:00:00" in wrapper_text
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS" not in text
    assert "stage solver" in text
    assert "stage minimal_hardware_capture" in text
    assert "if (( OPENFOAM_NODES == 1 )); then" in text
    assert "minimal_hardware_argv+=(--node-ordinal 0)" in text
    assert '"${node_launch[@]}"' in text
    assert '--node-ordinal-from-env "${global_rank_env}"' in text
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
    assert "if (( ranks_per_node == 112 )); then" in wrapper_text
    assert (
        'I_MPI_PIN_PROCESSOR_LIST="0-13,15-28,30-43,45-58,'
        '60-73,75-88,90-103,105-118"'
    ) in wrapper_text
    assert "OPENFOAM_PROFILE_DIR" not in text
    assert 'vtune_root="${profile_root}/${profile_run_id}"' in text
    assert 'WM_COMPILE_OPTION="${build_environment[0]}"' in wrapper_text
    assert 'test "${WM_OPTIONS}" = "${build_environment[1]}"' in wrapper_text
    assert "capture-workload" in text
    assert '--expected-nodes "${OPENFOAM_NODES}"' in text
    assert '--stderr-path "${IMB_STDERR}" --timeout-sec 600' in text
    assert '--profile-rank "${OPENFOAM_VTUNE_RANK}"' in text
    assert '--profile-wrapper "${PROVISION_DIR}/scripts/exec-profiler.sh"' in text
    assert '"${PROVISION_DIR}/scripts/allow-vtune-attach.py"' in (
        (ROOT / "scripts/exec-profiler.sh").read_text()
    )
    assert '"${PROVISION_DIR}/scripts/export-vtune-hotspots.sh"' in text
    assert "-data-limit=0" in (ROOT / "scripts/exec-profiler.sh").read_text()
    assert "record-build-provision" in text
    assert "record-minimal-hardware" in text
    assert "record-mesh" in text
    assert '--block-mesh-log "${LOG_DIR}/blockMesh.log"' in text
    assert '--decompose-log "${LOG_DIR}/decomposePar.log"' in text

    prepare = ROOT / "platforms/genkai/prepare-openfoam-case.pjm"
    subprocess.run(["bash", "-n", str(prepare)], check=True)
    prepare_text = prepare.read_text(encoding="utf-8")
    assert "blockMesh" in prepare_text
    assert "decomposePar" in prepare_text
    assert 'WM_COMPILE_OPTION="${build_environment[0]}"' in prepare_text
    assert 'test "${WM_OPTIONS}" = "${build_environment[1]}"' in prepare_text
    # The installed hardware probe has an env python3 shebang.  Genkai's
    # system Python is too old, so every direct or MPI-launched probe must
    # inherit the provisioned interpreter without changing the probe argv.
    python_path = 'probe_python_dir="${PROVISION_DIR}/experiment-metrics/.venv/bin"'
    export_path = 'export PATH="${probe_python_dir}:${PATH}"'
    assert python_path in text
    assert '[[ -x "${probe_python_dir}/python3" ]]' not in text
    assert export_path in text
    assert text.index(export_path) < text.index("CAPTURE_HARDWARE=$(command -v")
    assert text.index(export_path) < text.index("stage minimal_hardware_capture")
    assert text.index(export_path) < text.index("stage profile_hardware_capture")


def test_workflow_uses_mode_0600_credential_path_for_direct_sends() -> None:
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")

    assert "submit-run" in workflow
    assert '--manifest "${RUN_MANIFEST}"' in workflow
    assert "--pjm-script-repository-path platforms/genkai/run-openfoam.pjm" in workflow
    assert "record-scheduler-terminal --manifest" in workflow
    assert "record-execution-context --manifest" in workflow
    assert "record-profile-vtune" not in workflow
    assert "Publish VTune hotspots to Actions summary" in workflow
    assert "purpose='${{ inputs.run_purpose }}'" not in workflow
    assert "run_purpose:" not in workflow
    assert "if [[ '${{ inputs.profile }}' == true ]]" in workflow
    assert "build_preset:" not in workflow
    assert "profile_rank:" in workflow
    assert "profile_analysis:" in workflow
    assert "OPENFOAM_PROFILE_RANK" not in workflow
    assert "OPENFOAM_PROFILE_ANALYSIS" not in workflow
    assert "OPENFOAM_EXPERIMENT_PRESET" not in workflow
    assert """--profile-rank '${{ inputs.profile_rank }}'""" in workflow
    assert """--profile-analysis '${{ inputs.profile_analysis }}'""" in workflow
    assert "type: string" in workflow
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
    assert "queue: max" not in workflow
    assert "queue: single" not in workflow
    assert '${GITHUB_RUN_ID}.tar.zst' in workflow
    assert '${GITHUB_RUN_NUMBER}.tar.zst' not in workflow
    assert workflow.count("- name: Initialize metrics and submit OpenFOAM") == 1
    assert workflow.count("- name: Finalize metrics and package artifacts") == 1
    assert 'steps.v2_context.outputs.pjm_job_id != \'\'' in workflow
    assert "needs.run.outputs.artifact_uploaded == 'true'" in workflow
    assert "LC_ALL=C sort -u" in workflow
    assert "- name: Verify runner BigQuery connectivity" not in workflow
    assert "- name: Record v2 terminal sources" not in workflow
    assert "- name: Package fixed v2 artifact set" not in workflow
    assert "metrics.jsonl" not in workflow
    assert "-name 'node-*.json'" in workflow
    assert "! -name 'node-*.json'" in workflow


def test_control_plane_does_not_preflight_files_consumed_by_the_next_command() -> None:
    genkai = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    gadi = (ROOT / ".github/workflows/gadi.yml").read_text(encoding="utf-8")
    prepare = (ROOT / "scripts/prepare-openfoam-case.sh").read_text(encoding="utf-8")

    assert "archive_step_count" not in genkai
    assert 'test -f "${protocol_path}"' not in genkai
    assert 'test -f "${cache_dir}/READY"' not in genkai
    assert '[[ -s "${archive}" && -s "${sidecar}" ]]' not in genkai
    assert '[[ -s "${archive}" && -s "${sidecar}" ]]' not in gadi
    assert 'if [[ ! -s "${openfoam_archive}" ]]' not in gadi
    assert 'if [[ ! -s "${thirdparty_archive}" ]]' not in gadi
    assert 'test -f "${cache_dir}/READY"' not in gadi
    assert '[[ -d "${SOURCE_CASE}" ]]' not in prepare
    assert '[[ -e "${TARGET_CASE}" ]]' not in prepare


def test_gadi_boundary_uses_pbs_and_target_local_storage() -> None:
    workflow = (ROOT / ".github/workflows/gadi.yml").read_text(encoding="utf-8")
    wrapper = (ROOT / "platforms/gadi/run-openfoam.pbs").read_text(encoding="utf-8")
    builder = (ROOT / "platforms/gadi/build-openfoam.pbs").read_text(encoding="utf-8")
    entry = (ROOT / ".github/workflows/openfoam.yml").read_text(encoding="utf-8")

    assert "runs-on: [self-hosted, gadi]" in workflow
    assert "/scratch/hb15/tk7779/openfoam/gadi" in workflow
    assert "/home/pj26000080" not in workflow
    assert "submit-pbs-run" in workflow
    assert "record-pbs-terminal" in workflow
    assert "ncpus=104,mem=400GB,jobfs=400GB" in workflow
    assert workflow.count("- name: Initialize metrics and submit PBS run") == 1
    assert workflow.count("- name: Finalize metrics and package artifacts") == 1
    assert 'steps.context.outputs.pbs_job_id != \'\'' in workflow
    assert "if: always() && needs.provision.result == 'success'" in workflow
    assert "if: always() && needs.run.outputs.artifact_uploaded == 'true'" in workflow
    assert 'export EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE="${credential_file}"' in workflow
    assert "LC_ALL=C sort -u" in workflow
    assert "- name: Verify runner BigQuery connectivity" not in workflow
    assert "- name: Record terminal metrics" not in workflow
    assert "- name: Package fixed run artifact" not in workflow
    assert '${GITHUB_RUN_ID}.tar.zst' in workflow
    assert '${GITHUB_RUN_NUMBER}.tar.zst' not in workflow
    assert "openfoam-v2-protocol-gadi-scotch" not in workflow
    assert 'module load gcc/13.2.0 openmpi/4.1.7' in wrapper
    assert "OMPI_COMM_WORLD_RANK" in wrapper
    assert '--solver-launch-arg --map-by' in wrapper
    assert '"${PBS_JOBFS}/openfoam-build"' in builder
    assert 'tar -xzf "${OPENFOAM_SOURCE_ARCHIVE}"' in builder
    assert '--case-cache-root "/scratch/hb15/${USER}/openfoam/gadi/case-cache"' in wrapper
    assert '"${PROVISION_DIR}/platforms/gadi/wait-pbs-job.sh" "${job_id}"' in workflow
    assert "uses: ./.github/workflows/gadi.yml" in entry
    assert "contains(github.event.head_commit.message, '[cluster:genkai]')" in entry
    assert "contains(github.event.head_commit.message, '[cluster:gadi]')" in entry
    assert "inputs.run_genkai" in entry
    assert "inputs.run_gadi" in entry
    assert entry.count("contains(github.event.head_commit.message, '[nodes:4]')") == 2
    assert entry.count("contains(github.event.head_commit.message, '[nodes:2]')") == 2
    assert entry.count("github.event_name == 'workflow_dispatch' && inputs.node_count") == 2
    assert "select-target" not in entry
    assert "select-actions-target.sh" not in entry


def test_workflow_dispatch_exposes_only_inputs_owned_by_each_entry_workflow() -> None:
    entry = (ROOT / ".github/workflows/openfoam.yml").read_text(encoding="utf-8")
    profile = (ROOT / ".github/workflows/genkai-profile.yml").read_text(
        encoding="utf-8"
    )
    genkai = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    gadi = (ROOT / ".github/workflows/gadi.yml").read_text(encoding="utf-8")

    entry_inputs = entry.split("permissions:", 1)[0]
    assert "run_genkai:" in entry_inputs
    assert "run_gadi:" in entry_inputs
    assert "node_count:" in entry_inputs
    assert "require_build:" not in entry_inputs
    assert "reshare_ccache:" not in entry_inputs
    assert "run_purpose:" not in entry_inputs
    assert "profile_rank:" not in entry_inputs
    assert "profile_analysis:" not in entry_inputs

    profile_inputs = profile.split("permissions:", 1)[0]
    assert "profile_rank:" in profile_inputs
    assert "profile_analysis:" in profile_inputs
    assert "node_count:" in profile_inputs
    assert "run_genkai:" not in profile_inputs
    assert "run_gadi:" not in profile_inputs
    assert "require_build:" not in profile_inputs
    assert "run_purpose:" not in profile_inputs
    assert "profile: true" in profile

    assert "require_build:" not in genkai
    assert "reshare_ccache:" not in genkai
    assert "run_purpose:" not in genkai
    assert "require_build:" not in gadi
    assert "run_purpose:" not in gadi
    push_gate = 'if [[ "${GITHUB_EVENT_NAME}" == push ]]; then\n            commit_message="$(git log -1 --format=%B "${GITHUB_SHA}")"'
    assert push_gate in genkai
    assert push_gate in gadi


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
    assert "build_condition=baseline" in script
    assert "build_compile_option=Opt" in script
    assert "build_tuning_flags=" in script
    assert "-qopt-report-phase=loop,vec,cg" in script
    assert 'export FOAM_EXTRA_CXXFLAGS="${build_extra_cxxflags}"' in script
    assert 'test "${FOAM_EXTRA_CXXFLAGS}" = "${build_extra_cxxflags}"' in script
    assert "WM_COMPILE_CONTROL=+ccache" in script
    assert "CMAKE_CXX_COMPILER_LAUNCHER=ccache" in script
    assert "CCACHE_RECACHE" not in script
    assert '${GITHUB_RUN_ID}.tar.zst' in script
    assert '${GITHUB_RUN_NUMBER}.tar.zst' not in script


def test_ruff_does_not_enforce_code_width() -> None:
    config = (ROOT / "experiment-metrics/pyproject.toml").read_text(encoding="utf-8")
    assert "line-length" not in config
    assert 'ignore = ["E501"]' in config
