#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "使用方法: $0 RUN_MANIFEST TARGET_ROOT" >&2
  exit 64
fi
run_manifest=$1
target_root=$2
[[ "${run_manifest}" == /* && "${target_root}" == /* ]]
install -D -m 0444 "${run_manifest}" "${target_root}/control/run-manifest.json"
install -d -m 0755 "${target_root}/source/placement"
