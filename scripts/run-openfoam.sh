#!/usr/bin/env bash

# Scheduler-neutral compute-side executor. Cluster wrappers establish the
# toolchain and MPI environment and pass launcher argv without shell parsing.
set -euo pipefail

solver_launch=()
node_launch=()
job_id=
case_cache_root=
global_rank_env=
local_rank_env=
local_size_env=
profile_root=
while [[ $# -gt 0 ]]
do
  case "$1" in
    --solver-launch-arg) [[ $# -ge 2 ]]; solver_launch+=("$2"); shift 2 ;;
    --node-launch-arg) [[ $# -ge 2 ]]; node_launch+=("$2"); shift 2 ;;
    --job-id) [[ $# -ge 2 ]]; job_id=$2; shift 2 ;;
    --case-cache-root) [[ $# -ge 2 ]]; case_cache_root=$2; shift 2 ;;
    --global-rank-env) [[ $# -ge 2 ]]; global_rank_env=$2; shift 2 ;;
    --local-rank-env) [[ $# -ge 2 ]]; local_rank_env=$2; shift 2 ;;
    --local-size-env) [[ $# -ge 2 ]]; local_size_env=$2; shift 2 ;;
    --profile-root) [[ $# -ge 2 ]]; profile_root=$2; shift 2 ;;
    *) printf 'unknown run-openfoam argument: %s\n' "$1" >&2; exit 64 ;;
  esac
done
[[ "${job_id}" =~ ^[0-9]+([.][A-Za-z0-9.-]+)?$ ]]
[[ "${#solver_launch[@]}" -gt 0 && "${solver_launch[0]}" == /* ]]
[[ "${#node_launch[@]}" -gt 0 && "${node_launch[0]}" == /* ]]
[[ "${case_cache_root}" == /* && "${profile_root}" == /* ]]
for rank_env in "${global_rank_env}" "${local_rank_env}" "${local_size_env}"
do
  [[ "${rank_env}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]
done

: "${RUN_ID:?runner-generated v2 run ID is required}"
: "${RUN_MANIFEST:?runner-generated manifest path is required}"
: "${RUN_DIR:?runner-generated runtime path is required}"
: "${PROVISION_DIR:?provision directory is required}"
: "${OPENFOAM_NODES:?protocol node count is required}"
: "${OPENFOAM_MPI_PROCS:?protocol rank count is required}"
: "${OPENFOAM_RESOURCE_GROUP:?protocol resource group is required}"
: "${OPENFOAM_TRANSPORT_POLICY:?protocol transport policy is required}"
: "${OPENFOAM_PROTOCOL_PATH:?effective protocol path is required}"
: "${OPENFOAM_ITERATIONS:?protocol iteration target is required}"
: "${OPENFOAM_EXPECTED_CELLS:?workload cell count is required}"
: "${OPENFOAM_DISTRIBUTION:?OpenFOAM distribution is required}"
: "${OPENFOAM_RELEASE:?OpenFOAM release is required}"
: "${OPENFOAM_SOLVER:?solver identity is required}"
: "${OPENFOAM_WORKLOAD_ID:?workload identity is required}"
: "${WORKLOAD_MESH_ARCHIVE:?verified mesh archive is required}"
[[ "${OPENFOAM_SOLVER}" == simpleFoam && "${OPENFOAM_DISTRIBUTION}" == OpenFOAM.com && "${OPENFOAM_RELEASE}" == v2512 && "${OPENFOAM_WORKLOAD_ID}" == occDrivAerStaticMesh-65M ]]

OPENFOAM_RUN_PURPOSE=${OPENFOAM_RUN_PURPOSE:-bench}
: "${OPENFOAM_VTUNE_RANK:?scheduler-selected VTune rank is required}"
: "${OPENFOAM_VTUNE_ANALYSIS:?scheduler-selected VTune analysis is required}"
case "${OPENFOAM_VTUNE_ANALYSIS}" in
  hotspots|hpc-performance|memory-access) ;;
  *) printf 'Unsupported VTune analysis: %s\n' "${OPENFOAM_VTUNE_ANALYSIS}" >&2; exit 2 ;;
esac
PROTOCOL_NAME=$(basename "${OPENFOAM_PROTOCOL_PATH}" .toml)
case "${OPENFOAM_RUN_PURPOSE}" in
  bench|profile) ;;
  *) printf 'Unsupported OPENFOAM_RUN_PURPOSE: %s\n' "${OPENFOAM_RUN_PURPOSE}" >&2; exit 2 ;;
esac
(( OPENFOAM_NODES > 0 && OPENFOAM_MPI_PROCS > 0 ))
(( OPENFOAM_MPI_PROCS % OPENFOAM_NODES == 0 ))

CASE_DIR="${RUN_DIR}/work/occDrivAerStaticMesh"
CASE_INPUT_DIR="${RUN_DIR}/work/occDrivAerStaticMesh-input"
LOG_DIR="${RUN_DIR}/logs"
SOURCE_DIR="${RUN_DIR}/source"
RESULTS_DIR="${RUN_DIR}/results"
REGISTRY="${PROVISION_DIR}/experiment-metrics/registry/openfoam-v2.toml"
METRICS_CLI="${PROVISION_DIR}/experiment-metrics/.venv/bin/experiment-metrics"

DECOMPOSE_PAR_DICT=system/decomposeParDict
SOLVER_LOG="${LOG_DIR}/solver.log"
SUPERVISOR_STATE="${RUN_DIR}/domain/supervisor-state.json"
profile_run_id="${RUN_ID}-${job_id}"
vtune_root="${profile_root}/${profile_run_id}"
OPENFOAM_VTUNE_RESULT_DIR="${vtune_root}/rank-${OPENFOAM_VTUNE_RANK}-${OPENFOAM_VTUNE_ANALYSIS}"
OPENFOAM_VTUNE_STATUS_PATH="${RUN_DIR}/profile/raw/vtune-summary/collection-status.json"
export OPENFOAM_VTUNE_RESULT_DIR OPENFOAM_VTUNE_STATUS_PATH
test "$(basename -- "${RUN_DIR}")" = "${RUN_ID}"
install -d -m 0755 "${CASE_DIR%/*}" "${LOG_DIR}" "${SOURCE_DIR}" "${RESULTS_DIR}" "${RUN_DIR}/domain"
"${METRICS_CLI}" supervisor-start --manifest "${RUN_MANIFEST}" --state "${SUPERVISOR_STATE}" --job-id "${job_id}"
finish_supervisor() {
  local original_status=$?
  local finish_status=0
  trap - EXIT
  set +e
  "${METRICS_CLI}" supervisor-finish --manifest "${RUN_MANIFEST}" --state "${SUPERVISOR_STATE}" --exit-code "${original_status}"
  finish_status=$?
  if [[ "${original_status}" -eq 0 && "${finish_status}" -ne 0 ]]; then
    original_status=${finish_status}
  fi
  exit "${original_status}"
}
trap finish_supervisor EXIT
"${METRICS_CLI}" validate-bundle-runtime --manifest "${RUN_MANIFEST}" --bundle "${RUN_DIR}/control/instrumentation-bundle.json" --registry "${REGISTRY}"

# One exact argv is given directly to StageRunner; stdout and stderr are a
# single durable record rather than a shell pipeline with ambiguous status.
stage() {
  local stage_name=$1
  local stdout_path=$2
  shift 2
  "${METRICS_CLI}" run-stage --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --producer stage.runner --stage "${stage_name}" --cwd "${CASE_DIR}" --stderr-mode stdout --stdout-path "${stdout_path}" -- "$@"
}

stage_at() {
  local stage_name=$1
  local stdout_path=$2
  local cwd=$3
  shift 3
  "${METRICS_CLI}" run-stage --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --producer stage.runner --stage "${stage_name}" --cwd "${cwd}" --stderr-mode stdout --stdout-path "${stdout_path}" -- "$@"
}

# capture-hardware is a tracked, dependency-free Python probe whose installed
# shebang is intentionally portable.  Genkai's system python3 is 3.6, while
# the probe and the metrics runtime require the provisioned Python.  Put that
# interpreter first for both the direct minimal capture and the MPI-launched
# profile capture; the executable identity remains the tracked probe itself.
probe_python_dir="${PROVISION_DIR}/experiment-metrics/.venv/bin"
export PATH="${probe_python_dir}:${PATH}"
set +u
source "${WM_PROJECT_DIR:?OpenFOAM project directory is required}/bin/tools/RunFunctions"
set -u

MPIEXEC=$(command -v mpirun)
DECOMPOSE_PAR=$(command -v decomposePar)
SIMPLE_FOAM=$(command -v simpleFoam)
CHECK_MESH=$(command -v checkMesh)
RENUMBER_MESH=$(command -v renumberMesh)
POTENTIAL_FOAM=$(command -v potentialFoam)
APPLY_BOUNDARY_LAYER=$(command -v applyBoundaryLayer)
MESH_FACTS=$(command -v mesh-facts)
PARTITION_AUDIT=$(command -v partition-audit)
CAPTURE_HARDWARE=$(command -v capture-hardware)

provision_args=(validate-provision --manifest "${RUN_MANIFEST}" --build-sidecar "${RUN_DIR}/control/build-sidecar.json" --provision-root "${PROVISION_DIR}" --output "${RUN_DIR}/control/build-provision-validation.json" --executable "simpleFoam=${SIMPLE_FOAM}" --executable "decomposePar=${DECOMPOSE_PAR}" --executable "checkMesh=${CHECK_MESH}" --executable "renumberMesh=${RENUMBER_MESH}" --executable "potentialFoam=${POTENTIAL_FOAM}" --executable "applyBoundaryLayer=${APPLY_BOUNDARY_LAYER}" --executable "mesh-facts=${MESH_FACTS}" --executable "partition-audit=${PARTITION_AUDIT}" --executable "capture-hardware=${CAPTURE_HARDWARE}" --executable "mpirun=${MPIEXEC}")
if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  [[ "${OPENFOAM_VTUNE_RANK}" =~ ^[0-9]+$ ]]
  (( OPENFOAM_VTUNE_RANK < OPENFOAM_MPI_PROCS ))
  OPENFOAM_VTUNE_PATH=$(command -v vtune)
  export OPENFOAM_VTUNE_PATH
  provision_args+=(--executable "vtune=${OPENFOAM_VTUNE_PATH}")
fi
"${METRICS_CLI}" "${provision_args[@]}"
"${METRICS_CLI}" record-build-provision --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --build-provision "${RUN_DIR}/control/build-provision-validation.json" || printf '%s\n' 'build provision metrics could not be recorded' >&2

cp -a "${PROVISION_DIR}/benchmark/occDrivAerStaticMesh" "${CASE_INPUT_DIR}"
install -d -m 0755 "${SOURCE_DIR}/mesh" "${SOURCE_DIR}/hardware"

# Seal the exact pinned official setup before the first OpenFOAM stage reads it.
"${METRICS_CLI}" capture-workload --manifest "${RUN_MANIFEST}" --case-root "${CASE_INPUT_DIR}" --definition "${PROVISION_DIR}/benchmark/workload.json" --output-root "${SOURCE_DIR}/workload"

"${METRICS_CLI}" supervisor-mark-pipeline --state "${SUPERVISOR_STATE}" --mark start
case "${PROTOCOL_NAME}" in
  *-scotch-*)
    PREPARE_COMMAND=("${PROVISION_DIR}/scripts/prepare-openfoam-case.sh" "${CASE_INPUT_DIR}" "${CASE_DIR}" "${DECOMPOSE_PAR}" "${CHECK_MESH}" "${WORKLOAD_MESH_ARCHIVE}" "${PROVISION_DIR}/benchmark/workload.json" "${RUN_DIR}/control/build-sidecar.json" "${OPENFOAM_MPI_PROCS}" "${case_cache_root}")
    ;;
  *) echo "unsupported protocol decomposition: ${PROTOCOL_NAME}" >&2; exit 64 ;;
esac
stage_at case_prepare "${LOG_DIR}/case-prepare.log" "${CASE_DIR%/*}" "${PREPARE_COMMAND[@]}" --require-cache
cd "${CASE_DIR}"
install -m 0644 "${DECOMPOSE_PAR_DICT}" "${SOURCE_DIR}/mesh/decomposeParDict"
install -m 0644 logs/checkMesh.log "${LOG_DIR}/checkMesh.log"
install -m 0644 logs/decomposePar.log "${LOG_DIR}/decomposePar.log"
cache_dir=$(sed -n 's/^cache_dir=//p' "${LOG_DIR}/case-prepare.log" | tail -n 1)
[[ "${cache_dir}" == "${case_cache_root}/"* ]]
install -m 0644 "${cache_dir}/manifest.json" "${SOURCE_DIR}/mesh/case-cache-manifest.json"

sed -i -E "s/^(endTime[[:space:]]+)[0-9]+;/\\1${OPENFOAM_ITERATIONS};/" system/controlDict
restore0Dir -processor
stage renumber_mesh "${LOG_DIR}/renumberMesh.log" "${solver_launch[@]}" "${RENUMBER_MESH}" -constant -overwrite -parallel -fileHandler uncollated
stage potential_foam "${LOG_DIR}/potentialFoam.log" "${solver_launch[@]}" "${POTENTIAL_FOAM}" -initialiseUBCs -parallel -fileHandler uncollated
stage apply_boundary_layer "${LOG_DIR}/applyBoundaryLayer.log" "${solver_launch[@]}" "${APPLY_BOUNDARY_LAYER}" -ybl 0.0450244 -parallel -fileHandler uncollated

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  install -d -m 2770 "${vtune_root}"
  install -d -m 0700 "${RUN_DIR}/profile/raw/vtune-summary"
fi
install -d -m 0755 "${SOURCE_DIR}/env" "${SOURCE_DIR}/placement"
"${METRICS_CLI}" capture-host-exec --manifest "${RUN_MANIFEST}" --output "${SOURCE_DIR}/env/host-exec.snapshot"
if [[ "${OPENFOAM_RUN_PURPOSE}" == bench ]]; then
  stage rank_placement "${LOG_DIR}/rank-placement.log" "${solver_launch[@]}" "${PROVISION_DIR}/experiment-metrics/.venv/bin/python" -m experiment_metrics.rank_wrapper --manifest "${RUN_MANIFEST}" --expected-ranks "${OPENFOAM_MPI_PROCS}" --expected-nodes "${OPENFOAM_NODES}" --placement-root "${SOURCE_DIR}/placement" --global-rank-env "${global_rank_env}" --local-rank-env "${local_rank_env}" --local-size-env "${local_size_env}" --capture-only
fi
set +e
if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  # Every rank records its placement first. The selected rank then execs the
  # profiler, which launches simpleFoam directly so VTune follows the solver
  # rather than the Python placement process.
  stage solver "${SOLVER_LOG}" "${solver_launch[@]}" "${PROVISION_DIR}/experiment-metrics/.venv/bin/python" -m experiment_metrics.rank_wrapper --manifest "${RUN_MANIFEST}" --expected-ranks "${OPENFOAM_MPI_PROCS}" --expected-nodes "${OPENFOAM_NODES}" --placement-root "${SOURCE_DIR}/placement" --global-rank-env "${global_rank_env}" --local-rank-env "${local_rank_env}" --local-size-env "${local_size_env}" --profile-rank "${OPENFOAM_VTUNE_RANK}" --profile-wrapper "${PROVISION_DIR}/scripts/exec-profiler.sh" -- "${SIMPLE_FOAM}" -parallel -fileHandler uncollated
else
  stage solver "${SOLVER_LOG}" "${solver_launch[@]}" "${SIMPLE_FOAM}" -parallel -fileHandler uncollated
fi
solver_status=$?
set -e
"${METRICS_CLI}" supervisor-mark-pipeline --state "${SUPERVISOR_STATE}" --mark finish

if [[ "${solver_status}" -ne 0 ]]; then
  exit "${solver_status}"
fi

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  set +e
  "${PROVISION_DIR}/scripts/export-vtune-hotspots.sh"
  vtune_export_status=$?
  set -e
  if [[ "${vtune_export_status}" -ne 0 ]]; then
    printf 'VTune hotspot export failed (%d); solver result remains authoritative\n' "${vtune_export_status}" >&2
  fi
fi

"${PROVISION_DIR}/benchmark/parse_result.sh" "${SOLVER_LOG}" "${LOG_DIR}/checkMesh.log" "${OPENFOAM_MPI_PROCS}" "${OPENFOAM_NODES}" "${OPENFOAM_ITERATIONS}" "${OPENFOAM_EXPECTED_CELLS}" "${OPENFOAM_RELEASE}" "${OPENFOAM_WORKLOAD_ID}" "${OPENFOAM_DISTRIBUTION}" > "${RESULTS_DIR}/result.txt"
grep -qx 'STATUS: VALID' "${RESULTS_DIR}/result.txt"
grep -q '^RESULT:' "${RESULTS_DIR}/result.txt"

# Reuse the small, durable preparation logs. Never reopen or hash the 65M-cell
# serial/processor meshes just to collect metrics.
"${METRICS_CLI}" record-mesh --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --decompose-dict "${SOURCE_DIR}/mesh/decomposeParDict" --check-mesh-log "${LOG_DIR}/checkMesh.log" --decompose-log "${LOG_DIR}/decomposePar.log" || printf '%s\n' 'mesh metrics could not be recorded; solver result remains valid' >&2

minimal_hardware_argv=("${CAPTURE_HARDWARE}" --mode minimal --subject-kind regular_run --subject-id "${RUN_ID}" --manifest "${RUN_MANIFEST}" --output-root "${SOURCE_DIR}/hardware")
if (( OPENFOAM_NODES == 1 )); then
  minimal_hardware_argv+=(--node-ordinal 0)
else
  minimal_hardware_argv=(
    "${node_launch[@]}"
    "${minimal_hardware_argv[@]}"
    --node-ordinal-from-env "${global_rank_env}"
  )
fi
set +e
stage minimal_hardware_capture "${LOG_DIR}/minimal-hardware-capture.log" "${minimal_hardware_argv[@]}"
minimal_hardware_status=$?
set -e
if [[ "${minimal_hardware_status}" -ne 0 ]]; then
  printf '%s\n' 'minimal hardware capture failed; solver result remains valid' >&2
else
  "${METRICS_CLI}" record-minimal-hardware --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --hardware-root "${SOURCE_DIR}/hardware" --protocol "${OPENFOAM_PROTOCOL_PATH}" || printf '%s\n' 'minimal hardware metrics could not be recorded' >&2
fi

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  set +e
  stage profile_hardware_capture "${LOG_DIR}/profile-hardware-capture.log" "${node_launch[@]}" "${CAPTURE_HARDWARE}" --mode profile-postrun --subject-kind regular_run --subject-id "${RUN_ID}" --manifest "${RUN_MANIFEST}" --output-root "${RUN_DIR}/profile/raw/hardware" --node-ordinal-from-env "${global_rank_env}"
  profile_hardware_status=$?
  set -e
  if [[ "${profile_hardware_status}" -ne 0 ]]; then
    printf '%s\n' 'profile hardware capture failed; solver result remains valid' >&2
  else
    "${METRICS_CLI}" record-profile-hardware --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --profile-hardware-root "${RUN_DIR}/profile/raw/hardware" --protocol "${OPENFOAM_PROTOCOL_PATH}" || printf '%s\n' 'profile hardware metrics could not be recorded' >&2
  fi
fi

# Network measurement is an independent post-solver stage.  Missing IMB,
# failed execution, or malformed output deliberately does not alter the solver
# success marker; network diagnostics remain a separate non-gating stage.
IMB_STDOUT="${SOURCE_DIR}/network/imb-mpi1/stdout.txt"
IMB_STDERR="${SOURCE_DIR}/network/imb-mpi1/stderr.txt"
IMB_ARGV="${SOURCE_DIR}/network/imb-mpi1/argv.json"
install -d -m 0755 "${IMB_STDOUT%/*}"
imb_bin=$(command -v IMB-MPI1 || true)
if [[ -n "${imb_bin}" ]]; then
  imb_argv=(
    "${solver_launch[@]}"
    "${imb_bin}" -npmin "${OPENFOAM_MPI_PROCS}" -msglog 0:22
    -iter 1000 -time 1 -iter_policy dynamic PingPong Sendrecv Allreduce
  )
  "${METRICS_CLI}" capture-argv --manifest "${RUN_MANIFEST}" --output "${IMB_ARGV}" -- "${imb_argv[@]}"
  set +e
  "${METRICS_CLI}" run-stage --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --producer stage.runner --stage network_imb_mpi1 --cwd "${CASE_DIR}" --stderr-mode separate --stdout-path "${IMB_STDOUT}" --stderr-path "${IMB_STDERR}" --timeout-sec 600 -- "${imb_argv[@]}"
  imb_status=$?
  set -e
  if [[ "${imb_status}" -eq 0 ]]; then
    "${METRICS_CLI}" record-imb-mpi1 --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --stdout "${IMB_STDOUT}" --stderr "${IMB_STDERR}" --argv-json "${IMB_ARGV}" --protocol "${OPENFOAM_PROTOCOL_PATH}" --source-member source/network/imb-mpi1/stdout.txt ||
      printf '%s\n' 'IMB output was not a complete canonical capture' >&2
  else
    printf '%s\n' "IMB-MPI1 stage failed (${imb_status}); collection will be incomplete" >&2
  fi
else
  printf '%s\n' 'IMB-MPI1 is unavailable; collection will be incomplete' >&2
fi

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  : > "${LOG_DIR}/profile-location.txt"
  vtune_result_dirs=()
  for candidate in "${OPENFOAM_VTUNE_RESULT_DIR}" "${OPENFOAM_VTUNE_RESULT_DIR}".*
  do
    [[ -d "${candidate}" ]] && vtune_result_dirs+=("${candidate}")
  done
  du -sh "${vtune_root}" >> "${LOG_DIR}/profile-location.txt" 2>/dev/null || true
  if [[ "${#vtune_result_dirs[@]}" -eq 1 ]]; then
    printf 'vtune_result_dir=%s\n' "${vtune_result_dirs[0]}" >> "${LOG_DIR}/profile-location.txt"
  else
    printf 'Expected one VTune result directory for %s, found %d\n' "${OPENFOAM_VTUNE_RESULT_DIR}" "${#vtune_result_dirs[@]}" >&2
  fi
fi
# Only solver validity controls the scheduler/job success marker.
touch "${RUN_DIR}/run-success"
