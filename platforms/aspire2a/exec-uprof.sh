#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "使用方法: $0 AMDUPROF_CLI COMMAND [ARGUMENT ...]" >&2
  exit 64
fi

uprof_cli=$1
shift
[[ "${uprof_cli}" == /* ]]
test -x "${uprof_cli}"
uprof_bin_dir=$(dirname -- "${uprof_cli}")
export LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
exec "${uprof_cli}" "$@"
