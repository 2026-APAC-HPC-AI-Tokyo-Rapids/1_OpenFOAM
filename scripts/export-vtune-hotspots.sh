#!/usr/bin/env bash

set -euo pipefail

: "${OPENFOAM_VTUNE_RESULT_DIR:?}"
: "${OPENFOAM_VTUNE_RANK:?}"
: "${OPENFOAM_VTUNE_STATUS_PATH:?}"
: "${OPENFOAM_VTUNE_PATH:?}"
: "${PROVISION_DIR:?}"
: "${RUN_DIR:?}"
: "${RUN_MANIFEST:?}"
: "${OPENFOAM_VTUNE_DURATION_SEC:=60}"

result_dirs=()
for candidate in "${OPENFOAM_VTUNE_RESULT_DIR}" "${OPENFOAM_VTUNE_RESULT_DIR}".*
do
  [[ -d "${candidate}" ]] && result_dirs+=("${candidate}")
done
[[ "${#result_dirs[@]}" -eq 1 ]] || {
  printf 'Expected one VTune result directory for %s, found %d\n' \
    "${OPENFOAM_VTUNE_RESULT_DIR}" "${#result_dirs[@]}" >&2
  exit 2
}

[[ "${OPENFOAM_VTUNE_PATH}" == /* && -x "${OPENFOAM_VTUNE_PATH}" ]]
summary_dir="${RUN_DIR}/profile/raw/vtune-summary"
install -d -m 0700 "${summary_dir}"

# VTune 2025 may return an empty -report-output file even when the report
# succeeds, so capture the CSV report from stdout.
"${OPENFOAM_VTUNE_PATH}" -quiet -report hotspots \
  -result-dir "${result_dirs[0]}" \
  -group-by function,module \
  -column time \
  -format csv \
  -csv-delimiter comma \
  > "${summary_dir}/hotspots.csv"

if ! "${PROVISION_DIR}/experiment-metrics/.venv/bin/experiment-metrics" \
  record-profile-vtune \
  --manifest "${RUN_MANIFEST}" \
  --runtime-dir "${RUN_DIR}" \
  --registry "${PROVISION_DIR}/experiment-metrics/registry/openfoam-v2.toml" \
  --report "${summary_dir}/hotspots.csv" \
  --status "${OPENFOAM_VTUNE_STATUS_PATH}" \
  --summary "${summary_dir}/summary.json" \
  --markdown "${summary_dir}/summary.md" \
  --profiled-rank "${OPENFOAM_VTUNE_RANK}" \
  --collection-duration-sec "${OPENFOAM_VTUNE_DURATION_SEC}"
then
  sed -n '1,80p' "${summary_dir}/hotspots.csv" >&2
  exit 1
fi
