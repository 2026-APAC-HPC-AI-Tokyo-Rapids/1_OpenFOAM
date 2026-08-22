#!/usr/bin/env bash

set -euo pipefail

cluster=
profile_run_id=
config_path=${OPENFOAM_VTUNE_TRANSFER_CONFIG:-${HOME}/.config/openfoam-vtune-transfer/env}
ssh_bin=${OPENFOAM_VTUNE_SSH_BIN:-ssh}

while [[ $# -gt 0 ]]
do
  case "$1" in
    --cluster) [[ $# -ge 2 ]]; cluster=$2; shift 2 ;;
    --profile-run-id) [[ $# -ge 2 ]]; profile_run_id=$2; shift 2 ;;
    --config) [[ $# -ge 2 ]]; config_path=$2; shift 2 ;;
    *) printf '未知のVTune転送引数です: %s\n' "$1" >&2; exit 64 ;;
  esac
done

[[ -f "${config_path}" ]]
if [[ "${profile_run_id}" =~ ^(r-[0-9a-f]{32})-([0-9]+([.][A-Za-z0-9.-]+)?)$ ]]; then
  run_id=${BASH_REMATCH[1]}
  scheduler_job_id=${BASH_REMATCH[2]}
else
  printf 'VTune profile run IDが不正です: %s\n' "${profile_run_id}" >&2
  exit 64
fi

# shellcheck source=/dev/null
source "${config_path}"
: "${OPENFOAM_VTUNE_ARCHIVE_ROOT:?自宅側VTune保存先が必要です}"
[[ "${OPENFOAM_VTUNE_ARCHIVE_ROOT}" == /* && "${OPENFOAM_VTUNE_ARCHIVE_ROOT}" != / ]]

case "${cluster}" in
  genkai)
    source_target=${OPENFOAM_VTUNE_GENKAI_SSH_TARGET:?玄界SSH targetが必要です}
    source_root=${OPENFOAM_VTUNE_GENKAI_ROOT:?玄界VTune rootが必要です}
    ;;
  gadi)
    source_target=${OPENFOAM_VTUNE_GADI_SSH_TARGET:?Gadi SSH targetが必要です}
    source_root=${OPENFOAM_VTUNE_GADI_ROOT:?Gadi VTune rootが必要です}
    ;;
  *)
    printf '未対応のVTune転送クラスタです: %s\n' "${cluster}" >&2
    exit 64
    ;;
esac
[[ "${source_root}" == /* && "${source_root}" != / ]]

cluster_root="${OPENFOAM_VTUNE_ARCHIVE_ROOT}/${cluster}"
destination="${cluster_root}/${profile_run_id}"
archive="${destination}/vtune-result.tar.zst"
manifest="${destination}/manifest.json"

validate_archive() {
  local expected_size actual_size expected_sha actual_sha
  [[ -f "${archive}" && -f "${manifest}" ]]
  jq -e --arg cluster "${cluster}" --arg profile_run_id "${profile_run_id}" --arg run_id "${run_id}" --arg scheduler_job_id "${scheduler_job_id}" --arg source_target "${source_target}" --arg source_path "${source_root}/${profile_run_id}" 'select(.schema_version == "openfoam-vtune-archive/v1" and .cluster == $cluster and .profile_run_id == $profile_run_id and .run_id == $run_id and .scheduler_job_id == $scheduler_job_id and .source_target == $source_target and .source_path == $source_path and .archive.path == "vtune-result.tar.zst")' "${manifest}" >/dev/null
  expected_size=$(jq -er '.archive.size_bytes' "${manifest}")
  expected_sha=$(jq -er '.archive.sha256' "${manifest}")
  actual_size=$(stat -c '%s' "${archive}")
  actual_sha=$(sha256sum "${archive}" | awk '{print $1}')
  [[ "${expected_size}" =~ ^[0-9]+$ && "${expected_size}" == "${actual_size}" ]]
  [[ "${expected_sha}" =~ ^[0-9a-f]{64}$ && "${expected_sha}" == "${actual_sha}" ]]
  tar -I zstd -tf "${archive}" | awk -v prefix="${profile_run_id}/" 'index($0, prefix) != 1 { bad = 1 } $0 != prefix { payload = 1 } END { exit(bad || !payload) }'
}

remove_source() {
  "${ssh_bin}" "${source_target}" bash -s -- "${source_root}" "${profile_run_id}" <<'REMOTE_DELETE'
set -euo pipefail
root=$(realpath -e -- "$1")
profile_run_id=$2
[[ "${root}" == /* && "${root}" != / ]]
[[ "${profile_run_id}" =~ ^r-[0-9a-f]{32}-[0-9]+([.][A-Za-z0-9.-]+)?$ ]]
candidate="${root}/${profile_run_id}"
if [[ ! -e "${candidate}" ]]; then exit 0; fi
candidate_real=$(realpath -e -- "${candidate}")
[[ -d "${candidate_real}" && ! -L "${candidate}" && "$(dirname -- "${candidate_real}")" == "${root}" && "$(basename -- "${candidate_real}")" == "${profile_run_id}" ]]
rm -rf -- "${candidate_real:?}"
REMOTE_DELETE
}

if [[ -e "${destination}" ]]; then
  validate_archive
  remove_source
  printf 'home_archive=%s\nsource_removed=%s\n' "${archive}" "${source_root}/${profile_run_id}"
  exit 0
fi

install -d -m 0750 "${cluster_root}"
staging="${cluster_root}/.${profile_run_id}.incoming-${$}"
[[ ! -e "${staging}" ]]
install -d -m 0750 "${staging}"
cleanup() {
  local status=$?
  trap - EXIT
  if [[ -d "${staging}" ]]; then rm -rf -- "${staging:?}"; fi
  exit "${status}"
}
trap cleanup EXIT
staging_archive="${staging}/vtune-result.tar.zst"

"${ssh_bin}" "${source_target}" bash -s -- "${source_root}" "${profile_run_id}" > "${staging_archive}" <<'REMOTE_ARCHIVE'
set -euo pipefail
root=$(realpath -e -- "$1")
profile_run_id=$2
[[ "${root}" == /* && "${root}" != / ]]
[[ "${profile_run_id}" =~ ^r-[0-9a-f]{32}-[0-9]+([.][A-Za-z0-9.-]+)?$ ]]
candidate="${root}/${profile_run_id}"
candidate_real=$(realpath -e -- "${candidate}")
[[ -d "${candidate_real}" && ! -L "${candidate}" && "$(dirname -- "${candidate_real}")" == "${root}" && "$(basename -- "${candidate_real}")" == "${profile_run_id}" ]]
result_count=$(find "${candidate_real}" -mindepth 1 -maxdepth 1 -type d | wc -l)
[[ "${result_count}" -eq 1 ]]
find "${candidate_real}" -mindepth 2 -print -quit | grep -q .
tar -I zstd -cf - -C "${root}" "${profile_run_id}"
REMOTE_ARCHIVE

tar -I zstd -tf "${staging_archive}" | awk -v prefix="${profile_run_id}/" 'index($0, prefix) != 1 { bad = 1 } $0 != prefix { payload = 1 } END { exit(bad || !payload) }'
archive_size=$(stat -c '%s' "${staging_archive}")
archive_sha=$(sha256sum "${staging_archive}" | awk '{print $1}')
created_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
jq -n -c --arg cluster "${cluster}" --arg profile_run_id "${profile_run_id}" --arg run_id "${run_id}" --arg scheduler_job_id "${scheduler_job_id}" --arg source_target "${source_target}" --arg source_path "${source_root}/${profile_run_id}" --arg created_utc "${created_utc}" --arg sha256 "${archive_sha}" --argjson size_bytes "${archive_size}" '{schema_version:"openfoam-vtune-archive/v1",cluster:$cluster,profile_run_id:$profile_run_id,run_id:$run_id,scheduler_job_id:$scheduler_job_id,source_target:$source_target,source_path:$source_path,created_utc:$created_utc,archive:{path:"vtune-result.tar.zst",size_bytes:$size_bytes,sha256:$sha256}}' > "${staging}/manifest.json"
mv -T -- "${staging}" "${destination}"
trap - EXIT
validate_archive
remove_source
printf 'home_archive=%s\nsource_removed=%s\n' "${archive}" "${source_root}/${profile_run_id}"
