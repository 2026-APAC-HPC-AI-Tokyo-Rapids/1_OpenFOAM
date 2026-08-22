#!/usr/bin/env bash

set -euo pipefail

cluster=
github_run_id=
profile_run_id=
config_path=${OPENFOAM_VTUNE_TRANSFER_CONFIG:-${HOME}/.config/openfoam-vtune-transfer/env}
ssh_bin=${OPENFOAM_VTUNE_SSH_BIN:-ssh}

while [[ $# -gt 0 ]]
do
  case "$1" in
    --cluster) [[ $# -ge 2 ]]; cluster=$2; shift 2 ;;
    --github-run-id) [[ $# -ge 2 ]]; github_run_id=$2; shift 2 ;;
    --profile-run-id) [[ $# -ge 2 ]]; profile_run_id=$2; shift 2 ;;
    --config) [[ $# -ge 2 ]]; config_path=$2; shift 2 ;;
    *) printf '未知のVTune転送引数です: %s\n' "$1" >&2; exit 64 ;;
  esac
done

[[ -f "${config_path}" && "${github_run_id}" =~ ^[1-9][0-9]*$ ]]
if [[ "${profile_run_id}" =~ ^(r-[0-9a-f]{32})-([0-9]+([.][A-Za-z0-9.-]+)?)$ ]]; then
  run_id=${BASH_REMATCH[1]}
  scheduler_job_id=${BASH_REMATCH[2]}
else
  printf 'VTune profile run IDが不正です: %s\n' "${profile_run_id}" >&2
  exit 64
fi

# shellcheck source=/dev/null
source "${config_path}"
: "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT:?自宅側OpenFOAM成果物保存先が必要です}"
[[ "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" == /* && "${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}" != / ]]

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

run_artifact_dir="${OPENFOAM_ARTIFACT_ARCHIVE_ROOT}/${github_run_id}/${cluster}/openfoam-${cluster}-v2-${run_id}"
destination="${run_artifact_dir}/large-output"
vtune_archive="${destination}/vtune/vtune-result.tar.zst"
paraview_archive="${destination}/paraview/paraview-case.tar.zst"
manifest="${destination}/manifest.json"

validate_destination() {
  local expected_size actual_size expected_sha actual_sha relative vtune_result_available
  [[ -f "${paraview_archive}" && -f "${destination}/paraview/manifest.json" && -f "${manifest}" ]]
  jq -e --arg cluster "${cluster}" --arg github_run_id "${github_run_id}" --arg profile_run_id "${profile_run_id}" --arg run_id "${run_id}" --arg scheduler_job_id "${scheduler_job_id}" --arg source_target "${source_target}" --arg source_path "${source_root}/${profile_run_id}" 'select(.schema_version == "openfoam-large-output-archive/v1" and .cluster == $cluster and .github_run_id == $github_run_id and .profile_run_id == $profile_run_id and .run_id == $run_id and .scheduler_job_id == $scheduler_job_id and .source_target == $source_target and .source_path == $source_path)' "${manifest}" >/dev/null
  vtune_result_available=$(jq -r 'if has("vtune_result_available") then .vtune_result_available elif any(.files[]; .path == "vtune/vtune-result.tar.zst") then true else false end | select(type == "boolean")' "${manifest}")
  [[ "${vtune_result_available}" == true || "${vtune_result_available}" == false ]]
  if [[ "${vtune_result_available}" == true ]]; then
    [[ -f "${vtune_archive}" ]]
    tar -I zstd -tf "${vtune_archive}" | awk 'NF { found = 1 } END { exit(!found) }'
  else
    [[ ! -e "${vtune_archive}" ]]
  fi
  for relative in paraview/paraview-case.tar.zst paraview/manifest.json; do
    expected_size=$(jq -er --arg relative "${relative}" '.files[] | select(.path == $relative) | .size_bytes' "${manifest}")
    expected_sha=$(jq -er --arg relative "${relative}" '.files[] | select(.path == $relative) | .sha256' "${manifest}")
    actual_size=$(stat -c '%s' "${destination}/${relative}")
    actual_sha=$(sha256sum "${destination}/${relative}" | awk '{print $1}')
    [[ "${expected_size}" =~ ^[0-9]+$ && "${expected_size}" == "${actual_size}" ]]
    [[ "${expected_sha}" =~ ^[0-9a-f]{64}$ && "${expected_sha}" == "${actual_sha}" ]]
  done
  if [[ "${vtune_result_available}" == true ]]; then
    expected_size=$(jq -er '.files[] | select(.path == "vtune/vtune-result.tar.zst") | .size_bytes' "${manifest}")
    expected_sha=$(jq -er '.files[] | select(.path == "vtune/vtune-result.tar.zst") | .sha256' "${manifest}")
    [[ "$(stat -c '%s' "${vtune_archive}")" == "${expected_size}" ]]
    [[ "$(sha256sum "${vtune_archive}" | awk '{print $1}')" == "${expected_sha}" ]]
  fi
  tar -I zstd -tf "${paraview_archive}" | awk '$0 == "occDrivAerStaticMesh.foam" { found = 1 } END { exit(!found) }'
  jq -e --arg run_id "${run_id}" --arg profile_run_id "${profile_run_id}" 'select(.schema_version == "openfoam-paraview-archive/v1" and .run_id == $run_id and .profile_run_id == $profile_run_id and .archive.path == "paraview-case.tar.zst")' "${destination}/paraview/manifest.json" >/dev/null
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
  validate_destination
  remove_source
  printf 'home_large_output=%s\nsource_removed=%s\n' "${destination}" "${source_root}/${profile_run_id}"
  exit 0
fi

install -d -m 0750 "${run_artifact_dir}"
staging="${run_artifact_dir}/.large-output.incoming-${$}"
[[ ! -e "${staging}" ]]
install -d -m 0750 "${staging}/paraview"
cleanup() {
  local status=$?
  trap - EXIT
  if [[ -d "${staging}" ]]; then rm -rf -- "${staging:?}"; fi
  exit "${status}"
}
trap cleanup EXIT

vtune_result_available=true
install -d -m 0750 "${staging}/vtune"
if "${ssh_bin}" "${source_target}" bash -s -- "${source_root}" "${profile_run_id}" > "${staging}/vtune/vtune-result.tar.zst" <<'REMOTE_VTUNE'
set -euo pipefail
root=$(realpath -e -- "$1")
profile_run_id=$2
candidate=$(realpath -e -- "${root}/${profile_run_id}")
[[ "$(dirname -- "${candidate}")" == "${root}" && "$(basename -- "${candidate}")" == "${profile_run_id}" ]]
readarray -d '' results < <(find "${candidate}" -mindepth 1 -maxdepth 1 -type d ! -name paraview -print0)
if [[ "${#results[@]}" -eq 0 ]]; then exit 3; fi
[[ "${#results[@]}" -eq 1 ]]
[[ -n "$(find "${results[0]}" -mindepth 1 -print -quit)" ]]
tar -I zstd -cf - -C "${candidate}" "$(basename -- "${results[0]}")"
REMOTE_VTUNE
then
  :
else
  status=$?
  rm -rf -- "${staging}/vtune"
  if [[ "${status}" -eq 3 ]]; then vtune_result_available=false; else exit "${status}"; fi
fi

"${ssh_bin}" "${source_target}" bash -s -- "${source_root}" "${profile_run_id}" <<'REMOTE_PARAVIEW' | tar -xf - -C "${staging}"
set -euo pipefail
root=$(realpath -e -- "$1")
profile_run_id=$2
candidate=$(realpath -e -- "${root}/${profile_run_id}")
[[ "$(dirname -- "${candidate}")" == "${root}" && "$(basename -- "${candidate}")" == "${profile_run_id}" ]]
paraview="${candidate}/paraview"
[[ -f "${paraview}/paraview-case.tar.zst" && -f "${paraview}/manifest.json" ]]
expected_size=$(jq -er '.archive.size_bytes' "${paraview}/manifest.json")
expected_sha=$(jq -er '.archive.sha256' "${paraview}/manifest.json")
[[ "$(stat -c '%s' "${paraview}/paraview-case.tar.zst")" == "${expected_size}" ]]
[[ "$(sha256sum "${paraview}/paraview-case.tar.zst" | awk '{print $1}')" == "${expected_sha}" ]]
tar -cf - -C "${candidate}" paraview
REMOTE_PARAVIEW

if [[ "${vtune_result_available}" == true ]]; then tar -I zstd -tf "${staging}/vtune/vtune-result.tar.zst" | awk 'NF { found = 1 } END { exit(!found) }'; fi
tar -I zstd -tf "${staging}/paraview/paraview-case.tar.zst" | awk '$0 == "occDrivAerStaticMesh.foam" { found = 1 } END { exit(!found) }'
created_utc=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
files=()
if [[ "${vtune_result_available}" == true ]]; then files+=("$(jq -n -c --arg path vtune/vtune-result.tar.zst --argjson size_bytes "$(stat -c '%s' "${staging}/vtune/vtune-result.tar.zst")" --arg sha256 "$(sha256sum "${staging}/vtune/vtune-result.tar.zst" | awk '{print $1}')" '{path:$path,size_bytes:$size_bytes,sha256:$sha256}')"); fi
for relative in paraview/paraview-case.tar.zst paraview/manifest.json; do files+=("$(jq -n -c --arg path "${relative}" --argjson size_bytes "$(stat -c '%s' "${staging}/${relative}")" --arg sha256 "$(sha256sum "${staging}/${relative}" | awk '{print $1}')" '{path:$path,size_bytes:$size_bytes,sha256:$sha256}')"); done
printf '%s\n' "${files[@]}" | jq -s -c --arg cluster "${cluster}" --arg github_run_id "${github_run_id}" --arg profile_run_id "${profile_run_id}" --arg run_id "${run_id}" --arg scheduler_job_id "${scheduler_job_id}" --arg source_target "${source_target}" --arg source_path "${source_root}/${profile_run_id}" --arg created_utc "${created_utc}" --argjson vtune_result_available "${vtune_result_available}" '{schema_version:"openfoam-large-output-archive/v1",cluster:$cluster,github_run_id:$github_run_id,profile_run_id:$profile_run_id,run_id:$run_id,scheduler_job_id:$scheduler_job_id,source_target:$source_target,source_path:$source_path,created_utc:$created_utc,vtune_result_available:$vtune_result_available,files:.}' > "${staging}/manifest.json"
mv -T -- "${staging}" "${destination}"
trap - EXIT
validate_destination
remove_source
printf 'home_large_output=%s\nvtune_result_available=%s\nsource_removed=%s\n' "${destination}" "${vtune_result_available}" "${source_root}/${profile_run_id}"
