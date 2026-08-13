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
export OPENFOAM_SOURCE_REF=refs/heads/experiment/amul-csr
export THIRDPARTY_SOURCE_REF=refs/heads/main
export OPENFOAM_BUILD_PARALLELISM=120
export CC=mpiicx
export CXX=mpiicpx
export CMAKE_C_COMPILER_LAUNCHER=ccache
export CMAKE_CXX_COMPILER_LAUNCHER=ccache
export EXPERIMENT_METRICS_NATIVE_ROOT="${GITHUB_WORKSPACE}/experiment-metrics/native"

# ビルドツリー、ccache、一時 archive の場所を先に決めておく。
export BUILD_TREE="${BUILD_DIR}/tree"
export CCACHE_LOCAL_DIR="/dev/shm/ccache-${USER:?}"
export PUBLISH_TMP="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_NUMBER}.tar.zst.${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}.tmp"
export PUBLISH_SIDECAR_TMP="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_NUMBER}.build-sidecar.json.${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}.tmp"
export CCACHE_BASEDIR="${BUILD_TREE}"
export CCACHE_CONFIGPATH="${HOME}/.config/ccache/ccache.conf"
export CCACHE_DIR="${CCACHE_LOCAL_DIR}"
export CCACHE_TEMPDIR="${BUILD_DIR}/ccache-tmp"

# ビルドが中断・失敗した場合も、一時 archive を削除する。
cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -f -- "${PUBLISH_TMP}" "${PUBLISH_SIDECAR_TMP}" 2>/dev/null || true
  exit "${status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# 前回のビルドツリーを削除し、今回のビルドに必要なディレクトリを作成する。
rm -rf -- "${BUILD_DIR:?}"
install -d -m 2775 "${BUILD_ARCHIVE_DIR}" "${SOURCE_ARCHIVE_CACHE_DIR}" "${BUILD_TREE}" "${BUILD_DIR}/logs" "${BUILD_DIR}/ccache-tmp"
install -d -m 0700 "${CCACHE_LOCAL_DIR}"

# OpenFOAM v2606 と対応する ThirdParty を、ソースリポジトリ側で更新される
# 読み取り専用の共有 mirror からローカル clone する。
git clone --no-checkout \
  "${GIT_MIRROR_DIR}/3_OpenFOAM_Src.git" \
  "${BUILD_TREE}/OpenFOAM"
git -C "${BUILD_TREE}/OpenFOAM" checkout --detach "${OPENFOAM_SOURCE_REF}"
openfoam_source_algorithm="$(git -C "${BUILD_TREE}/OpenFOAM" rev-parse --show-object-format)"
openfoam_source_oid="$(git -C "${BUILD_TREE}/OpenFOAM" rev-parse HEAD)"

git clone --no-checkout \
  "${GIT_MIRROR_DIR}/4_OpenFOAM_ThirdParty_Src.git" \
  "${BUILD_TREE}/ThirdParty"
git -C "${BUILD_TREE}/ThirdParty" checkout --detach "${THIRDPARTY_SOURCE_REF}"
thirdparty_source_algorithm="$(git -C "${BUILD_TREE}/ThirdParty" rev-parse --show-object-format)"
thirdparty_source_oid="$(git -C "${BUILD_TREE}/ThirdParty" rev-parse HEAD)"

# Bundle-declared in-process sources must be present in, and byte-identical to,
# the exact detached OpenFOAM source commit before its Git metadata is removed.
# Executable component paths are relative to the separately provisioned
# instrumentation artifact root, so they must not be resolved in this upstream
# OpenFOAM checkout.
test -z "$(git -C "${BUILD_TREE}/OpenFOAM" status --porcelain=v1 --untracked-files=all)"
test -z "$(git -C "${BUILD_TREE}/ThirdParty" status --porcelain=v1 --untracked-files=all)"
while IFS= read -r source_path
do
  git -C "${BUILD_TREE}/OpenFOAM" cat-file -e "HEAD:${source_path}"
  cmp -- "${BUILD_TREE}/OpenFOAM/${source_path}" \
    <(git -C "${BUILD_TREE}/OpenFOAM" show "HEAD:${source_path}")
done < <(
  jq -r \
    '.components[].activation | select(.kind == "in_process_hook") | .source_path' \
    "${GITHUB_WORKSPACE}/experiment-metrics/bundles/openfoam-score-v1.json" \
    "${GITHUB_WORKSPACE}/experiment-metrics/bundles/openfoam-profile-vtune-hotspots-v1.json" |
    LC_ALL=C sort -u
)

# ビルドには worktree だけを使うため、成果物へ Git オブジェクトを含めない。
rm -rf -- "${BUILD_TREE}/OpenFOAM/.git" "${BUILD_TREE}/ThirdParty/.git"
ln -s ../ThirdParty "${BUILD_TREE}/OpenFOAM/ThirdParty"

# ThirdParty リポジトリが管理するスクリプトで、v2606 ビルドに必要な依存を
# 共有 archive cache から検証・展開する。
"${BUILD_TREE}/ThirdParty/download-v2606-sources.sh"

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

# タスク専用ビルドスクリプトが参照するプロジェクトへ移動する。
cd "${WM_PROJECT_DIR}"

# ccache の統計をリセットしてから、cavity3D の前処理と実行に必要な
# blockMesh、decomposePar、renumberMesh、icoFoam とその依存だけをビルドする。
ccache --zero-stats
"${GITHUB_WORKSPACE}/scripts/build-profiler.sh" \
  "${GITHUB_WORKSPACE}/scripts/build-openfoam-task.sh" \
    > "${BUILD_DIR}/logs/allwmake.log" 2>&1 || {
  build_status=$?
  grep -Eai -m 200 '(^|[[:space:]])(fatal[[:space:]]+)?error([[:space:](]|:)|undefined reference|collect2:|make(\[[0-9]+\])?: \*\*\*|wmake error' "${BUILD_DIR}/logs/allwmake.log" >&2 || true
  exit "${build_status}"
}
ccache --show-stats

# The dependency-free probe entrypoint is installed byte-for-byte from the
# tracked source and becomes the seventh build-owned executable.
install -m 0755 \
  "${GITHUB_WORKSPACE}/experiment-metrics/src/experiment_metrics/probes/capture_hardware.py" \
  "${FOAM_APPBIN}/capture-hardware"

# Capture all pre-archive semantic inputs while the toolchain environment and
# resolved build paths are still live. The final archive hash is added only
# after tar has completed, avoiding archive self-reference.
uv sync --project "${GITHUB_WORKSPACE}/experiment-metrics" --frozen --no-dev
metrics_cli="${GITHUB_WORKSPACE}/experiment-metrics/.venv/bin/experiment-metrics"
build_state="${BUILD_DIR}/build-state.json"
"${metrics_cli}" capture-build-state \
  --output "${build_state}" \
  --build-tree "${BUILD_TREE}" \
  --build-definition-repo "${GITHUB_WORKSPACE}" \
  --openfoam-oid "${openfoam_source_oid}" \
  --openfoam-algorithm "${openfoam_source_algorithm}" \
  --thirdparty-oid "${thirdparty_source_oid}" \
  --thirdparty-algorithm "${thirdparty_source_algorithm}" \
  --compile-flag "WM_OPTIONS=${WM_OPTIONS:-}" \
  --compile-flag "WM_COMPILER=${WM_COMPILER:-}" \
  --compile-flag "WM_COMPILE_OPTION=${WM_COMPILE_OPTION:-}" \
  --compile-flag "WM_PRECISION_OPTION=${WM_PRECISION_OPTION:-}" \
  --compile-flag "WM_LABEL_SIZE=${WM_LABEL_SIZE:-}" \
  --executable "icoFoam=${FOAM_APPBIN}/icoFoam" \
  --executable "blockMesh=${FOAM_APPBIN}/blockMesh" \
  --executable "decomposePar=${FOAM_APPBIN}/decomposePar" \
  --executable "renumberMesh=${FOAM_APPBIN}/renumberMesh" \
  --executable "checkMesh=${FOAM_APPBIN}/checkMesh" \
  --executable "mesh-facts=${FOAM_APPBIN}/mesh-facts" \
  --executable "partition-audit=${FOAM_APPBIN}/partition-audit" \
  --executable "capture-hardware=${FOAM_APPBIN}/capture-hardware"

# ビルド済みツリーを圧縮し、後続ジョブが再利用できる archive として公開する。
tar -I zstd -cf "${PUBLISH_TMP}" -C "${BUILD_TREE}" .
"${metrics_cli}" finalize-build-sidecar \
  --state "${build_state}" \
  --archive "${PUBLISH_TMP}" \
  --output "${PUBLISH_SIDECAR_TMP}"
mv -- "${PUBLISH_TMP}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
mv -- "${PUBLISH_SIDECAR_TMP}" \
  "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.build-sidecar.json"
echo "Published ${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
