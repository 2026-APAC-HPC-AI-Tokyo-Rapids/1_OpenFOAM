#!/usr/bin/env bash
set -euo pipefail

: "${GIT_MIRROR_DIR:?}"

readonly FETCH_RETRIES="${SOURCE_MIRROR_FETCH_RETRIES:-3}"

update_mirror() {
  local repository_name=$1
  local required_ref=$2
  local mirror_path="${GIT_MIRROR_DIR}/${repository_name}.git"
  local attempt

  if [[ ! -d "${mirror_path}" ]] ||
     [[ "$(git -C "${mirror_path}" rev-parse --is-bare-repository 2>/dev/null)" != true ]]; then
    echo "The source mirror is not initialized: ${mirror_path}" >&2
    echo "Create it once from a Genkai login session before running this workflow." >&2
    return 1
  fi

  for ((attempt = 1; attempt <= FETCH_RETRIES; attempt++))
  do
    if git -C "${mirror_path}" fetch --prune --prune-tags origin; then
      break
    fi

    if ((attempt < FETCH_RETRIES)); then
      echo "Fetch attempt ${attempt}/${FETCH_RETRIES} failed for ${repository_name}; retrying." >&2
      sleep "$((attempt * 2))"
    else
      echo "Could not update ${repository_name}; using the last complete mirror state." >&2
    fi
  done

  if ! git -C "${mirror_path}" show-ref --verify --quiet "${required_ref}"; then
    echo "The required source ref is not available in ${mirror_path}: ${required_ref}" >&2
    return 1
  fi
}

update_mirror 3_OpenFOAM_Src refs/tags/OpenFOAM-v2606
update_mirror 4_OpenFOAM_ThirdParty_Src refs/heads/main
