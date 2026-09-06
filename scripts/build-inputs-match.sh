#!/usr/bin/env bash
set -euo pipefail

cluster="${1:?cluster is required}"
sidecar="${2:?build sidecar is required}"
case "${cluster}" in
  genkai|gadi) ;;
  *) exit 64 ;;
esac

# 再利用runのcommitではなく、archiveを生成した元のcommitを比較する。
definition_oid=$(jq -er '.source_commits[] | select(.commit_role == "build_definition") | .oid' "${sidecar}")
openfoam_oid=$(jq -er '.source_commits[] | select(.commit_role == "openfoam_source") | .oid' "${sidecar}")
thirdparty_oid=$(jq -er '.source_commits[] | select(.commit_role == "thirdparty_source") | .oid' "${sidecar}")
[[ "${openfoam_oid}" == "${OPENFOAM_SOURCE_OID:?}" && "${thirdparty_oid}" == "${THIRDPARTY_SOURCE_OID:?}" ]]

# modules、compiler flags、Scotch取得、native utilities、archiveへ導入するprobeが
# build入力。runtime、解析、文書の変更はarchiveを無効にしない。
git diff --quiet "${definition_oid}" "${GITHUB_SHA:?}" -- scripts/build-openfoam.sh scripts/build-openfoam-task.sh "platforms/${cluster}/build-environment.sh" experiment-metrics/native experiment-metrics/src/experiment_metrics/probes/capture_hardware.py
