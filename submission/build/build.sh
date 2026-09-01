#!/usr/bin/env bash

# occDrivAerStaticMeshで使うOpenFOAM構成要素だけをビルドする。
# 対象は領域分割、公式の前処理、検証、simpleFoamである。
set -euo pipefail

: "${WM_PROJECT_DIR:?}"
: "${WM_THIRD_PARTY_DIR:?}"

if [[ $# -ne 2 || ! $1 =~ ^[1-9][0-9]*$ ]]; then
  echo "使用方法: $0 ビルド並列数 experiment-metricsネイティブツールのルート" >&2
  exit 64
fi
build_parallelism=$1
experiment_metrics_native_root=$2

export WM_NCOMPPROCS="${build_parallelism}"
cd "${WM_PROJECT_DIR}"

# wmakeと、唯一必要な外部ライブラリを準備する。
"${WM_DIR}/src/Allmake"
"${WM_THIRD_PARTY_DIR}/makeSCOTCH" -no-mpi

# applyBoundaryLayerは非圧縮性流体用と熱物性用の両ライブラリへリンクする。
# この公式ツールとsimpleFoamのABIをそろえるため、配布元v2512のライブラリ群を
# すべてビルドする。アプリケーションは課題で必要なものだけに限定する。
src/Allwmake

for application in applications/utilities/parallelProcessing/decomposePar applications/utilities/mesh/manipulation/checkMesh applications/utilities/mesh/manipulation/renumberMesh applications/solvers/basic/potentialFoam applications/utilities/preProcessing/applyBoundaryLayer applications/solvers/incompressible/simpleFoam
do
  wmake -j "${build_parallelism}" "${application}"
done

# v2計測ツールは、このOpenFOAMソースツリーに対してコンパイルしてFOAM_APPBINへ
# 配置する。実行ファイルの正本は実行機の作業領域ではなく、公開するビルド成果物とする。
native_tree="${WM_PROJECT_DIR}/applications/utilities/experimentMetricsV2"
install -d "${native_tree}"
for utility in mesh-facts partition-audit
do
  cp -a "${experiment_metrics_native_root}/${utility}" "${native_tree}/${utility}"
  wmake -j "${build_parallelism}" "${native_tree}/${utility}"
done

# 実行環境の配備時まで不足に気付かない事態を避け、ここで実行ファイルの欠落を
# ビルド失敗として扱う。共有ライブラリの依存関係もすべて解決できることを確認する。
for application in simpleFoam decomposePar checkMesh renumberMesh potentialFoam applyBoundaryLayer mesh-facts partition-audit
do
  executable="${FOAM_APPBIN}/${application}"
  if ldd "${executable}" | grep -q 'not found'; then
    ldd "${executable}" >&2
    exit 1
  fi
done
