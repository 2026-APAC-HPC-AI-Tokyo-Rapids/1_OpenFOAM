#!/usr/bin/env bash

# スケジューラに依存しない計算ノード側の実行処理。クラスタ別の呼び出し側で
# ツールチェーンとMPI環境を設定し、起動引数をシェルで再解釈せずに渡す。
set -euo pipefail

solver_launch=()
node_launch=()
openfoam_args=()
job_id=
case_cache_root=
case_dir=
prepared_case_manifest=
rank_manifest=
rank_placement_root=
placement_collector=
bind_rank_placement=false
paraview_collector=
global_rank_env=
local_rank_env=
local_size_env=
large_output_dir=
runtime_root=
compute_tools_root=
imb_bin=
while [[ $# -gt 0 ]]
do
  case "$1" in
    --solver-launch-arg) [[ $# -ge 2 ]]; solver_launch+=("$2"); shift 2 ;;
    --node-launch-arg) [[ $# -ge 2 ]]; node_launch+=("$2"); shift 2 ;;
    --job-id) [[ $# -ge 2 ]]; job_id=$2; shift 2 ;;
    --case-cache-root) [[ $# -ge 2 ]]; case_cache_root=$2; shift 2 ;;
    --case-dir) [[ $# -ge 2 ]]; case_dir=$2; shift 2 ;;
    --prepared-case-manifest) [[ $# -ge 2 ]]; prepared_case_manifest=$2; shift 2 ;;
    --rank-manifest) [[ $# -ge 2 ]]; rank_manifest=$2; shift 2 ;;
    --rank-placement-root) [[ $# -ge 2 ]]; rank_placement_root=$2; shift 2 ;;
    --placement-collector) [[ $# -ge 2 ]]; placement_collector=$2; shift 2 ;;
    --bind-rank-placement) bind_rank_placement=true; shift ;;
    --paraview-collector) [[ $# -ge 2 ]]; paraview_collector=$2; shift 2 ;;
    --global-rank-env) [[ $# -ge 2 ]]; global_rank_env=$2; shift 2 ;;
    --local-rank-env) [[ $# -ge 2 ]]; local_rank_env=$2; shift 2 ;;
    --local-size-env) [[ $# -ge 2 ]]; local_size_env=$2; shift 2 ;;
    --large-output-dir) [[ $# -ge 2 ]]; large_output_dir=$2; shift 2 ;;
    --runtime-root) [[ $# -ge 2 ]]; runtime_root=$2; shift 2 ;;
    --compute-tools-root) [[ $# -ge 2 ]]; compute_tools_root=$2; shift 2 ;;
    --imb-bin) [[ $# -ge 2 ]]; imb_bin=$2; shift 2 ;;
    --openfoam-arg) [[ $# -ge 2 ]]; openfoam_args+=("$2"); shift 2 ;;
    *) printf 'run-openfoamの未知の引数です: %s\n' "$1" >&2; exit 64 ;;
  esac
done
[[ "${job_id}" =~ ^[0-9]+([.][A-Za-z0-9.-]+)?$ ]]
[[ "${#solver_launch[@]}" -gt 0 && "${solver_launch[0]}" == /* ]]
[[ "${#node_launch[@]}" -gt 0 && "${node_launch[0]}" == /* ]]
[[ "${large_output_dir}" == /* ]]
if [[ -n "${imb_bin}" ]]; then [[ "${imb_bin}" == /* && -x "${imb_bin}" ]]; fi
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
: "${OPENFOAM_SOLVER:?ソルバーの識別情報が必要です}"
: "${OPENFOAM_WORKLOAD_ID:?workload identity is required}"
: "${WORKLOAD_MESH_ARCHIVE:?verified mesh archive is required}"
[[ "${OPENFOAM_SOLVER}" == simpleFoam && "${OPENFOAM_DISTRIBUTION}" == OpenFOAM.com && "${OPENFOAM_RELEASE}" == v2512 && "${OPENFOAM_WORKLOAD_ID}" == occDrivAerStaticMesh-65M ]]

OPENFOAM_RUN_PURPOSE=${OPENFOAM_RUN_PURPOSE:-bench}
OPENFOAM_PROFILE_TOOL=${OPENFOAM_PROFILE_TOOL:-vtune}
case "${OPENFOAM_PROFILE_TOOL}" in vtune|uprof) ;; *) printf '未対応のprofile toolです: %s\n' "${OPENFOAM_PROFILE_TOOL}" >&2; exit 2 ;; esac
PROTOCOL_NAME=$(basename "${OPENFOAM_PROTOCOL_PATH}" .toml)
case "${OPENFOAM_RUN_PURPOSE}" in
  bench|profile) ;;
  *) printf '未対応のOPENFOAM_RUN_PURPOSEです: %s\n' "${OPENFOAM_RUN_PURPOSE}" >&2; exit 2 ;;
esac
if [[ "${OPENFOAM_RUN_PURPOSE}" == profile && "${OPENFOAM_PROFILE_TOOL}" == vtune ]]; then
  : "${OPENFOAM_VTUNE_RANK:?scheduler-selected VTune rank is required}"
  : "${OPENFOAM_VTUNE_ANALYSIS:?scheduler-selected VTune analysis is required}"
  case "${OPENFOAM_VTUNE_ANALYSIS}" in hotspots|hpc-performance|memory-access|memory-access-core) ;; *) printf '未対応のVTune解析です: %s\n' "${OPENFOAM_VTUNE_ANALYSIS}" >&2; exit 2 ;; esac
fi
(( OPENFOAM_NODES > 0 && OPENFOAM_MPI_PROCS > 0 ))
(( OPENFOAM_MPI_PROCS % OPENFOAM_NODES == 0 ))

runtime_root=${runtime_root:-${PROVISION_DIR}}
compute_tools_root=${compute_tools_root:-${PROVISION_DIR}}
case_dir=${case_dir:-${RUN_DIR}/work/occDrivAerStaticMesh}
[[ "${runtime_root}" == /* && "${compute_tools_root}" == /* && "${case_dir}" == /* ]]
if [[ -z "${prepared_case_manifest}" ]]; then
  [[ "${case_cache_root}" == /* ]]
else
  [[ "${prepared_case_manifest}" == /* ]]
fi
CASE_DIR=${case_dir}
CASE_INPUT_DIR="${PROVISION_DIR}/benchmark/occDrivAerStaticMesh"
LOG_DIR="${RUN_DIR}/logs"
SOURCE_DIR="${RUN_DIR}/source"
RESULTS_DIR="${RUN_DIR}/results"
REGISTRY="${PROVISION_DIR}/experiment-metrics/registry/openfoam-v2.toml"
METRICS_CLI="${PROVISION_DIR}/experiment-metrics/.venv/bin/experiment-metrics"
RANK_PYTHON="${compute_tools_root}/experiment-metrics/.venv/bin/python"
RANK_PYTHON_LAUNCH=(/usr/bin/env "${RANK_PYTHON}")
RANK_PLACEMENT_ARGS=()
if [[ "${bind_rank_placement}" == true ]]; then RANK_PLACEMENT_ARGS+=(--bind-local-rank); fi
rank_manifest=${rank_manifest:-${RUN_MANIFEST}}
rank_placement_root=${rank_placement_root:-${SOURCE_DIR}/placement}
[[ "${rank_manifest}" == /* && "${rank_placement_root}" == /* ]]
if [[ "${rank_manifest}" == "${RUN_MANIFEST}" ]]; then [[ "${rank_placement_root}" == "${SOURCE_DIR}/placement" && -z "${placement_collector}" ]]; else [[ "${placement_collector}" == /* ]]; fi
if [[ -n "${paraview_collector}" ]]; then [[ "${paraview_collector}" == /* ]]; fi

DECOMPOSE_PAR_DICT=system/decomposeParDict
SOLVER_LOG="${LOG_DIR}/solver.log"
SUPERVISOR_STATE="${RUN_DIR}/domain/supervisor-state.json"
profile_run_id="${RUN_ID}-${job_id}"
uprof_root="${RUN_DIR}/profile/raw/uprof"
if [[ "${OPENFOAM_RUN_PURPOSE}" == profile && "${OPENFOAM_PROFILE_TOOL}" == vtune ]]; then
  vtune_root="${large_output_dir}/vtune"
  OPENFOAM_VTUNE_RESULT_DIR="${vtune_root}/rank-${OPENFOAM_VTUNE_RANK}-${OPENFOAM_VTUNE_ANALYSIS}"
  OPENFOAM_VTUNE_STATUS_PATH="${RUN_DIR}/profile/raw/vtune-summary/collection-status.json"
  export OPENFOAM_VTUNE_RESULT_DIR OPENFOAM_VTUNE_STATUS_PATH
fi
export OPENFOAM_COMPUTE_TOOLS_ROOT="${compute_tools_root}"
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

# 一意に定めた引数列をStageRunnerへ直接渡す。終了状態が曖昧になるシェルの
# パイプラインは使わず、標準出力と標準エラーを一つの永続的な記録にまとめる。
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
JQ=$(command -v jq)
ENV=$(command -v env)

provision_args=(validate-provision --manifest "${RUN_MANIFEST}" --build-sidecar "${RUN_DIR}/control/build-sidecar.json" --provision-root "${runtime_root}" --output "${RUN_DIR}/control/build-provision-validation.json" --executable "simpleFoam=${SIMPLE_FOAM}" --executable "decomposePar=${DECOMPOSE_PAR}" --executable "checkMesh=${CHECK_MESH}" --executable "renumberMesh=${RENUMBER_MESH}" --executable "potentialFoam=${POTENTIAL_FOAM}" --executable "applyBoundaryLayer=${APPLY_BOUNDARY_LAYER}" --executable "mesh-facts=${MESH_FACTS}" --executable "partition-audit=${PARTITION_AUDIT}" --executable "capture-hardware=${CAPTURE_HARDWARE}" --executable "mpirun=${MPIEXEC}")
uprof_bin_dir=
if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  if [[ "${OPENFOAM_PROFILE_TOOL}" == vtune ]]; then
    [[ "${OPENFOAM_VTUNE_RANK}" =~ ^[0-9]+$ ]]
    (( OPENFOAM_VTUNE_RANK < OPENFOAM_MPI_PROCS ))
    OPENFOAM_VTUNE_PATH=$(command -v vtune)
    export OPENFOAM_VTUNE_PATH
    provision_args+=(--executable "vtune=${OPENFOAM_VTUNE_PATH}")
  else
    : "${AMDUPROF_ROOT:?AMD uProf installation root is required}"
    uprof_bin_dir="${AMDUPROF_ROOT}/bin"
    OPENFOAM_UPROF_PATH="${uprof_bin_dir}/AMDuProfCLI-bin"
    test -x "${OPENFOAM_UPROF_PATH}"
    export OPENFOAM_UPROF_PATH
    provision_args+=(--executable "uprof=${OPENFOAM_UPROF_PATH}")
  fi
fi
if [[ -n "${uprof_bin_dir}" ]]; then LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" "${METRICS_CLI}" "${provision_args[@]}"; else "${METRICS_CLI}" "${provision_args[@]}"; fi
"${METRICS_CLI}" record-build-provision --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --build-provision "${RUN_DIR}/control/build-provision-validation.json" || printf '%s\n' 'ビルド配備の計測値を記録できませんでした' >&2

install -d -m 0755 "${SOURCE_DIR}/mesh" "${SOURCE_DIR}/hardware"

# 最初のOpenFOAM処理が読み込む前に、固定した公式設定をそのまま記録する。
"${METRICS_CLI}" capture-workload --manifest "${RUN_MANIFEST}" --case-root "${CASE_INPUT_DIR}" --definition "${PROVISION_DIR}/benchmark/workload.json" --output-root "${SOURCE_DIR}/workload"

"${METRICS_CLI}" supervisor-mark-pipeline --state "${SUPERVISOR_STATE}" --mark start
case "${PROTOCOL_NAME}" in
  *-scotch-*) ;;
  *) echo "未対応の領域分割条件です: ${PROTOCOL_NAME}" >&2; exit 64 ;;
esac
if [[ -z "${prepared_case_manifest}" ]]; then
  PREPARE_COMMAND=("${PROVISION_DIR}/scripts/prepare-openfoam-case.sh" "${CASE_INPUT_DIR}" "${CASE_DIR}" "${DECOMPOSE_PAR}" "${CHECK_MESH}" "${WORKLOAD_MESH_ARCHIVE}" "${PROVISION_DIR}/benchmark/workload.json" "${RUN_DIR}/control/build-sidecar.json" "${OPENFOAM_MPI_PROCS}" "${case_cache_root}")
  stage_at case_prepare "${LOG_DIR}/case-prepare.log" "${CASE_DIR%/*}" "${PREPARE_COMMAND[@]}" --require-cache
  cache_dir=$(sed -n 's/^cache_dir=//p' "${LOG_DIR}/case-prepare.log" | tail -n 1)
  [[ "${cache_dir}" == "${case_cache_root}/"* ]]
  case_manifest="${cache_dir}/manifest.json"
  restore_case=true
else
  case_manifest=${prepared_case_manifest}
  restore_case=false
  stage_at case_prepare "${LOG_DIR}/case-prepare.log" "${CASE_DIR}" "${JQ}" -e --argjson number_of_subdomains "${OPENFOAM_MPI_PROCS}" 'select(.schema_version == "openfoam-case-cache/v4" and .number_of_subdomains == $number_of_subdomains)' "${prepared_case_manifest}"
fi
cd "${CASE_DIR}"
sed -E -e 's/^(numberOfSubdomains[[:space:]]+)\$nCores;/\1'"${OPENFOAM_MPI_PROCS}"';/' -e 's/^(method[[:space:]]+)\$decompositionMethod;/\1scotch;/' "${DECOMPOSE_PAR_DICT}" > "${SOURCE_DIR}/mesh/decomposeParDict"
grep -Eq "^numberOfSubdomains[[:space:]]+${OPENFOAM_MPI_PROCS};$" "${SOURCE_DIR}/mesh/decomposeParDict"
grep -Eq '^method[[:space:]]+scotch;' "${SOURCE_DIR}/mesh/decomposeParDict"
install -m 0644 logs/checkMesh.log "${LOG_DIR}/checkMesh.log"
install -m 0644 logs/decomposePar.log "${LOG_DIR}/decomposePar.log"
install -m 0644 "${case_manifest}" "${SOURCE_DIR}/mesh/case-cache-manifest.json"

sed -i -E "s/^(endTime[[:space:]]+)[0-9]+;/\\1${OPENFOAM_ITERATIONS};/" system/controlDict
install -m 0644 system/controlDict "${SOURCE_DIR}/mesh/controlDict"
install -m 0644 system/include/caseDefinition "${SOURCE_DIR}/mesh/caseDefinition"
if [[ "${restore_case}" == true ]]; then restore0Dir -processor; fi
stage renumber_mesh "${LOG_DIR}/renumberMesh.log" "${solver_launch[@]}" "${RENUMBER_MESH}" -constant -overwrite -parallel -fileHandler uncollated "${openfoam_args[@]}"
stage potential_foam "${LOG_DIR}/potentialFoam.log" "${solver_launch[@]}" "${POTENTIAL_FOAM}" -initialiseUBCs -parallel -fileHandler uncollated "${openfoam_args[@]}"
stage apply_boundary_layer "${LOG_DIR}/applyBoundaryLayer.log" "${solver_launch[@]}" "${APPLY_BOUNDARY_LAYER}" -ybl 0.0450244 -parallel -fileHandler uncollated "${openfoam_args[@]}"

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  # coded function objectの初回コンパイルをprofile収集区間へ混ぜない。
  # -postProcessはsolver反復を行わずfunction objectだけを初期化・実行し、生成した
  # 共有libraryを後続の正式solver実行が再利用する。公式function objectは0反復の終了時に0/0を
  # 計算するため、warmupだけFPE trapを無効化する。solverの実行環境は変更しない。
  stage profile_warmup "${LOG_DIR}/profile-warmup.log" "${ENV}" FOAM_SIGFPE=false "${solver_launch[@]}" "${SIMPLE_FOAM}" -postProcess -parallel -fileHandler uncollated "${openfoam_args[@]}"
  if [[ "${OPENFOAM_PROFILE_TOOL:-vtune}" == vtune ]]; then install -d -m 2770 "${vtune_root}"; install -d -m 0700 "${RUN_DIR}/profile/raw/vtune-summary"; else install -d -m 0750 "${uprof_root}/sessions"; fi
  # v2512は既存coefficient.datがあると正式出力をcoefficient_0.datへ改名する。
  # warmupのrawを退避し、正式solverが規定名へ出力できるようにする。
  mv -T "${CASE_DIR}/postProcessing" "${RUN_DIR}/profile/raw/warmup-postProcessing"
fi
install -d -m 0755 "${SOURCE_DIR}/env" "${SOURCE_DIR}/placement"
"${METRICS_CLI}" capture-host-exec --manifest "${RUN_MANIFEST}" --output "${SOURCE_DIR}/env/host-exec.snapshot"
if [[ "${OPENFOAM_RUN_PURPOSE}" == bench || "${OPENFOAM_PROFILE_TOOL}" == uprof ]]; then
  stage rank_placement "${LOG_DIR}/rank-placement.log" "${solver_launch[@]}" "${RANK_PYTHON_LAUNCH[@]}" -m experiment_metrics.rank_wrapper --manifest "${rank_manifest}" --expected-ranks "${OPENFOAM_MPI_PROCS}" --expected-nodes "${OPENFOAM_NODES}" --placement-root "${rank_placement_root}" --global-rank-env "${global_rank_env}" --local-rank-env "${local_rank_env}" --local-size-env "${local_size_env}" "${RANK_PLACEMENT_ARGS[@]}" --capture-only
fi
set +e
if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  if [[ "${OPENFOAM_PROFILE_TOOL}" == uprof ]]; then
    uprof_target_argv_file="${RUN_DIR}/control/uprof-target.argv"
    printf '%s\0' "${SIMPLE_FOAM}" -parallel -fileHandler uncollated "${openfoam_args[@]}" > "${uprof_target_argv_file}"
    chmod 0600 "${uprof_target_argv_file}"
    stage solver "${SOLVER_LOG}" "${solver_launch[@]}" /usr/bin/bash "${compute_tools_root}/platforms/aspire2a/exec-uprof.sh" "${OPENFOAM_UPROF_PATH}" collect --config hotspots -g --mpi --output-dir "${uprof_root}/sessions" "${compute_tools_root}/platforms/aspire2a/exec-uprof-target.sh" "${uprof_target_argv_file}"
  else
    stage solver "${SOLVER_LOG}" "${solver_launch[@]}" "${RANK_PYTHON_LAUNCH[@]}" -m experiment_metrics.rank_wrapper --manifest "${rank_manifest}" --expected-ranks "${OPENFOAM_MPI_PROCS}" --expected-nodes "${OPENFOAM_NODES}" --placement-root "${rank_placement_root}" --global-rank-env "${global_rank_env}" --local-rank-env "${local_rank_env}" --local-size-env "${local_size_env}" --profile-rank "${OPENFOAM_VTUNE_RANK}" --profile-wrapper "${compute_tools_root}/scripts/exec-profiler.sh" -- "${SIMPLE_FOAM}" -parallel -fileHandler uncollated "${openfoam_args[@]}"
  fi
else
  stage solver "${SOLVER_LOG}" "${solver_launch[@]}" "${SIMPLE_FOAM}" -parallel -fileHandler uncollated "${openfoam_args[@]}"
fi
solver_status=$?
set -e
"${METRICS_CLI}" supervisor-mark-pipeline --state "${SUPERVISOR_STATE}" --mark finish

if [[ "${solver_status}" -ne 0 ]]; then
  exit "${solver_status}"
fi
# This shell and MPI rank 0 share the first node's case root, including on Gadi.
# Copy force coefficients to the persistent run before optional profile collection.
"${METRICS_CLI}" collect-coefficient --case-root "${CASE_DIR}" --output-root "${RESULTS_DIR}" --iterations "${OPENFOAM_ITERATIONS}"
if [[ -n "${placement_collector}" ]]; then "${node_launch[@]}" "${placement_collector}" "${rank_placement_root}" "${SOURCE_DIR}/placement" "$(( OPENFOAM_MPI_PROCS / OPENFOAM_NODES ))"; fi

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  if [[ "${OPENFOAM_PROFILE_TOOL}" == uprof ]]; then
    "${compute_tools_root}/platforms/aspire2a/export-uprof.sh" "${OPENFOAM_UPROF_PATH}" "${uprof_root}"
  else
    set +e
    "${PROVISION_DIR}/scripts/export-vtune-hotspots.sh"
    vtune_export_status=$?
    set -e
    if [[ "${vtune_export_status}" -ne 0 ]]; then printf 'VTuneホットスポットの出力に失敗しました（%d）。ソルバーの結果を正本として維持します\n' "${vtune_export_status}" >&2; fi
  fi
fi

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile && -n "${paraview_collector}" ]]; then
  paraview_output_dir="${large_output_dir}/paraview"
  "${node_launch[@]}" "${paraview_collector}" "${CASE_DIR}" "${paraview_output_dir}" "$(( OPENFOAM_MPI_PROCS / OPENFOAM_NODES ))" "${OPENFOAM_NODES}" "${global_rank_env}"
  "${compute_tools_root}/scripts/finalize-paraview-case.sh" "${paraview_output_dir}" "${RUN_ID}" "${profile_run_id}" "${OPENFOAM_NODES}"
fi

"${PROVISION_DIR}/benchmark/parse_result.sh" "${SOLVER_LOG}" "${LOG_DIR}/checkMesh.log" "${OPENFOAM_MPI_PROCS}" "${OPENFOAM_NODES}" "${OPENFOAM_ITERATIONS}" "${OPENFOAM_EXPECTED_CELLS}" "${OPENFOAM_RELEASE}" "${OPENFOAM_WORKLOAD_ID}" "${OPENFOAM_DISTRIBUTION}" "${RESULTS_DIR}/coefficient.dat" > "${RESULTS_DIR}/result.txt"
grep -qx 'STATUS: VALID' "${RESULTS_DIR}/result.txt"
grep -q '^RESULT:' "${RESULTS_DIR}/result.txt"

# 小さく永続的な準備ログを再利用する。計測値を集めるだけのために、65Mセルの
# 非分割メッシュやprocessorメッシュを開き直したりハッシュ計算したりしない。
"${METRICS_CLI}" record-mesh --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --decompose-dict "${SOURCE_DIR}/mesh/decomposeParDict" --check-mesh-log "${LOG_DIR}/checkMesh.log" --decompose-log "${LOG_DIR}/decomposePar.log" || printf '%s\n' 'メッシュの計測値を記録できませんでした。ソルバーの結果は有効です' >&2

# MPIの-genv PATHは呼出元で固定済み。OS Pythonへ戻らないよう配備済みinterpreterを明示する。
minimal_hardware_argv=("${RANK_PYTHON_LAUNCH[@]}" "${CAPTURE_HARDWARE}" --mode minimal --subject-kind regular_run --subject-id "${RUN_ID}" --manifest "${RUN_MANIFEST}" --output-root "${SOURCE_DIR}/hardware")
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
  printf '%s\n' '最小構成のハードウェア情報取得に失敗しました。ソルバーの結果は有効です' >&2
else
  "${METRICS_CLI}" record-minimal-hardware --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --hardware-root "${SOURCE_DIR}/hardware" --protocol "${OPENFOAM_PROTOCOL_PATH}" || printf '%s\n' '最小構成のハードウェア計測値を記録できませんでした' >&2
fi

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  set +e
  stage profile_hardware_capture "${LOG_DIR}/profile-hardware-capture.log" "${node_launch[@]}" "${RANK_PYTHON_LAUNCH[@]}" "${CAPTURE_HARDWARE}" --mode profile-postrun --subject-kind regular_run --subject-id "${RUN_ID}" --manifest "${RUN_MANIFEST}" --output-root "${RUN_DIR}/profile/raw/hardware" --node-ordinal-from-env "${global_rank_env}"
  profile_hardware_status=$?
  set -e
  if [[ "${profile_hardware_status}" -ne 0 ]]; then
    printf '%s\n' 'プロファイル用ハードウェア情報の取得に失敗しました。ソルバーの結果は有効です' >&2
  else
    "${METRICS_CLI}" record-profile-hardware --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --profile-hardware-root "${RUN_DIR}/profile/raw/hardware" --protocol "${OPENFOAM_PROTOCOL_PATH}" || printf '%s\n' 'プロファイル用ハードウェア計測値を記録できませんでした' >&2
  fi
fi

# ネットワーク計測はソルバー後の独立した処理である。IMBがない場合、実行失敗、
# 不正な出力があっても、意図的にソルバーの成功印は変更しない。ネットワーク診断は
# 成否判定に影響しない別処理として維持する。
IMB_STDOUT="${SOURCE_DIR}/network/imb-mpi1/stdout.txt"
IMB_STDERR="${SOURCE_DIR}/network/imb-mpi1/stderr.txt"
IMB_ARGV="${SOURCE_DIR}/network/imb-mpi1/argv.json"
install -d -m 0755 "${IMB_STDOUT%/*}"
imb_bin=${imb_bin:-$(command -v IMB-MPI1 || true)}
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
      printf '%s\n' 'IMB出力を正規化された完全な記録として取得できませんでした' >&2
  else
    printf '%s\n' "IMB-MPI1 stage failed (${imb_status}); collection will be incomplete" >&2
  fi
else
  printf '%s\n' 'IMB-MPI1を利用できないため、収集結果は不完全になります' >&2
fi

if [[ "${OPENFOAM_RUN_PURPOSE}" == profile ]]; then
  : > "${LOG_DIR}/profile-location.txt"
  if [[ "${OPENFOAM_PROFILE_TOOL}" == uprof ]]; then
    du -sh "${uprof_root}" >> "${LOG_DIR}/profile-location.txt" 2>/dev/null || true
    sed -n 's/^session=/uprof_session=/p' "${uprof_root}/session.txt" >> "${LOG_DIR}/profile-location.txt"
  else
    vtune_result_dirs=()
    for candidate in "${OPENFOAM_VTUNE_RESULT_DIR}" "${OPENFOAM_VTUNE_RESULT_DIR}".*
    do
      [[ -d "${candidate}" ]] && vtune_result_dirs+=("${candidate}")
    done
    du -sh "${vtune_root}" >> "${LOG_DIR}/profile-location.txt" 2>/dev/null || true
    if [[ "${#vtune_result_dirs[@]}" -eq 1 ]]; then
      printf 'vtune_result_dir=%s\n' "${vtune_result_dirs[0]}" >> "${LOG_DIR}/profile-location.txt"
    else
      printf 'VTune結果ディレクトリは%sに1件必要ですが、%d件見つかりました\n' "${OPENFOAM_VTUNE_RESULT_DIR}" "${#vtune_result_dirs[@]}" >&2
    fi
  fi
fi
# スケジューラジョブの成功印はソルバーの有効性だけで決める。
touch "${RUN_DIR}/run-success"
