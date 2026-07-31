#!/usr/bin/env bash
set -euo pipefail

: "${BUILD_ARCHIVE_DIR:?}"
: "${BUILD_DIR:?}"
: "${GITHUB_RUN_ATTEMPT:?}"
: "${GITHUB_RUN_ID:?}"
: "${GITHUB_RUN_NUMBER:?}"
: "${GITHUB_WORKSPACE:?}"
: "${GIT_MIRROR_DIR:?}"
: "${SOURCE_ARCHIVE_CACHE_DIR:?}"


# ビルド仕様はここへ集約し、workflow からは実行ごとのパスと
# GitHub Actions のメタデータだけを受け取る。
export OPENFOAM_VERSION=v2606
export OPENFOAM_SOURCE_REF=refs/tags/OpenFOAM-v2606
export THIRDPARTY_SOURCE_REF=refs/heads/main
export OPENFOAM_BUILD_PARALLELISM=120
export CC=mpiicx
export CXX=mpiicpx
export CMAKE_C_COMPILER_LAUNCHER=ccache
export CMAKE_CXX_COMPILER_LAUNCHER=ccache

# ビルドツリー、ccache、一時 archive の場所を先に決めておく。
export BUILD_TREE="${BUILD_DIR}/tree"
export CCACHE_LOCAL_DIR="/dev/shm/ccache-${USER:?}"
export PUBLISH_TMP="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_NUMBER}.tar.zst.${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}.tmp"
export CCACHE_BASEDIR="${BUILD_TREE}"
export CCACHE_CONFIGPATH="${HOME}/.config/ccache/ccache.conf"
export CCACHE_DIR="${CCACHE_LOCAL_DIR}"
export CCACHE_TEMPDIR="${BUILD_DIR}/ccache-tmp"

# ビルドが中断・失敗した場合も、一時 archive を削除する。
cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -f -- "${PUBLISH_TMP}" 2>/dev/null || true
  exit "${status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# 前回のビルドツリーを削除し、今回のビルドに必要なディレクトリを作成する。
rm -rf -- "${BUILD_DIR:?}"
install -d -m 2775 "${BUILD_ARCHIVE_DIR}" "${SOURCE_ARCHIVE_CACHE_DIR}" "${BUILD_TREE}" "${BUILD_DIR}/logs" "${BUILD_DIR}/ccache-tmp"
install -d -m 0700 "${CCACHE_LOCAL_DIR}"

# OpenFOAM v2606 と対応する ThirdParty を、更新済みの共有 mirror から
# ローカル clone する。初回の GitHub からの mirror 作成は運用時に一度だけ行う。
git clone --no-checkout \
  "${GIT_MIRROR_DIR}/3_OpenFOAM_Src.git" \
  "${BUILD_TREE}/OpenFOAM"
git -C "${BUILD_TREE}/OpenFOAM" checkout --detach "${OPENFOAM_SOURCE_REF}"

git clone --no-checkout \
  "${GIT_MIRROR_DIR}/4_OpenFOAM_ThirdParty_Src.git" \
  "${BUILD_TREE}/ThirdParty"
git -C "${BUILD_TREE}/ThirdParty" checkout --detach "${THIRDPARTY_SOURCE_REF}"

# ビルドには worktree だけを使うため、成果物へ Git オブジェクトを含めない。
rm -rf -- "${BUILD_TREE}/OpenFOAM/.git" "${BUILD_TREE}/ThirdParty/.git"
ln -s ../ThirdParty "${BUILD_TREE}/OpenFOAM/ThirdParty"

# ThirdParty リポジトリが管理するスクリプトで、v2606 ビルドに必要な依存を
# 共有 archive cache から検証・展開する。
"${BUILD_TREE}/ThirdParty/download-v2606-sources.sh"

# リポジトリで管理している OpenFOAM の追加 patch を適用する。
for patch_file in "${GITHUB_WORKSPACE}"/patches/*.patch
do
  patch -d "${BUILD_TREE}" -p0 < "${patch_file}"
done

module purge
module load intel/2025.1.3 impi

# 使用するコンパイラと ccache が利用可能であることを確認する。
for build_tool in "${CC}" "${CXX}" ccache
do
  "${build_tool}" --version
done

# ccache の設定を確認し、ビルドツリー専用の統計・一時領域を使う。
[[ -r "${CCACHE_CONFIGPATH}" ]]
ccache --show-config

# OpenFOAM の bashrc は未設定変数や中間コマンドの失敗を許容するため、
# 初期化中だけ厳格なエラーチェックを緩める。
set +eu
source "${BUILD_TREE}/OpenFOAM/etc/bashrc" WM_COMPILER=Icx WM_MPLIB=INTELMPI WM_LABEL_SIZE=64 WM_PRECISION_OPTION=DP WM_COMPILE_CONTROL=+ccache
set -eu

# OpenFOAM のビルドに必要なライブラリ検索パスを設定し、実行場所を移動する。
export LD_LIBRARY_PATH="${FFTW_ARCH_PATH}/lib:${LD_LIBRARY_PATH:-}"
export FOAM_EXTRA_LDFLAGS="-Wl,-rpath-link,${FFTW_ARCH_PATH}/lib"
cd "${WM_PROJECT_DIR}"

# ccache の統計をリセットしてから、指定した並列度で OpenFOAM をビルドする。
ccache --zero-stats
"${GITHUB_WORKSPACE}/scripts/build-profiler.sh" \
  bash -o pipefail ./Allwmake -j "${OPENFOAM_BUILD_PARALLELISM}" -s \
    -log="${BUILD_DIR}/logs/allwmake.log" > /dev/null || {
  build_status=$?
  grep -Eai -m 200 '(^|[[:space:]])(fatal[[:space:]]+)?error([[:space:](]|:)|undefined reference|collect2:|make(\[[0-9]+\])?: \*\*\*|wmake error' "${BUILD_DIR}/logs/allwmake.log" >&2 || true
  exit "${build_status}"
}
ccache --show-stats

# ビルド済みツリーを圧縮し、後続ジョブが再利用できる archive として公開する。
tar -I zstd -cf "${PUBLISH_TMP}" -C "${BUILD_TREE}" .
mv -- "${PUBLISH_TMP}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
echo "Published ${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
