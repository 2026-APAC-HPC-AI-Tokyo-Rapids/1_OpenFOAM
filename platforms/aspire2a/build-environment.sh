#!/usr/bin/env bash
# scripts/build-openfoam.shから読み込むASPIRE-2A専用設定。
# shellcheck disable=SC2034,SC2154
: "${OPENFOAM_SOURCE_ARCHIVE:?OpenFOAM source archive is required}"
: "${OPENFOAM_SOURCE_ARCHIVE_SHA256:?OpenFOAM source archive digest is required}"
: "${OPENFOAM_SOURCE_OID:?OpenFOAM source commit is required}"
: "${THIRDPARTY_SOURCE_ARCHIVE:?ThirdParty source archive is required}"
: "${THIRDPARTY_SOURCE_ARCHIVE_SHA256:?ThirdParty source archive digest is required}"
: "${THIRDPARTY_SOURCE_OID:?ThirdParty source commit is required}"

[[ "${OPENFOAM_SOURCE_OID}" =~ ^[0-9a-f]{40,64}$ && "${THIRDPARTY_SOURCE_OID}" =~ ^[0-9a-f]{40,64}$ ]]
test "$(sha256sum "${OPENFOAM_SOURCE_ARCHIVE}" | awk '{print $1}')" = "${OPENFOAM_SOURCE_ARCHIVE_SHA256}"
test "$(sha256sum "${THIRDPARTY_SOURCE_ARCHIVE}" | awk '{print $1}')" = "${THIRDPARTY_SOURCE_ARCHIVE_SHA256}"
build_parallelism=16
build_directory_mode=0750
build_extra_cxxflags="${build_tuning_flags}"
build_cc=cc
build_cxx=CC
build_wm_compiler=Gcc
build_wm_mplib=CRAY-MPICH
build_compile_control=
build_use_ccache=false
openfoam_source_oid="${OPENFOAM_SOURCE_OID}"
thirdparty_source_oid="${THIRDPARTY_SOURCE_OID}"
openfoam_source_algorithm=sha1
thirdparty_source_algorithm=sha1
module purge
module load PrgEnv-gnu craype-x86-milan mkl

prepare_build_sources() {
  install -d -m 0750 "${build_tree}/OpenFOAM" "${build_tree}/ThirdParty"
  tar -xzf "${OPENFOAM_SOURCE_ARCHIVE}" -C "${build_tree}/OpenFOAM" --strip-components=1
  tar -xzf "${THIRDPARTY_SOURCE_ARCHIVE}" -C "${build_tree}/ThirdParty" --strip-components=1
  install -d "${build_tree}/ThirdParty/sources/scotch"
  cp -a /app/apps/openfoam/2512/ThirdParty-v2512/sources/scotch/scotch_6.1.0 "${build_tree}/ThirdParty/sources/scotch/"
  scotch_source_identity=$(find "${build_tree}/ThirdParty/sources/scotch/scotch_6.1.0" -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
  cluster_compile_flags=(--compile-flag "SCOTCH_SOURCE_IDENTITY=${scotch_source_identity}" --compile-flag "CRAY_MPICH_VERSION=${CRAY_MPICH_VERSION:-unknown}" --compile-flag "PRGENV=${PE_ENV:-GNU}")
}

finish_cluster_build() {
  :
}
