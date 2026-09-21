#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "使用方法: $0 AMDUPROF_CLI OUTPUT_ROOT" >&2
  exit 64
fi

uprof_cli=$1
output_root=$2
[[ "${uprof_cli}" == /* && "${output_root}" == /* ]]
test -x "${uprof_cli}"
uprof_bin_dir=$(dirname -- "${uprof_cli}")
export LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
: "${OPENFOAM_NODES:?expected node count is required}"
[[ "${OPENFOAM_NODES}" =~ ^[0-9]+$ ]]
mapfile -t host_roots < <(find "${output_root}/sessions" -mindepth 1 -maxdepth 1 -type d -print | LC_ALL=C sort)
[[ "${#host_roots[@]}" -eq "${OPENFOAM_NODES}" ]]
install -d -m 0750 "${output_root}/reports"
: > "${output_root}/session.txt"
for host_root in "${host_roots[@]}"
do
  host=$(basename -- "${host_root}")
  [[ "${host}" =~ ^[A-Za-z0-9._-]+$ ]]
  mapfile -t sessions < <(find "${host_root}" -mindepth 1 -maxdepth 1 -type d -name 'AMDuProf-*' -print)
  [[ "${#sessions[@]}" -eq 1 ]]
  session=${sessions[0]}
  "${uprof_cli}" report --input-dir "${session}" --host "${host}" --detail --cutoff 0 > "${output_root}/reports/${host}.stdout" 2> "${output_root}/reports/${host}.stderr"
  test -s "${session}/report.csv"
  install -m 0640 "${session}/report.csv" "${output_root}/reports/${host}.csv"
  printf 'host=%s session=%s\n' "${host}" "$(basename -- "${session}")" >> "${output_root}/session.txt"
done
