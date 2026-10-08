#!/usr/bin/env bash
# 計算ノードでは、PALSのCPU固定とNUMA固定（--mem-bind local）がMPI_Init中に外され、固定のないrankの
# メモリは他のNUMAノードへ散らばる（Issue #36 A3）。exec前にメモリポリシーで、各rankのメモリを
# PMI_LOCAL_RANKのNUMAノード（1 NUMAノードあたり16 core）へ固定する。メモリポリシーはプロセス自身の属性で、
# 外からのCPU affinityの書き換えでは変わらない。
set -euo pipefail

# Issue #59 A：PGOの学習はsimpleFoamだけで行う。simpleFoamのrankは、実行回数を別のdirectoryへ書く。
if [[ "${1##*/}" == simpleFoam ]]; then export GCOV_PREFIX="${TMPDIR}/pgo/simpleFoam"; fi
exec numactl --membind="$(( PMI_LOCAL_RANK / 16 ))" "$@"
