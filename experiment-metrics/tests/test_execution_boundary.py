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
        continued = [
            number
            for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            )
            if line.endswith("\\")
        ]
        assert not continued, f"{path}: command continuation at lines {continued}"


def test_pjm_compute_boundary_is_credential_free_and_uses_exact_stages() -> None:
    script = ROOT / "scripts/run-openfoam.sh"
    text = script.read_text(encoding="utf-8")
    wrapper = ROOT / "platforms/genkai/run-openfoam.pjm"
    wrapper_text = wrapper.read_text(encoding="utf-8")

    subprocess.run(["bash", "-n", str(script)], check=True)
    subprocess.run(["bash", "-n", str(wrapper)], check=True)
    assert "#PJM -L elapse=01:00:00" in wrapper_text
    assert 'export PATH="${PATH//${user_local_bin}/}"' in wrapper_text
    assert (
        '--solver-launch-arg -genv --solver-launch-arg PATH --solver-launch-arg "${PATH}"'
        in wrapper_text
    )
    assert (
        '--node-launch-arg -genv --node-launch-arg PATH --node-launch-arg "${PATH}"'
        in wrapper_text
    )
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS" not in text
    assert "smoke-send --run" not in text
    assert "stage solver" in text
    assert "stage minimal_hardware_capture" in text
    assert "if (( OPENFOAM_NODES == 1 )); then" in text
    assert "minimal_hardware_argv+=(--node-ordinal 0)" in text
    assert '"${node_launch[@]}"' in text
    assert '--node-ordinal-from-env "${global_rank_env}"' in text
    assert "stage_at case_prepare" in text
    assert "stage rank_placement" in text
    assert 'stage solver "${SOLVER_LOG}" "${solver_launch[@]}" "${SIMPLE_FOAM}"' in text
    assert text.index("stage rank_placement") < text.index(
        'stage solver "${SOLVER_LOG}"'
    )
    assert "prepare-openfoam-case.sh" in text
    assert "--require-cache" in text
    assert '"${RUN_DIR}/control/build-sidecar.json"' in text
    assert "stage mesh_facts" not in text
    assert "stage partition_audit" not in text
    assert 'stage mesh_facts "${LOG_DIR}/mesh-facts.log"' not in text
    assert 'stage partition_audit "${LOG_DIR}/partition-audit.log"' not in text
    assert "stage check_mesh" not in text
    assert "native tool is not provisioned" not in text
    assert "-fileHandler uncollated" in text
    assert "OPENFOAM_METRICS_PSTREAM_DIR" not in text
    assert "OPENFOAM_METRICS_RUN_ID" not in text
    assert "OPENFOAM_RANKS" not in text
    assert "OPENFOAM_MPI_PPN" not in text
    assert "scheduler-selected VTune rank is required" in text
    assert "if (( ranks_per_node == 112 )); then" in wrapper_text
    assert (
        'I_MPI_PIN_PROCESSOR_LIST="0-13,15-28,30-43,45-58,60-73,75-88,90-103,105-118"'
    ) in wrapper_text
    assert "OPENFOAM_PROFILE_DIR" not in text
    assert 'vtune_root="${profile_root}/${profile_run_id}"' in text
    assert "/home/pj26000080" not in text
    assert 'WM_COMPILE_OPTION="${build_environment[0]}"' in wrapper_text
    assert 'test "${WM_OPTIONS}" = "${build_environment[1]}"' in wrapper_text
    assert "capture-workload" in text
    assert '"${OPENFOAM_SOLVER}" == simpleFoam' in text
    assert '"${OPENFOAM_DISTRIBUTION}" == OpenFOAM.com' in text
    assert '"${OPENFOAM_WORKLOAD_ID}" == occDrivAerStaticMesh-65M' in text
    assert (
        'source "${WM_PROJECT_DIR:?OpenFOAM project directory is required}/bin/tools/RunFunctions"'
        in text
    )
    assert "RESTORE_ZERO_DIR=$(command -v restore0Dir)" not in text
    assert "restore0Dir -processor" in text
    source_index = text.index('source "${WM_PROJECT_DIR:?')
    assert text.rindex("set +u", 0, source_index) < source_index
    assert text.index("set -u", source_index) > source_index
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
    assert '--check-mesh-log "${LOG_DIR}/checkMesh.log"' in text
    assert '--decompose-log "${LOG_DIR}/decomposePar.log"' in text

    prepare = ROOT / "platforms/genkai/prepare-openfoam-case.pjm"
    subprocess.run(["bash", "-n", str(prepare)], check=True)
    prepare_text = prepare.read_text(encoding="utf-8")
    assert "checkMesh" in prepare_text
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


def test_genkai_uploads_metrics_from_login_runner_after_the_job() -> None:
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
    assert "profile_rank:" not in workflow
    assert "profile_analysis:" not in workflow
    assert "OPENFOAM_PROFILE_RANK" not in workflow
    assert "OPENFOAM_PROFILE_ANALYSIS" not in workflow
    assert "OPENFOAM_EXPERIMENT_PRESET" not in workflow
    assert "--profile-rank" not in workflow
    assert "--profile-analysis" not in workflow
    assert "openfoam-profile-vtune-hotspots-v1.json" in workflow
    assert "profile_mode" not in workflow
    assert "perf-stat" not in workflow
    assert "Perfetto" not in workflow
    assert "Merge terminal fragments" not in workflow
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64" not in workflow
    assert "record-pstream --manifest" not in workflow
    assert "Publish v2 raw facts to BigQuery" not in workflow
    assert "install -m 0600" in workflow
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE" in workflow
    assert 'smoke-send --run "${RUN_ID}" --source runner' in workflow
    assert "Prepare OpenFOAM case cache" in workflow
    prepare_concurrency = "genkai-openfoam-case-${{ needs.select-build.outputs.experiment_preset }}-${{ needs.select-build.outputs.prepare_script_sha256 }}-${{ needs.select-build.outputs.build_cache_key }}"
    assert prepare_concurrency in workflow
    assert "build_cache_key: ${{ steps.select.outputs.build_cache_key }}" in workflow
    assert "queue: max" not in workflow
    assert "queue: single" not in workflow
    assert "${GITHUB_RUN_ID}.tar.zst" in workflow
    assert "${GITHUB_RUN_NUMBER}.tar.zst" not in workflow
    assert workflow.count("- name: Initialize metrics and submit OpenFOAM") == 1
    assert workflow.count("- name: Finalize metrics and package artifacts") == 1
    assert "steps.v2_context.outputs.pjm_job_id != ''" in workflow
    assert "needs.run.outputs.artifact_uploaded == 'true'" in workflow
    assert "LC_ALL=C sort -u" in workflow
    assert (
        'send-fragments --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}"'
        in workflow
    )
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


def test_gadi_uses_login_build_and_pbs_execution() -> None:
    workflow = (ROOT / ".github/workflows/gadi.yml").read_text(encoding="utf-8")
    wrapper = (ROOT / "platforms/gadi/run-openfoam.pbs").read_text(encoding="utf-8")
    runner = (ROOT / "scripts/run-openfoam.sh").read_text(encoding="utf-8")
    builder_path = ROOT / "platforms/gadi/build-openfoam.sh"
    builder = builder_path.read_text(encoding="utf-8")
    entry = (ROOT / ".github/workflows/openfoam.yml").read_text(encoding="utf-8")

    assert "runs-on: [self-hosted, gadi]" in workflow
    runtime_provisioner = (
        ROOT / "platforms/gadi/provision-openfoam-runtime.sh"
    ).read_text(encoding="utf-8")
    assert (
        'platforms/gadi/provision-openfoam-runtime.sh "${archive}" "${sidecar}" "${provision_dir}"'
        in workflow
    )
    assert (
        'ln -- "${archive}" "${provision_dir}/runtime.tar.zst"' in runtime_provisioner
    )
    assert (
        'tar -I zstd -xf "${archive}" -C "${provision_dir}" ./control/build-raw'
        in runtime_provisioner
    )
    assert "runtime-cache" not in runtime_provisioner
    assert "group: gadi-openfoam-runtime" not in workflow
    assert "/scratch/hb15/tk7779/openfoam/gadi" in workflow
    assert "/home/pj26000080" not in workflow
    assert "submit-pbs-run" in workflow
    assert "record-pbs-terminal" in workflow
    assert (
        "/tmp/openfoam-build/run-${{ github.run_id }}-${{ github.run_attempt }}"
        in workflow
    )
    assert "platforms/gadi/build-openfoam.sh" in workflow
    assert "build_cache_key: ${{ steps.select.outputs.build_cache_key }}" in workflow
    assert (
        "gadi-openfoam-case-${{ needs.select-build.outputs.ranks }}-${{ needs.select-build.outputs.prepare_script_sha256 }}-${{ needs.select-build.outputs.build_cache_key }}"
        in workflow
    )
    assert "openfoam_build" not in workflow
    assert workflow.count("- name: Initialize metrics and submit OpenFOAM") == 1
    assert workflow.count("- name: Finalize metrics and package artifacts") == 1
    assert "steps.v2_context.outputs.pbs_job_id != ''" in workflow
    assert "if: always() && needs.provision.result == 'success'" in workflow
    assert "if: always() && needs.run.outputs.artifact_uploaded == 'true'" in workflow
    assert (
        'export EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE="${credential_file}"'
        in workflow
    )
    assert "LC_ALL=C sort -u" in workflow
    assert (
        'send-fragments --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}"'
        in workflow
    )
    assert "- name: Verify runner BigQuery connectivity" not in workflow
    assert "- name: Record terminal metrics" not in workflow
    assert "- name: Package fixed run artifact" not in workflow
    assert "${GITHUB_RUN_ID}.tar.zst" in workflow
    assert "${GITHUB_RUN_NUMBER}.tar.zst" not in workflow
    assert "openfoam-v2-protocol-gadi-scotch" not in workflow
    assert "module load intel-compiler-llvm/2025.1.1 intel-mpi/2021.15.0" in wrapper
    assert "module load intel-vtune/2025.3.0" in wrapper
    assert "WM_COMPILER=Icx WM_MPLIB=INTELMPI" in wrapper
    assert "PMI_RANK" in wrapper
    assert "--solver-launch-arg -ppn" in wrapper
    assert "build_parallelism=16" in builder
    assert 'build_tree="${BUILD_DIR}/tree"' in builder
    assert "PBS_JOBFS" not in builder
    assert builder_path.stat().st_mode & 0o111
    assert 'tar -xzf "${OPENFOAM_SOURCE_ARCHIVE}"' in builder
    assert 'runtime_root="${PBS_JOBFS}/openfoam-runtime"' in wrapper
    assert 'case_dir="${PBS_JOBFS}/openfoam-case/occDrivAerStaticMesh"' in wrapper
    assert (
        'case_archive_root="/scratch/hb15/${USER}/openfoam/gadi/case-archives"'
        in wrapper
    )
    assert "--openfoam-arg -hostRoots" in wrapper
    assert 'host_roots="((\\\".*\\\" \\\"${PBS_JOBFS}/openfoam-case\\\"))"' in wrapper
    assert 'io_ranks+="$(( node * ranks_per_node )) "' in wrapper
    assert "--openfoam-arg -ioRanks" in wrapper
    assert "if (( OPENFOAM_NODES > 1 ))" in wrapper
    assert '"${distributed_root_args[@]}"' in wrapper
    assert "stage-rank-context.sh" in wrapper
    assert "platforms/gadi/stage-rank-context.sh platforms/gadi/collect-rank-placement.sh" in workflow
    assert "--rank-manifest" in wrapper
    assert "--rank-placement-root" in wrapper
    assert "--placement-collector" in wrapper
    assert '"${node_launch[@]}" "${placement_collector}"' in runner
    assert "numberOfSubdomains[[:space:]]+${OPENFOAM_MPI_PROCS}" in runner
    assert "method[[:space:]]+scotch" in runner
    assert "jobfs=100GB" in workflow
    assert '"${PROVISION_DIR}/platforms/gadi/wait-pbs-job.sh" "${job_id}"' in workflow
    assert "uses: ./.github/workflows/gadi.yml" in entry
    assert "contains(github.event.head_commit.message, '[cluster:genkai]')" in entry
    assert "contains(github.event.head_commit.message, '[cluster:gadi]')" in entry
    assert "inputs.run_genkai" in entry
    assert "inputs.run_gadi" in entry
    assert entry.count("contains(github.event.head_commit.message, '[nodes:4]')") == 2
    assert entry.count("contains(github.event.head_commit.message, '[nodes:2]')") == 2
    assert (
        entry.count("github.event_name == 'workflow_dispatch' && inputs.node_count")
        == 2
    )
    assert "select-target" not in entry
    assert "select-actions-target.sh" not in entry


def test_workflow_dispatch_exposes_only_inputs_owned_by_each_entry_workflow() -> None:
    entry = (ROOT / ".github/workflows/openfoam.yml").read_text(encoding="utf-8")
    genkai = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    gadi = (ROOT / ".github/workflows/gadi.yml").read_text(encoding="utf-8")

    entry_inputs = entry.split("permissions:", 1)[0]
    assert "run_genkai:" in entry_inputs
    assert "run_gadi:" in entry_inputs
    assert "node_count:" in entry_inputs
    assert "require_build:" not in entry_inputs
    assert "reshare_ccache:" not in entry_inputs
    assert "run_purpose:" not in entry_inputs
    assert "profile:" in entry_inputs
    assert "profile_rank:" not in entry_inputs
    assert "profile_analysis:" not in entry_inputs
    profile_push_gate = "github.event_name == 'push' && contains(github.event.head_commit.message, '[profile]')"
    assert entry.count(profile_push_gate) == 2
    assert not (ROOT / ".github/workflows/genkai-profile.yml").exists()

    assert "require_build:" not in genkai
    assert "reshare_ccache:" not in genkai
    assert "run_purpose:" not in genkai
    assert "require_build:" not in gadi
    assert "run_purpose:" not in gadi
    for workflow in (genkai, gadi):
        assert "profile:" in workflow
        assert "profile_rank:" not in workflow
        assert "profile_analysis:" not in workflow
        assert "--profile-rank" not in workflow
        assert "--profile-analysis" not in workflow
        assert (
            'gh run list --workflow openfoam.yml --commit "${commit}" --limit 1000'
            in workflow
        )
        assert (
            'select(.schema_version == "build-sidecar/v1" and .build_archive.path == "build.tar.zst")'
            in workflow
        )
        assert 'commit="${GITHUB_SHA}"' in workflow
        assert 'git rev-parse "${commit}^"' in workflow
        assert "git diff --quiet" not in workflow
        assert "git cat-file" not in workflow
        assert "commit_role" not in workflow
    push_gate = 'if [[ "${GITHUB_EVENT_NAME}" == push ]]; then\n            commit_message="$(git log -1 --format=%B "${GITHUB_SHA}")"'
    assert push_gate in genkai
    assert push_gate in gadi


def test_cluster_workflows_have_the_same_job_lifecycle() -> None:
    genkai = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    gadi = (ROOT / ".github/workflows/gadi.yml").read_text(encoding="utf-8")
    expected = [
        "select-build",
        "reuse-build",
        "build-openfoam",
        "provision",
        "prepare-case",
        "run",
        "archive-artifacts",
    ]
    for cluster, workflow in (("genkai", genkai), ("gadi", gadi)):
        assert f"openfoam-{cluster}-build-log-" in workflow
        assert f"openfoam-{cluster}-v2-" in workflow
        assert f"openfoam-{cluster}-occdrivaer-65m-result-" in workflow
        assert f'pattern: "openfoam-{cluster}-*"' in workflow
        assert f'startswith("openfoam-{cluster}-")' in workflow
        assert f"openfoam-artifacts/${{GITHUB_RUN_ID}}/{cluster}" in workflow
        assert ".artifacts[].id" not in workflow
        assert "cavity3d" not in workflow.lower()
        job_section = workflow.split("jobs:\n", 1)[1]
        jobs = [
            line[2:-1]
            for line in job_section.splitlines()
            if line.startswith("  ")
            and not line.startswith("    ")
            and line.endswith(":")
        ]
        assert jobs == expected
        assert workflow.index("- name: Wait for OpenFOAM job") < workflow.index(
            "- name: Finalize metrics and package artifacts"
        )
        assert workflow.index(
            "- name: Finalize metrics and package artifacts"
        ) < workflow.index(
            'send-fragments --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}"'
        )
        assert workflow.index(
            'send-fragments --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}"'
        ) < workflow.index("- name: Upload fixed v2 artifact set")


def test_partition_audit_uses_json_writer_for_std_string_digest() -> None:
    source = (
        ROOT / "experiment-metrics/native/partition-audit/partition-audit.C"
    ).read_text(encoding="utf-8")

    assert "writeJsonString(output, locator.sha256);" in source
    assert '<< locator.sha256 << "\\"}"' not in source


def test_builder_uses_the_pinned_unmodified_v2512_sources() -> None:
    script = (ROOT / "scripts/build-openfoam.sh").read_text(encoding="utf-8")

    assert "openfoam_source_ref=refs/tags/OpenFOAM-v2512" in script
    assert "thirdparty_source_ref=refs/tags/v2512" in script
    assert 'select(.kind == "in_process_hook")' not in script
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
    assert "${GITHUB_RUN_ID}.tar.zst" in script
    assert "${GITHUB_RUN_NUMBER}.tar.zst" not in script
    assert "build_parallelism=120" in script


def test_ruff_does_not_enforce_code_width() -> None:
    config = (ROOT / "experiment-metrics/pyproject.toml").read_text(encoding="utf-8")
    assert "line-length" not in config
    assert 'ignore = ["E501"]' in config
