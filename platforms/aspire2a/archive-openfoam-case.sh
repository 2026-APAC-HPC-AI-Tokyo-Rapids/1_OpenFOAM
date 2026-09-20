#!/usr/bin/env bash

set -euo pipefail

verify_archive() {
  local archive_dir=$1
  local cache_identity=$2
  printf '%s\n' "${cache_identity}" | cmp -s - "${archive_dir}/READY" || return 1
  jq -e --arg cache_identity "${cache_identity}" 'select(.schema_version == "openfoam-case-archive/v2" and .cache_identity == $cache_identity and .number_of_subdomains > 0 and .archive.name == "case.tar.zst" and (.archive.size_bytes | type) == "number" and (.archive.sha256 | test("^[0-9a-f]{64}$")) and (.case_manifest.size_bytes | type) == "number" and (.case_manifest.sha256 | test("^[0-9a-f]{64}$")))' "${archive_dir}/manifest.json" >/dev/null || return 1
  test "$(stat -c '%s' "${archive_dir}/case-manifest.json")" = "$(jq -er '.case_manifest.size_bytes' "${archive_dir}/manifest.json")" || return 1
  test "$(sha256sum "${archive_dir}/case-manifest.json" | awk '{print $1}')" = "$(jq -er '.case_manifest.sha256' "${archive_dir}/manifest.json")" || return 1
  test "$(stat -c '%s' "${archive_dir}/case.tar.zst")" = "$(jq -er '.archive.size_bytes' "${archive_dir}/manifest.json")" || return 1
  test "$(sha256sum "${archive_dir}/case.tar.zst" | awk '{print $1}')" = "$(jq -er '.archive.sha256' "${archive_dir}/manifest.json")" || return 1
}

if [[ $# -eq 3 && $1 == verify ]]; then
  verify_archive "$2" "$3"
  exit 0
fi

if [[ $# -ne 4 || $1 != create ]]; then
  echo "使用方法: $0 verify ARCHIVE_DIR CACHE_IDENTITY" >&2
  echo "          $0 create EXPANDED_CACHE_DIR ARCHIVE_DIR CACHE_IDENTITY" >&2
  exit 64
fi

expanded_cache_dir=$2
archive_dir=$3
cache_identity=$4
number_of_subdomains=$(jq -er --arg cache_identity "${cache_identity}" 'select(.schema_version == "openfoam-case-cache/v4" and .cache_identity == $cache_identity and .number_of_subdomains > 0) | .number_of_subdomains' "${expanded_cache_dir}/manifest.json")

if verify_archive "${archive_dir}" "${cache_identity}" 2>/dev/null; then
  printf 'cache_hit=true\ncache_dir=%s\n' "${archive_dir}"
  exit 0
fi

temporary="${archive_dir}.tmp.$$"
trap 'rm -rf -- "${temporary}"' EXIT
rm -rf -- "${temporary}"
install -d "${temporary}"
install -m 0644 "${expanded_cache_dir}/manifest.json" "${temporary}/case-manifest.json"
tar --use-compress-program='zstd -T0 -3' -cf "${temporary}/case.tar.zst" -C "${expanded_cache_dir}/case" .
jq -n --arg cache_identity "${cache_identity}" --argjson number_of_subdomains "${number_of_subdomains}" --argjson case_manifest_size_bytes "$(stat -c '%s' "${temporary}/case-manifest.json")" --arg case_manifest_sha256 "$(sha256sum "${temporary}/case-manifest.json" | awk '{print $1}')" --argjson archive_size_bytes "$(stat -c '%s' "${temporary}/case.tar.zst")" --arg archive_sha256 "$(sha256sum "${temporary}/case.tar.zst" | awk '{print $1}')" '{schema_version:"openfoam-case-archive/v2",cache_identity:$cache_identity,number_of_subdomains:$number_of_subdomains,case_manifest:{size_bytes:$case_manifest_size_bytes,sha256:$case_manifest_sha256},archive:{name:"case.tar.zst",size_bytes:$archive_size_bytes,sha256:$archive_sha256}}' > "${temporary}/manifest.json"
printf '%s\n' "${cache_identity}" > "${temporary}/READY"
verify_archive "${temporary}" "${cache_identity}"
rm -rf -- "${archive_dir}"
mv -- "${temporary}" "${archive_dir}"
trap - EXIT
printf 'cache_hit=false\ncache_dir=%s\n' "${archive_dir}"
