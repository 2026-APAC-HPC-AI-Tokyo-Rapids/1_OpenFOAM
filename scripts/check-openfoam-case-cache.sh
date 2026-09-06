#!/usr/bin/env bash
# ログインノードから準備済みケースを確認する。75はcache miss、その他は入力エラー。
set -euo pipefail

[[ $# -eq 5 ]] || exit 64
cluster=$1
provision=$2
subdomains=$3
cache_root=$4
mesh_archive=$5
case "${cluster}" in genkai|gadi) ;; *) exit 64 ;; esac

# identity-onlyではOpenFOAM executableを起動しない。runtime展開やmodule設定も不要。
identity_output=$("${provision}/scripts/prepare-openfoam-case.sh" "${provision}/benchmark/occDrivAerStaticMesh" - - - "${mesh_archive}" "${provision}/benchmark/workload.json" "${provision}/control/build-sidecar.json" "${subdomains}" "${cache_root}" --identity-only) || exit 2
cache_identity=$(sed -n 's/^cache_identity=//p' <<< "${identity_output}")
[[ "${cache_identity}" =~ ^[0-9a-f]{64}$ ]] || exit 2
cache_dir="${cache_root}/${cache_identity}"
case "${cluster}" in
  genkai) printf '%s\n' "${cache_identity}" | cmp -s - "${cache_dir}/READY" || exit 75 ;;
  gadi) "${provision}/platforms/gadi/archive-openfoam-case.sh" verify "${cache_dir}" "${cache_identity}" || exit 75 ;;
esac
printf 'cache_hit=true\ncache_dir=%s\n' "${cache_dir}"
