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
report_hosts=()
report_ranks=()
report_sessions=()
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
    report_hosts+=("${host}")
    report_ranks+=("${rank}")
    report_sessions+=("${sessions[0]}")
  done
done
[[ "${rank_count}" -eq "${OPENFOAM_MPI_PROCS}" ]]
for ((rank = 0; rank < OPENFOAM_MPI_PROCS; rank += 1)); do [[ -n "${seen_ranks[${rank}]:-}" ]]; done

wait_batch() {
  local status=0
  local pid
  for pid in "$@"; do wait "${pid}" || status=$?; done
  return "${status}"
}

report_parallelism=16
report_pids=()
for index in "${!report_sessions[@]}"
do
  host=${report_hosts[${index}]}
  rank=${report_ranks[${index}]}
  session=${report_sessions[${index}]}
  (
    "${uprof_cli}" report --input-dir "${session}" --host "${host}" --detail --cutoff 0 > "${output_root}/reports/${host}/rank-${rank}.stdout" 2> "${output_root}/reports/${host}/rank-${rank}.stderr"
    test -s "${session}/report.csv"
    install -m 0640 "${session}/report.csv" "${output_root}/reports/${host}/rank-${rank}.csv"
  ) &
  report_pids+=("$!")
  if [[ "${#report_pids[@]}" -eq "${report_parallelism}" ]]; then wait_batch "${report_pids[@]}"; report_pids=(); fi
done
if [[ "${#report_pids[@]}" -gt 0 ]]; then wait_batch "${report_pids[@]}"; fi

for index in "${!report_sessions[@]}"; do printf 'host=%s rank=%s session=%s\n' "${report_hosts[${index}]}" "${report_ranks[${index}]}" "$(basename -- "${report_sessions[${index}]}")" >> "${output_root}/session.txt"; done
