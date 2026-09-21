#!/usr/bin/env bash

set -euo pipefail

: "${PMI_LOCAL_RANK:?PALS local rank is required}"
if [[ ! "${PMI_LOCAL_RANK}" =~ ^[0-9]+$ ]]; then printf 'invalid PALS local rank: %s\n' "${PMI_LOCAL_RANK}" >&2; exit 2; fi
if [[ "$#" -eq 0 ]]; then printf '%s\n' 'rank command is required' >&2; exit 2; fi

exec /usr/bin/taskset --cpu-list "${PMI_LOCAL_RANK}" "$@"
