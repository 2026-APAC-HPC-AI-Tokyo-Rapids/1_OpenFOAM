#!/usr/bin/env bash
# solverとIMBの後に、このノードのDRAM帯域をtriadで測る（Issue #61、計測区間の外）。配置は3つ。
# full128は全128コア、spread64はL3ごとに4コア（16個のL3、8つのNUMA）、packed64はL3ごとに8コア
# （8個のL3、各ソケット2つずつの4つのNUMA）で、各runのrank配置と同じCPUをOMP_PLACESに並べる。
set -euo pipefail

triad=$1
host=$(hostname)
declare -A layouts
layouts[full128]=$(seq -s ' ' 0 127)
layouts[spread64]=$(for l in $(seq 0 63); do printf '%d ' $(( l / 4 * 8 + l % 4 )); done)
layouts[packed64]=$(for l in $(seq 0 63); do printf '%d ' $(( l / 32 * 64 + l % 32 )); done)
for layout in full128 spread64 packed64; do
  read -r -a cpus <<< "${layouts[${layout}]}"
  places=$(printf '{%d},' "${cpus[@]}")
  result=$(OMP_NUM_THREADS="${#cpus[@]}" OMP_PLACES="${places%,}" OMP_PROC_BIND=close "${triad}")
  printf 'triad host=%s layout=%s %s\n' "${host}" "${layout}" "${result}"
done
