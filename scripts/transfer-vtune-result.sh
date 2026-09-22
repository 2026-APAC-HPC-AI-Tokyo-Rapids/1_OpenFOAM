#!/usr/bin/env bash

set -euo pipefail

cluster=
github_run_id=
profile_run_id=
source_dir=

while [[ $# -gt 0 ]]
do
  case "$1" in
    --cluster) [[ $# -ge 2 ]]; cluster=$2; shift 2 ;;
    --github-run-id) [[ $# -ge 2 ]]; github_run_id=$2; shift 2 ;;
    --profile-run-id) [[ $# -ge 2 ]]; profile_run_id=$2; shift 2 ;;
    --source-dir) [[ $# -ge 2 ]]; source_dir=$2; shift 2 ;;
    *) printf '未知のVTune転送引数です: %s\n' "$1" >&2; exit 64 ;;
  esac
done

[[ "${github_run_id}" =~ ^[1-9][0-9]*$ ]]
if [[ "${profile_run_id}" =~ ^(r-[0-9a-f]{32})-([0-9]+([.][A-Za-z0-9.-]+)?)$ ]]; then
  run_id=${BASH_REMATCH[1]}
  scheduler_job_id=${BASH_REMATCH[2]}
else
  printf 'VTune profile run IDが不正です: %s\n' "${profile_run_id}" >&2
  exit 64
fi

: "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT:?自宅側OpenFOAM成果物保存先が必要です}"
[[ "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" == /* && "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" != / ]]

case "${cluster}" in
  genkai|gadi) connection="${cluster}-shell" ;;
  *)
    printf '未対応のVTune転送クラスタです: %s\n' "${cluster}" >&2
    exit 64
    ;;
esac
[[ "${source_dir}" == /* && "${source_dir}" != / ]]

run_artifact_dir="${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}/${github_run_id}/${cluster}/openfoam-${cluster}-v2-${run_id}"
destination="${run_artifact_dir}/large-output"
vtune_archive="${destination}/vtune/vtune-result.tar.zst"
manifest="${destination}/manifest.json"

validate_destination() {
  local expected_size expected_sha vtune_result_available
  [[ -f "${manifest}" ]]
  jq -e --arg cluster "${cluster}" --arg github_run_id "${github_run_id}" --arg profile_run_id "${profile_run_id}" --arg run_id "${run_id}" --arg scheduler_job_id "${scheduler_job_id}" --arg source_connection "${connection}" --arg source_path "${source_dir}" 'select(.schema_version == "openfoam-large-output-archive/v1" and .cluster == $cluster and .github_run_id == $github_run_id and .profile_run_id == $profile_run_id and .run_id == $run_id and .scheduler_job_id == $scheduler_job_id and .source_connection == $source_connection and .source_path == $source_path)' "${manifest}" >/dev/null
  vtune_result_available=$(jq -r 'if has("vtune_result_available") then .vtune_result_available elif any(.files[]; .path == "vtune/vtune-result.tar.zst") then true else false end | select(type == "boolean")' "${manifest}")
  [[ "${vtune_result_available}" == true || "${vtune_result_available}" == false ]]
  if [[ "${vtune_result_available}" == true ]]; then
    [[ -f "${vtune_archive}" ]]
    tar -I zstd -tf "${vtune_archive}" | awk 'NF { found = 1 } END { exit(!found) }'
  else
    [[ ! -e "${vtune_archive}" ]]
  fi
  if [[ "${vtune_result_available}" == true ]]; then
    expected_size=$(jq -er '.files[] | select(.path == "vtune/vtune-result.tar.zst") | .size_bytes' "${manifest}")
    expected_sha=$(jq -er '.files[] | select(.path == "vtune/vtune-result.tar.zst") | .sha256' "${manifest}")
    [[ "$(stat -c '%s' "${vtune_archive}")" == "${expected_size}" ]]
    [[ "$(sha256sum "${vtune_archive}" | awk '{print $1}')" == "${expected_sha}" ]]
  fi
}

if [[ -e "${destination}" ]]; then
  validate_destination
  printf 'home_large_output=%s\nsource_preserved=%s\n' "${destination}" "${source_dir}"
  exit 0
fi

install -d -m 0750 "${run_artifact_dir}"
staging="${run_artifact_dir}/.large-output.incoming-${$}"
[[ ! -e "${staging}" ]]
install -d -m 0750 "${staging}"
cleanup() {
  local status=$?
  trap - EXIT
  if [[ -d "${staging}" ]]; then rm -rf -- "${staging:?}"; fi
  exit "${status}"
}
trap cleanup EXIT

vtune_result_available=true
install -d -m 0750 "${staging}/vtune"
if "${connection}" bash -s -- "${source_dir}" "${run_id}" > "${staging}/vtune/vtune-result.tar.zst" <<'REMOTE_VTUNE'
set -euo pipefail
candidate=$(realpath -e -- "$1")
run_id=$2
[[ ! -L "$1" && "$(basename -- "${candidate}")" == large-output && "$(basename -- "$(dirname -- "${candidate}")")" == "${run_id}" ]]
vtune="${candidate}/vtune"
[[ -d "${vtune}" && ! -L "${vtune}" ]]
readarray -d '' results < <(find "${vtune}" -mindepth 1 -maxdepth 1 -type d -print0)
if [[ "${#results[@]}" -eq 0 ]]; then exit 3; fi
[[ "${#results[@]}" -eq 1 ]]
[[ -n "$(find "${results[0]}" -mindepth 1 -print -quit)" ]]
tar -I zstd -cf - -C "${vtune}" "$(basename -- "${results[0]}")"
REMOTE_VTUNE
then
  :
else
  status=$?
  rm -rf -- "${staging}/vtune"
  if [[ "${status}" -eq 3 ]]; then vtune_result_available=false; else exit "${status}"; fi
fi

if [[ "${vtune_result_available}" == true ]]; then tar -I zstd -tf "${staging}/vtune/vtune-result.tar.zst" | awk 'NF { found = 1 } END { exit(!found) }'; fi
created_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
files=()
if [[ "${vtune_result_available}" == true ]]; then files+=("$(jq -n -c --arg path vtune/vtune-result.tar.zst --argjson size_bytes "$(stat -c '%s' "${staging}/vtune/vtune-result.tar.zst")" --arg sha256 "$(sha256sum "${staging}/vtune/vtune-result.tar.zst" | awk '{print $1}')" '{path:$path,size_bytes:$size_bytes,sha256:$sha256}')"); fi
printf '%s\n' "${files[@]}" | jq -s -c --arg cluster "${cluster}" --arg github_run_id "${github_run_id}" --arg profile_run_id "${profile_run_id}" --arg run_id "${run_id}" --arg scheduler_job_id "${scheduler_job_id}" --arg source_connection "${connection}" --arg source_path "${source_dir}" --arg created_utc "${created_utc}" --argjson vtune_result_available "${vtune_result_available}" '{schema_version:"openfoam-large-output-archive/v1",cluster:$cluster,github_run_id:$github_run_id,profile_run_id:$profile_run_id,run_id:$run_id,scheduler_job_id:$scheduler_job_id,source_connection:$source_connection,source_path:$source_path,created_utc:$created_utc,vtune_result_available:$vtune_result_available,files:.}' > "${staging}/manifest.json"
mv -T -- "${staging}" "${destination}"
trap - EXIT
validate_destination
printf 'home_large_output=%s\nvtune_result_available=%s\nsource_preserved=%s\n' "${destination}" "${vtune_result_available}" "${source_dir}"
