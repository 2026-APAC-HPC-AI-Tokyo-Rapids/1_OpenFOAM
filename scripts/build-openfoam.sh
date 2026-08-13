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
openfoam_source_ref=refs/heads/master
thirdparty_source_ref=refs/heads/main
build_parallelism=120
build_condition=opt-avx512
build_compile_option=OptAVX512
build_tuning_flags=
optimization_report_flags='-qopt-report=3 -qopt-report-phase=loop,vec,cg'
export CC=mpiicx
export CXX=mpiicpx
build_extra_cxxflags="${build_tuning_flags:+${build_tuning_flags} }${optimization_report_flags}"

# ビルドツリー、ccache、一時 archive の場所を先に決めておく。
build_tree="${BUILD_DIR}/tree"
publish_tmp="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_NUMBER}.tar.zst.${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}.tmp"
publish_sidecar_tmp="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_NUMBER}.build-sidecar.json.${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}.tmp"

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
install -d -m 2775 "${BUILD_ARCHIVE_DIR}" "${SOURCE_ARCHIVE_CACHE_DIR}" "${build_tree}" "${BUILD_DIR}/logs"

# OpenFOAM v2606 と対応する ThirdParty を、ソースリポジトリ側で更新される
# 読み取り専用の共有 mirror からローカル clone する。
git clone --no-checkout "${GIT_MIRROR_DIR}/3_OpenFOAM_Src.git" "${build_tree}/OpenFOAM"
git -C "${build_tree}/OpenFOAM" checkout --detach "${openfoam_source_ref}"
openfoam_source_algorithm="$(git -C "${build_tree}/OpenFOAM" rev-parse --show-object-format)"
openfoam_source_oid="$(git -C "${build_tree}/OpenFOAM" rev-parse HEAD)"

git clone --no-checkout "${GIT_MIRROR_DIR}/4_OpenFOAM_ThirdParty_Src.git" "${build_tree}/ThirdParty"
git -C "${build_tree}/ThirdParty" checkout --detach "${thirdparty_source_ref}"
thirdparty_source_algorithm="$(git -C "${build_tree}/ThirdParty" rev-parse --show-object-format)"
thirdparty_source_oid="$(git -C "${build_tree}/ThirdParty" rev-parse HEAD)"

# Bundle-declared in-process sources must be present in, and byte-identical to,
# the exact detached OpenFOAM source commit before its Git metadata is removed.
# Executable component paths are relative to the separately provisioned
# instrumentation artifact root, so they must not be resolved in this upstream
# OpenFOAM checkout.
test -z "$(git -C "${build_tree}/OpenFOAM" status --porcelain=v1 --untracked-files=all)"
test -z "$(git -C "${build_tree}/ThirdParty" status --porcelain=v1 --untracked-files=all)"
while IFS= read -r source_path
do
  git -C "${build_tree}/OpenFOAM" cat-file -e "HEAD:${source_path}"
  cmp -- "${build_tree}/OpenFOAM/${source_path}" <(git -C "${build_tree}/OpenFOAM" show "HEAD:${source_path}")
done < <(
  jq -r '.components[].activation | select(.kind == "in_process_hook") | .source_path' "${GITHUB_WORKSPACE}/experiment-metrics/bundles/openfoam-score-v1.json" "${GITHUB_WORKSPACE}/experiment-metrics/bundles/openfoam-profile-vtune-hotspots-v1.json" |
    LC_ALL=C sort -u
)

# ビルドには worktree だけを使うため、成果物へ Git オブジェクトを含めない。
rm -rf -- "${build_tree}/OpenFOAM/.git" "${build_tree}/ThirdParty/.git"
ln -s ../ThirdParty "${build_tree}/OpenFOAM/ThirdParty"

# ThirdParty リポジトリが管理するスクリプトで、v2606 ビルドに必要な依存を
# 共有 archive cache から検証・展開する。
"${build_tree}/ThirdParty/download-v2606-sources.sh"

module purge
module load intel/2025.1.3 impi

# 使用するコンパイラが利用可能であることを確認する。
for build_tool in "${CC}" "${CXX}"
do
  "${build_tool}" --version
done

# OpenFOAM の bashrc は未設定変数や中間コマンドの失敗を許容するため、
# 初期化中だけ厳格なエラーチェックを緩める。
set +eu
source "${build_tree}/OpenFOAM/etc/bashrc" WM_COMPILER=Icx WM_MPLIB=INTELMPI WM_LABEL_SIZE=64 WM_PRECISION_OPTION=DP WM_COMPILE_OPTION="${build_compile_option}" FOAM_EXTRA_CXXFLAGS="${build_extra_cxxflags}"
set -eu
test "${FOAM_EXTRA_CXXFLAGS}" = "${build_extra_cxxflags}"

# タスク専用ビルドスクリプトが参照するプロジェクトへ移動する。
cd "${WM_PROJECT_DIR}"

# cavity3D の前処理と実行に必要なblockMesh、decomposePar、checkMesh、
# icoFoamとその依存だけをビルドする。
"${GITHUB_WORKSPACE}/scripts/build-profiler.sh" "${GITHUB_WORKSPACE}/scripts/build-openfoam-task.sh" "${build_parallelism}" "${GITHUB_WORKSPACE}/experiment-metrics/native" > "${BUILD_DIR}/logs/allwmake.log" 2>&1 || {
  build_status=$?
  grep -Eai -m 200 '(^|[[:space:]])(fatal[[:space:]]+)?error([[:space:](]|:)|undefined reference|collect2:|make(\[[0-9]+\])?: \*\*\*|wmake error' "${BUILD_DIR}/logs/allwmake.log" >&2 || true
  exit "${build_status}"
}
report_list="${BUILD_DIR}/logs/optimization-report-files.txt"
find "${build_tree}/OpenFOAM" -type f -name '*.optrpt' -printf '%P\n' | LC_ALL=C sort > "${report_list}"
test -s "${report_list}"
tar -I zstd -cf "${BUILD_DIR}/logs/optimization-reports.tar.zst" -C "${build_tree}/OpenFOAM" -T "${report_list}"

# The dependency-free probe entrypoint is installed byte-for-byte from the
# tracked source and becomes the seventh build-owned executable.
install -m 0755 "${GITHUB_WORKSPACE}/experiment-metrics/src/experiment_metrics/probes/capture_hardware.py" "${FOAM_APPBIN}/capture-hardware"

# Capture all pre-archive semantic inputs while the toolchain environment and
# resolved build paths are still live. The final archive hash is added only
# after tar has completed, avoiding archive self-reference.
uv sync --project "${GITHUB_WORKSPACE}/experiment-metrics" --frozen --no-dev
metrics_cli="${GITHUB_WORKSPACE}/experiment-metrics/.venv/bin/experiment-metrics"
build_state="${BUILD_DIR}/build-state.json"
"${metrics_cli}" capture-build-state --output "${build_state}" --build-tree "${build_tree}" --build-definition-repo "${GITHUB_WORKSPACE}" --openfoam-oid "${openfoam_source_oid}" --openfoam-algorithm "${openfoam_source_algorithm}" --thirdparty-oid "${thirdparty_source_oid}" --thirdparty-algorithm "${thirdparty_source_algorithm}" --compile-flag "BUILD_CONDITION=${build_condition}" --compile-flag "WM_OPTIONS=${WM_OPTIONS:-}" --compile-flag "WM_COMPILER=${WM_COMPILER:-}" --compile-flag "WM_COMPILE_OPTION=${WM_COMPILE_OPTION:-}" --compile-flag "WM_PRECISION_OPTION=${WM_PRECISION_OPTION:-}" --compile-flag "WM_LABEL_SIZE=${WM_LABEL_SIZE:-}" --compile-flag "FOAM_EXTRA_CXXFLAGS=${FOAM_EXTRA_CXXFLAGS}" --executable "icoFoam=${FOAM_APPBIN}/icoFoam" --executable "blockMesh=${FOAM_APPBIN}/blockMesh" --executable "decomposePar=${FOAM_APPBIN}/decomposePar" --executable "checkMesh=${FOAM_APPBIN}/checkMesh" --executable "mesh-facts=${FOAM_APPBIN}/mesh-facts" --executable "partition-audit=${FOAM_APPBIN}/partition-audit" --executable "capture-hardware=${FOAM_APPBIN}/capture-hardware"

# ビルド済みツリーを圧縮し、後続ジョブが再利用できる archive として公開する。
tar -I zstd -cf "${publish_tmp}" -C "${build_tree}" .
"${metrics_cli}" finalize-build-sidecar --state "${build_state}" --archive "${publish_tmp}" --output "${publish_sidecar_tmp}"
mv -- "${publish_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
mv -- "${publish_sidecar_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.build-sidecar.json"
echo "Published ${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
