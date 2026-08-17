#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 7 ]]; then
  echo "usage: $0 ARCHIVE_DIR CACHE_IDENTITY NODES RANKS_PER_NODE ITERATIONS TARGET_CASE RUNTIME_ROOT" >&2
  exit 64
fi

archive_dir=$1
cache_identity=$2
nodes=$3
ranks_per_node=$4
iterations=$5
target_case=$6
runtime_root=$7
node_ordinal=${PMI_RANK:?one staging rank per node is required}
[[ "${node_ordinal}" =~ ^[0-9]+$ ]]
(( node_ordinal < nodes ))
printf -v node_archive_name 'node-%03d.tar.zst' "${node_ordinal}"
printf '%s\n' "${cache_identity}" | cmp -s - "${archive_dir}/READY"
jq -e --arg cache_identity "${cache_identity}" --argjson nodes "${nodes}" --argjson ranks_per_node "${ranks_per_node}" --arg node_archive_name "${node_archive_name}" 'select(.schema_version == "openfoam-case-archive/v1" and .cache_identity == $cache_identity and .nodes == $nodes and .ranks_per_node == $ranks_per_node and (.archives | length) == ($nodes + 1) and any(.archives[]; .name == "common.tar.zst") and any(.archives[]; .name == $node_archive_name))' "${archive_dir}/manifest.json" >/dev/null
test "$(stat -c '%s' "${archive_dir}/case-manifest.json")" = "$(jq -er '.case_manifest.size_bytes' "${archive_dir}/manifest.json")"
test "$(sha256sum "${archive_dir}/case-manifest.json" | awk '{print $1}')" = "$(jq -er '.case_manifest.sha256' "${archive_dir}/manifest.json")"

for archive_name in common.tar.zst "${node_archive_name}"
do
  read -r expected_size expected_sha256 < <(jq -er --arg name "${archive_name}" '.archives[] | select(.name == $name) | "\(.size_bytes) \(.sha256)"' "${archive_dir}/manifest.json")
  test "$(stat -c '%s' "${archive_dir}/${archive_name}")" = "${expected_size}"
  test "$(sha256sum "${archive_dir}/${archive_name}" | awk '{print $1}')" = "${expected_sha256}"
done

rm -rf -- "${target_case}"
install -d "${target_case}"
tar -I zstd -xf "${archive_dir}/common.tar.zst" -C "${target_case}"
tar -I zstd -xf "${archive_dir}/${node_archive_name}" -C "${target_case}"
chmod -R u+w "${target_case}"
sed -i -E "s/^(endTime[[:space:]]+)[0-9]+;/\\1${iterations};/" "${target_case}/system/controlDict"
set +u
source "${runtime_root}/OpenFOAM/bin/tools/RunFunctions"
set -u
cd "${target_case}"
restore0Dir -processor
printf 'node_ordinal=%s\nhost=%s\ncase_dir=%s\n' "${node_ordinal}" "$(hostname)" "${target_case}"
