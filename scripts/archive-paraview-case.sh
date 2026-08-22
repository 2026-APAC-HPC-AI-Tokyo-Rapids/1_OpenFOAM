#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "使用方法: $0 CASE_DIR OUTPUT_DIR RANKS_PER_NODE NODE_COUNT GLOBAL_RANK_ENV" >&2
  exit 64
fi

case_dir=$1
output_dir=$2
ranks_per_node=$3
node_count=$4
global_rank_env=$5
[[ "${case_dir}" == /* && "${output_dir}" == /* ]]
[[ "${ranks_per_node}" =~ ^[1-9][0-9]*$ && "${node_count}" =~ ^[1-9][0-9]*$ ]]
[[ "${global_rank_env}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]
node_ordinal=${!global_rank_env:?node ordinal is required}
[[ "${node_ordinal}" =~ ^[0-9]+$ ]]
(( node_ordinal < node_count ))

first_rank=$(( node_ordinal * ranks_per_node ))
last_rank=$(( first_rank + ranks_per_node - 1 ))
members=()
for (( rank = first_rank; rank <= last_rank; rank++ )); do
  [[ -d "${case_dir}/processor${rank}" ]]
  members+=("processor${rank}")
done
if (( node_ordinal == 0 )); then
  : > "${case_dir}/occDrivAerStaticMesh.foam"
  members=(0.orig constant system occDrivAerStaticMesh.foam "${members[@]}")
fi

install -d -m 2770 "${output_dir}"
part_name=$(printf 'paraview-case-node-%02d-of-%02d.tar' "$(( node_ordinal + 1 ))" "${node_count}")
temporary="${output_dir}/.${part_name}.tmp-${$}"
trap 'rm -f -- "${temporary}"' EXIT
tar --blocking-factor=1 -cf "${temporary}" -C "${case_dir}" "${members[@]}"
if (( node_ordinal + 1 < node_count )); then truncate -s -1024 "${temporary}"; fi
mv -- "${temporary}" "${output_dir}/${part_name}"
trap - EXIT
