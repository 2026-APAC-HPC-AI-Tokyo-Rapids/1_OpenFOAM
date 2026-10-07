#!/bin/bash
# One per node, for the whole job. On ASPIRE-2A the launcher's CPU binding (--cpu-bind) is reset to all CPUs from outside the
# process during MPI_Init. This watcher pins the main thread of every simpleFoam process on the node back to the core of its
# local rank (PMI_LOCAL_RANK), each time simpleFoam starts. When a simpleFoam run ends it prints how many re-pins it made;
# 60 s after the start it prints how many processes are on their core. solve.pbs stops it with SIGTERM.
set -uo pipefail

# The watcher itself sits on the last SMT sibling, which no rank uses.
taskset -pc 255 $$ > /dev/null
user=$(id -un)
host=$(hostname)
declare -A local_rank_of
rebinds=0
last_rebind=
seen_at=
checked=false
report() {
  printf 'affinity-keeper host=%s done rebinds=%d last_rebind_after_s=%s\n' "${host}" "${rebinds}" "${last_rebind:-none}"
}
trap 'if [[ -n "${seen_at}" ]]; then report; fi; exit 0' TERM INT
while :; do
  mapfile -t pids < <(pgrep -u "${user}" -x simpleFoam)
  if (( ${#pids[@]} == 0 )); then
    if [[ -n "${seen_at}" ]]; then
      report
      local_rank_of=()
      rebinds=0
      last_rebind=
      seen_at=
      checked=false
    fi
    sleep 0.2
    continue
  fi
  [[ -n "${seen_at}" ]] || seen_at=${SECONDS}
  bound=0
  for pid in "${pids[@]}"; do
    if [[ -z "${local_rank_of[${pid}]:-}" ]]; then
      local_rank=
      while IFS= read -r -d '' entry; do [[ "${entry}" == PMI_LOCAL_RANK=* ]] && local_rank=${entry#PMI_LOCAL_RANK=}; done 2>/dev/null < "/proc/${pid}/environ"
      [[ "${local_rank}" =~ ^[0-9]+$ ]] || continue
      local_rank_of[${pid}]=${local_rank}
    fi
    allowed=
    while IFS=$':\t ' read -r key value; do if [[ "${key}" == Cpus_allowed_list ]]; then allowed=${value}; break; fi; done 2>/dev/null < "/proc/${pid}/status"
    if [[ "${allowed}" == "${local_rank_of[${pid}]}" ]]; then
      bound=$(( bound + 1 ))
    elif [[ -n "${allowed}" ]] && taskset -pc "${local_rank_of[${pid}]}" "${pid}" > /dev/null 2>&1; then
      rebinds=$(( rebinds + 1 ))
      last_rebind=$(( SECONDS - seen_at ))
    fi
  done
  if [[ "${checked}" == false ]] && (( SECONDS - seen_at >= 60 )); then
    printf 'affinity-keeper host=%s after_60s bound=%d/%d rebinds=%d\n' "${host}" "${bound}" "${#pids[@]}" "${rebinds}"
    checked=true
  fi
  if (( SECONDS - seen_at < 60 )); then sleep 0.1; else sleep 2; fi
done
