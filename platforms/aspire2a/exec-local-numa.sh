#!/usr/bin/env bash
# 計算ノードでは、PALSのCPU固定とNUMA固定（--mem-bind local）がMPI_Init中に外され、固定のないrankの
# メモリは他のNUMAノードへ散らばる（Issue #36 A3）。exec前にメモリポリシーで、各rankのメモリを
# そのrankを固定するCPU（rank-cpus.txtのPMI_LOCAL_RANK番目、Issue #61）のNUMAノード（1 NUMAノードあたり16 core）へ固定する。
# メモリポリシーはプロセス自身の属性で、外からのCPU affinityの書き換えでは変わらない。
set -euo pipefail

read -r -a rank_cpus < "${BASH_SOURCE[0]%/*}/rank-cpus.txt"
exec numactl --membind="$(( rank_cpus[PMI_LOCAL_RANK] / 16 ))" "$@"
