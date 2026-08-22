#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 5 ]]; then
  echo "使用方法: $0 BUILD_ARCHIVE BUILD_SIDECAR COMPUTE_TOOLS_ARCHIVE COMPUTE_TOOLS_MANIFEST TARGET_ROOT" >&2
  exit 64
fi

archive=$1
sidecar=$2
compute_tools_archive=$3
compute_tools_manifest=$4
target_root=$5

test "$(stat -c '%s' "${archive}")" = "$(jq -er '.build_archive.size_bytes' "${sidecar}")"
test "$(sha256sum "${archive}" | awk '{print $1}')" = "$(jq -er '.build_archive.sha256' "${sidecar}")"
test "$(stat -c '%s' "${compute_tools_archive}")" = "$(jq -er 'select(.schema_version == "openfoam-compute-tools-archive/v1" and .archive.path == "compute-tools.tar.zst") | .archive.size_bytes' "${compute_tools_manifest}")"
test "$(sha256sum "${compute_tools_archive}" | awk '{print $1}')" = "$(jq -er '.archive.sha256' "${compute_tools_manifest}")"
rm -rf -- "${target_root}"
install -d -m 0750 "${target_root}"
tar -I zstd -xf "${archive}" -C "${target_root}" --exclude='*.o' --exclude='./OpenFOAM/applications' --exclude='./ThirdParty/build' --exclude='./ThirdParty/sources' --exclude='*.cmake' --exclude='CMakeFiles' --exclude='CMakeCache.txt' --exclude='compile_commands.json' --exclude='install_manifest.txt' --exclude='Makefile'
tar -I zstd -xf "${compute_tools_archive}" -C "${target_root}"
test -x "${target_root}/OpenFOAM/platforms/linux64IcxDPInt32Opt/bin/simpleFoam"
test -x "${target_root}/experiment-metrics/.venv/bin/python"
test -x "${target_root}/scripts/exec-profiler.sh"
printf 'runtime_root=%s\nruntime_archive=%s\n' "${target_root}" "${archive}"
