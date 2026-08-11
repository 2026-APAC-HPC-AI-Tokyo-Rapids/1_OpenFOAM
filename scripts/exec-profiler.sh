#!/usr/bin/env bash

set -euo pipefail

# このスクリプトは、引数で指定されたプロセスをプロファイラで観測する。
# MPI の起動は呼び出し側が行い、このスクリプト自身は MPI ランチャーを起動しない。
: "${OPENFOAM_PROFILE_DIR:?}"
: "${1:?観測対象のプロセスを指定してください}"

# 実行結果とログの保存先を準備する。
install -d -m 0700 "${OPENFOAM_PROFILE_DIR}"

# 提出用の通常実行はプロファイラを付けず、計測時だけ環境変数で明示的に選ぶ。
# これにより、ソースを編集せず同じ起動経路で通常実行とプロファイルを切り替えられる。
case "${OPENFOAM_PROFILE_MODE:-direct}" in
  direct)
    exec "$@"
    ;;
  perf-stat)
    : "${OPENFOAM_PERF_PATH:?validated perf path is required}"
    exec "${OPENFOAM_PERF_PATH}" stat -x, -o "${OPENFOAM_PROFILE_DIR}/perf-stat.csv" \
      -e cycles,instructions,branches,branch-misses,cache-misses -- "$@"
    ;;
  vtune-hotspots)
    : "${OPENFOAM_VTUNE_RESULT_DIR:?VTune result directory is required}"
    command -v vtune >/dev/null
    exec vtune -collect hotspots \
      -knob enable-stack-collection=true \
      -result-dir "${OPENFOAM_VTUNE_RESULT_DIR}" -- "$@"
    ;;
  *)
    printf 'Unknown OPENFOAM_PROFILE_MODE: %s\n' \
      "${OPENFOAM_PROFILE_MODE}" >&2
    exit 2
    ;;
esac
