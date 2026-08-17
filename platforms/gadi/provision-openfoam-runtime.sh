#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 BUILD_ARCHIVE BUILD_SIDECAR PROVISION_DIR RUNTIME_CACHE_ROOT" >&2
  exit 64
fi

archive=$1
sidecar=$2
provision_dir=$3
runtime_cache_root=$4

test "$(stat -c '%s' "${archive}")" = "$(jq -er '.build_archive.size_bytes' "${sidecar}")"
test "$(sha256sum "${archive}" | awk '{print $1}')" = "$(jq -er '.build_archive.sha256' "${sidecar}")"
runtime_key=$(jq -er '.build_archive.sha256 | select(test("^[0-9a-f]{64}$"))' "${sidecar}")
runtime_cache="${runtime_cache_root}/${runtime_key}"
install -d -m 0750 "${runtime_cache_root}"
exec {runtime_cache_lock_fd}>"${runtime_cache_root}/.gadi-populate.lock"
flock "${runtime_cache_lock_fd}"
if [[ ! -f "${runtime_cache}/READY" ]]; then
  runtime_cache_temporary=$(mktemp -d "${runtime_cache_root}/.${runtime_key}.${GITHUB_RUN_ID:?GitHub run ID is required}.${GITHUB_RUN_ATTEMPT:?GitHub run attempt is required}.XXXXXXXX")
  trap 'rm -rf -- "${runtime_cache_temporary}"' EXIT
  tar -I zstd -xf "${archive}" -C "${runtime_cache_temporary}" --exclude='*.o' --exclude='./OpenFOAM/applications' --exclude='./ThirdParty/build' --exclude='./ThirdParty/sources' --exclude='*.cmake' --exclude='CMakeFiles' --exclude='CMakeCache.txt' --exclude='compile_commands.json' --exclude='install_manifest.txt' --exclude='Makefile'
  touch "${runtime_cache_temporary}/READY"
  mv -- "${runtime_cache_temporary}" "${runtime_cache}"
  trap - EXIT
fi
flock -u "${runtime_cache_lock_fd}"
ln -s -- "${runtime_cache}/OpenFOAM" "${provision_dir}/OpenFOAM"
ln -s -- "${runtime_cache}/ThirdParty" "${provision_dir}/ThirdParty"
