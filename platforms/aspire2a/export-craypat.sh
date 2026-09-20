#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "使用方法: $0 CRAYPAT_EXPERIMENT OUTPUT_ROOT" >&2
  exit 64
fi

experiment_dir=$1
output_root=$2
[[ "${experiment_dir}" == /* && "${output_root}" == /* ]]
test -d "${experiment_dir}"
module load perftools-base
pat_report -f ap2 "${experiment_dir}"
pat_report -o "${output_root}/summary.txt" "${experiment_dir}"
pat_report -f html -o "${output_root}/html" "${experiment_dir}"
find "${experiment_dir}/ap2-files" -type f -name '*.ap2' -size +0c -print -quit | grep -q .
test -s "${experiment_dir}/index.ap2"
test -s "${output_root}/html/pat_report.html"
