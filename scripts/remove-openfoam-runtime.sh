#!/usr/bin/env bash

set -euo pipefail

cluster=
run_dir=
config_path=${OPENFOAM_VTUNE_TRANSFER_CONFIG:-${HOME}/.config/openfoam-vtune-transfer/env}
ssh_bin=${OPENFOAM_VTUNE_SSH_BIN:-ssh}

while [[ $# -gt 0 ]]
do
  case "$1" in
    --cluster) [[ $# -ge 2 ]]; cluster=$2; shift 2 ;;
    --run-dir) [[ $# -ge 2 ]]; run_dir=$2; shift 2 ;;
    --config) [[ $# -ge 2 ]]; config_path=$2; shift 2 ;;
    *) printf '未知のruntime削除引数です: %s\n' "$1" >&2; exit 64 ;;
  esac
done

[[ -f "${config_path}" && "${run_dir}" == /* && "${run_dir}" != / ]]
run_id=$(basename -- "${run_dir}")
[[ "${run_id}" =~ ^r-[0-9a-f]{32}$ ]]

# shellcheck source=/dev/null
source "${config_path}"
case "${cluster}" in
  genkai) target=${OPENFOAM_VTUNE_GENKAI_SSH_TARGET:?玄界SSH targetが必要です} ;;
  gadi) target=${OPENFOAM_VTUNE_GADI_SSH_TARGET:?Gadi SSH targetが必要です} ;;
  *) printf '未対応のruntime削除クラスタです: %s\n' "${cluster}" >&2; exit 64 ;;
esac

"${ssh_bin}" "${target}" bash -s -- "${run_dir}" "${run_id}" <<'REMOTE_DELETE'
set -euo pipefail
run_dir=$1
run_id=$2
if [[ ! -e "${run_dir}" ]]; then exit 0; fi
candidate=$(realpath -e -- "${run_dir}")
[[ ! -L "${run_dir}" && -d "${candidate}" && "$(basename -- "${candidate}")" == "${run_id}" && "$(basename -- "$(dirname -- "${candidate}")")" == runs ]]
current_uid=$(id -u)
[[ "$(find "${candidate}" -xdev -type d ! -uid "${current_uid}" -print -quit)" == '' ]]
find "${candidate}" -xdev -type d -uid "${current_uid}" -exec chmod u+rwx -- {} +
rm -rf --one-file-system -- "${candidate:?}"
REMOTE_DELETE

printf 'runtime_removed=%s\n' "${run_dir}"
