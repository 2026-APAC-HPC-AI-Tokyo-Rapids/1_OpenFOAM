#!/usr/bin/env bash

set -euo pipefail

: "${BUILD_ARCHIVE_DIR:?build archive directory is required}"
: "${BUILD_DIR:?login-node build directory is required}"
: "${GITHUB_RUN_ATTEMPT:?GitHub run attempt is required}"
: "${GITHUB_RUN_ID:?GitHub run ID is required}"
: "${GITHUB_WORKSPACE:?build definition checkout is required}"
: "${OPENFOAM_SOURCE_ARCHIVE:?OpenFOAM source archive is required}"
: "${OPENFOAM_SOURCE_ARCHIVE_SHA256:?OpenFOAM source archive digest is required}"
: "${OPENFOAM_SOURCE_OID:?OpenFOAM source commit is required}"
: "${THIRDPARTY_SOURCE_ARCHIVE:?ThirdParty source archive is required}"
: "${THIRDPARTY_SOURCE_ARCHIVE_SHA256:?ThirdParty source archive digest is required}"
: "${THIRDPARTY_SOURCE_OID:?ThirdParty source commit is required}"

[[ "${OPENFOAM_SOURCE_OID}" =~ ^[0-9a-f]{40,64}$ && "${THIRDPARTY_SOURCE_OID}" =~ ^[0-9a-f]{40,64}$ ]]
test "$(sha256sum "${OPENFOAM_SOURCE_ARCHIVE}" | awk '{print $1}')" = "${OPENFOAM_SOURCE_ARCHIVE_SHA256}"
test "$(sha256sum "${THIRDPARTY_SOURCE_ARCHIVE}" | awk '{print $1}')" = "${THIRDPARTY_SOURCE_ARCHIVE_SHA256}"

# Gadiのログインノードは24コアのソケットを2基備えるが、v2512のライブラリ群を
# 48個のicpxで同時にコンパイルするとログインノードのメモリを使い切ったため、
# 31990408500. Keep enough memory per compiler process instead of matching cores.
build_parallelism=16
build_tree="${BUILD_DIR}/tree"
openfoam_tree="${build_tree}/OpenFOAM"
thirdparty_tree="${build_tree}/ThirdParty"
build_log_dir="${BUILD_DIR}/logs"
ccache_local_dir="/dev/shm/ccache-${USER:?}"
ccache_remote_dir="/scratch/hb15/${USER}/openfoam/gadi/ccache"
publish_tmp="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_ID}.tar.zst.${GITHUB_RUN_ATTEMPT}.tmp"
sidecar_tmp="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_ID}.build-sidecar.json.${GITHUB_RUN_ATTEMPT}.tmp"
export CCACHE_BASEDIR="${build_tree}"
export CCACHE_CONFIGPATH="${HOME}/.config/ccache/ccache.conf"
export CCACHE_DIR="${ccache_local_dir}"
export CCACHE_TEMPDIR="${BUILD_DIR}/ccache-tmp"
cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -f -- "${publish_tmp}" "${sidecar_tmp}" 2>/dev/null || true
  exit "${status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

rm -rf -- "${BUILD_DIR:?}"
install -d -m 0750 "${openfoam_tree}" "${thirdparty_tree}" "${BUILD_ARCHIVE_DIR}" "${build_log_dir}"
install -d -m 0700 "${CCACHE_TEMPDIR}" "${ccache_local_dir}" "${ccache_remote_dir}"
tar -xzf "${OPENFOAM_SOURCE_ARCHIVE}" -C "${openfoam_tree}" --strip-components=1
tar -xzf "${THIRDPARTY_SOURCE_ARCHIVE}" -C "${thirdparty_tree}" --strip-components=1
ln -s ../ThirdParty "${openfoam_tree}/ThirdParty"
install -d "${thirdparty_tree}/sources/scotch"
cp -a /apps/OpenFOAM/2512/ThirdParty-v2512/sources/scotch/scotch_6.1.0 "${thirdparty_tree}/sources/scotch/"
scotch_source_identity=$(find "${thirdparty_tree}/sources/scotch/scotch_6.1.0" -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')

module purge
module load intel-compiler-llvm/2025.1.1 intel-mpi/2021.15.0
export CC=mpiicx
export CXX=mpiicpx
export CMAKE_C_COMPILER_LAUNCHER=ccache
export CMAKE_CXX_COMPILER_LAUNCHER=ccache
ccache --show-config

set +eu
source "${openfoam_tree}/etc/bashrc" WM_COMPILER=Icx WM_MPLIB=INTELMPI WM_LABEL_SIZE=32 WM_PRECISION_OPTION=DP WM_COMPILE_OPTION=Opt WM_COMPILE_CONTROL=+ccache
set -eu
export FOAM_EXTRA_CXXFLAGS=
cd "${WM_PROJECT_DIR}"
ccache --zero-stats
"${GITHUB_WORKSPACE}/scripts/build-openfoam-task.sh" "${build_parallelism}" "${GITHUB_WORKSPACE}/experiment-metrics/native" > "${build_log_dir}/allwmake.log" 2>&1 || {
  build_status=$?
  grep -Eai -m 200 '(^|[[:space:]])(fatal[[:space:]]+)?error([[:space:](]|:)|undefined reference|collect2:|make(\[[0-9]+\])?: \*\*\*|wmake error' "${build_log_dir}/allwmake.log" >&2 || true
  exit "${build_status}"
}
ccache --show-stats
ccache --trim-dir "${ccache_remote_dir}" --trim-max-size 10GB || true

install -m 0755 "${GITHUB_WORKSPACE}/experiment-metrics/src/experiment_metrics/probes/capture_hardware.py" "${FOAM_APPBIN}/capture-hardware"
metrics_cli="${GITHUB_WORKSPACE}/experiment-metrics/.venv/bin/experiment-metrics"
build_state="${build_log_dir}/build-state.json"
"${metrics_cli}" capture-build-state --output "${build_state}" --build-tree "${build_tree}" --build-definition-repo "${GITHUB_WORKSPACE}" --openfoam-oid "${OPENFOAM_SOURCE_OID}" --openfoam-algorithm sha1 --thirdparty-oid "${THIRDPARTY_SOURCE_OID}" --thirdparty-algorithm sha1 --compiler-c "$(command -v mpiicx)" --compiler-cxx "$(command -v mpiicpx)" --mpi-launcher "$(command -v mpirun)" --precision DP --label-bits 32 --compile-flag BUILD_CONDITION=baseline --compile-flag "WM_OPTIONS=${WM_OPTIONS}" --compile-flag "WM_COMPILER=${WM_COMPILER}" --compile-flag "WM_COMPILE_OPTION=${WM_COMPILE_OPTION}" --compile-flag "WM_PRECISION_OPTION=${WM_PRECISION_OPTION}" --compile-flag "WM_LABEL_SIZE=${WM_LABEL_SIZE}" --compile-flag "FOAM_EXTRA_CXXFLAGS=${FOAM_EXTRA_CXXFLAGS}" --compile-flag "SCOTCH_SOURCE_IDENTITY=${scotch_source_identity}" --executable "simpleFoam=${FOAM_APPBIN}/simpleFoam" --executable "decomposePar=${FOAM_APPBIN}/decomposePar" --executable "checkMesh=${FOAM_APPBIN}/checkMesh" --executable "renumberMesh=${FOAM_APPBIN}/renumberMesh" --executable "potentialFoam=${FOAM_APPBIN}/potentialFoam" --executable "applyBoundaryLayer=${FOAM_APPBIN}/applyBoundaryLayer" --executable "mesh-facts=${FOAM_APPBIN}/mesh-facts" --executable "partition-audit=${FOAM_APPBIN}/partition-audit" --executable "capture-hardware=${FOAM_APPBIN}/capture-hardware"

tar -I zstd -cf "${publish_tmp}" -C "${build_tree}" .
"${metrics_cli}" finalize-build-sidecar --state "${build_state}" --archive "${publish_tmp}" --output "${sidecar_tmp}"
mv -- "${publish_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.tar.zst"
mv -- "${sidecar_tmp}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_ID}.build-sidecar.json"
trap - EXIT
