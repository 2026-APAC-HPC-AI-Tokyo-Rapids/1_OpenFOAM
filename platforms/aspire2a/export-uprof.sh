#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "使用方法: $0 AMDUPROF_CLI OUTPUT_ROOT" >&2
  exit 64
fi

uprof_cli=$1
output_root=$2
[[ "${uprof_cli}" == /* && "${output_root}" == /* ]]
test -x "${uprof_cli}"
uprof_bin_dir=$(dirname -- "${uprof_cli}")
export LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
: "${OPENFOAM_NODES:?expected node count is required}"
: "${OPENFOAM_MPI_PROCS:?expected MPI rank count is required}"
[[ "${OPENFOAM_NODES}" =~ ^[0-9]+$ && "${OPENFOAM_MPI_PROCS}" =~ ^[0-9]+$ ]]
mapfile -t host_roots < <(find "${output_root}/sessions" -mindepth 1 -maxdepth 1 -type d -print | LC_ALL=C sort)
[[ "${#host_roots[@]}" -eq "${OPENFOAM_NODES}" ]]
install -d -m 0750 "${output_root}/reports"
: > "${output_root}/session.txt"
rank_count=0
declare -A seen_ranks=()
for host_root in "${host_roots[@]}"
do
  host=$(basename -- "${host_root}")
  [[ "${host}" =~ ^[A-Za-z0-9._-]+$ ]]
  install -d -m 0750 "${output_root}/reports/${host}"
  mapfile -t rank_roots < <(find "${host_root}" -mindepth 1 -maxdepth 1 -type d -name 'rank-*' -print | LC_ALL=C sort)
  [[ "${#rank_roots[@]}" -gt 0 ]]
  for rank_root in "${rank_roots[@]}"
  do
    rank_name=$(basename -- "${rank_root}")
    rank=${rank_name#rank-}
    [[ "${rank}" =~ ^[0-9]+$ && -z "${seen_ranks[${rank}]:-}" ]]
    seen_ranks[${rank}]=1
    ((rank_count += 1))
    mapfile -t sessions < <(find "${rank_root}" -mindepth 1 -maxdepth 1 -type d -name 'AMDuProf-*' -print)
    [[ "${#sessions[@]}" -eq 1 ]]
    session=${sessions[0]}
    "${uprof_cli}" report --input-dir "${session}" --host "${host}" --detail --cutoff 0 > "${output_root}/reports/${host}/${rank_name}.stdout" 2> "${output_root}/reports/${host}/${rank_name}.stderr"
    test -s "${session}/report.csv"
    install -m 0640 "${session}/report.csv" "${output_root}/reports/${host}/${rank_name}.csv"
    printf 'host=%s rank=%s session=%s\n' "${host}" "${rank}" "$(basename -- "${session}")" >> "${output_root}/session.txt"
  done
done
[[ "${rank_count}" -eq "${OPENFOAM_MPI_PROCS}" ]]
for ((rank = 0; rank < OPENFOAM_MPI_PROCS; rank += 1)); do [[ -n "${seen_ranks[${rank}]:-}" ]]; done
