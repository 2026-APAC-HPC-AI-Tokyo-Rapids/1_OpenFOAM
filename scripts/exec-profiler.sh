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
compute_tools_root=${OPENFOAM_COMPUTE_TOOLS_ROOT:-${PROVISION_DIR}}
[[ "${compute_tools_root}" == /* ]]
target_launcher="${compute_tools_root}/scripts/allow-vtune-attach.py"
install -d -m 0700 "$(dirname -- "${OPENFOAM_VTUNE_STATUS_PATH}")"
vtune_cli_log="$(dirname -- "${OPENFOAM_VTUNE_STATUS_PATH}")/collection.log"

# 60秒の収集終了と正式solverの終了は独立させる。VTuneから対象を起動すると
# duration到達時に対象rankも停止するため、すべてのanalysisで既に起動したsolverへattachする。
"${target_launcher}" "$@" &
target_pid=$!
trap 'kill -TERM "${target_pid}" 2>/dev/null || true; wait "${target_pid}" 2>/dev/null || true; exit 143' TERM INT
set +e
case "${OPENFOAM_VTUNE_ANALYSIS}" in
  hotspots)
    # attach後のVTuneは対象とは別プロセスで結果をfinalizeする。進捗表示を対象の
    # stdoutへ混ぜると公式parserがsolverの行を認識できないため、専用記録へ分離する。
    "${OPENFOAM_VTUNE_PATH}" -collect hotspots -knob sampling-mode=sw -knob enable-stack-collection=false -duration="${OPENFOAM_VTUNE_DURATION_SEC}" -result-dir "${OPENFOAM_VTUNE_RESULT_DIR}" -target-pid "${target_pid}" > "${vtune_cli_log}" 2>&1
    ;;
  hpc-performance)
    "${OPENFOAM_VTUNE_PATH}" -collect hpc-performance -knob enable-stack-collection=true -knob collect-memory-bandwidth=true -knob dram-bandwidth-limits=false -knob analyze-openmp=false -duration="${OPENFOAM_VTUNE_DURATION_SEC}" -result-dir "${OPENFOAM_VTUNE_RESULT_DIR}" -target-pid "${target_pid}" > "${vtune_cli_log}" 2>&1
    ;;
  memory-access)
    # 対象プロセスの事象と、同居ノード全体のアンコア帯域カウンタを収集する。
    "${OPENFOAM_VTUNE_PATH}" -collect memory-access -knob analyze-mem-objects=false -knob dram-bandwidth-limits=true -knob analyze-openmp=false -data-limit=0 -duration="${OPENFOAM_VTUNE_DURATION_SEC}" -result-dir "${OPENFOAM_VTUNE_RESULT_DIR}" -target-pid "${target_pid}" > "${vtune_cli_log}" 2>&1
    ;;
  memory-access-core)
    memory_access_core_events='CPU_CLK_UNHALTED.THREAD:sa=1900000,INST_RETIRED.ANY:sample:sa=1900000,MEM_INST_RETIRED.ALL_LOADS:sa=100003,MEM_INST_RETIRED.ALL_STORES:sa=100003,MEM_TRANS_RETIRED.LOAD_LATENCY_GT_4:sa=10003,DTLB_LOAD_MISSES.STLB_HIT:cmask=1:sa=10003,DTLB_LOAD_MISSES.WALK_ACTIVE:sa=10003,DTLB_LOAD_MISSES.WALK_COMPLETED_4K:sa=10003,DTLB_LOAD_MISSES.WALK_COMPLETED_2M_4M:sa=10003,DTLB_LOAD_MISSES.WALK_COMPLETED_1G:sa=10003,DTLB_STORE_MISSES.STLB_HIT:cmask=1:sa=10003,DTLB_STORE_MISSES.WALK_ACTIVE:sa=10003,DTLB_STORE_MISSES.WALK_COMPLETED_4K:sa=10003,DTLB_STORE_MISSES.WALK_COMPLETED_2M_4M:sa=10003,DTLB_STORE_MISSES.WALK_COMPLETED_1G:sa=10003,MEM_INST_RETIRED.STLB_MISS_LOADS:sa=10003,MEM_INST_RETIRED.STLB_MISS_STORES:sa=10003,MEM_LOAD_L3_MISS_RETIRED.LOCAL_DRAM:sa=10003,MEM_LOAD_L3_MISS_RETIRED.REMOTE_DRAM:sa=10003,MEM_LOAD_L3_MISS_RETIRED.REMOTE_FWD:sa=10003,MEM_LOAD_L3_MISS_RETIRED.REMOTE_HITM:sa=10003'
    "${OPENFOAM_VTUNE_PATH}" -collect-with runsa -knob enable-driverless-collection=true -knob enable-pebs-collection=true -knob event-config="${memory_access_core_events}" -data-limit=0 -duration="${OPENFOAM_VTUNE_DURATION_SEC}" -result-dir "${OPENFOAM_VTUNE_RESULT_DIR}" -target-pid "${target_pid}" > "${vtune_cli_log}" 2>&1
    ;;
  *) printf '未対応のVTune解析です: %s\n' "${OPENFOAM_VTUNE_ANALYSIS}" >&2; exit 2 ;;
esac
vtune_status=$?
wait "${target_pid}"
target_status=$?
set -e
status_tmp="${OPENFOAM_VTUNE_STATUS_PATH}.tmp-$$"
printf '{"schema_version":"vtune-collection-status/v1","target_exit_code":%d,"vtune_exit_code":%d}\n' "${target_status}" "${vtune_status}" > "${status_tmp}"
mv -- "${status_tmp}" "${OPENFOAM_VTUNE_STATUS_PATH}"

# ソルバーの終了状態を正本とする。収集失敗は状態記録に残し、実行後の出力処理で
# ソルバーとは独立に扱う。
exit "${target_status}"
