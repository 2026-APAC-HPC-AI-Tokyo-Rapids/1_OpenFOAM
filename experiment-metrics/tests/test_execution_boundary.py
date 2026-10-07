from __future__ import annotations

import os
import subprocess
import sys
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
    assert "stage_at() {" in text
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
    assert 'vtune_root="${large_output_dir}/vtune"' in text
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
    assert 'stage profile_warmup "${LOG_DIR}/profile-warmup.log"' in text
    assert '"${ENV}" FOAM_SIGFPE=false "${solver_launch[@]}" "${SIMPLE_FOAM}" -postProcess -parallel' in text
    assert '--profile-wrapper "${compute_tools_root}/scripts/exec-profiler.sh"' in text
    assert '"${compute_tools_root}/scripts/allow-vtune-attach.py"' in (
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
    assert 'RANK_PYTHON_LAUNCH=(/usr/bin/env "${RANK_PYTHON}")' in text
    assert 'minimal_hardware_argv=("${RANK_PYTHON_LAUNCH[@]}" "${CAPTURE_HARDWARE}"' in text
    assert '"${node_launch[@]}" "${RANK_PYTHON_LAUNCH[@]}" "${CAPTURE_HARDWARE}" --mode profile-postrun' in text


def test_hardware_probe_uses_deployed_python_when_mpi_overrides_path(tmp_path: Path) -> None:
    script = (ROOT / "scripts/run-openfoam.sh").read_text()
    old_bin = tmp_path / "old-bin"
    old_bin.mkdir()
    old_python = old_bin / "python3"
    old_python.write_text("#!/bin/bash\necho old-system-python >&2\nexit 91\n")
    old_python.chmod(0o755)
    mpi = tmp_path / "mpirun"
    mpi.write_text(f'#!/bin/bash\nexport PATH="{old_bin}:/usr/bin:/bin"\nexec "$@"\n')
    mpi.chmod(0o755)
    probe = tmp_path / "capture-hardware"
    probe.write_bytes((ROOT / "experiment-metrics/src/experiment_metrics/probes/capture_hardware.py").read_bytes())
    probe.chmod(0o755)
    assert subprocess.run([mpi, probe, "--help"], capture_output=True).returncode == 91
    minimal = next(line for line in script.splitlines() if line.startswith("minimal_hardware_argv=("))
    profile = next(line for line in script.splitlines() if line.lstrip().startswith("stage profile_hardware_capture "))
    prefix = 'set -euo pipefail\nnode_launch=("${MPI}")\nRANK_PYTHON_LAUNCH=(/usr/bin/env "${RANK_PYTHON}")\nstage() { shift 2; "$@" --help; }\n'
    environment = {**os.environ, "MPI": str(mpi), "RANK_PYTHON": sys.executable, "CAPTURE_HARDWARE": str(probe), "RUN_ID": "test", "RUN_DIR": str(tmp_path), "RUN_MANIFEST": str(tmp_path / "manifest.json"), "SOURCE_DIR": str(tmp_path), "LOG_DIR": str(tmp_path), "global_rank_env": "PMI_RANK"}
    for command in [minimal + '\n"${node_launch[@]}" "${minimal_hardware_argv[@]}" --help', profile]:
        result = subprocess.run(["bash", "-c", prefix + command], env=environment, capture_output=True, text=True, check=True)
        assert "usage: capture-hardware" in result.stdout
        assert "old-system-python" not in result.stderr


def test_hardware_capture_diagnostic_logs_are_archived() -> None:
    for cluster in ("genkai", "gadi", "aspire2a"):
        workflow = (ROOT / f".github/workflows/{cluster}.yml").read_text()
        assert "logs/minimal-hardware-capture.log:postrun_source" in workflow
        assert "logs/profile-hardware-capture.log:postrun_source" in workflow
        assert "logs/rank-placement.log:postrun_source" in workflow


def test_genkai_uploads_metrics_from_login_runner_after_the_job() -> None:
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")

    assert "submit-run" in workflow
    assert workflow.index('cd "${RUN_DIR}"') < workflow.index("submit-run")
    assert '--manifest "${RUN_MANIFEST}"' in workflow
    assert "--pjm-script-repository-path platforms/genkai/run-openfoam.pjm" in workflow
    assert "record-scheduler-terminal --manifest" in workflow
    assert "record-execution-context --manifest" in workflow
    assert "record-profile-vtune" not in workflow
    assert "VTuneホットスポットをActionsの概要へ掲載" in workflow
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
    assert '--profile-condition "${PROVISION_DIR}/benchmark/profile.json"' in workflow
    assert "memory-access-core" in (ROOT / "scripts/exec-profiler.sh").read_text(encoding="utf-8")
    assert "openfoam-profile-vtune-hotspots-v1.json" in workflow
    assert "profile_mode" not in workflow
    assert "perf-stat" not in workflow
    assert "Perfetto" not in workflow
    assert "Merge terminal fragments" not in workflow
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_BASE64" not in workflow
    assert "record-pstream --manifest" not in workflow
    assert "Publish v2 raw facts to BigQuery" not in workflow
    assert "/tmp/openfoam-bigquery-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" in workflow
    assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE" in workflow
    assert 'smoke-send --run "${RUN_ID}" --source runner' in workflow
    assert "OpenFOAMケースのキャッシュを準備" in workflow
    prepare_concurrency = "genkai-openfoam-case-${{ needs.select-build.outputs.experiment_preset }}-${{ needs.select-build.outputs.prepare_script_sha256 }}-${{ needs.select-build.outputs.build_cache_key }}"
    assert prepare_concurrency in workflow
    assert "group: genkai-openfoam-build\n" not in workflow
    assert workflow.count("concurrency:") == 1
    assert "build_cache_key: ${{ steps.select.outputs.build_cache_key }}" in workflow
    assert "queue: max" not in workflow
    assert "queue: single" not in workflow
    assert "${GITHUB_RUN_ID}.tar.zst" in workflow
    assert "${GITHUB_RUN_NUMBER}.tar.zst" not in workflow
    assert workflow.count("- name: 計測記録を初期化してOpenFOAMを投入") == 1
    assert workflow.count("- name: 計測記録を確定して成果物を梱包") == 1
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


def test_genkai_wait_reconnects_in_bounded_slices() -> None:
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    wait_script = (ROOT / "platforms/genkai/wait-openfoam-job.sh").read_text(encoding="utf-8")

    assert 'shell: bash\n        run: |\n          while true; do\n            if /opt/actions-runner-shells/genkai-shell --github-shell' in workflow
    assert 'timeout --foreground 45s pjwait -z "${PJM_JOB_ID}"' in wait_script
    assert 'exit 75' in wait_script
    assert '[[ ! -e "${RUN_DIR}/run-success" ]]' in wait_script


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
    builder_path = ROOT / "scripts/build-openfoam.sh"
    builder = builder_path.read_text(encoding="utf-8") + (ROOT / "platforms/gadi/build-environment.sh").read_text(encoding="utf-8")
    entry = (ROOT / ".github/workflows/openfoam.yml").read_text(encoding="utf-8")

    assert "runs-on: [self-hosted, home-lab]" in workflow
    assert "shell: gadi-shell --github-shell {0}" in workflow
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
    assert workflow.index('cd "${RUN_DIR}"') < workflow.index("submit-pbs-run")
    assert "record-pbs-terminal" in workflow
    assert (
        "/tmp/openfoam-build/run-${{ github.run_id }}-${{ github.run_attempt }}"
        in workflow
    )
    assert 'scripts/build-openfoam.sh" gadi' in workflow
    assert "build_cache_key: ${{ steps.select.outputs.build_cache_key }}" in workflow
    assert (
        "gadi-openfoam-case-${{ needs.select-build.outputs.ranks }}-${{ needs.select-build.outputs.prepare_script_sha256 }}-${{ needs.select-build.outputs.build_cache_key }}"
        in workflow
    )
    assert "group: gadi-openfoam-build\n" not in workflow
    assert workflow.count("concurrency:") == 1
    assert 'source_archive_run_dir="${SOURCE_ARCHIVE_DIR}/run-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"' in workflow
    assert 'rm -rf -- "${SOURCE_ARCHIVE_RUN_DIR:?}"' in workflow
    assert "openfoam_build" not in workflow
    assert workflow.count("- name: 計測記録を初期化してOpenFOAMを投入") == 1
    assert workflow.count("- name: 計測記録を確定して成果物を梱包") == 1
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
    assert '"${PROVISION_DIR}/compute-tools.tar.zst"' in wrapper
    assert 'uv sync --project "${provision_dir}/experiment-metrics" --frozen --no-dev --no-editable' in workflow
    assert '--compute-tools-root "${runtime_root}"' in wrapper
    assert 'RANK_PYTHON="${compute_tools_root}/experiment-metrics/.venv/bin/python"' in runner
    assert 'profile-wrapper "${compute_tools_root}/scripts/exec-profiler.sh"' in runner
    assert 'case_dir="${PBS_JOBFS}/openfoam-case/occDrivAerStaticMesh"' in wrapper
    assert (
        'case_archive_root="/scratch/hb15/${USER}/openfoam/gadi/case-archives"'
        in wrapper
    )
    assert '"${archive_dir}/case.tar.zst"' in (
        ROOT / "platforms/gadi/stage-openfoam-case.sh"
    ).read_text(encoding="utf-8")
    assert "common.tar.zst" not in (
        ROOT / "platforms/gadi/archive-openfoam-case.sh"
    ).read_text(encoding="utf-8")
    assert "node-NNN.tar.zst" not in (
        ROOT / "platforms/gadi/archive-openfoam-case.sh"
    ).read_text(encoding="utf-8")
    assert "PREPARE_NODES" not in workflow
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
    assert 'decomposition_method=scotch' in runner
    assert "jobfs=100GB" in workflow
    assert '"${PROVISION_DIR}/platforms/gadi/wait-pbs-job.sh" "${job_id}"' in workflow
    assert "uses: ./.github/workflows/gadi.yml" in entry
    assert "contains(github.event.head_commit.message, '[cluster:genkai]')" in entry
    assert "contains(github.event.head_commit.message, '[cluster:gadi]')" in entry
    assert "contains(github.event.head_commit.message, '[cluster:aspire2a]')" in entry
    assert "inputs.run_genkai" in entry
    assert "inputs.run_gadi" in entry
    assert "inputs.run_aspire2a" in entry
    assert entry.count("contains(github.event.head_commit.message, '[nodes:4]')") == 3
    assert entry.count("contains(github.event.head_commit.message, '[nodes:2]')") == 3
    assert (
        entry.count("github.event_name == 'workflow_dispatch' && inputs.node_count")
        == 3
    )
    assert "select-target" not in entry
    assert "select-actions-target.sh" not in entry


def test_aspire2a_uses_cray_pbs_and_separate_storage() -> None:
    workflow = (ROOT / ".github/workflows/aspire2a.yml").read_text(encoding="utf-8")
    wrapper = (ROOT / "platforms/aspire2a/run-openfoam.pbs").read_text(encoding="utf-8")
    numa_wrapper = (ROOT / "platforms/aspire2a/exec-local-numa.sh").read_text(encoding="utf-8")
    keeper = (ROOT / "platforms/aspire2a/keep-rank-affinity.sh").read_text(encoding="utf-8")
    runner = (ROOT / "scripts/run-openfoam.sh").read_text(encoding="utf-8")
    entry = (ROOT / ".github/workflows/openfoam.yml").read_text(encoding="utf-8")

    assert "shell: aspire2a-shell --github-shell {0}" in workflow
    assert "/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a" in workflow
    assert "platforms/aspire2a/build-openfoam.pbs" in workflow
    assert 'qsub -v "${exported}"' in workflow
    assert 'scripts/build-openfoam.sh" aspire2a' not in workflow
    assert "submit-pbs-run" in workflow
    assert "qsub -P 59000014 -q normal" in workflow
    assert 'platforms/aspire2a/wait-pbs-job.sh" "${job_id}"' in workflow
    assert 'accounting=$(aspire2a-shell qstat -fx "${PBS_JOB_ID}")' in workflow
    assert 'aspire2a-shell test -e "${RUN_DIR}/run-success"' in workflow
    assert "select=1:ncpus=4:mpiprocs=1:mem=120gb" in workflow
    assert "openfoam-profile-uprof-hotspots-v1.json" in workflow
    assert "openfoam-profile-craypat-mpi-v1.json" in workflow
    assert "openfoam-profile-mpi-timing-v1.json" in workflow
    assert "provision-uprof.sh" in workflow
    assert "AMDuProf_Linux_x64_5.3.521.tar.bz2" in workflow
    assert "platforms/aspire2a/exec-uprof.sh" in workflow
    assert "platforms/aspire2a/exec-uprof-target.c" in workflow
    assert "scripts/archive-paraview-case.sh" not in workflow
    assert "scripts/finalize-paraview-case.sh" not in workflow
    assert "--paraview-collector" not in wrapper
    assert "--large-output-dir" not in wrapper
    assert 'if [[ "${OPENFOAM_RUN_PURPOSE}" == profile && "${OPENFOAM_PROFILE_TOOL}" == vtune ]]; then' in runner
    assert '[[ "${large_output_dir}" == /* ]]' in runner
    assert '--profile-tool "${profile_tool}"' in workflow
    assert 'module load perftools-preload' in wrapper
    assert 'uprof_bin_dir="${AMDUPROF_ROOT}/bin"' in runner
    assert 'OPENFOAM_UPROF_PATH="${uprof_bin_dir}/AMDuProfCLI-bin"' in runner
    assert 'LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" "${METRICS_CLI}" "${provision_args[@]}"' in runner
    assert 'printf \'%s\\0\' "${SIMPLE_FOAM}" -parallel -fileHandler uncollated "${openfoam_args[@]}" > "${uprof_target_argv_file}"' in runner
    assert '"${solver_launch[@]}" /usr/bin/bash "${compute_tools_root}/platforms/aspire2a/exec-uprof.sh" "${OPENFOAM_UPROF_PATH}" "${uprof_root}/sessions"' in runner
    assert '"${compute_tools_root}/platforms/aspire2a/exec-uprof-target" "${uprof_target_argv_file}"' in runner
    uprof_launcher = (ROOT / "platforms/aspire2a/exec-uprof.sh").read_text(
        encoding="utf-8"
    )
    assert 'exec "${uprof_cli}" collect --config hotspots -g --output-dir' in uprof_launcher
    assert '--output-dir "${rank_session_root}"' in uprof_launcher
    assert "PMI_LOCAL_RANK % profile_rank_stride" in uprof_launcher
    assert "eval" not in uprof_launcher
    uprof_exporter = (ROOT / "platforms/aspire2a/export-uprof.sh").read_text(
        encoding="utf-8"
    )
    assert "report_parallelism=4" in uprof_exporter
    assert 'report_args=(report --input-dir "${session}" --host "${host}" --detail --cutoff 30)' in uprof_exporter
    uprof_target_launcher = (ROOT / "platforms/aspire2a/exec-uprof-target.c").read_text(encoding="utf-8")
    assert "getdelim(&argument, &argument_capacity, '\\0', input)" in uprof_target_launcher
    assert "execv(target_argv[0], target_argv)" in uprof_target_launcher
    assert "eval" not in uprof_target_launcher
    assert 'if [[ "${OPENFOAM_PROFILE_TOOL}" == uprof ]]; then' in runner
    assert '"${compute_tools_root}/platforms/aspire2a/export-uprof.sh"' not in runner
    assert "AMD uProf reportをlogin nodeで生成" in workflow
    assert '"${PROVISION_DIR}/platforms/aspire2a/export-uprof.sh"' in workflow
    assert "--uprof-rank-stride 16" in workflow
    assert 'results/uprof-summary.json' in workflow
    assert 'results/uprof-summary.md' in workflow
    assert 'platforms/aspire2a/export-craypat.sh' in workflow
    assert '"${RUN_DIR}/profile/raw/craypat" "${PROVISION_DIR}/runtime.tar.zst" "${PROVISION_DIR}/control/build-sidecar.json"' in workflow
    craypat_exporter = (ROOT / "platforms/aspire2a/export-craypat.sh").read_text(encoding="utf-8")
    assert 'tar -I zstd -xf "${build_archive}" -C "${output_root}" "./${simplefoam_relative}"' in craypat_exporter
    assert '"${pat_report}" -i "${report_binary}"' in craypat_exporter
    assert 'stage solver "${SOLVER_LOG}" "${ENV}" PAT_RT_EXPDIR_BASE="${craypat_root}"' in runner
    assert 'stage solver "${SOLVER_LOG}" "${solver_launch[@]}" /usr/bin/bash "${compute_tools_root}/platforms/aspire2a/exec-mpi-temporal-profile.sh"' in runner
    assert '[[ "${#mpi_timing_files[@]}" -eq "${OPENFOAM_MPI_PROCS}" ]]' in runner
    assert '[[ "${#mpi_timing_stack_files[@]}" -eq "${OPENFOAM_MPI_PROCS}" ]]' in runner
    assert '[[ "${#mpi_timing_request_files[@]}" -eq "${OPENFOAM_MPI_PROCS}" ]]' in runner
    assert 'platforms/aspire2a/mpi-temporal-profile.c' in workflow
    assert 'mpi_timing) ;;' in wrapper
    assert "stage_at() {" in runner
    assert 'profile/uprof-summary' not in workflow
    assert "scripts/exec-profiler.sh" not in workflow
    assert "scripts/allow-vtune-attach.py" not in workflow
    assert "scripts/export-vtune-hotspots.sh" not in workflow
    assert 'source "${PROVISION_DIR}/platforms/aspire2a/toolchain.conf"' in wrapper
    assert 'aspire2a_load_toolchain "${aspire2a_toolchain}"' in wrapper
    assert 'WM_COMPILER="${aspire2a_wm_compiler}"' in wrapper
    assert 'WM_MPLIB="${aspire2a_wm_mplib}"' in wrapper
    assert '/usr/bin/bash "${PROVISION_DIR}/platforms/aspire2a/stage-openfoam-runtime.sh"' in wrapper
    assert '/usr/bin/bash "${PROVISION_DIR}/platforms/aspire2a/stage-openfoam-case.sh"' in wrapper
    assert '/usr/bin/bash "${PROVISION_DIR}/platforms/aspire2a/stage-rank-context.sh"' in wrapper
    assert "--global-rank-env PMI_RANK" in wrapper
    assert "--local-rank-env PMI_LOCAL_RANK" in wrapper
    assert "--local-size-env PMI_LOCAL_SIZE" in wrapper
    assert '--imb-bin "${imb_bin}"' in wrapper
    assert "cpu_bind_list=" not in wrapper
    assert "--solver-launch-arg --cpu-bind" in wrapper
    assert "--solver-launch-arg depth" in wrapper
    assert "--solver-launch-arg -d" in wrapper
    assert "LD_PRELOAD" not in wrapper
    assert '--solver-launch-arg 1 --solver-launch-arg /usr/bin/bash --solver-launch-arg "${PROVISION_DIR}/platforms/aspire2a/exec-local-numa.sh"' in wrapper
    assert '-ppn 1 --cpu-bind none /usr/bin/bash "${PROVISION_DIR}/platforms/aspire2a/keep-rank-affinity.sh" &' in wrapper
    assert 'kill "${keeper_pid}"' in wrapper
    assert "--multi-level-domains 4,2,4,16" in wrapper
    assert "decomposition-1n.txt" in wrapper
    assert "decomposition-2n.txt" in wrapper
    assert "decomposition-4n.txt" in wrapper
    assert 'experiment_preset="aspire2a-${decomposition}-1n-128r"' in workflow
    assert 'experiment_preset="aspire2a-${decomposition}-2n-256r"' in workflow
    assert 'experiment_preset="aspire2a-${decomposition}-4n-512r"' in workflow
    assert 'platforms/aspire2a/decomposition-1n.txt' in workflow
    assert 'platforms/aspire2a/decomposition-2n.txt' in workflow
    assert 'platforms/aspire2a/decomposition-4n.txt' in workflow
    assert '*-multilevel-*) decomposition_method=multiLevel' in runner
    assert '*-kahip-*) decomposition_method=kahip' in runner
    assert '*-metis-*) decomposition_method=metis' in runner
    assert '*-ptscotch-*) decomposition_method=ptscotch' in runner
    assert "--bind-rank-placement" in wrapper
    assert "platforms/aspire2a/exec-local-numa.sh" in workflow
    assert "platforms/aspire2a/keep-rank-affinity.sh" in workflow
    assert "mpi-rank-affinity" not in workflow
    assert "experiment-metrics/src/experiment_metrics/rank_wrapper.py" in workflow
    assert "experiment-metrics/src/experiment_metrics/pbs_scheduler.py" in workflow
    assert "experiment-metrics/src/experiment_metrics/imb.py" in workflow
    assert "platforms/aspire2a/bind-local-rank.sh" not in workflow
    assert 'exec numactl --membind="$(( PMI_LOCAL_RANK / 16 ))" "$@"' in numa_wrapper
    assert 'pgrep -u "${user}" -x simpleFoam' in keeper
    assert 'taskset -pc "${local_rank_of[${pid}]}" "${pid}"' in keeper
    assert "trap " in keeper
    assert "--bind-local-rank" in runner
    assert "--solver-launch-arg --depth" not in wrapper
    assert 'aspire2a_check_mpi_link "${RUN_DIR}/logs/imb-mpi1-ldd.log"' in wrapper
    assert 'aspire2a_check_mpi_link "${RUN_DIR}/logs/aocl-runtime-link.log"' in wrapper
    assert 'if [[ "${aspire2a_mpi_transport}" == ofi ]]; then export FI_OFI_RXM_USE_SRX=0; fi' in wrapper
    assert "grep -q '/oneapi/'" in wrapper
    assert "uses: ./.github/workflows/aspire2a.yml" in entry
    assert "contains(github.event.head_commit.message, '[cluster:aspire2a]')" in entry
    assert "group: aspire2a-openfoam-build\n" not in workflow
    assert workflow.count("concurrency:") == 1
    assert 'source_archive_run_dir="${SOURCE_ARCHIVE_DIR}/run-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"' in workflow
    assert 'rm -rf -- "${SOURCE_ARCHIVE_RUN_DIR:?}"' in workflow


def test_aspire2a_toolchains_use_cray_mpich_and_aocl() -> None:
    toolchain = (ROOT / "platforms/aspire2a/toolchain.sh").read_text(encoding="utf-8")
    selection = (ROOT / "platforms/aspire2a/toolchain.conf").read_text(encoding="utf-8")
    build = (ROOT / "platforms/aspire2a/build-environment.sh").read_text(encoding="utf-8")
    shared_build = (ROOT / "scripts/build-openfoam.sh").read_text(encoding="utf-8")
    runtime = (ROOT / "platforms/aspire2a/run-openfoam.pbs").read_text(encoding="utf-8")
    assert "aspire2a_toolchain=gnu" in selection
    assert "aspire2a_network_module=craype-network-ofi" in selection
    assert "aspire2a_mpi_module=cray-mpich/8.1.15" in selection
    assert "PrgEnv-gnu/8.3.3 craype-x86-milan aocl/4.0.0-gcc11.2" in toolchain
    assert "aocc/5.0 PrgEnv-aocc/8.3.3 craype-x86-milan aocl/5.1.0-aocc5.0" in toolchain
    assert "aspire2a_cc=gcc" in toolchain
    assert "aspire2a_cxx=g++" in toolchain
    assert "aspire2a_cc=clang" in toolchain
    assert "aspire2a_cxx=clang++" in toolchain
    assert "aspire2a_wm_mplib=CRAY-MPICH" in toolchain
    assert "aspire2a_mpi_launcher=mpiexec" in toolchain
    assert 'module swap craype-network-ofi "${aspire2a_network_module' in toolchain
    assert 'module swap cray-mpich "${aspire2a_mpi_module' in toolchain
    assert "aspire2a_mpi_transport=${CRAYPE_NETWORK_TARGET:" in toolchain
    assert 'test "${aspire2a_network_module}" = "craype-network-${aspire2a_mpi_transport}"' in toolchain
    assert 'grep -Fq "${aspire2a_mpi_library_root}/libmpi_" "${listing}"' in toolchain
    assert "for ucx_library in libucp.so libucs.so libuct.so" in toolchain
    assert "grep -q 'libfabric[.]so' \"${listing}\"" in toolchain
    assert "intel" not in toolchain.lower()
    assert "mkl" not in toolchain.lower()
    assert "AOCL_MODULE=" in build
    assert "AOCL_LIBM=${aspire2a_aocl_libm}" in build
    assert "AOCL_LIBMEM=${aspire2a_aocl_libmem}" in build
    assert 'build_extra_ldflags="-Wl,--no-as-needed -L${AOCL_ROOT}/lib -lalm"' in build
    assert '-lalm -Wl,--as-needed' not in build
    assert '--compile-flag "FOAM_EXTRA_LDFLAGS=${FOAM_EXTRA_LDFLAGS}"' in shared_build
    assert 'LD_PRELOAD="${aspire2a_aocl_libmem}" ldd "$(command -v simpleFoam)"' not in runtime
    assert "LD_PRELOAD" not in runtime
    assert 'grep -Fq "${aspire2a_aocl_libm}" "${RUN_DIR}/logs/aocl-runtime-link.log"' in runtime
    assert 'if grep -Fq "${aspire2a_aocl_libmem}" "${RUN_DIR}/logs/aocl-runtime-link.log"' in runtime
    assert "CRAYPE_NETWORK_MODULE=${aspire2a_network_module}" in build
    assert "MPI_TRANSPORT=${aspire2a_mpi_transport}" in build
    assert '--compile-flag "${aspire2a_transport_version}"' in build
    assert 'aspire2a_check_mpi_link "${BUILD_DIR}/logs/simplefoam-ldd.log"' in build
    assert 'aspire2a_check_mpi_link "${BUILD_DIR}/logs/imb-mpi1-ldd.log"' in build
    assert "IMB_SOURCE_OID=${IMB_SOURCE_OID}" in build
    assert 'make -C "${build_tree}/IMB" CC=cc CXX=CC IMB-MPI1' in build
    assert 'grep -Fq "${FOAM_LIBBIN}/libscotchDecomp.so"' in build
    assert 'ldd -r "${FOAM_LIBBIN}/libfieldFunctionObjects.so"' in build
    assert 'install -m 0755 "${build_tree}/IMB/IMB-MPI1" "${FOAM_APPBIN}/IMB-MPI1"' in build
    assert "module load git/2.39.2" in build
    assert 'ofi) aspire2a_transport_version="LIBFABRIC_VERSION=$(fi_info --version' in toolchain
    assert "build_use_ccache=true" in build
    assert 'build_ccache_namespace="aspire2a-${aspire2a_toolchain}-${aspire2a_mpi_transport}"' in build
    assert 'CCACHE_REMOTE_STORAGE="file:/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/build-cache/ccache/${aspire2a_toolchain}/${aspire2a_mpi_transport}"' in build
    assert '--compile-flag "CCACHE_VERSION=${aspire2a_ccache_version}"' in build
    assert '--compile-flag "CCACHE_NAMESPACE=${build_ccache_namespace}"' in build
    assert '--compile-flag "CCACHE_REMOTE_STORAGE=${CCACHE_REMOTE_STORAGE}"' in build
    assert 'ccache-${USER:?}-${build_ccache_namespace}' in shared_build


def test_cluster_steps_use_home_lab_remote_shells() -> None:
    for cluster in ("genkai", "gadi", "aspire2a"):
        workflow = (ROOT / f".github/workflows/{cluster}.yml").read_text(
            encoding="utf-8"
        )
        assert f"shell: {cluster}-shell --github-shell {{0}}" in workflow
        assert f"runs-on: [self-hosted, {cluster}]" not in workflow
        assert "runs-on: [self-hosted, home-lab]" in workflow


def test_bigquery_credentials_stay_in_login_runner_steps() -> None:
    for cluster in ("genkai", "gadi", "aspire2a"):
        workflow = (ROOT / f".github/workflows/{cluster}.yml").read_text(
            encoding="utf-8"
        )
        temporary = (
            'mktemp "/tmp/openfoam-bigquery-${GITHUB_RUN_ID}-'
            '${GITHUB_RUN_ATTEMPT}.XXXXXXXX.json"'
        )
        assert workflow.count(temporary) == 2
        assert workflow.count("METRICS_CREDENTIAL_JSON: ${{ secrets.EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_JSON }}") == 2
        assert "bigquery-credential.json" not in workflow
        assert "EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE=%s" not in workflow


def test_workflow_dispatch_exposes_only_inputs_owned_by_each_entry_workflow() -> None:
    entry = (ROOT / ".github/workflows/openfoam.yml").read_text(encoding="utf-8")
    genkai = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    gadi = (ROOT / ".github/workflows/gadi.yml").read_text(encoding="utf-8")
    aspire2a = (ROOT / ".github/workflows/aspire2a.yml").read_text(encoding="utf-8")

    entry_inputs = entry.split("permissions:", 1)[0]
    assert "run_genkai:" in entry_inputs
    assert "run_gadi:" in entry_inputs
    assert "run_aspire2a:" in entry_inputs
    assert "node_count:" in entry_inputs
    assert "require_build:" not in entry_inputs
    assert "reshare_ccache:" not in entry_inputs
    assert "run_purpose:" not in entry_inputs
    assert "profile:" in entry_inputs
    assert "profile_rank:" not in entry_inputs
    assert "profile_analysis:" not in entry_inputs
    profile_push_gate = "github.event_name == 'push' && contains(github.event.head_commit.message, '[profile]')"
    assert entry.count(profile_push_gate) == 3
    assert not (ROOT / ".github/workflows/genkai-profile.yml").exists()

    assert "require_build:" not in genkai
    assert "reshare_ccache:" not in genkai
    assert "run_purpose:" not in genkai
    assert "require_build:" not in gadi
    assert "run_purpose:" not in gadi
    for workflow in (genkai, gadi, aspire2a):
        assert "profile:" in workflow
        assert "profile_rank:" not in workflow
        assert "profile_analysis:" not in workflow
        assert "--profile-rank" not in workflow
        assert "--profile-analysis" not in workflow
        assert '--profile-condition "${PROVISION_DIR}/benchmark/profile.json"' in workflow
        assert 'select(.schema_version == "build-sidecar/v1" and .build_archive.path == "build.tar.zst")' in workflow
        assert "find \"${BUILD_ARCHIVE_DIR}\" -maxdepth 1 -type f -name '*.build-sidecar.json'" in workflow
        assert "LC_ALL=C sort -rn" in workflow
        assert "git diff --quiet" not in workflow
        assert "git cat-file" not in workflow
        assert "commit_role" not in workflow
        assert "scripts/build-inputs-match.sh" in workflow
    for workflow in (genkai, gadi, aspire2a):
        assert 'gh run list --workflow openfoam.yml --commit "${commit}" --limit 1000' not in workflow
    push_gate = 'if [[ "${GITHUB_EVENT_NAME}" == push ]]; then\n            commit_message="$(git log -1 --format=%B "${GITHUB_SHA}")"'
    assert push_gate in genkai
    assert push_gate in gadi
    assert push_gate in aspire2a


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
        assert "OPENFOAM_ARTIFACT_ARCHIVE_ROOT: /hdd_raid/samba/net_share/openfoam-artifacts" in workflow
        assert f'"${{OPENFOAM_ARTIFACT_ARCHIVE_ROOT}}/${{GITHUB_RUN_ID}}/{cluster}"' in workflow
        assert "runs-on: [self-hosted, home-lab]" in workflow
        assert "tailscale/github-action" not in workflow
        assert "ARTIFACT_SERVER_SSH_PRIVATE_KEY" not in workflow
        assert "tomokazu@tomokazu-ubuntu-server" not in workflow
        assert "profile_run_id: ${{ steps.v2_context.outputs.profile_run_id }}" in workflow
        assert "run_dir: ${{ steps.v2_context.outputs.run_dir }}" in workflow
        assert "- name: VTuneの完全結果をrun単位で直接転送" in workflow
        assert "archive-paraview-case.sh" not in workflow
        assert "finalize-paraview-case.sh" not in workflow
        assert "if: inputs.profile && needs.run.result == 'success'" in workflow
        assert f"--cluster {cluster} --github-run-id" in workflow
        assert "--profile-run-id" in workflow
        assert "--source-dir" in workflow
        assert 'scripts/transfer-vtune-result.sh' in workflow
        assert 'scripts/remove-openfoam-runtime.sh' in workflow
        assert f'--connection {cluster}-shell' in workflow
        assert "if [[ '${{ inputs.profile }}' == true ]]; then" in workflow
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
        assert workflow.index("- name: OpenFOAMジョブの終了を待機") < workflow.index(
            "- name: 計測記録を確定して成果物を梱包"
        )
        assert workflow.index(
            "- name: 計測記録を確定して成果物を梱包"
        ) < workflow.index(
            'send-fragments --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}"'
        )
        assert workflow.index(
            'send-fragments --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}"'
        ) < workflow.index("- name: 固定構成のv2成果物を保存")


def test_partition_audit_uses_json_writer_for_std_string_digest() -> None:
    source = (
        ROOT / "experiment-metrics/native/partition-audit/partition-audit.C"
    ).read_text(encoding="utf-8")

    assert "writeJsonString(output, locator.sha256);" in source
    assert '<< locator.sha256 << "\\"}"' not in source


def test_builder_uses_the_pinned_unmodified_v2512_sources() -> None:
    script = (ROOT / "scripts/build-openfoam.sh").read_text(encoding="utf-8") + (ROOT / "platforms/genkai/build-environment.sh").read_text(encoding="utf-8")

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
    assert "build_compile_control=+ccache" in script
    assert 'WM_COMPILE_CONTROL="${build_compile_control}"' in script
    assert "CMAKE_CXX_COMPILER_LAUNCHER=ccache" in script
    assert "CCACHE_RECACHE" not in script
    assert "${GITHUB_RUN_ID}.tar.zst" in script
    assert "${GITHUB_RUN_NUMBER}.tar.zst" not in script
    assert "build_parallelism=120" in script


def test_ruff_does_not_enforce_code_width() -> None:
    config = (ROOT / "experiment-metrics/pyproject.toml").read_text(encoding="utf-8")
    assert "line-length" not in config
    assert 'ignore = ["E501"]' in config
