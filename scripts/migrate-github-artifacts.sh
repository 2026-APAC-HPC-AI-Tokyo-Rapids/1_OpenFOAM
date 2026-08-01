#!/usr/bin/env bash

set -euo pipefail

repository="2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM"
remote="tomokazu@tomokazu-ubuntu-server"
remote_root="/hdd_raid/samba/net_share/openfoam-artifacts"
parallelism="${MIGRATION_PARALLELISM:-6}"
download_segments="${MIGRATION_DOWNLOAD_SEGMENTS:-4}"

for command in curl gh ssh scp mktemp unzip xargs
do
  command -v "${command}" >/dev/null || {
    echo "Required command is not available: ${command}" >&2
    exit 1
  }
done

gh auth status >/dev/null
github_token="$(gh auth token)"
ssh "${remote}" "test -d /hdd_raid/samba/net_share && mkdir -p -- ${remote_root}"

mapfile -t artifacts < <(
  gh api --paginate \
    "/repos/${repository}/actions/artifacts?per_page=100" \
    --jq '.artifacts[] | select(.expired == false) | [.workflow_run.id, .id, .name, .size_in_bytes] | @tsv'
)

echo "Migrating ${#artifacts[@]} GitHub Actions artifacts"

migrate_artifact() {
  artifact="$1"
  IFS=$'\t' read -r run_id artifact_id artifact_name artifact_size <<< "${artifact}"
  work_dir="$(mktemp -d)"
  cleanup_worker() {
    mapfile -t running_jobs < <(jobs -pr)
    if (( ${#running_jobs[@]} > 0 )); then
      kill "${running_jobs[@]}" 2>/dev/null || true
    fi
    rm -rf -- "${work_dir:?}"
  }
  trap cleanup_worker EXIT INT TERM
  local_artifact_dir="${work_dir}/${artifact_name}"
  local_zip="${work_dir}/${artifact_name}.zip"
  remote_run_dir="${remote_root}/${run_id}"

  echo "Migrating run ${run_id} artifact ${artifact_name} (${artifact_id})"
  mkdir -p "${local_artifact_dir}"
  signed_url="$(
    curl --silent --show-error --fail \
      --output /dev/null \
      --write-out '%{redirect_url}' \
      --header 'Accept: application/vnd.github+json' \
      --header "Authorization: Bearer ${github_token}" \
      --header 'X-GitHub-Api-Version: 2022-11-28' \
      "https://api.github.com/repos/${repository}/actions/artifacts/${artifact_id}/zip"
  )" || return 255
  [[ -n "${signed_url}" ]] || return 255

  segment_count="${download_segments}"
  if (( artifact_size < segment_count )); then
    segment_count="${artifact_size}"
  fi
  segment_size=$(( (artifact_size + segment_count - 1) / segment_count ))
  download_failed=0
  download_pids=()
  for ((segment = 0; segment < segment_count; segment += 1))
  do
    start=$((segment * segment_size))
    end=$((start + segment_size - 1))
    if (( end >= artifact_size )); then
      end=$((artifact_size - 1))
    fi
    curl --silent --show-error --fail \
      --retry 5 \
      --retry-all-errors \
      --connect-timeout 30 \
      --range "${start}-${end}" \
      --output "${local_zip}.part-${segment}" \
      "${signed_url}" &
    download_pids+=("$!")
  done
  for download_pid in "${download_pids[@]}"
  do
    wait "${download_pid}" || download_failed=1
  done
  [[ "${download_failed}" -eq 0 ]] || return 255

  : > "${local_zip}"
  for ((segment = 0; segment < segment_count; segment += 1))
  do
    cat "${local_zip}.part-${segment}" >> "${local_zip}" || return 255
  done
  [[ "$(stat -c %s "${local_zip}")" -eq "${artifact_size}" ]] || return 255
  unzip -tq "${local_zip}" >/dev/null || return 255
  unzip -q "${local_zip}" -d "${local_artifact_dir}" || return 255
  find "${local_artifact_dir}" -mindepth 1 -print -quit | grep -q . || return 255

  ssh "${remote}" "mkdir -p -- ${remote_run_dir}" || return 255
  scp -r "${local_artifact_dir}" "${remote}:${remote_run_dir}/" || return 255
  gh api --method DELETE "/repos/${repository}/actions/artifacts/${artifact_id}" || return 255
  rm -rf -- "${work_dir:?}"
  trap - EXIT
}
export -f migrate_artifact
export repository remote remote_root download_segments github_token

if (( ${#artifacts[@]} > 0 )); then
  printf '%s\0' "${artifacts[@]}" |
    xargs --null --max-args=1 --max-procs="${parallelism}" \
      bash -c 'migrate_artifact "$1"' _
fi

remaining="$({
  gh api --paginate \
    "/repos/${repository}/actions/artifacts?per_page=100" \
    --jq '.artifacts[] | select(.expired == false) | .id'
} | wc -l)"
test "${remaining}" -eq 0
echo "Migration complete; no unexpired GitHub Actions artifacts remain"

gh api --paginate \
  "/repos/${repository}/actions/runs?per_page=100" \
  --jq '.workflow_runs[] | [.id, .updated_at] | @tsv' |
  ssh "${remote}" '
    updated_count=0
    while read -r run_id updated_at
    do
      case "${run_id}" in
        ""|*[!0-9]*)
          echo "Invalid workflow run ID: ${run_id}" >&2
          exit 1
          ;;
      esac
      run_dir="/hdd_raid/samba/net_share/openfoam-artifacts/${run_id}"
      if test -d "${run_dir}"; then
        touch --date="${updated_at}" -- "${run_dir}"
        updated_count=$((updated_count + 1))
      fi
    done
    echo "Synchronized ${updated_count} run directory mtimes"
  '
