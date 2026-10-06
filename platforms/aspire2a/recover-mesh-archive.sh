#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo '使用方法: recover-mesh-archive.sh {basic|bonus}' >&2
  exit 64
fi
case_name=$1
case "${case_name}" in
  basic)
    cache_identity=98bcec2d9fc050ec941ae41d29d4d21855a42b63bfd64a532e61d2db92679634
    method=scotch
    domains='[]'
    reference_run=37206922099
    ;;
  bonus)
    cache_identity=b036b1f77a6c7485437b963d7653fc594460e8dd1983a1f5c7edc647cfc1f63c
    method=multiLevel
    domains='[4,2,4,16]'
    reference_run=37217223164
    ;;
  *) echo '回収対象はbasicまたはbonusです' >&2; exit 64 ;;
esac

: "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT:?成果物保存先が必要です}"
: "${GITHUB_RUN_ID:?Actions実行IDが必要です}"
: "${GITHUB_SHA:?回収処理のcommitが必要です}"
[[ "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" == /* && "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" != / ]]
[[ "${GITHUB_RUN_ID}" =~ ^[1-9][0-9]*$ ]]
source_dir="/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/case-archives/${cache_identity}"
destination="${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}/${GITHUB_RUN_ID}/aspire2a/mesh-${case_name}"
staging="${destination}.incoming-${GITHUB_RUN_ATTEMPT:-1}"
install -d -m 0750 "$(dirname -- "${destination}")"
mkdir -m 0750 -- "${staging}"
trap 'rm -rf -- "${staging:?}"' EXIT

# Read only from ASPIRE. Validate the selected case before transferring its large archive.
for member in READY manifest.json case-manifest.json; do
  aspire2a-shell --pull "${source_dir}/${member}" "${staging}"
done
[[ "$(cat "${staging}/READY")" == "${cache_identity}" ]]
jq -e --arg identity "${cache_identity}" 'select(.schema_version == "openfoam-case-archive/v2" and .cache_identity == $identity and .number_of_subdomains == 512 and .archive.name == "case.tar.zst")' "${staging}/manifest.json" >/dev/null
jq -e --arg identity "${cache_identity}" --arg method "${method}" --argjson domains "${domains}" 'select(.schema_version == "openfoam-case-cache/v4" and .cache_identity == $identity and .number_of_subdomains == 512 and .method == $method and .domains == $domains and .file_handler == "uncollated")' "${staging}/case-manifest.json" >/dev/null

aspire2a-shell --pull "${source_dir}/case.tar.zst" "${staging}"
zstd -t -- "${staging}/case.tar.zst"
# Record the actual recovered file's identity; do not duplicate the archive in GitHub artifacts.
jq -n --arg case_name "${case_name}" --arg source_dir "${source_dir}" --arg reference_run "${reference_run}" --arg recovery_run "${GITHUB_RUN_ID}" --arg commit "${GITHUB_SHA}" --arg created_utc "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" --argjson size_bytes "$(stat -c '%s' "${staging}/case.tar.zst")" --arg sha256 "$(sha256sum "${staging}/case.tar.zst" | awk '{print $1}')" '{schema_version:"openfoam-mesh-recovery/v1",case_name:$case_name,source_connection:"aspire2a-shell",source_dir:$source_dir,reference_github_run_id:$reference_run,recovery_github_run_id:$recovery_run,recovery_commit:$commit,created_utc:$created_utc,archive:{path:"case.tar.zst",size_bytes:$size_bytes,sha256:$sha256},contents:"Decomposed mesh and initial fields; not final solver fields"}' > "${staging}/recovery.json"
# Refuse to replace an existing published directory, including when a job is re-run.
[[ ! -e "${destination}" ]]
mv -T -- "${staging}" "${destination}"
trap - EXIT
printf '回収先: %s\nASPIRE原本を保持: %s\n' "${destination}" "${source_dir}"
if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  printf '### ASPIRE-2A %s mesh\n\n- [Download directory](https://mizuha-dev.com/files/openfoam-artifacts/%s/aspire2a/mesh-%s/)\n- Source: `%s`\n- Reference Actions run: `%s`\n- Mesh: 512 partitions, `%s`\n- Initial fields only; final solver fields are not included.\n- ASPIRE source archive is preserved.\n' "${case_name}" "${GITHUB_RUN_ID}" "${case_name}" "${source_dir}" "${reference_run}" "${method}" >> "${GITHUB_STEP_SUMMARY}"
fi
