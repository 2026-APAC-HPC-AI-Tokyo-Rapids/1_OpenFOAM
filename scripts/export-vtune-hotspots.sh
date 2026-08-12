#!/usr/bin/env bash

set -euo pipefail

: "${OPENFOAM_VTUNE_RESULT_DIR:?}"
: "${OPENFOAM_VTUNE_RANK:?}"
: "${PROVISION_DIR:?}"
: "${RUN_DIR:?}"

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

command -v vtune >/dev/null
python_path="${PROVISION_DIR}/experiment-metrics/.venv/bin/python"
[[ -x "${python_path}" ]]
summary_dir="${RUN_DIR}/profile/raw/vtune-summary"
install -d -m 0700 "${summary_dir}"

# VTune 2025 may return an empty -report-output file even when the report
# succeeds, so capture the CSV report from stdout.
vtune -quiet -report hotspots \
  -result-dir "${result_dirs[0]}" \
  -group-by function,module \
  -column time \
  -format csv \
  -csv-delimiter comma \
  > "${summary_dir}/hotspots.csv"
vtune --version > "${summary_dir}/vtune-version.txt"

if ! "${python_path}" "${PROVISION_DIR}/scripts/vtune-hotspots-summary.py" \
  --hotspots "${summary_dir}/hotspots.csv" \
  --summary "${summary_dir}/summary.json" \
  --markdown "${summary_dir}/summary.md" \
  --profiled-rank "${OPENFOAM_VTUNE_RANK}"
then
  sed -n '1,80p' "${summary_dir}/hotspots.csv" >&2
  exit 1
fi
