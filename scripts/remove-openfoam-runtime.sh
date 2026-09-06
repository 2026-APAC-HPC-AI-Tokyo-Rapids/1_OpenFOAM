#!/usr/bin/env bash

set -euo pipefail

cluster=
run_dir=
connection=

while [[ $# -gt 0 ]]
do
  case "$1" in
    --cluster) [[ $# -ge 2 ]]; cluster=$2; shift 2 ;;
    --run-dir) [[ $# -ge 2 ]]; run_dir=$2; shift 2 ;;
    --connection) [[ $# -ge 2 ]]; connection=$2; shift 2 ;;
    *) printf '未知のruntime削除引数です: %s\n' "$1" >&2; exit 64 ;;
  esac
done

[[ "${run_dir}" == /* && "${run_dir}" != / ]]
run_id=$(basename -- "${run_dir}")
[[ "${run_id}" =~ ^r-[0-9a-f]{32}$ ]]

case "${cluster}" in
  genkai) expected_connection=genkai-shell ;;
  gadi) expected_connection=gadi-shell ;;
  *) printf '未対応のruntime削除クラスタです: %s\n' "${cluster}" >&2; exit 64 ;;
esac

[[ -n "${connection}" ]] || { printf '%s\n' 'runtime削除には--connectionが必要です' >&2; exit 64; }
[[ "${connection}" == "${expected_connection}" ]] || { printf 'クラスタ%sの接続は%sを指定してください: %s\n' "${cluster}" "${expected_connection}" "${connection}" >&2; exit 64; }
command -v "${connection}" >/dev/null || { printf '接続コマンドが見つかりません: %s\n' "${connection}" >&2; exit 69; }

"${connection}" bash -s -- "${run_dir}" "${run_id}" <<'REMOTE_DELETE'
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
