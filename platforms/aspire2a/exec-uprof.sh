#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "使用方法: $0 AMDUPROF_CLI SESSION_ROOT TARGET [ARGUMENT ...]" >&2
  exit 64
fi

uprof_cli=$1
session_root=$2
shift 2
[[ "${uprof_cli}" == /* && "${session_root}" == /* ]]
test -x "${uprof_cli}"
uprof_bin_dir=$(dirname -- "${uprof_cli}")
export LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
host=$(/bin/hostname)
[[ "${host}" =~ ^[A-Za-z0-9._-]+$ ]]
: "${PMI_RANK:?global MPI rank is required}"
[[ "${PMI_RANK}" =~ ^[0-9]+$ ]]
rank_session_root="${session_root}/${host}/rank-${PMI_RANK}"
install -d -m 0750 "${rank_session_root}"
exec "${uprof_cli}" collect --config hotspots -g --output-dir "${rank_session_root}" "$@"
