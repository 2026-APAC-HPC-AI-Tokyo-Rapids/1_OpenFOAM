#!/usr/bin/env bash

set -euo pipefail

: "${OPENFOAM_PROFILE_DIR:?}"
: "${OPENFOAM_PROFILE_LABEL:?}"

analysis="${1:?VTune analysis type is required}"
shift

result_dir="${OPENFOAM_PROFILE_DIR}/vtune-${OPENFOAM_PROFILE_LABEL}-${analysis}"
log_dir="${PROVISION_DIR:?}/logs"
collect_args=(
  -collect "${analysis}"
  -knob enable-stack-collection=true
)
if [[ "${analysis}" == hpc-performance ]]; then
  collect_args+=(
    -knob collect-memory-bandwidth=true
    -knob collect-affinity=true
  )
fi
mkdir -p "${result_dir}" "${log_dir}"

echo "VTune ${analysis} result: ${result_dir}"
vtune "${collect_args[@]}" \
  -result-dir "${result_dir}" \
  -- "$@"

vtune -report summary \
  -result-dir "${result_dir}" \
  -report-output "${result_dir}/summary.txt"
cp "${result_dir}/summary.txt" \
  "${log_dir}/vtune-${OPENFOAM_PROFILE_LABEL}-${analysis}-summary.txt"

if [[ "${analysis}" == hotspots ]]; then
  vtune -report hotspots \
    -result-dir "${result_dir}" \
    -group-by function \
    -format csv \
    -report-output "${result_dir}/hotspots.csv"
  cp "${result_dir}/hotspots.csv" \
    "${log_dir}/vtune-${OPENFOAM_PROFILE_LABEL}-hotspots.csv"
fi
