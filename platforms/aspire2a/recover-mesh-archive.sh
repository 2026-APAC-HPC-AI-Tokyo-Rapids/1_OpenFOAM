#!/usr/bin/env bash
set -euo pipefail

[[ $# == 0 ]]
: "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT:?成果物保存先が必要です}"
: "${GITHUB_RUN_ID:?Actions実行IDが必要です}"
: "${GITHUB_SHA:?回収処理のcommitが必要です}"
[[ "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" == /* && "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" != / ]]
cache_identity=98bcec2d9fc050ec941ae41d29d4d21855a42b63bfd64a532e61d2db92679634
source_dir="/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/case-archives/${cache_identity}"
destination="${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}/37420126890/aspire2a/mesh-basic"
staging="${destination}.incoming-3"
[[ ! -e "${destination}" ]]
[[ "$(cat "${staging}/READY")" == "${cache_identity}" ]]
jq -e --arg identity "${cache_identity}" 'select(.schema_version == "openfoam-case-archive/v2" and .cache_identity == $identity and .number_of_subdomains == 512 and .archive.name == "case.tar.zst")' "${staging}/manifest.json" >/dev/null
jq -e --arg identity "${cache_identity}" 'select(.schema_version == "openfoam-case-cache/v4" and .cache_identity == $identity and .number_of_subdomains == 512 and .method == "scotch" and .domains == [] and .file_handler == "uncollated")' "${staging}/case-manifest.json" >/dev/null
size_bytes=$(stat -c '%s' "${staging}/case.tar.zst")
expected_bytes=$(jq -er '.archive.size_bytes' "${staging}/manifest.json")
[[ "${expected_bytes}" =~ ^[1-9][0-9]*$ && "${size_bytes}" -gt 0 && "${size_bytes}" -le "${expected_bytes}" ]]
printf 'Resume Basic archive at byte %s of %s; keep partial data on interruption.\n' "${size_bytes}" "${expected_bytes}"

# The retained prefix belongs to this same immutable prepared archive.
# Keep it on failure; append mode sends only the remaining bytes over SSH.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
rsync --partial --append --info=progress2 --rsh="bash ${script_dir}/rsync-mesh-shell.sh" "aspire2a-mesh:${source_dir}/case.tar.zst" "${staging}/case.tar.zst"
[[ "$(stat -c '%s' "${staging}/case.tar.zst")" == "${expected_bytes}" ]]
zstd -t -- "${staging}/case.tar.zst"
jq -n --arg source_dir "${source_dir}" --arg recovery_run "${GITHUB_RUN_ID}" --arg commit "${GITHUB_SHA}" --arg created_utc "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" --argjson resumed_from_bytes "${size_bytes}" --argjson size_bytes "${expected_bytes}" --arg sha256 "$(sha256sum "${staging}/case.tar.zst" | awk '{print $1}')" '{schema_version:"openfoam-mesh-recovery/v1",case_name:"basic",source_connection:"aspire2a-shell",source_dir:$source_dir,reference_github_run_id:"37206922099",recovery_github_run_id:$recovery_run,recovery_commit:$commit,created_utc:$created_utc,resumed_from_bytes:$resumed_from_bytes,archive:{path:"case.tar.zst",size_bytes:$size_bytes,sha256:$sha256},contents:"Decomposed mesh and initial fields; not final solver fields"}' > "${staging}/recovery.json"
mv -T -- "${staging}" "${destination}"
printf 'Recovered Basic archive: %s\nASPIRE source archive retained: %s\n' "${destination}" "${source_dir}"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  printf '### Basic mesh recovery completed\n\n- [Download directory](https://mizuha-dev.com/files/openfoam-artifacts/37420126890/aspire2a/mesh-basic/)\n- Resumed from byte: %s\n- Final size: %s bytes\n- Mesh: 512 scotch partitions and initial fields.\n- ASPIRE source archive retained.\n' "${size_bytes}" "${expected_bytes}" >> "${GITHUB_STEP_SUMMARY}"
fi
