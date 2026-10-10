#!/usr/bin/env bash
# 計算ノードでは、PALSの--cpu-bindによるCPU固定がMPI_Init中にプロセスの外から全CPUへ戻される（Issue #36 A3）。
# このnode上の各simpleFoamのmain threadを、rank-cpus.txtのPMI_LOCAL_RANK番目のCPU（Issue #61）へtasksetで固定し直す。simpleFoamが
# 起動するたびに（profileのwarmupと本計算を含む）同じ処理を行い、終了ごとに固定し直した回数をpbs.logへ出力する。
# 呼び出し側がSIGTERMで止める。
set -uo pipefail

# 自身は計算に使わない最後のSMT siblingに置く。
taskset -pc 255 $$ > /dev/null
read -r -a rank_cpus < "${BASH_SOURCE[0]%/*}/rank-cpus.txt"
user=$(id -un)
host=$(hostname)
declare -A cpu_of
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
      cpu_of=()
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
    if [[ -z "${cpu_of[${pid}]:-}" ]]; then
      local_rank=
      while IFS= read -r -d '' entry; do [[ "${entry}" == PMI_LOCAL_RANK=* ]] && local_rank=${entry#PMI_LOCAL_RANK=}; done 2>/dev/null < "/proc/${pid}/environ"
      [[ "${local_rank}" =~ ^[0-9]+$ ]] || continue
      cpu_of[${pid}]=${rank_cpus[local_rank]}
    fi
    allowed=
    while IFS=$':\t ' read -r key value; do if [[ "${key}" == Cpus_allowed_list ]]; then allowed=${value}; break; fi; done 2>/dev/null < "/proc/${pid}/status"
    if [[ "${allowed}" == "${cpu_of[${pid}]}" ]]; then
      bound=$(( bound + 1 ))
    elif [[ -n "${allowed}" ]] && taskset -pc "${cpu_of[${pid}]}" "${pid}" > /dev/null 2>&1; then
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
