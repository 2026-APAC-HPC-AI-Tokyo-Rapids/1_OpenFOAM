#!/usr/bin/env bash

set -euo pipefail

start_ns=$(date +%s%N)
status=0
"$@" || status=$?
end_ns=$(date +%s%N)

if [[ -n "${BUILD_PROFILER_TIMING_FILE:-}" ]]; then
  printf '%s\n' "$((end_ns - start_ns))" > "${BUILD_PROFILER_TIMING_FILE}"
fi

exit "${status}"
