#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "使用方法: $0 TARGET_ARGV_FILE" >&2
  exit 64
fi

target_argv_file=$1
[[ "${target_argv_file}" == /* ]]
mapfile -d '' -t target_argv < "${target_argv_file}"
[[ "${#target_argv[@]}" -gt 0 ]]
[[ "${target_argv[0]}" == /* ]]
test -x "${target_argv[0]}"
exec "${target_argv[@]}"
