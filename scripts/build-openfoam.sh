#!/usr/bin/env bash
set -euo pipefail

: "${BUILD_ARCHIVE_DIR:?}"
: "${BUILD_DIR:?}"
: "${GITHUB_RUN_ATTEMPT:?}"
: "${GITHUB_RUN_ID:?}"
: "${GITHUB_WORKSPACE:?}"
: "${GIT_MIRROR_DIR:?}"
: "${OPENFOAM_SOURCE_OID:?pinned OpenFOAM source commit is required}"
: "${SOURCE_ARCHIVE_CACHE_DIR:?}"
: "${THIRDPARTY_SOURCE_OID:?pinned ThirdParty source commit is required}"
# ビルド仕様はここへ集約し、workflow からは実行ごとのパスと
# GitHub Actions のメタデータだけを受け取る。
openfoam_source_ref=refs/tags/OpenFOAM-v2512
thirdparty_source_ref=refs/tags/v2512
# genkai0001/0002 expose two 60-core sockets. Use physical cores and do not
# count the second SMT thread as another compiler worker.
build_parallelism=120
build_condition=baseline
build_compile_option=Opt
build_tuning_flags=
optimization_report_flags='-qopt-report=3 -qopt-report-phase=loop,vec,cg'
export CC=mpiicx
export CXX=mpiicpx
build_extra_cxxflags="${build_tuning_flags:+${build_tuning_flags} }${optimization_report_flags}"
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
install -d -m 2775 "${BUILD_ARCHIVE_DIR}" "${SOURCE_ARCHIVE_CACHE_DIR}" "${build_tree}" "${BUILD_DIR}/logs" "${BUILD_DIR}/ccache-tmp"
install -d -m 0700 "${ccache_local_dir}"

# OpenFOAM v2512 と対応する ThirdParty を、ソースリポジトリ側で管理される
# 読み取り専用の共有 mirror からローカル clone する。
git clone --no-checkout "${GIT_MIRROR_DIR}/3_OpenFOAM_Src.git" "${build_tree}/OpenFOAM"
git -C "${build_tree}/OpenFOAM" checkout --detach "${openfoam_source_ref}"
openfoam_source_algorithm="$(git -C "${build_tree}/OpenFOAM" rev-parse --show-object-format)"
openfoam_source_oid="$(git -C "${build_tree}/OpenFOAM" rev-parse HEAD)"
test "${openfoam_source_oid}" = "${OPENFOAM_SOURCE_OID}"

git clone --no-checkout "${GIT_MIRROR_DIR}/4_OpenFOAM_ThirdParty_Src.git" "${build_tree}/ThirdParty"
git -C "${build_tree}/ThirdParty" checkout --detach "${thirdparty_source_ref}"
thirdparty_source_algorithm="$(git -C "${build_tree}/ThirdParty" rev-parse --show-object-format)"
thirdparty_source_oid="$(git -C "${build_tree}/ThirdParty" rev-parse HEAD)"
test "${thirdparty_source_oid}" = "${THIRDPARTY_SOURCE_OID}"

# ビルドには worktree だけを使うため、成果物へ Git オブジェクトを含めない。
rm -rf -- "${build_tree}/OpenFOAM/.git" "${build_tree}/ThirdParty/.git"
ln -s ../ThirdParty "${build_tree}/OpenFOAM/ThirdParty"

# v2512 が要求する Scotch 6.1.0 を、玄界の共有 source cache から展開する。
scotch_archive="${SOURCE_ARCHIVE_CACHE_DIR}/scotch-v6.1.0.tar.gz"
test "$(sha256sum "${scotch_archive}" | awk '{print $1}')" = 4fe537f608f0fe39ec78807f90203f9cca1181deb16bfa93b7d4cd440e01bbd1
install -d "${build_tree}/ThirdParty/sources/scotch"
tar -xzf "${scotch_archive}" -C "${build_tree}/ThirdParty/sources/scotch"
mv "${build_tree}/ThirdParty/sources/scotch/scotch-v6.1.0" "${build_tree}/ThirdParty/sources/scotch/scotch_6.1.0"

module purge
module load intel/2025.1.3 impi

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
"${metrics_cli}" capture-build-state --output "${build_state}" --build-tree "${build_tree}" --build-definition-repo "${GITHUB_WORKSPACE}" --openfoam-oid "${openfoam_source_oid}" --openfoam-algorithm "${openfoam_source_algorithm}" --thirdparty-oid "${thirdparty_source_oid}" --thirdparty-algorithm "${thirdparty_source_algorithm}" --compiler-c "$(command -v mpiicx)" --compiler-cxx "$(command -v mpiicpx)" --mpi-launcher "$(command -v mpirun)" --precision DP --label-bits 32 --compile-flag "BUILD_CONDITION=${build_condition}" --compile-flag "WM_OPTIONS=${WM_OPTIONS:-}" --compile-flag "WM_COMPILER=${WM_COMPILER:-}" --compile-flag "WM_COMPILE_OPTION=${WM_COMPILE_OPTION:-}" --compile-flag "WM_PRECISION_OPTION=${WM_PRECISION_OPTION:-}" --compile-flag "WM_LABEL_SIZE=${WM_LABEL_SIZE:-}" --compile-flag "FOAM_EXTRA_CXXFLAGS=${FOAM_EXTRA_CXXFLAGS}" --compile-flag SCOTCH_SOURCE_SHA256=4fe537f608f0fe39ec78807f90203f9cca1181deb16bfa93b7d4cd440e01bbd1 --executable "simpleFoam=${FOAM_APPBIN}/simpleFoam" --executable "decomposePar=${FOAM_APPBIN}/decomposePar" --executable "checkMesh=${FOAM_APPBIN}/checkMesh" --executable "renumberMesh=${FOAM_APPBIN}/renumberMesh" --executable "potentialFoam=${FOAM_APPBIN}/potentialFoam" --executable "applyBoundaryLayer=${FOAM_APPBIN}/applyBoundaryLayer" --executable "mesh-facts=${FOAM_APPBIN}/mesh-facts" --executable "partition-audit=${FOAM_APPBIN}/partition-audit" --executable "capture-hardware=${FOAM_APPBIN}/capture-hardware"

# ビルド済みツリーを圧縮し、後続ジョブが再利用できる archive として公開する。
tar -I zstd -cf "${publish_tmp}" -C "${build_tree}" .
"${metrics_cli}" finalize-build-sidecar --state "${build_state}" --archive "${publish_tmp}" --output "${publish_sidecar_tmp}"
mv -- "${publish_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.tar.zst"
mv -- "${publish_sidecar_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.build-sidecar.json"
echo "Published ${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.tar.zst"
