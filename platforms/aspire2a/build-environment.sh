#!/usr/bin/env bash
# scripts/build-openfoam.shから読み込むASPIRE-2A専用設定。
# shellcheck disable=SC2034,SC2154
: "${OPENFOAM_SOURCE_ARCHIVE:?OpenFOAM source archive is required}"
: "${OPENFOAM_SOURCE_ARCHIVE_SHA256:?OpenFOAM source archive digest is required}"
: "${OPENFOAM_SOURCE_OID:?OpenFOAM source commit is required}"
: "${THIRDPARTY_SOURCE_ARCHIVE:?ThirdParty source archive is required}"
: "${THIRDPARTY_SOURCE_ARCHIVE_SHA256:?ThirdParty source archive digest is required}"
: "${THIRDPARTY_SOURCE_OID:?ThirdParty source commit is required}"
: "${IMB_SOURCE_ARCHIVE:?IMB source archive is required}"
: "${IMB_SOURCE_ARCHIVE_SHA256:?IMB source archive digest is required}"
: "${IMB_SOURCE_OID:?IMB source commit is required}"

[[ "${OPENFOAM_SOURCE_OID}" =~ ^[0-9a-f]{40,64}$ && "${THIRDPARTY_SOURCE_OID}" =~ ^[0-9a-f]{40,64}$ ]]
[[ "${IMB_SOURCE_OID}" =~ ^[0-9a-f]{40,64}$ ]]
test "$(sha256sum "${OPENFOAM_SOURCE_ARCHIVE}" | awk '{print $1}')" = "${OPENFOAM_SOURCE_ARCHIVE_SHA256}"
test "$(sha256sum "${THIRDPARTY_SOURCE_ARCHIVE}" | awk '{print $1}')" = "${THIRDPARTY_SOURCE_ARCHIVE_SHA256}"
test "$(sha256sum "${IMB_SOURCE_ARCHIVE}" | awk '{print $1}')" = "${IMB_SOURCE_ARCHIVE_SHA256}"
build_parallelism=16
build_directory_mode=0750
build_extra_cxxflags="${build_tuning_flags}"
build_compile_control=+ccache
build_use_ccache=true
openfoam_source_oid="${OPENFOAM_SOURCE_OID}"
thirdparty_source_oid="${THIRDPARTY_SOURCE_OID}"
openfoam_source_algorithm=sha1
thirdparty_source_algorithm=sha1
source "${GITHUB_WORKSPACE}/platforms/aspire2a/toolchain.conf"
source "${GITHUB_WORKSPACE}/platforms/aspire2a/toolchain.sh"
aspire2a_load_toolchain "${aspire2a_toolchain}"
module load git/2.39.2
build_ccache_namespace="aspire2a-${aspire2a_toolchain}"
aspire2a_ccache=$(command -v ccache)
aspire2a_ccache_version=$(ccache --version | sed -n '1s/^ccache version //p')
export CCACHE_REMOTE_STORAGE="file:/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/build-cache/ccache/${aspire2a_toolchain}"
test -x "${aspire2a_ccache}"
test -n "${aspire2a_ccache_version}"
# OpenFOAMは登録処理だけを持つライブラリも--no-as-neededで保持する。
# FOAM_EXTRA_LDFLAGSは本体のライブラリより前に入るため、ここでas-neededへ戻さない。
build_extra_ldflags="-Wl,--no-as-needed -L${AOCL_ROOT}/lib -lalm"
build_cc=${aspire2a_cc}
build_cxx=${aspire2a_cxx}
build_mpi_launcher=${aspire2a_mpi_launcher}
build_wm_compiler=${aspire2a_wm_compiler}
build_wm_mplib=${aspire2a_wm_mplib}

prepare_build_sources() {
  install -d -m 0750 "${build_tree}/OpenFOAM" "${build_tree}/ThirdParty" "${build_tree}/IMB"
  tar -xzf "${OPENFOAM_SOURCE_ARCHIVE}" -C "${build_tree}/OpenFOAM" --strip-components=1
  tar -xzf "${THIRDPARTY_SOURCE_ARCHIVE}" -C "${build_tree}/ThirdParty" --strip-components=1
  tar -xzf "${IMB_SOURCE_ARCHIVE}" -C "${build_tree}/IMB" --strip-components=1
  install -d "${build_tree}/ThirdParty/sources/scotch"
  cp -a /app/apps/openfoam/2512/ThirdParty-v2512/sources/scotch/scotch_6.1.0 "${build_tree}/ThirdParty/sources/scotch/"
  scotch_source_identity=$("${GITHUB_WORKSPACE}/scripts/source-tree-identity.sh" "${build_tree}/ThirdParty/sources/scotch/scotch_6.1.0")
  cluster_compile_flags=(--compile-flag "SCOTCH_SOURCE_IDENTITY=${scotch_source_identity}" --compile-flag "IMB_SOURCE_OID=${IMB_SOURCE_OID}" --compile-flag "ASPIRE2A_TOOLCHAIN=${aspire2a_toolchain}" --compile-flag "AOCL_MODULE=${aspire2a_aocl_module}" --compile-flag "AOCL_ROOT=${AOCL_ROOT}" --compile-flag "AOCL_LIBM=${aspire2a_aocl_libm}" --compile-flag "AOCL_LIBMEM=${aspire2a_aocl_libmem}" --compile-flag "CRAY_MPICH_VERSION=${CRAY_MPICH_VERSION}" --compile-flag "LIBFABRIC_VERSION=${aspire2a_libfabric_version}" --compile-flag "PRGENV=${PE_ENV}" --compile-flag "CCACHE=${aspire2a_ccache}" --compile-flag "CCACHE_VERSION=${aspire2a_ccache_version}" --compile-flag "CCACHE_NAMESPACE=${build_ccache_namespace}" --compile-flag "CCACHE_REMOTE_STORAGE=${CCACHE_REMOTE_STORAGE}")
}

finish_cluster_build() {
  make -C "${build_tree}/IMB" CC=cc CXX=CC IMB-MPI1 > "${BUILD_DIR}/logs/imb-mpi1-build.log" 2>&1
  install -m 0755 "${build_tree}/IMB/IMB-MPI1" "${FOAM_APPBIN}/IMB-MPI1"
  ldd "${FOAM_APPBIN}/simpleFoam" > "${BUILD_DIR}/logs/simplefoam-ldd.log"
  grep -Fq "${aspire2a_aocl_libm}" "${BUILD_DIR}/logs/simplefoam-ldd.log"
  ldd "${FOAM_APPBIN}/decomposePar" > "${BUILD_DIR}/logs/decomposepar-ldd.log"
  if ! grep -Fq "${FOAM_LIBBIN}/libscotchDecomp.so" "${BUILD_DIR}/logs/decomposepar-ldd.log"; then cat "${BUILD_DIR}/logs/decomposepar-ldd.log" >&2; exit 1; fi
  if ldd -r "${FOAM_LIBBIN}/libfieldFunctionObjects.so" > "${BUILD_DIR}/logs/field-function-objects-ldd-r.log" 2>&1 && ! grep -q 'undefined symbol:' "${BUILD_DIR}/logs/field-function-objects-ldd-r.log"; then :; else cat "${BUILD_DIR}/logs/field-function-objects-ldd-r.log" >&2; exit 1; fi
  ldd "${FOAM_APPBIN}/IMB-MPI1" > "${BUILD_DIR}/logs/imb-mpi1-ldd.log"
  readelf --dynamic "${FOAM_APPBIN}/IMB-MPI1" > "${BUILD_DIR}/logs/imb-mpi1-dynamic.log"
  rm -rf -- "${build_tree}/IMB"
}
