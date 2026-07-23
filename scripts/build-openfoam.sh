#!/usr/bin/env bash
set -euo pipefail

: "${ADIOS2_VERSION:?}"
: "${BUILD_ARCHIVE_DIR:?}"
: "${BUILD_DIR:?}"
: "${CC:?}"
: "${CGAL_VERSION:?}"
: "${CXX:?}"
: "${GITHUB_RUN_ATTEMPT:?}"
: "${GITHUB_RUN_ID:?}"
: "${GITHUB_RUN_NUMBER:?}"
: "${GITHUB_WORKSPACE:?}"
: "${OPENFOAM_BUILD_PARALLELISM:?}"
: "${OPENFOAM_VERSION:?}"
: "${SOURCE_ARCHIVE_CACHE_DIR:?}"

BUILD_TREE="${BUILD_DIR}/tree"
PUBLISH_TMP="${BUILD_ARCHIVE_DIR}/.${GITHUB_RUN_NUMBER}.tar.zst.${GITHUB_RUN_ID}.${GITHUB_RUN_ATTEMPT}.tmp"

cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -f -- "${PUBLISH_TMP}" 2>/dev/null || true
  exit "${status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

rm -rf -- "${BUILD_DIR:?}"
install -d -m 2775 \
  "${BUILD_ARCHIVE_DIR}" \
  "${SOURCE_ARCHIVE_CACHE_DIR}" \
  "${BUILD_TREE}" \
  "${BUILD_DIR}/logs" \
  "${BUILD_DIR}/ccache-cache" \
  "${BUILD_DIR}/ccache-tmp"

for archive_url in \
  "https://dl.openfoam.com/source/${OPENFOAM_VERSION}/OpenFOAM-${OPENFOAM_VERSION}.tgz" \
  "https://dl.openfoam.com/source/${OPENFOAM_VERSION}/ThirdParty-${OPENFOAM_VERSION}.tar.gz" \
  "https://github.com/ornladios/ADIOS2/archive/refs/tags/v${ADIOS2_VERSION}.tar.gz" \
  "https://github.com/CGAL/cgal/releases/download/v${CGAL_VERSION}/CGAL-${CGAL_VERSION}.tar.xz"
do
  wget --no-verbose --no-clobber --directory-prefix="${SOURCE_ARCHIVE_CACHE_DIR}" "${archive_url}"
done

tar -xzf "${SOURCE_ARCHIVE_CACHE_DIR}/OpenFOAM-${OPENFOAM_VERSION}.tgz" -C "${BUILD_TREE}"
tar -xzf "${SOURCE_ARCHIVE_CACHE_DIR}/ThirdParty-${OPENFOAM_VERSION}.tar.gz" -C "${BUILD_TREE}"
THIRDPARTY_SOURCE_DIR="${BUILD_TREE}/ThirdParty-${OPENFOAM_VERSION}"
mkdir -p "${THIRDPARTY_SOURCE_DIR}/sources/adios" "${THIRDPARTY_SOURCE_DIR}/sources/cgal"
tar -xzf "${SOURCE_ARCHIVE_CACHE_DIR}/v${ADIOS2_VERSION}.tar.gz" -C "${THIRDPARTY_SOURCE_DIR}/sources/adios"
tar -xJf "${SOURCE_ARCHIVE_CACHE_DIR}/CGAL-${CGAL_VERSION}.tar.xz" -C "${THIRDPARTY_SOURCE_DIR}/sources/cgal"
mv "${BUILD_TREE}/OpenFOAM-${OPENFOAM_VERSION}" "${BUILD_TREE}/OpenFOAM"
mv "${THIRDPARTY_SOURCE_DIR}" "${BUILD_TREE}/ThirdParty"
ln -s ../ThirdParty "${BUILD_TREE}/OpenFOAM/ThirdParty"
for patch_file in "${GITHUB_WORKSPACE}"/patches/*.patch
do
  patch -d "${BUILD_TREE}" -p0 < "${patch_file}"
done

module purge
module load intel/2025.1.3 impi
for build_tool in "${CC}" "${CXX}" ccache
do
  "${build_tool}" --version
done

export CCACHE_BASEDIR="${BUILD_TREE}"
export CCACHE_CONFIGPATH="${HOME}/.config/ccache/ccache.conf"
export CCACHE_DIR="${BUILD_DIR}/ccache-cache"
export CCACHE_TEMPDIR="${BUILD_DIR}/ccache-tmp"
[[ -r "${CCACHE_CONFIGPATH}" ]]
ccache --show-config

# OpenFOAM's bashrc tolerates unset variables and intermediate command failures.
set +eu
source "${BUILD_TREE}/OpenFOAM/etc/bashrc" \
  WM_COMPILER=Icx \
  WM_MPLIB=INTELMPI \
  WM_LABEL_SIZE=64 \
  WM_PRECISION_OPTION=DP \
  WM_COMPILE_CONTROL=+ccache
set -eu

export LD_LIBRARY_PATH="${FFTW_ARCH_PATH}/lib:${LD_LIBRARY_PATH:-}"
export FOAM_EXTRA_LDFLAGS="-Wl,-rpath-link,${FFTW_ARCH_PATH}/lib"
cd "${WM_PROJECT_DIR}"
ccache --zero-stats
"${GITHUB_WORKSPACE}/scripts/build-profiler.sh" \
  bash -o pipefail ./Allwmake -j "${OPENFOAM_BUILD_PARALLELISM}" -s \
    -log="${BUILD_DIR}/logs/allwmake.log" > /dev/null || {
  build_status=$?
  grep -Eai -m 200 \
    '(^|[[:space:]])(fatal[[:space:]]+)?error([[:space:](]|:)|undefined reference|collect2:|make(\[[0-9]+\])?: \*\*\*|wmake error' \
    "${BUILD_DIR}/logs/allwmake.log" >&2 || true
  exit "${build_status}"
}
ccache --show-stats

tar -I zstd -cf "${PUBLISH_TMP}" -C "${BUILD_TREE}" .
mv -- "${PUBLISH_TMP}" "${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
echo "Published ${BUILD_ARCHIVE_DIR}/${GITHUB_RUN_NUMBER}.tar.zst"
