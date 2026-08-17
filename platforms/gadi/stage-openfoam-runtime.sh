#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "使用方法: $0 BUILD_ARCHIVE BUILD_SIDECAR TARGET_ROOT" >&2
  exit 64
fi

archive=$1
sidecar=$2
target_root=$3

test "$(stat -c '%s' "${archive}")" = "$(jq -er '.build_archive.size_bytes' "${sidecar}")"
test "$(sha256sum "${archive}" | awk '{print $1}')" = "$(jq -er '.build_archive.sha256' "${sidecar}")"
rm -rf -- "${target_root}"
install -d -m 0750 "${target_root}"
tar -I zstd -xf "${archive}" -C "${target_root}" --exclude='*.o' --exclude='./OpenFOAM/applications' --exclude='./ThirdParty/build' --exclude='./ThirdParty/sources' --exclude='*.cmake' --exclude='CMakeFiles' --exclude='CMakeCache.txt' --exclude='compile_commands.json' --exclude='install_manifest.txt' --exclude='Makefile'
test -x "${target_root}/OpenFOAM/platforms/linux64IcxDPInt32Opt/bin/simpleFoam"
printf 'runtime_root=%s\nruntime_archive=%s\n' "${target_root}" "${archive}"
