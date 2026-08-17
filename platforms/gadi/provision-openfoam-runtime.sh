#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "使用方法: $0 BUILD_ARCHIVE BUILD_SIDECAR PROVISION_DIR" >&2
  exit 64
fi

archive=$1
sidecar=$2
provision_dir=$3

test "$(stat -c '%s' "${archive}")" = "$(jq -er '.build_archive.size_bytes' "${sidecar}")"
test "$(sha256sum "${archive}" | awk '{print $1}')" = "$(jq -er '.build_archive.sha256' "${sidecar}")"
ln -- "${archive}" "${provision_dir}/runtime.tar.zst"
tar -I zstd -xf "${archive}" -C "${provision_dir}" ./control/build-raw
