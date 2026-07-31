#!/usr/bin/env bash

set -euo pipefail

: "${PROFILE_RESULT_DIR:?}"
: "${PROVISION_DIR:?}"

VTUNE_RESULT_DIR="${PROFILE_RESULT_DIR}/vtune"
SUMMARY_DIR="${PROFILE_RESULT_DIR}/browser-summary"
MAX_TIME_BINS="${OPENFOAM_VTUNE_TIME_BINS:-300}"
TOP_FUNCTIONS="${OPENFOAM_VTUNE_TOP_FUNCTIONS:-20}"
MAX_TRACE_BYTES="${OPENFOAM_VTUNE_MAX_TRACE_BYTES:-5000000}"

[[ -d "${VTUNE_RESULT_DIR}" ]] || {
  printf 'VTune result directory was not found: %s\n' "${VTUNE_RESULT_DIR}" >&2
  exit 2
}
command -v vtune >/dev/null
install -d -m 0700 "${SUMMARY_DIR}"

# Timelineはブラウザ表示に必要な時間ビンへ集約してから出力する。Hotspotsは
# 変換スクリプト側で上位関数だけを残す。
vtune -report timeline \
  -result-dir "${VTUNE_RESULT_DIR}" \
  -report-knob column-by=CPUTime \
  -report-knob "bin-count=${MAX_TIME_BINS}" \
  -format csv \
  -csv-delimiter comma \
  -report-output "${SUMMARY_DIR}/timeline.csv"

vtune -report hotspots \
  -result-dir "${VTUNE_RESULT_DIR}" \
  -group-by function,module \
  -format csv \
  -csv-delimiter comma \
  -report-output "${SUMMARY_DIR}/hotspots.csv"

python3 "${PROVISION_DIR}/scripts/vtune-to-trace.py" \
  --timeline "${SUMMARY_DIR}/timeline.csv" \
  --hotspots "${SUMMARY_DIR}/hotspots.csv" \
  --output "${SUMMARY_DIR}/openfoam-vtune-trace.json.gz" \
  --summary "${SUMMARY_DIR}/summary.json" \
  --top-functions "${TOP_FUNCTIONS}" \
  --max-time-bins "${MAX_TIME_BINS}" \
  --max-trace-bytes "${MAX_TRACE_BYTES}" \
  --run-label "${OPENFOAM_PROFILE_LABEL:-openfoam}"

cp "${SUMMARY_DIR}/summary.json" \
  "${SUMMARY_DIR}/openfoam-vtune-trace.json.gz" \
  "${PROVISION_DIR}/logs/"
