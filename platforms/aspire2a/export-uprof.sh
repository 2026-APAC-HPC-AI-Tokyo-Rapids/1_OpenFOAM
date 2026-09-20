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
mapfile -t sessions < <(find "${output_root}/sessions" -mindepth 1 -maxdepth 1 -type d -name 'AMDuProf-*' -print)
[[ "${#sessions[@]}" -eq 1 ]]
session=${sessions[0]}
"${uprof_cli}" report --input-dir "${session}" --host all --detail --cutoff 30 > "${output_root}/report.stdout" 2> "${output_root}/report.stderr"
test -s "${session}/report.csv"
install -m 0640 "${session}/report.csv" "${output_root}/report.csv"
printf 'session=%s\n' "$(basename -- "${session}")" > "${output_root}/session.txt"
