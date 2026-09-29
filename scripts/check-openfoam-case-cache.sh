#!/usr/bin/env bash
# ログインノードから準備済みケースを確認する。75はcache miss、その他は入力エラー。
set -euo pipefail

[[ $# -eq 5 ]] || exit 64
cluster=$1
provision=$2
subdomains=$3
cache_root=$4
mesh_archive=$5
case "${cluster}" in genkai|gadi|aspire2a) ;; *) exit 64 ;; esac

# identity-onlyではOpenFOAM executableを起動しない。runtime展開やmodule設定も不要。
prepare_options=(--identity-only)
if [[ "${cluster}" == aspire2a ]]; then
  case "${subdomains}" in
    128) decomposition_file=decomposition-1n.txt ;;
    256) decomposition_file=decomposition-2n.txt ;;
    512) decomposition_file=decomposition-4n.txt ;;
    *) echo "未対応のsubdomain数です: ${subdomains}" >&2; exit 64 ;;
  esac
  decomposition=$(cat "${provision}/platforms/aspire2a/${decomposition_file}")
  case "${decomposition}" in
    hierarchical) prepare_options=(--identity-only --case-default-hierarchical) ;;
    multilevel)
      [[ "${subdomains}" == 512 ]] || { echo 'multiLevelは4ノードのみ対応です' >&2; exit 64; }
      prepare_options=(--identity-only --multi-level-domains 4,2,4,16)
      ;;
    scotch|metis|kahip|ptscotch) prepare_options=(--identity-only --decomposition-method "${decomposition}") ;;
    *) echo '未対応の分割条件です' >&2; exit 64 ;;
  esac
fi
identity_output=$("${provision}/scripts/prepare-openfoam-case.sh" "${provision}/benchmark/occDrivAerStaticMesh" - - - "${mesh_archive}" "${provision}/benchmark/workload.json" "${provision}/control/build-sidecar.json" "${subdomains}" "${cache_root}" "${prepare_options[@]}") || exit 2
cache_identity=$(sed -n 's/^cache_identity=//p' <<< "${identity_output}")
[[ "${cache_identity}" =~ ^[0-9a-f]{64}$ ]] || exit 2
cache_dir="${cache_root}/${cache_identity}"
case "${cluster}" in
  genkai) printf '%s\n' "${cache_identity}" | cmp -s - "${cache_dir}/READY" || exit 75 ;;
  gadi|aspire2a) "${provision}/platforms/${cluster}/archive-openfoam-case.sh" verify "${cache_dir}" "${cache_identity}" || exit 75 ;;
esac
printf 'cache_hit=true\ncache_dir=%s\n' "${cache_dir}"
