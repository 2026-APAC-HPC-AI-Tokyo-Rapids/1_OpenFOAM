#!/usr/bin/env bash

set -euo pipefail

: "${PJM_JOB_ID:?}"
: "${RUN_DIR:?}"

if timeout --foreground 45s pjwait -z "${PJM_JOB_ID}"; then
  sleep 1
  pjwait "${PJM_JOB_ID}"
  if [[ ! -e "${RUN_DIR}/run-success" ]]; then
    echo 'OpenFOAMジョブがrun-successを生成しませんでした' >&2
    tail -n 240 "${RUN_DIR}/logs/${PJM_JOB_ID}.pjm.log" >&2 || true
    tail -n 240 "${RUN_DIR}/logs/solver.log" >&2 || true
    exit 1
  fi
  exit 0
else
  status=$?
fi

if [[ "${status}" -eq 124 ]]; then
  tail -n 40 "${RUN_DIR}/logs/${PJM_JOB_ID}.pjm.log" 2>/dev/null || true
  exit 75
fi

exit "${status}"
