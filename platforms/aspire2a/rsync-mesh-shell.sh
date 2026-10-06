#!/usr/bin/env bash
set -euo pipefail
# rsync supplies this logical host before its remote server command.
[[ ${1:-} == aspire2a-mesh ]]
shift
exec aspire2a-shell "$@"
