#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "使用方法: $0 AMDUPROF_CLI SESSION_ROOT ANALYSIS TARGET [ARGUMENT ...]" >&2
  exit 64
fi

uprof_cli=$1
session_root=$2
analysis=$3
shift 3
[[ "${uprof_cli}" == /* && "${session_root}" == /* ]]
test -x "${uprof_cli}"
host=$(/bin/hostname)
[[ "${host}" =~ ^[A-Za-z0-9._-]+$ ]]
: "${PMI_RANK:?global MPI rank is required}"
: "${PMI_LOCAL_RANK:?local MPI rank is required}"
[[ "${PMI_RANK}" =~ ^[0-9]+$ && "${PMI_LOCAL_RANK}" =~ ^[0-9]+$ ]]
# 128 physical cores are split into eight 16-core NUMA domains on each node.
profile_rank_stride=16
if (( PMI_LOCAL_RANK % profile_rank_stride != 0 )); then exec "$@"; fi
uprof_bin_dir=$(dirname -- "${uprof_cli}")
export LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
rank_session_root="${session_root}/${host}/rank-${PMI_RANK}"
install -d -m 0750 "${rank_session_root}"
case "${analysis}" in
  hotspots) exec "${uprof_cli}" collect --config hotspots -g --output-dir "${rank_session_root}" "$@" ;;
  assess|data_access) exec "${uprof_cli}" collect --config "${analysis}" --output-dir "${rank_session_root}" "$@" ;;
  *) printf '未対応のAMD uProf解析です: %s\n' "${analysis}" >&2; exit 2 ;;
esac
