#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "使用方法: $0 ARCHIVE_DIR CACHE_IDENTITY ITERATIONS TARGET_CASE RUNTIME_ROOT" >&2
  exit 64
fi

archive_dir=$1
cache_identity=$2
iterations=$3
target_case=$4
runtime_root=$5
script_dir=$(dirname "${BASH_SOURCE[0]}")
"${script_dir}/archive-openfoam-case.sh" verify "${archive_dir}" "${cache_identity}"

rm -rf -- "${target_case}"
install -d "${target_case}"
tar -I zstd -xf "${archive_dir}/case.tar.zst" -C "${target_case}"
chmod -R u+w "${target_case}"
sed -i -E "s/^(endTime[[:space:]]+)[0-9]+;/\\1${iterations};/" "${target_case}/system/controlDict"
set +u
source "${runtime_root}/OpenFOAM/bin/tools/RunFunctions"
set -u
cd "${target_case}"
restore0Dir -processor
printf 'host=%s\ncase_dir=%s\n' "$(hostname)" "${target_case}"
