#!/usr/bin/env bash

set -euo pipefail

# このスクリプトは、引数で指定されたプロセスをプロファイラで観測する。
# MPI の起動は呼び出し側が行い、このスクリプト自身は MPI ランチャーを起動しない。
: "${OPENFOAM_PROFILE_DIR:?}"
: "${OPENFOAM_PROFILE_LABEL:?}"
: "${PROVISION_DIR:?}"
: "${1:?観測対象のプロセスを指定してください}"

# 実行結果とログの保存先を準備する。
export PROFILE_LOG_DIR="${PROVISION_DIR}/logs"
export PROFILE_RESULT_DIR="${OPENFOAM_PROFILE_DIR}/${OPENFOAM_PROFILE_LABEL}"
export PROFILE_TIMING_LOG="${PROFILE_LOG_DIR}/time-${OPENFOAM_PROFILE_LABEL}.txt"
install -d -m 0700 "${PROFILE_LOG_DIR}" "${PROFILE_RESULT_DIR}"

# コメントの編集ではなく実験条件からプロファイラを選べるようにする。既存runと
# 同じ挙動を保つため、未指定時はperf statを使う。
case "${OPENFOAM_PROFILE_MODE:-perf-stat}" in
  none)
    exec "$@"
    ;;
  perf-stat)
    exec perf stat -x, -o "${PROFILE_TIMING_LOG}" \
      -e cycles,instructions,branches,branch-misses,cache-misses -- "$@"
    ;;
  time)
    exec /usr/bin/time -v -o "${PROFILE_TIMING_LOG}" "$@"
    ;;
  aps)
    exec aps --result-dir="${PROFILE_RESULT_DIR}" \
      --collection-mode=all --stat-level=5 --mpi-imbalance=2 \
      --storage-format=compact "$@"
    ;;
  vtune-hotspots)
    command -v vtune >/dev/null
    exec vtune -collect hotspots \
      -knob enable-stack-collection=true \
      -result-dir "${PROFILE_RESULT_DIR}/vtune" -- "$@"
    ;;
  *)
    printf 'Unknown OPENFOAM_PROFILE_MODE: %s\n' \
      "${OPENFOAM_PROFILE_MODE}" >&2
    exit 2
    ;;
esac
