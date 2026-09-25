#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 9 ]]; then
  echo "使用方法: $0 SOURCE_CASE TARGET_CASE DECOMPOSE_PAR CHECK_MESH MESH_ARCHIVE WORKLOAD_DEFINITION BUILD_SIDECAR SUBDOMAINS CACHE_ROOT [--require-cache|--identity-only] [--case-default-hierarchical|--multi-level-ranks-per-node RANKS|--multi-level-domains DOMAIN,DOMAIN,...] [--weighted-boundary-cells]" >&2
  exit 64
fi

source_case=$1
target_case=$2
decompose_par=$3
check_mesh=$4
mesh_archive=$5
workload_definition=$6
build_sidecar=$7
subdomains=$8
cache_root=$9
shift 9
mode=
multi_level_ranks_per_node=
multi_level_domains=
case_default_hierarchical=false
weighted_boundary_cells=false
while [[ $# -gt 0 ]]
do
  case "$1" in
    --require-cache|--identity-only) [[ -z "${mode}" ]]; mode=$1; shift ;;
    --multi-level-ranks-per-node) [[ $# -ge 2 && -z "${multi_level_ranks_per_node}" ]]; multi_level_ranks_per_node=$2; shift 2 ;;
    --multi-level-domains) [[ $# -ge 2 && -z "${multi_level_domains}" ]]; multi_level_domains=$2; shift 2 ;;
    --case-default-hierarchical) [[ "${case_default_hierarchical}" == false ]]; case_default_hierarchical=true; shift ;;
    --weighted-boundary-cells) [[ "${weighted_boundary_cells}" == false ]]; weighted_boundary_cells=true; shift ;;
    *) echo "未対応のケース準備引数です: $1" >&2; exit 64 ;;
  esac
done
[[ "${subdomains}" =~ ^[1-9][0-9]*$ ]]
decomposition_method=scotch
decomposition_domains=()
[[ -z "${multi_level_ranks_per_node}" || -z "${multi_level_domains}" ]]
if [[ "${case_default_hierarchical}" == true ]]; then
  [[ -z "${multi_level_ranks_per_node}" && -z "${multi_level_domains}" && "${subdomains}" == 512 ]]
  grep -Eq '^[[:space:]]*decompositionMethod[[:space:]]+hierarchical;' "${source_case}/system/include/caseDefinition"
  grep -Eq '^[[:space:]]*nHierarchical[[:space:]]+\(16 8 4\);' "${source_case}/system/include/caseDefinition"
  decomposition_method=hierarchical
  decomposition_domains=(16 8 4)
fi
if [[ -n "${multi_level_ranks_per_node}" ]]; then
  [[ "${multi_level_ranks_per_node}" =~ ^[1-9][0-9]*$ ]]
  (( subdomains % multi_level_ranks_per_node == 0 ))
  node_domains=$(( subdomains / multi_level_ranks_per_node ))
  decomposition_method=multiLevel
  if (( node_domains == 1 )); then decomposition_domains=("${multi_level_ranks_per_node}"); else decomposition_domains=("${node_domains}" "${multi_level_ranks_per_node}"); fi
elif [[ -n "${multi_level_domains}" ]]; then
  [[ "${multi_level_domains}" =~ ^[1-9][0-9]*(,[1-9][0-9]*)+$ ]]
  IFS=, read -r -a decomposition_domains <<< "${multi_level_domains}"
  product=1
  for domain in "${decomposition_domains[@]}"; do (( product <= subdomains / domain )); product=$(( product * domain )); done
  (( product == subdomains ))
  decomposition_method=multiLevel
fi
decomposition_domains_text="(${decomposition_domains[*]})"
decomposition_domains_json=$(printf '%s\n' "${decomposition_domains[@]}" | jq -Rsc 'split("\n") | map(select(length > 0) | tonumber)')
if [[ "${weighted_boundary_cells}" == true ]]; then
  [[ "${decomposition_method}" == multiLevel && "${decomposition_domains_text}" == '(4 2 4 16)' && "${subdomains}" == 512 ]]
  weight_source="$(dirname "$0")/../platforms/aspire2a/write-decomposition-weights.c"
  weight_generator="$(dirname "$0")/../platforms/aspire2a/write-decomposition-weights"
  weight_source_sha256=$(sha256sum "${weight_source}" | awk '{print $1}')
else
  weight_source_sha256=none
fi

expected_size=$(jq -er '.mesh.size_bytes' "${workload_definition}")
expected_md5=$(jq -er '.mesh.md5' "${workload_definition}")
expected_sha256=$(jq -er '.mesh.sha256' "${workload_definition}")
test "$(stat -c '%s' "${mesh_archive}")" = "${expected_size}"
test "$(md5sum "${mesh_archive}" | awk '{print $1}')" = "${expected_md5}"
test "$(sha256sum "${mesh_archive}" | awk '{print $1}')" = "${expected_sha256}"

script_sha256=$(sha256sum "$0" | awk '{print $1}')
source_identity=$(cd "${source_case}" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
prepare_toolchain_identity=$(jq -ecS 'select(.schema_version == "build-sidecar/v1" and ([.runtime_objects[] | select(.kind == "executable" and (.role == "checkMesh" or .role == "decomposePar")) | .role] | sort) == ["checkMesh", "decomposePar"]) | {source_commits,compile_flags,precision,label_bits,runtime_objects:[.runtime_objects[] | select(.kind == "shared_library" or (.kind == "executable" and (.role == "checkMesh" or .role == "decomposePar")))]}' "${build_sidecar}" | sha256sum | awk '{print $1}')
cache_identity=$(printf '%s\n' "prepare=${script_sha256}" "toolchain=${prepare_toolchain_identity}" "case=${source_identity}" "mesh=${expected_sha256}" "subdomains=${subdomains}" "method=${decomposition_method}" "domains=${decomposition_domains_text}" "weight_generator=${weight_source_sha256}" 'fileHandler=uncollated' | sha256sum | awk '{print $1}')
cache_dir="${cache_root}/${cache_identity}"
if [[ "${mode}" == --identity-only ]]; then
  printf 'prepare_script_sha256=%s\ncache_identity=%s\ncache_dir=%s\n' "${script_sha256}" "${cache_identity}" "${cache_dir}"
  exit 0
fi
mkdir -p "${cache_root}"

cache_valid() {
  printf '%s\n' "${cache_identity}" | cmp -s - "${cache_dir}/READY"
}

cache_hit=true
if ! cache_valid; then
  if [[ "${mode}" == --require-cache ]]; then
    echo "必要なキャッシュが存在しないか無効です: ${cache_dir}" >&2
    exit 75
  fi
  cache_hit=false
  temporary="${cache_dir}.tmp.$$"
  cleanup_temporary() {
    status=$?
    trap - EXIT
    if [[ "${status}" -ne 0 && -d "${temporary}/case/logs" ]]; then find "${temporary}/case/logs" -type f -print -exec tail -n 200 {} \; >&2; fi
    rm -rf -- "${temporary:-}"
    exit "${status}"
  }
  trap cleanup_temporary EXIT
  chmod -R u+w "${cache_dir}" 2>/dev/null || true
  rm -rf -- "${cache_dir}" "${temporary}"
  install -d "${temporary}/case/logs"
  cp -a "${source_case}/." "${temporary}/case/"
  install -d "${temporary}/case/constant"
  cp "${temporary}/case/system/controlDict.noWrite" "${temporary}/case/system/controlDict"
  cp "${temporary}/case/system/fvSolution.fixedIter" "${temporary}/case/system/fvSolution"
  cp -a "${temporary}/case/0.orig" "${temporary}/case/0"
  sed -i -E "s/^(nCores[[:space:]]+)[0-9]+;/\\1${subdomains};/; s/^(decompositionMethod[[:space:]]+)[^;]+;/\\1${decomposition_method};/" "${temporary}/case/system/include/caseDefinition"
  if [[ "${decomposition_method}" == multiLevel ]]; then printf '\nmultiLevelCoeffs\n{\n    method scotch;\n    domains %s;\n}\n' "${decomposition_domains_text}" >> "${temporary}/case/system/decomposeParDict"; fi
  if [[ "${weighted_boundary_cells}" == true ]]; then printf '\nweightField costWeight;\n' >> "${temporary}/case/system/decomposeParDict"; fi
  tar -xzf "${mesh_archive}" -C "${temporary}/case/constant"
  (
    cd "${temporary}/case"
    "${check_mesh}" -constant -fileHandler uncollated > logs/checkMesh.log 2>&1
    if [[ "${weighted_boundary_cells}" == true ]]; then "${weight_generator}" constant/polyMesh/boundary constant/polyMesh/owner 0/costWeight > logs/decomposition-weights.log; fi
    "${decompose_par}" -constant -fileHandler uncollated > logs/decomposePar.log 2>&1
    if [[ "${weighted_boundary_cells}" == true ]]; then rm -f -- 0/costWeight processor*/0/costWeight; fi
  )
  printf '%s\n' "${cache_identity}" > "${temporary}/READY"
  jq -n --arg cache_identity "${cache_identity}" --arg prepare_script_sha256 "${script_sha256}" --arg prepare_toolchain_identity "${prepare_toolchain_identity}" --arg case_identity "${source_identity}" --arg mesh_sha256 "${expected_sha256}" --argjson number_of_subdomains "${subdomains}" --arg method "${decomposition_method}" --argjson domains "${decomposition_domains_json}" --arg weight_source_sha256 "${weight_source_sha256}" '{schema_version:"openfoam-case-cache/v4",cache_identity:$cache_identity,prepare_script_sha256:$prepare_script_sha256,prepare_toolchain_identity:$prepare_toolchain_identity,case_identity:$case_identity,mesh_sha256:$mesh_sha256,number_of_subdomains:$number_of_subdomains,method:$method,domains:$domains,weight_source_sha256:$weight_source_sha256,file_handler:"uncollated"}' > "${temporary}/manifest.json"
  find "${temporary}/case" -type f -exec chmod a-w {} +
  find "${temporary}/case" -type d -exec chmod a-w {} +
  mv "${temporary}" "${cache_dir}"
  trap - EXIT
fi

if [[ "${target_case}" != - ]]; then
  rm -rf -- "${target_case}"
  cp -a --reflink=auto "${cache_dir}/case" "${target_case}"
  chmod -R u+w "${target_case}"
fi
printf 'cache_hit=%s\nprepare_script_sha256=%s\ncache_dir=%s\n' "${cache_hit}" "${script_sha256}" "${cache_dir}"
