#!/usr/bin/env bash

set -euo pipefail

if [[ "${1:-}" == --version && $# -eq 1 ]]; then printf '%s\n' 'mpi-temporal-profile/v1'; exit 0; fi
if [[ $# -lt 3 ]]; then printf 'Usage: %s LIBRARY OUTPUT_DIR TARGET [ARGUMENT ...]\n' "$0" >&2; exit 64; fi

library=$1
output_dir=$2
shift 2
[[ "${library}" == /* && -f "${library}" && "${output_dir}" == /* && "$1" == /* ]]
: "${PMI_RANK:?global MPI rank is required}"
[[ "${PMI_RANK}" =~ ^[0-9]+$ ]]
[[ -d "${output_dir}" ]]
export MPI_TIMING_DIR="${output_dir}"
export LD_PRELOAD="${LD_PRELOAD:+${LD_PRELOAD}:}${library}"
exec "$@"
