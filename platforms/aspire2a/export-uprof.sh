#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "使用方法: $0 AMDUPROF_CLI OUTPUT_ROOT ANALYSIS" >&2
  exit 64
fi

uprof_cli=$1
output_root=$2
analysis=$3
[[ "${uprof_cli}" == /* && "${output_root}" == /* ]]
case "${analysis}" in assess|data_access|hotspots) ;; *) printf '未対応のAMD uProf解析です: %s\n' "${analysis}" >&2; exit 2 ;; esac
test -x "${uprof_cli}"
uprof_bin_dir=$(dirname -- "${uprof_cli}")
export LD_LIBRARY_PATH="${uprof_bin_dir}${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
: "${OPENFOAM_NODES:?expected node count is required}"
: "${OPENFOAM_MPI_PROCS:?expected MPI rank count is required}"
[[ "${OPENFOAM_NODES}" =~ ^[0-9]+$ && "${OPENFOAM_MPI_PROCS}" =~ ^[0-9]+$ ]]
# Keep this platform invariant aligned with exec-uprof.sh and the parser invocation.
profile_rank_stride=16
(( OPENFOAM_MPI_PROCS % OPENFOAM_NODES == 0 ))
ranks_per_host=$((OPENFOAM_MPI_PROCS / OPENFOAM_NODES))
(( ranks_per_host % profile_rank_stride == 0 ))
profile_ranks_per_host=$((ranks_per_host / profile_rank_stride))
expected_profile_ranks=$((OPENFOAM_NODES * profile_ranks_per_host))
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
  [[ "${#rank_roots[@]}" -eq "${profile_ranks_per_host}" ]]
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
[[ "${rank_count}" -eq "${expected_profile_ranks}" ]]
for ((host_rank = 0; host_rank < OPENFOAM_MPI_PROCS; host_rank += ranks_per_host)); do for ((local_rank = 0; local_rank < ranks_per_host; local_rank += profile_rank_stride)); do rank=$((host_rank + local_rank)); [[ -n "${seen_ranks[${rank}]:-}" ]]; done; done

wait_batch() {
  local status=0
  local pid
  for pid in "$@"; do wait "${pid}" || status=$?; done
  return "${status}"
}

report_parallelism=4
report_pids=()
for index in "${!report_sessions[@]}"
do
  host=${report_hosts[${index}]}
  rank=${report_ranks[${index}]}
  session=${report_sessions[${index}]}
  (
    report_args=(report --input-dir "${session}" --host "${host}" --detail --cutoff 30)
    if [[ "${analysis}" != hotspots ]]; then report_args+=(--show-event-count); fi
    "${uprof_cli}" "${report_args[@]}" > "${output_root}/reports/${host}/rank-${rank}.stdout" 2> "${output_root}/reports/${host}/rank-${rank}.stderr"
    test -s "${session}/report.csv"
    install -m 0640 "${session}/report.csv" "${output_root}/reports/${host}/rank-${rank}.csv"
  ) &
  report_pids+=("$!")
  if [[ "${#report_pids[@]}" -eq "${report_parallelism}" ]]; then wait_batch "${report_pids[@]}"; report_pids=(); fi
done
if [[ "${#report_pids[@]}" -gt 0 ]]; then wait_batch "${report_pids[@]}"; fi

for index in "${!report_sessions[@]}"; do printf 'host=%s rank=%s session=%s\n' "${report_hosts[${index}]}" "${report_ranks[${index}]}" "$(basename -- "${report_sessions[${index}]}")" >> "${output_root}/session.txt"; done
