#!/usr/bin/env bash

set -euo pipefail

: "${OPENFOAM_VTUNE_RESULT_DIR:?}"
: "${OPENFOAM_VTUNE_RANK:?}"
: "${OPENFOAM_VTUNE_STATUS_PATH:?}"
: "${OPENFOAM_VTUNE_PATH:?}"
: "${OPENFOAM_VTUNE_ANALYSIS:?}"
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
  printf 'VTune結果ディレクトリは%sに1件必要ですが、%d件見つかりました\n' "${OPENFOAM_VTUNE_RESULT_DIR}" "${#result_dirs[@]}" >&2
  exit 2
}

summary_dir="${RUN_DIR}/profile/raw/vtune-summary"
install -d -m 0700 "${summary_dir}"

# VTune 2025はレポート生成に成功しても-report-outputへ空ファイルを返す場合が
# あるため、CSVレポートは標準出力から取得する。
"${OPENFOAM_VTUNE_PATH}" -quiet -report hotspots -result-dir "${result_dirs[0]}" -group-by function,module -column time -format csv -csv-delimiter comma > "${summary_dir}/hotspots.csv"

if [[ "${OPENFOAM_VTUNE_ANALYSIS}" == hpc-performance ]]; then
  "${OPENFOAM_VTUNE_PATH}" -quiet -report summary -result-dir "${result_dirs[0]}" > "${summary_dir}/hpc-summary.txt"
  "${OPENFOAM_VTUNE_PATH}" -quiet -report hotspots -result-dir "${result_dirs[0]}" -group-by function,module -column "CPU Time:Self,Memory Bound:Self,Memory Bound:L1 Bound:Self,Memory Bound:L2 Bound:Self,Memory Bound:L3 Bound:Self,Memory Bound:DRAM Bound:Self,Vectorization:Self,Vectorization:% of FP Ops:Self,Vectorization:FP Arith/Mem Rd Instr. Ratio:Self,Vectorization:FP Arith/Mem Wr Instr. Ratio:Self,Instructions Retired:Self,CPI Rate:Self,Average CPU Frequency:Self" -format csv -csv-delimiter comma > "${summary_dir}/hpc-functions.csv"
fi

if [[ "${OPENFOAM_VTUNE_ANALYSIS}" == memory-access ]]; then
  "${OPENFOAM_VTUNE_PATH}" -quiet -report summary -result-dir "${result_dirs[0]}" > "${summary_dir}/memory-summary.txt"
  "${OPENFOAM_VTUNE_PATH}" -quiet -report hotspots -result-dir "${result_dirs[0]}" -group-by function,module -format csv -csv-delimiter comma > "${summary_dir}/memory-functions.csv"
fi

if ! "${PROVISION_DIR}/experiment-metrics/.venv/bin/experiment-metrics" record-profile-vtune --manifest "${RUN_MANIFEST}" --runtime-dir "${RUN_DIR}" --report "${summary_dir}/hotspots.csv" --status "${OPENFOAM_VTUNE_STATUS_PATH}" --summary "${summary_dir}/summary.json" --markdown "${summary_dir}/summary.md" --profiled-rank "${OPENFOAM_VTUNE_RANK}" --analysis-type "${OPENFOAM_VTUNE_ANALYSIS}" --collection-duration-sec "${OPENFOAM_VTUNE_DURATION_SEC}"
then
  sed -n '1,80p' "${summary_dir}/hotspots.csv" >&2
  exit 1
fi
