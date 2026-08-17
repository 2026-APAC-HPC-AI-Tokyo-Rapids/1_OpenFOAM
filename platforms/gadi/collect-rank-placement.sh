#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "使用方法: $0 LOCAL_ROOT SHARED_ROOT EXPECTED_LOCAL_RANKS" >&2
  exit 64
fi
local_root=$1
shared_root=$2
expected_local_ranks=$3
[[ "${local_root}" == /* && "${shared_root}" == /* && "${expected_local_ranks}" =~ ^[1-9][0-9]*$ ]]
shopt -s nullglob
placement_files=("${local_root}"/rank-*.json)
[[ "${#placement_files[@]}" -eq "${expected_local_ranks}" ]]
install -d -m 0755 "${shared_root}"
cp -- "${placement_files[@]}" "${shared_root}/"
