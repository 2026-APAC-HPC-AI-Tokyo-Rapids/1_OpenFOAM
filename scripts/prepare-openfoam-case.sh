#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 9 || $# -gt 10 ]]; then
  echo "使用方法: $0 SOURCE_CASE TARGET_CASE DECOMPOSE_PAR CHECK_MESH MESH_ARCHIVE WORKLOAD_DEFINITION BUILD_SIDECAR SUBDOMAINS CACHE_ROOT [--require-cache|--identity-only]" >&2
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
mode=${10:-}
case "${mode}" in
  ''|--require-cache|--identity-only) ;;
  *) echo "未対応のケース準備モードです: ${mode}" >&2; exit 64 ;;
esac
[[ "${subdomains}" =~ ^[1-9][0-9]*$ ]]

expected_size=$(jq -er '.mesh.size_bytes' "${workload_definition}")
expected_md5=$(jq -er '.mesh.md5' "${workload_definition}")
expected_sha256=$(jq -er '.mesh.sha256' "${workload_definition}")
test "$(stat -c '%s' "${mesh_archive}")" = "${expected_size}"
test "$(md5sum "${mesh_archive}" | awk '{print $1}')" = "${expected_md5}"
test "$(sha256sum "${mesh_archive}" | awk '{print $1}')" = "${expected_sha256}"

script_sha256=$(sha256sum "$0" | awk '{print $1}')
source_identity=$(cd "${source_case}" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
prepare_toolchain_identity=$(jq -ecS 'select(.schema_version == "build-sidecar/v1" and ([.runtime_objects[] | select(.kind == "executable" and (.role == "checkMesh" or .role == "decomposePar")) | .role] | sort) == ["checkMesh", "decomposePar"]) | {source_commits,compile_flags,precision,label_bits,runtime_objects:[.runtime_objects[] | select(.kind == "shared_library" or (.kind == "executable" and (.role == "checkMesh" or .role == "decomposePar")))]}' "${build_sidecar}" | sha256sum | awk '{print $1}')
cache_identity=$(printf '%s\n' "prepare=${script_sha256}" "toolchain=${prepare_toolchain_identity}" "case=${source_identity}" "mesh=${expected_sha256}" "subdomains=${subdomains}" 'method=scotch' 'fileHandler=uncollated' | sha256sum | awk '{print $1}')
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
  sed -i -E "s/^(nCores[[:space:]]+)[0-9]+;/\\1${subdomains};/; s/^(decompositionMethod[[:space:]]+)[^;]+;/\\1scotch;/" "${temporary}/case/system/include/caseDefinition"
  tar -xzf "${mesh_archive}" -C "${temporary}/case/constant"
  (
    cd "${temporary}/case"
    "${check_mesh}" -constant -fileHandler uncollated > logs/checkMesh.log 2>&1
    "${decompose_par}" -constant -fileHandler uncollated > logs/decomposePar.log 2>&1
  )
  printf '%s\n' "${cache_identity}" > "${temporary}/READY"
  jq -n --arg cache_identity "${cache_identity}" --arg prepare_script_sha256 "${script_sha256}" --arg prepare_toolchain_identity "${prepare_toolchain_identity}" --arg case_identity "${source_identity}" --arg mesh_sha256 "${expected_sha256}" --argjson number_of_subdomains "${subdomains}" '{schema_version:"openfoam-case-cache/v4",cache_identity:$cache_identity,prepare_script_sha256:$prepare_script_sha256,prepare_toolchain_identity:$prepare_toolchain_identity,case_identity:$case_identity,mesh_sha256:$mesh_sha256,number_of_subdomains:$number_of_subdomains,method:"scotch",file_handler:"uncollated"}' > "${temporary}/manifest.json"
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
