#!/usr/bin/env bash
# shellcheck source-path=SCRIPTDIR
set -euo pipefail

: "${BUILD_ARCHIVE_DIR:?}"
: "${BUILD_DIR:?}"
: "${GITHUB_RUN_ATTEMPT:?}"
: "${GITHUB_RUN_ID:?}"
: "${GITHUB_WORKSPACE:?}"
: "${OPENFOAM_SOURCE_OID:?pinned OpenFOAM source commit is required}"
: "${THIRDPARTY_SOURCE_OID:?pinned ThirdParty source commit is required}"
cluster="${1:?cluster (genkai or gadi) is required}"
build_condition=baseline
build_compile_option=Opt
build_tuning_flags=
# クラスタ別設定は並列数、追加flags、source展開とmodule/記憶領域の差だけを所有する。
case "${cluster}" in
  genkai)
    # shellcheck source=../platforms/genkai/build-environment.sh
    source "${GITHUB_WORKSPACE}/platforms/genkai/build-environment.sh"
    ;;
  gadi)
    # shellcheck source=../platforms/gadi/build-environment.sh
    source "${GITHUB_WORKSPACE}/platforms/gadi/build-environment.sh"
    ;;
  *) echo "unsupported cluster: ${cluster}" >&2; exit 64 ;;
esac
export CC=mpiicx
export CXX=mpiicpx
export CMAKE_C_COMPILER_LAUNCHER=ccache
export CMAKE_CXX_COMPILER_LAUNCHER=ccache

# ビルドツリー、ccache、一時 archive の場所を先に決めておく。
build_tree="${BUILD_DIR}/tree"
ccache_local_dir="/dev/shm/ccache-${USER:?}"
publish_tmp="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_ID}.tar.zst.${GITHUB_RUN_ATTEMPT}.tmp"
publish_sidecar_tmp="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_ID}.build-sidecar.json.${GITHUB_RUN_ATTEMPT}.tmp"
export CCACHE_BASEDIR="${build_tree}"
export CCACHE_CONFIGPATH="${HOME}/.config/ccache/ccache.conf"
export CCACHE_DIR="${ccache_local_dir}"
export CCACHE_TEMPDIR="${BUILD_DIR}/ccache-tmp"

# ビルドが中断・失敗した場合も、一時 archive を削除する。
cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -f -- "${publish_tmp}" "${publish_sidecar_tmp}" 2>/dev/null || true
  exit "${status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# 前回のビルドツリーを削除し、今回のビルドに必要なディレクトリを作成する。
rm -rf -- "${BUILD_DIR:?}"
install -d -m "${build_directory_mode}" "${BUILD_ARCHIVE_DIR}" "${build_tree}" "${BUILD_DIR}/logs" "${BUILD_DIR}/ccache-tmp"
install -d -m 0700 "${ccache_local_dir}"

prepare_build_sources
ln -s ../ThirdParty "${build_tree}/OpenFOAM/ThirdParty"

# 使用するコンパイラとccacheが利用可能であることを確認する。
for build_tool in "${CC}" "${CXX}" ccache
do
  "${build_tool}" --version
done

[[ -r "${CCACHE_CONFIGPATH}" ]]
ccache --show-config

# OpenFOAM の bashrc は未設定変数や中間コマンドの失敗を許容するため、
# 初期化中だけ厳格なエラーチェックを緩める。
set +eu
# shellcheck source=/dev/null
source "${build_tree}/OpenFOAM/etc/bashrc" WM_COMPILER=Icx WM_MPLIB=INTELMPI WM_LABEL_SIZE=32 WM_PRECISION_OPTION=DP WM_COMPILE_OPTION="${build_compile_option}" WM_COMPILE_CONTROL=+ccache
set -eu
export FOAM_EXTRA_CXXFLAGS="${build_extra_cxxflags}"
test "${FOAM_EXTRA_CXXFLAGS}" = "${build_extra_cxxflags}"

# タスク専用ビルドスクリプトが参照するプロジェクトへ移動する。
cd "${WM_PROJECT_DIR}"

# occDrivAerStaticMesh の前処理と simpleFoam に必要な対象だけをビルドする。
ccache --zero-stats
"${GITHUB_WORKSPACE}/scripts/build-openfoam-task.sh" "${build_parallelism}" "${GITHUB_WORKSPACE}/experiment-metrics/native" > "${BUILD_DIR}/logs/allwmake.log" 2>&1 || {
  build_status=$?
  grep -Eai -m 200 '(^|[[:space:]])(fatal[[:space:]]+)?error([[:space:](]|:)|undefined reference|collect2:|make(\[[0-9]+\])?: \*\*\*|wmake error' "${BUILD_DIR}/logs/allwmake.log" >&2 || true
  exit "${build_status}"
}
ccache --show-stats
finish_cluster_build

# 依存関係のない計測ツールの入口は、追跡中のソースからバイト単位で同一のまま
# 導入し、ビルド成果物が所有する実行ファイルとする。
install -m 0755 "${GITHUB_WORKSPACE}/experiment-metrics/src/experiment_metrics/probes/capture_hardware.py" "${FOAM_APPBIN}/capture-hardware"

# ツールチェーン環境と解決済みビルドパスが有効なうちに、圧縮前の意味的な入力を
# すべて記録する。圧縮ファイル自身への循環参照を避けるため、最終SHAはtar完了後に加える。
uv sync --project "${GITHUB_WORKSPACE}/experiment-metrics" --frozen --no-dev
metrics_cli="${GITHUB_WORKSPACE}/experiment-metrics/.venv/bin/experiment-metrics"
build_state="${BUILD_DIR}/build-state.json"
"${metrics_cli}" capture-build-state --output "${build_state}" --build-tree "${build_tree}" --build-definition-repo "${GITHUB_WORKSPACE}" --openfoam-oid "${openfoam_source_oid}" --openfoam-algorithm "${openfoam_source_algorithm}" --thirdparty-oid "${thirdparty_source_oid}" --thirdparty-algorithm "${thirdparty_source_algorithm}" --compiler-c "$(command -v mpiicx)" --compiler-cxx "$(command -v mpiicpx)" --mpi-launcher "$(command -v mpirun)" --precision DP --label-bits 32 --compile-flag "BUILD_CONDITION=${build_condition}" --compile-flag "WM_OPTIONS=${WM_OPTIONS:-}" --compile-flag "WM_COMPILER=${WM_COMPILER:-}" --compile-flag "WM_COMPILE_OPTION=${WM_COMPILE_OPTION:-}" --compile-flag "WM_PRECISION_OPTION=${WM_PRECISION_OPTION:-}" --compile-flag "WM_LABEL_SIZE=${WM_LABEL_SIZE:-}" --compile-flag "FOAM_EXTRA_CXXFLAGS=${FOAM_EXTRA_CXXFLAGS}" "${cluster_compile_flags[@]}" --executable "simpleFoam=${FOAM_APPBIN}/simpleFoam" --executable "decomposePar=${FOAM_APPBIN}/decomposePar" --executable "checkMesh=${FOAM_APPBIN}/checkMesh" --executable "renumberMesh=${FOAM_APPBIN}/renumberMesh" --executable "potentialFoam=${FOAM_APPBIN}/potentialFoam" --executable "applyBoundaryLayer=${FOAM_APPBIN}/applyBoundaryLayer" --executable "mesh-facts=${FOAM_APPBIN}/mesh-facts" --executable "partition-audit=${FOAM_APPBIN}/partition-audit" --executable "capture-hardware=${FOAM_APPBIN}/capture-hardware"

# ビルド済みツリーを圧縮し、後続ジョブが再利用できる archive として公開する。
tar -I zstd -cf "${publish_tmp}" -C "${build_tree}" .
"${metrics_cli}" finalize-build-sidecar --state "${build_state}" --archive "${publish_tmp}" --output "${publish_sidecar_tmp}"
mv -- "${publish_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.tar.zst"
mv -- "${publish_sidecar_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.build-sidecar.json"
echo "ビルド成果物を保存しました: ${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.tar.zst"
