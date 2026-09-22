#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "使用方法: $0 OUTPUT_ROOT" >&2
  exit 64
fi

output_root=$1
[[ "${output_root}" == /* ]]
module use /opt/cray/pe/modulefiles
module load perftools-base/22.04.0
pat_report=$(command -v pat_report)
mapfile -t experiments < <(find "${output_root}" -mindepth 1 -maxdepth 1 -type d -name 'simpleFoam+*' -print)
[[ "${#experiments[@]}" -eq 1 ]]
"${pat_report}" -O load_balance,load_balance_cm,load_balance_sm,mpi_callers,mpi_sm_callers,mpi_coll_callers,mpi_dest_bytes -o "${output_root}/pat-report.txt" "${experiments[0]}" > "${output_root}/pat-report.stdout" 2> "${output_root}/pat-report.stderr"
test -s "${output_root}/pat-report.txt"
