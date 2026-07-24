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

# 通常実行: プロファイラを使わず、引数で指定されたプロセスを直接実行する。
# プロファイリングを行う場合は、この行をコメントアウトする。
exec "$@"

# 実行時間・メモリ使用量を計測する場合は、上の通常実行をコメントアウトして
# 次の行を有効にする。
# exec /usr/bin/time -v -o "${PROFILE_TIMING_LOG}" "$@"

# Intel MPI の通信統計を収集する場合は、上の通常実行をコメントアウトして
# 次の行を有効にする。APS は引数で指定されたプロセスを計測する。
# exec aps \
#   --result-dir="${PROFILE_RESULT_DIR}" \
#   --collection-mode=all \
#   --stat-level=5 \
#   --mpi-imbalance=2 \
#   --storage-format=compact \
#   "$@"

# VTune のホットスポットを収集する場合は、上の通常実行をコメントアウトして
# 次の行を有効にする。VTune は引数で指定されたプロセスを計測する。
# exec vtune \
#   -collect hotspots \
#   -knob enable-stack-collection=true \
#   -result-dir "${PROFILE_RESULT_DIR}" \
#   -- "$@"
