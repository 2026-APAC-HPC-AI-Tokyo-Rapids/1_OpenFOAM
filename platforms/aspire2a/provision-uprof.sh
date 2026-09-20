#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "使用方法: $0 AMDUPROF_ARCHIVE AMDUPROF_ROOT" >&2
  exit 64
fi

archive=$1
target=$2
[[ "${archive}" == /* && "${target}" == /* ]]
if [[ -x "${target}/bin/AMDuProfCLI" ]]; then
  exit 0
fi
if [[ ! -f "${archive}" ]]; then
  printf 'AMDのEULAへ同意してAMDuProf_Linux_x64_5.3.521.tar.bz2を次へ配置してください: %s\n' "${archive}" >&2
  exit 66
fi
test "$(md5sum "${archive}" | awk '{print $1}')" = 45437d8bc0b4276a0b78e28d21de23cb
test ! -e "${target}"
install -d -m 0750 "$(dirname -- "${target}")"
temporary=$(mktemp -d "$(dirname -- "${target}")/.amduprof-5.3.521.XXXXXXXX")
cleanup() {
  rm -rf -- "${temporary}"
}
trap cleanup EXIT
tar -xjf "${archive}" -C "${temporary}"
mapfile -t candidates < <(find "${temporary}" -type f -path '*/bin/AMDuProfCLI' -print)
[[ "${#candidates[@]}" -eq 1 ]]
extracted_root=$(dirname -- "$(dirname -- "${candidates[0]}")")
test -x "${extracted_root}/bin/AMDuProfCLI"
mv -- "${extracted_root}" "${target}"
test -x "${target}/bin/AMDuProfCLI"
