#!/usr/bin/env bash

set -euo pipefail

: "${VTUNE_RESULT_DIR:?VTune result directory is required}"
: "${PROVISION_DIR:?Provision directory is required}"
: "${RUN_DIR:?Run directory is required}"

RUN_LABEL=${RUN_LABEL:-$(basename -- "${RUN_DIR}")}
MAX_TIME_BINS=${OPENFOAM_VTUNE_TIME_BINS:-300}
FUNCTION_BINS=${OPENFOAM_VTUNE_FUNCTION_BINS:-40}
TOP_FUNCTIONS=${OPENFOAM_VTUNE_TOP_FUNCTIONS:-50}
TIME_SERIES_FUNCTIONS=${OPENFOAM_VTUNE_TIME_SERIES_FUNCTIONS:-12}
FUNCTIONS_PER_WINDOW=${OPENFOAM_VTUNE_FUNCTIONS_PER_WINDOW:-8}
MAX_TRACE_BYTES=${OPENFOAM_VTUNE_MAX_TRACE_BYTES:-5000000}

for value_name in MAX_TIME_BINS FUNCTION_BINS TOP_FUNCTIONS \
  TIME_SERIES_FUNCTIONS FUNCTIONS_PER_WINDOW MAX_TRACE_BYTES
do
  value=${!value_name}
  [[ "${value}" =~ ^[1-9][0-9]*$ ]] || {
    printf '%s must be a positive integer, got %s\n' \
      "${value_name}" "${value}" >&2
    exit 2
  }
done

[[ -d "${VTUNE_RESULT_DIR}" ]]
command -v vtune >/dev/null
python_path="${PROVISION_DIR}/experiment-metrics/.venv/bin/python"
[[ -x "${python_path}" ]]

output_dir="${RUN_DIR}/profile/raw/vtune-perfetto"
slices_dir="${output_dir}/function-slices"
install -d -m 0700 "${output_dir}" "${slices_dir}"

# VTune 2025 may leave -report-output empty, so keep stdout as the canonical
# CSV input. The timeline and fixed windows provide chronological data instead
# of stretching aggregate hotspot totals across the whole solver run.
vtune -quiet -report timeline \
  -result-dir "${VTUNE_RESULT_DIR}" \
  -report-knob column-by=CPUTime \
  -report-knob "bin-count=${MAX_TIME_BINS}" \
  -format csv -csv-delimiter comma \
  > "${output_dir}/timeline.csv"

vtune -quiet -report hotspots \
  -result-dir "${VTUNE_RESULT_DIR}" \
  -group-by function,module \
  -column time \
  -format csv -csv-delimiter comma \
  > "${output_dir}/hotspots.csv"

timeline_start=$(awk -F, '/^[0-9]+,/ { print $2; exit }' \
  "${output_dir}/timeline.csv")
timeline_end=$(awk -F, '/^[0-9]+,/ { end=$3 } END { print end }' \
  "${output_dir}/timeline.csv")
[[ -n "${timeline_start}" && -n "${timeline_end}" ]]

printf 'file,start_sec,end_sec\n' > "${slices_dir}/windows.csv"
for ((slice_index = 0; slice_index < FUNCTION_BINS; slice_index++)); do
  read -r slice_start slice_end < <(
    awk -v start="${timeline_start}" -v end="${timeline_end}" \
      -v slice="${slice_index}" -v count="${FUNCTION_BINS}" \
      'BEGIN {
        duration = end - start
        printf "%.6f %.6f\n",
          start + duration * slice / count,
          start + duration * (slice + 1) / count
      }'
  )
  printf -v slice_name '%04d.csv' "${slice_index}"
  printf '%s,%s,%s\n' "${slice_name}" "${slice_start}" "${slice_end}" \
    >> "${slices_dir}/windows.csv"
  vtune -quiet -report hotspots \
    -result-dir "${VTUNE_RESULT_DIR}" \
    -group-by function,module \
    -column time \
    -time-filter "${slice_start}:${slice_end}" \
    -format csv -csv-delimiter comma \
    > "${slices_dir}/${slice_name}"
done

converter_args=(
  --timeline "${output_dir}/timeline.csv"
  --hotspots "${output_dir}/hotspots.csv"
  --function-slices-dir "${slices_dir}"
  --solver-log "${RUN_DIR}/logs/solver.log"
  --output "${output_dir}/openfoam-vtune-perfetto.json"
  --summary "${output_dir}/summary.json"
  --run-label "${RUN_LABEL}"
  --top-functions "${TOP_FUNCTIONS}"
  --time-series-functions "${TIME_SERIES_FUNCTIONS}"
  --functions-per-window "${FUNCTIONS_PER_WINDOW}"
  --max-time-bins "${MAX_TIME_BINS}"
  --max-trace-bytes "${MAX_TRACE_BYTES}"
)

"${python_path}" "${PROVISION_DIR}/scripts/vtune-to-perfetto.py" \
  "${converter_args[@]}"

test -s "${output_dir}/openfoam-vtune-perfetto.json"
test -s "${output_dir}/summary.json"
