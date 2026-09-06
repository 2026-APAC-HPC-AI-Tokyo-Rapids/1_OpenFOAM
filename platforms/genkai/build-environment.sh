#!/usr/bin/env bash
# scripts/build-openfoam.shから読み込む玄界専用設定。
# 呼出元と共有する変数は、このファイル単独では定義・参照が完結しない。
# shellcheck disable=SC2034,SC2154,SC2153
: "${GIT_MIRROR_DIR:?}"
: "${SOURCE_ARCHIVE_CACHE_DIR:?}"
openfoam_source_ref=refs/tags/OpenFOAM-v2512
thirdparty_source_ref=refs/tags/v2512
# 2ソケット各60物理コア。SMTはコンパイル並列数に含めない。
build_parallelism=120
build_directory_mode=2775
genkai_cpp=/opt/rh/gcc-toolset-11/root/usr/bin/cpp
optimization_report_flags='-qopt-report=3 -qopt-report-phase=loop,vec,cg'
build_extra_cxxflags="${build_tuning_flags:+${build_tuning_flags} }${optimization_report_flags}"
cluster_compile_flags=(--compile-flag "CPP=${genkai_cpp}" --compile-flag SCOTCH_SOURCE_SHA256=4fe537f608f0fe39ec78807f90203f9cca1181deb16bfa93b7d4cd440e01bbd1)
module purge
module load intel/2025.1.3 impi

prepare_build_sources() {
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

  # 玄界の計算ノードではOS標準の/lib/cppが対応するcc1を解決できない。
  # ログインノードだけでなく、coded functionを実行時コンパイルする計算ノードでも
  # 利用できるOS提供のgcc-toolset-11プリプロセッサをIcx規則へ固定する。
  genkai_cpp_rule="${build_tree}/OpenFOAM/wmake/rules/linux64Icx/general"
  test -x "${genkai_cpp}"
  sed -i "s|^CPP        = /lib/cpp |CPP        = ${genkai_cpp} |" "${genkai_cpp_rule}"
  grep -Fqx "CPP        = ${genkai_cpp} -traditional-cpp \$(GFLAGS)" "${genkai_cpp_rule}"

  # v2512が要求するScotch 6.1.0を、玄界の共有ソースキャッシュから展開する。
  scotch_archive="${SOURCE_ARCHIVE_CACHE_DIR}/scotch-v6.1.0.tar.gz"
  test "$(sha256sum "${scotch_archive}" | awk '{print $1}')" = 4fe537f608f0fe39ec78807f90203f9cca1181deb16bfa93b7d4cd440e01bbd1
  install -d "${build_tree}/ThirdParty/sources/scotch"
  tar -xzf "${scotch_archive}" -C "${build_tree}/ThirdParty/sources/scotch"
  mv "${build_tree}/ThirdParty/sources/scotch/scotch-v6.1.0" "${build_tree}/ThirdParty/sources/scotch/scotch_6.1.0"
}

finish_cluster_build() {
  report_list="${BUILD_DIR}/logs/optimization-report-files.txt"
  find "${build_tree}/OpenFOAM" -type f -name '*.optrpt' -printf '%P\n' | LC_ALL=C sort > "${report_list}"
  test -s "${report_list}"
  tar -I zstd -cf "${BUILD_DIR}/logs/optimization-reports.tar.zst" -C "${build_tree}/OpenFOAM" -T "${report_list}"
}
