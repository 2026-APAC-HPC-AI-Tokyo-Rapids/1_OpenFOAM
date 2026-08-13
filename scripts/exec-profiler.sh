#!/usr/bin/env bash

set -euo pipefail

# このスクリプトは、引数で指定されたプロセスをプロファイラで観測する。
# MPI の起動は呼び出し側が行い、このスクリプト自身は MPI ランチャーを起動しない。
: "${1:?観測対象のプロセスを指定してください}"
: "${OPENFOAM_VTUNE_RESULT_DIR:?VTune result directory is required}"
: "${OPENFOAM_VTUNE_STATUS_PATH:?VTune status path is required}"
: "${OPENFOAM_VTUNE_PATH:?validated VTune path is required}"
: "${OPENFOAM_VTUNE_ANALYSIS:?validated VTune analysis is required}"
: "${PROVISION_DIR:?provision directory is required}"
: "${OPENFOAM_VTUNE_DURATION_SEC:=60}"
[[ "${OPENFOAM_VTUNE_DURATION_SEC}" =~ ^[1-9][0-9]*$ ]]
[[ "${OPENFOAM_VTUNE_PATH}" == /* && -x "${OPENFOAM_VTUNE_PATH}" ]]
target_launcher="${PROVISION_DIR}/scripts/allow-vtune-attach.py"
[[ -x "${target_launcher}" ]]
install -d -m 0700 "$(dirname -- "${OPENFOAM_VTUNE_STATUS_PATH}")"

case "${OPENFOAM_VTUNE_ANALYSIS}" in
  hotspots)
    "${target_launcher}" "$@" &
    target_pid=$!
    terminate_target() {
      kill -TERM "${target_pid}" 2>/dev/null || true
      wait "${target_pid}" 2>/dev/null || true
      exit 143
    }
    trap terminate_target TERM INT
    set +e
    "${OPENFOAM_VTUNE_PATH}" -collect hotspots -knob sampling-mode=sw -knob enable-stack-collection=false -duration="${OPENFOAM_VTUNE_DURATION_SEC}" -result-dir "${OPENFOAM_VTUNE_RESULT_DIR}" -target-pid "${target_pid}"
    vtune_status=$?
    wait "${target_pid}"
    target_status=$?
    set -e
    ;;
  hpc-performance)
    set +e
    "${OPENFOAM_VTUNE_PATH}" -collect hpc-performance -knob enable-stack-collection=true -knob collect-memory-bandwidth=true -knob dram-bandwidth-limits=false -knob analyze-openmp=false -duration="${OPENFOAM_VTUNE_DURATION_SEC}" -return-app-exitcode -result-dir "${OPENFOAM_VTUNE_RESULT_DIR}" -- "$@"
    target_status=$?
    # -return-app-exitcode makes the CLI status authoritative for the target.
    # Report generation below independently validates the collection result.
    vtune_status=0
    set -e
    ;;
  *) printf 'Unsupported VTune analysis: %s\n' "${OPENFOAM_VTUNE_ANALYSIS}" >&2; exit 2 ;;
esac
status_tmp="${OPENFOAM_VTUNE_STATUS_PATH}.tmp-$$"
printf '{"schema_version":"vtune-collection-status/v1","target_exit_code":%d,"vtune_exit_code":%d}\n' "${target_status}" "${vtune_status}" > "${status_tmp}"
mv -- "${status_tmp}" "${OPENFOAM_VTUNE_STATUS_PATH}"

# The solver target remains authoritative. Collection failures are retained in
# the status source and handled independently by the post-run exporter.
exit "${target_status}"
