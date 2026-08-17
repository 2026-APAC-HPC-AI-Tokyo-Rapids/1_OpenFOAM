#!/usr/bin/env bash

set -euo pipefail

verify_archive() {
  local archive_dir=$1
  local cache_identity=$2
  local nodes=$3
  local ranks_per_node=$4
  printf '%s\n' "${cache_identity}" | cmp -s - "${archive_dir}/READY" || return 1
  jq -e --arg cache_identity "${cache_identity}" --argjson nodes "${nodes}" --argjson ranks_per_node "${ranks_per_node}" 'select(.schema_version == "openfoam-case-archive/v1" and .cache_identity == $cache_identity and .nodes == $nodes and .ranks_per_node == $ranks_per_node and .number_of_subdomains == ($nodes * $ranks_per_node) and (.archives | length) == ($nodes + 1) and (.case_manifest.size_bytes | type) == "number" and (.case_manifest.sha256 | test("^[0-9a-f]{64}$")))' "${archive_dir}/manifest.json" >/dev/null || return 1
  test "$(stat -c '%s' "${archive_dir}/case-manifest.json")" = "$(jq -er '.case_manifest.size_bytes' "${archive_dir}/manifest.json")" || return 1
  test "$(sha256sum "${archive_dir}/case-manifest.json" | awk '{print $1}')" = "$(jq -er '.case_manifest.sha256' "${archive_dir}/manifest.json")" || return 1
  local archive_count=0
  while IFS=$'\t' read -r name size sha256
  do
    [[ "${name}" == common.tar.zst || "${name}" =~ ^node-[0-9]{3}[.]tar[.]zst$ ]] || return 1
    test "$(stat -c '%s' "${archive_dir}/${name}")" = "${size}" || return 1
    test "$(sha256sum "${archive_dir}/${name}" | awk '{print $1}')" = "${sha256}" || return 1
    archive_count=$(( archive_count + 1 ))
  done < <(jq -er '.archives[] | [.name, .size_bytes, .sha256] | @tsv' "${archive_dir}/manifest.json")
  test "${archive_count}" -eq $(( nodes + 1 ))
}

if [[ $# -eq 5 && $1 == verify ]]; then
  verify_archive "$2" "$3" "$4" "$5"
  exit 0
fi

if [[ $# -ne 6 || $1 != create ]]; then
  echo "usage: $0 verify ARCHIVE_DIR CACHE_IDENTITY NODES RANKS_PER_NODE" >&2
  echo "       $0 create EXPANDED_CACHE_DIR ARCHIVE_DIR CACHE_IDENTITY NODES RANKS_PER_NODE" >&2
  exit 64
fi

expanded_cache_dir=$2
archive_dir=$3
cache_identity=$4
nodes=$5
ranks_per_node=$6
[[ "${nodes}" =~ ^[1-9][0-9]*$ && "${ranks_per_node}" =~ ^[1-9][0-9]*$ ]]
number_of_subdomains=$(( nodes * ranks_per_node ))
jq -e --arg cache_identity "${cache_identity}" --argjson number_of_subdomains "${number_of_subdomains}" 'select(.schema_version == "openfoam-case-cache/v4" and .cache_identity == $cache_identity and .number_of_subdomains == $number_of_subdomains)' "${expanded_cache_dir}/manifest.json" >/dev/null

if verify_archive "${archive_dir}" "${cache_identity}" "${nodes}" "${ranks_per_node}" 2>/dev/null; then
  printf 'cache_hit=true\ncache_dir=%s\n' "${archive_dir}"
  exit 0
fi

temporary="${archive_dir}.tmp.$$"
trap 'rm -rf -- "${temporary}"' EXIT
rm -rf -- "${temporary}"
install -d "${temporary}"
install -m 0644 "${expanded_cache_dir}/manifest.json" "${temporary}/case-manifest.json"
tar --use-compress-program='zstd -T0 -3' -cf "${temporary}/common.tar.zst" --exclude='./processor[0-9]*' --exclude='./constant/polyMesh' -C "${expanded_cache_dir}/case" .

for (( node = 0; node < nodes; node++ ))
do
  processors=()
  first_rank=$(( node * ranks_per_node ))
  for (( offset = 0; offset < ranks_per_node; offset++ )); do processors+=("processor$(( first_rank + offset ))"); done
  printf -v archive_name 'node-%03d.tar.zst' "${node}"
  tar --use-compress-program='zstd -T0 -3' -cf "${temporary}/${archive_name}" -C "${expanded_cache_dir}/case" "${processors[@]}"
done

archives_json="${temporary}/archives.json"
for archive_path in "${temporary}"/*.tar.zst
do
  jq -n --arg name "$(basename "${archive_path}")" --argjson size_bytes "$(stat -c '%s' "${archive_path}")" --arg sha256 "$(sha256sum "${archive_path}" | awk '{print $1}')" '{name:$name,size_bytes:$size_bytes,sha256:$sha256}'
done | jq -s 'sort_by(.name)' > "${archives_json}"
jq -n --arg cache_identity "${cache_identity}" --argjson nodes "${nodes}" --argjson ranks_per_node "${ranks_per_node}" --argjson number_of_subdomains "${number_of_subdomains}" --argjson case_manifest_size_bytes "$(stat -c '%s' "${temporary}/case-manifest.json")" --arg case_manifest_sha256 "$(sha256sum "${temporary}/case-manifest.json" | awk '{print $1}')" --slurpfile archives "${archives_json}" '{schema_version:"openfoam-case-archive/v1",cache_identity:$cache_identity,nodes:$nodes,ranks_per_node:$ranks_per_node,number_of_subdomains:$number_of_subdomains,case_manifest:{size_bytes:$case_manifest_size_bytes,sha256:$case_manifest_sha256},archives:$archives[0]}' > "${temporary}/manifest.json"
rm -- "${archives_json}"
printf '%s\n' "${cache_identity}" > "${temporary}/READY"
verify_archive "${temporary}" "${cache_identity}" "${nodes}" "${ranks_per_node}"
rm -rf -- "${archive_dir}"
mv -- "${temporary}" "${archive_dir}"
trap - EXIT
printf 'cache_hit=false\ncache_dir=%s\n' "${archive_dir}"
