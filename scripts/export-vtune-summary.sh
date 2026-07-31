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
FUNCTIONS_PER_BIN="${OPENFOAM_VTUNE_FUNCTIONS_PER_BIN:-5}"
MAX_TRACE_BYTES="${OPENFOAM_VTUNE_MAX_TRACE_BYTES:-250000}"
OPENFOAM_PYTHON="${OPENFOAM_PYTHON:-${PROVISION_DIR}/experiment-metrics/.venv/bin/python}"

for value_name in MAX_TIME_BINS TOP_FUNCTIONS FUNCTION_BINS FUNCTIONS_PER_BIN MAX_TRACE_BYTES
do
  value="${!value_name}"
  [[ "${value}" =~ ^[1-9][0-9]*$ ]] || {
    printf '%s must be a positive integer, got %s\n' "${value_name}" "${value}" >&2
    exit 2
  }
done

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
  vtune -quiet -report hotspots \
    -result-dir "${VTUNE_RESULT_DIR}" \
    -group-by function,module \
    -time-filter "${slice_start}:${slice_end}" \
    -limit "${FUNCTIONS_PER_BIN}" \
    -format csv \
    -csv-delimiter comma \
    > "${SUMMARY_DIR}/function-slices/${slice_name}"
done

if ! "${OPENFOAM_PYTHON}" "${PROVISION_DIR}/scripts/vtune-to-trace.py" \
  --timeline "${SUMMARY_DIR}/timeline.csv" \
  --hotspots "${SUMMARY_DIR}/hotspots.csv" \
  --function-slices-dir "${SUMMARY_DIR}/function-slices" \
  --output "${SUMMARY_DIR}/openfoam-vtune-trace.json" \
  --summary "${SUMMARY_DIR}/summary.json" \
  --top-functions "${TOP_FUNCTIONS}" \
  --max-time-bins "${MAX_TIME_BINS}" \
  --max-trace-bytes "${MAX_TRACE_BYTES}" \
  --run-label "${OPENFOAM_PROFILE_LABEL:-openfoam}"
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
