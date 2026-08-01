#!/usr/bin/env bash

set -euo pipefail

: "${OPENFOAM_PROFILE_DIR:?}"
: "${OPENFOAM_PROFILE_LABEL:?}"
: "${PROVISION_DIR:?}"

PROFILE_RESULT_DIR="${OPENFOAM_PROFILE_DIR}/${OPENFOAM_PROFILE_LABEL}"
SUMMARY_DIR="${PROFILE_RESULT_DIR}/browser-summary"
BROWSER_ARTIFACT_DIR="${PROVISION_DIR}/browser-summary"
MAX_TIME_BINS="${OPENFOAM_VTUNE_TIME_BINS:-300}"
TOP_FUNCTIONS="${OPENFOAM_VTUNE_TOP_FUNCTIONS:-50}"
FUNCTION_BINS="${OPENFOAM_VTUNE_FUNCTION_BINS:-40}"
FUNCTION_REPORT_LIMIT="${OPENFOAM_VTUNE_FUNCTION_REPORT_LIMIT:-0}"
FUNCTIONS_PER_WINDOW="${OPENFOAM_VTUNE_FUNCTIONS_PER_WINDOW:-8}"
TIME_SERIES_FUNCTIONS="${OPENFOAM_VTUNE_TIME_SERIES_FUNCTIONS:-12}"
MAX_TASK_EVENTS="${OPENFOAM_VTUNE_MAX_TASK_EVENTS:-1500}"
TASK_OCCUPANCY_BINS="${OPENFOAM_VTUNE_TASK_OCCUPANCY_BINS:-60}"
MAX_TRACE_BYTES="${OPENFOAM_VTUNE_MAX_TRACE_BYTES:-500000}"
OPENFOAM_PYTHON="${OPENFOAM_PYTHON:-${PROVISION_DIR}/experiment-metrics/.venv/bin/python}"

for value_name in MAX_TIME_BINS TOP_FUNCTIONS FUNCTION_BINS FUNCTIONS_PER_WINDOW TIME_SERIES_FUNCTIONS MAX_TASK_EVENTS TASK_OCCUPANCY_BINS MAX_TRACE_BYTES
do
  value="${!value_name}"
  [[ "${value}" =~ ^[1-9][0-9]*$ ]] || {
    printf '%s must be a positive integer, got %s\n' "${value_name}" "${value}" >&2
    exit 2
  }
done
[[ "${FUNCTION_REPORT_LIMIT}" =~ ^[0-9]+$ ]] || {
  printf 'FUNCTION_REPORT_LIMIT must be a non-negative integer, got %s\n' \
    "${FUNCTION_REPORT_LIMIT}" >&2
  exit 2
}

# Intel MPIのgtool経由では、VTuneが結果名へホスト名を付ける。固定名と
# vtune.<hostname>の両方を受け付け、別runを誤選択しないよう1件に限定する。
vtune_result_dirs=()
for candidate in "${PROFILE_RESULT_DIR}/vtune" "${PROFILE_RESULT_DIR}"/vtune.*
do
  [[ -d "${candidate}" ]] && vtune_result_dirs+=("${candidate}")
done
[[ "${#vtune_result_dirs[@]}" -eq 1 ]] || {
  printf 'Expected one VTune result directory under %s, found %d\n' \
    "${PROFILE_RESULT_DIR}" "${#vtune_result_dirs[@]}" >&2
  exit 2
}
VTUNE_RESULT_DIR="${vtune_result_dirs[0]}"
command -v vtune >/dev/null
[[ -x "${OPENFOAM_PYTHON}" ]] || {
  printf 'Python interpreter is not executable: %s\n' "${OPENFOAM_PYTHON}" >&2
  exit 2
}
install -d -m 0700 "${SUMMARY_DIR}" "${BROWSER_ARTIFACT_DIR}"
install -d -m 0700 "${SUMMARY_DIR}/function-slices"

# VTune 2025.3ではtimelineの-report-outputが成功しても0バイトになるため、
# CSV本体を標準出力から保存する。
vtune -quiet -report timeline \
  -result-dir "${VTUNE_RESULT_DIR}" \
  -report-knob column-by=CPUTime \
  -report-knob "bin-count=${MAX_TIME_BINS}" \
  -format csv \
  -csv-delimiter comma \
  > "${SUMMARY_DIR}/timeline.csv"

vtune -quiet -report hotspots \
  -result-dir "${VTUNE_RESULT_DIR}" \
  -group-by function,module \
  -format csv \
  -csv-delimiter comma \
  > "${SUMMARY_DIR}/hotspots.csv"

timeline_start="$(awk -F, '/^[0-9]+,/ { print $2; exit }' "${SUMMARY_DIR}/timeline.csv")"
timeline_end="$(awk -F, '/^[0-9]+,/ { end=$3 } END { print end }' "${SUMMARY_DIR}/timeline.csv")"
[[ -n "${timeline_start}" && -n "${timeline_end}" ]]

printf 'file,start_sec,end_sec\n' > "${SUMMARY_DIR}/function-slices/windows.csv"
for ((slice_index = 0; slice_index < FUNCTION_BINS; slice_index++)); do
  read -r slice_start slice_end < <(
    awk -v start="${timeline_start}" -v end="${timeline_end}" \
      -v slice_index="${slice_index}" -v count="${FUNCTION_BINS}" \
      'BEGIN {
        duration = end - start
        printf "%.6f %.6f\n",
          start + duration * slice_index / count,
          start + duration * (slice_index + 1) / count
      }'
  )
  printf -v slice_name '%04d.csv' "${slice_index}"
  printf '%s,%s,%s\n' "${slice_name}" "${slice_start}" "${slice_end}" \
    >> "${SUMMARY_DIR}/function-slices/windows.csv"
  if (( FUNCTION_REPORT_LIMIT > 0 )); then
    vtune -quiet -report hotspots \
      -result-dir "${VTUNE_RESULT_DIR}" \
      -group-by function,module \
      -time-filter "${slice_start}:${slice_end}" \
      -limit "${FUNCTION_REPORT_LIMIT}" \
      -format csv \
      -csv-delimiter comma \
      > "${SUMMARY_DIR}/function-slices/${slice_name}"
  else
    vtune -quiet -report hotspots \
      -result-dir "${VTUNE_RESULT_DIR}" \
      -group-by function,module \
      -time-filter "${slice_start}:${slice_end}" \
      -format csv \
      -csv-delimiter comma \
      > "${SUMMARY_DIR}/function-slices/${slice_name}"
  fi
done

solver_log_path="${SOLVER_LOG:-}"
if [[ ! -f "${solver_log_path}" ]]; then
  solver_log_path="${OPENFOAM_PROFILE_DIR}/solver-${OPENFOAM_PROFILE_LABEL}.log"
fi
converter_args=(
  --timeline "${SUMMARY_DIR}/timeline.csv"
  --hotspots "${SUMMARY_DIR}/hotspots.csv"
  --function-slices-dir "${SUMMARY_DIR}/function-slices"
  --output "${SUMMARY_DIR}/openfoam-vtune-trace.json"
  --summary "${SUMMARY_DIR}/summary.json"
  --top-functions "${TOP_FUNCTIONS}"
  --time-series-functions "${TIME_SERIES_FUNCTIONS}"
  --functions-per-window "${FUNCTIONS_PER_WINDOW}"
  --function-report-limit "${FUNCTION_REPORT_LIMIT}"
  --max-time-bins "${MAX_TIME_BINS}"
  --max-task-events "${MAX_TASK_EVENTS}"
  --task-occupancy-bins "${TASK_OCCUPANCY_BINS}"
  --max-trace-bytes "${MAX_TRACE_BYTES}"
  --run-label "${OPENFOAM_PROFILE_LABEL:-openfoam}"
)
task_trace_path="${PROFILE_RESULT_DIR}/openfoam-task-trace.csv"
if [[ -s "${task_trace_path}" ]]; then
  converter_args+=(--task-trace "${task_trace_path}")
  # CLOCK_MONOTONIC_RAWの境界列をVTune自身でもサンプルと相関できるよう、
  # Intelの外部interval CSV命名規則で完全な原本を結果ディレクトリに置く。
  cp "${task_trace_path}" \
    "${VTUNE_RESULT_DIR}/openfoam-tasks-hostname-$(hostname).csv"
fi
if [[ -f "${solver_log_path}" ]]; then
  converter_args+=(--solver-log "${solver_log_path}")
fi

if ! "${OPENFOAM_PYTHON}" "${PROVISION_DIR}/scripts/vtune-to-trace.py" \
  "${converter_args[@]}"
then
  # VTuneの版によってCSV schemaが異なる場合だけ、Actions artifactへ入力を
  # 残して診断できるようにする。成功時は軽量な2ファイルだけを公開する。
  cp "${SUMMARY_DIR}/timeline.csv" \
    "${SUMMARY_DIR}/hotspots.csv" \
    "${PROVISION_DIR}/logs/"
  exit 1
fi

cp "${SUMMARY_DIR}/summary.json" \
  "${SUMMARY_DIR}/openfoam-vtune-trace.json" \
  "${BROWSER_ARTIFACT_DIR}/"
