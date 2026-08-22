#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "使用方法: $0 OUTPUT_DIR RUN_ID PROFILE_RUN_ID NODE_COUNT" >&2
  exit 64
fi

output_dir=$1
run_id=$2
profile_run_id=$3
node_count=$4
[[ "${output_dir}" == /* && "${run_id}" =~ ^r-[0-9a-f]{32}$ && "${profile_run_id}" =~ ^${run_id}-[0-9]+([.][A-Za-z0-9.-]+)?$ && "${node_count}" =~ ^[1-9][0-9]*$ ]]

parts=()
for (( node = 1; node <= node_count; node++ )); do
  part_name=$(printf 'paraview-case-node-%02d-of-%02d.tar' "${node}" "${node_count}")
  part_path="${output_dir}/${part_name}"
  [[ -f "${part_path}" ]]
  parts+=("${part_path}")
done
archive="${output_dir}/paraview-case.tar.zst"
temporary="${output_dir}/.paraview-case.tar.zst.tmp-${$}"
trap 'rm -f -- "${temporary}"' EXIT
cat "${parts[@]}" | zstd -T0 -3 -o "${temporary}"
tar -I zstd -tf "${temporary}" | awk '$0 == "occDrivAerStaticMesh.foam" { marker = 1 } /^processor[0-9]+\// { processors[$1] = 1 } END { exit(!marker) }'
mv -- "${temporary}" "${archive}"
trap - EXIT
rm -f -- "${parts[@]}"
created_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
jq -n -c --arg run_id "${run_id}" --arg profile_run_id "${profile_run_id}" --arg created_utc "${created_utc}" --arg path "paraview-case.tar.zst" --argjson node_count "${node_count}" --argjson size_bytes "$(stat -c '%s' "${archive}")" --arg sha256 "$(sha256sum "${archive}" | awk '{print $1}')" '{schema_version:"openfoam-paraview-archive/v1",run_id:$run_id,profile_run_id:$profile_run_id,created_utc:$created_utc,node_count:$node_count,extraction:"Extract paraview-case.tar.zst, then open occDrivAerStaticMesh.foam in ParaView.",archive:{path:$path,size_bytes:$size_bytes,sha256:$sha256}}' > "${output_dir}/manifest.json"
