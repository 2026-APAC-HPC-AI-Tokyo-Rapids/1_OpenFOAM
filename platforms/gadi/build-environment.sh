#!/usr/bin/env bash
# scripts/build-openfoam.shから読み込むGadi専用設定。
# 呼出元と共有する変数は、このファイル単独では定義・参照が完結しない。
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
# Actions 31990408500で48並列はメモリ不足。完走実績のある16並列を維持する。
build_parallelism=16
build_directory_mode=0750
build_extra_cxxflags="${build_tuning_flags}"
ccache_remote_dir="/scratch/hb15/${USER:?}/openfoam/gadi/ccache"
openfoam_source_oid="${OPENFOAM_SOURCE_OID}"
thirdparty_source_oid="${THIRDPARTY_SOURCE_OID}"
openfoam_source_algorithm=sha1
thirdparty_source_algorithm=sha1
module purge
module load intel-compiler-llvm/2025.1.1 intel-mpi/2021.15.0

prepare_build_sources() {
  install -d -m 0750 "${build_tree}/OpenFOAM" "${build_tree}/ThirdParty"
  install -d -m 0700 "${ccache_remote_dir}"
  tar -xzf "${OPENFOAM_SOURCE_ARCHIVE}" -C "${build_tree}/OpenFOAM" --strip-components=1
  tar -xzf "${THIRDPARTY_SOURCE_ARCHIVE}" -C "${build_tree}/ThirdParty" --strip-components=1
  install -d "${build_tree}/ThirdParty/sources/scotch"
  cp -a /apps/OpenFOAM/2512/ThirdParty-v2512/sources/scotch/scotch_6.1.0 "${build_tree}/ThirdParty/sources/scotch/"
  scotch_source_identity=$("${GITHUB_WORKSPACE}/scripts/source-tree-identity.sh" "${build_tree}/ThirdParty/sources/scotch/scotch_6.1.0")
  cluster_compile_flags=(--compile-flag "SCOTCH_SOURCE_IDENTITY=${scotch_source_identity}")
}

finish_cluster_build() {
  ccache --trim-dir "${ccache_remote_dir}" --trim-max-size 10GB || true
}
