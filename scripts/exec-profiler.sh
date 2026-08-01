#!/usr/bin/env bash

set -euo pipefail

# このスクリプトは、引数で指定されたプロセスをプロファイラで観測する。
# MPI の起動は呼び出し側が行い、このスクリプト自身は MPI ランチャーを起動しない。
: "${OPENFOAM_PROFILE_DIR:?}"
: "${1:?観測対象のプロセスを指定してください}"

# 実行結果とログの保存先を準備する。
install -d -m 0700 "${OPENFOAM_PROFILE_DIR}"

# perf stat で引数のプロセスと、その子プロセスの基本的なハードウェア性能を計測する。
# 比較実験ではこの行を有効にし、通常実行の行をコメントアウトする。
exec perf stat -x, -o "${OPENFOAM_PROFILE_DIR}/perf-stat.csv" \
  -e cycles,instructions,branches,branch-misses,cache-misses -- "$@"

# 通常実行: プロファイラを使わず、引数で指定されたプロセスを直接実行する。
# プロファイリングを無効にする場合は、上の perf stat をコメントアウトして
# この行を有効にする。
# exec "$@"

# 実行時間・メモリ使用量を計測する場合は、上の perf stat をコメントアウトして
# 次の行を有効にする。
# exec /usr/bin/time -v -o "${OPENFOAM_PROFILE_DIR}/resource-usage.txt" "$@"

# Intel MPI の通信統計を収集する場合は、上の perf stat をコメントアウトして
# 次の行を有効にする。APS は引数で指定されたプロセスを計測する。
# exec aps --result-dir="${OPENFOAM_PROFILE_DIR}/aps" --collection-mode=all --stat-level=5 --mpi-imbalance=2 --storage-format=compact "$@"

# VTune のホットスポットを収集する場合は、上の perf stat をコメントアウトして
# 次の行を有効にする。VTune は引数で指定されたプロセスを計測する。
# exec vtune -collect hotspots -knob enable-stack-collection=true -result-dir "${OPENFOAM_PROFILE_DIR}/vtune" -- "$@"
