#!/usr/bin/env bash
# Diagnostic for Issue #62, started once per node by solve.pbs. When the solver log reaches step 5, it reads once, for every
# simpleFoam process on this node, the CPU affinity, the allowed memory nodes and the share of its pages on its home NUMA
# domain (local rank / 16, 16 cores per domain) from /proc, and writes one line per rank. It only reads /proc.
set -uo pipefail

# Itself on the last SMT sibling, which no rank uses.
taskset -pc 255 $$ > /dev/null
solver_log=$1
out_dir=$2
until grep -q '^Time = 5$' "${solver_log}" 2> /dev/null; do sleep 1; done
mkdir -p "${out_dir}"
out="${out_dir}/placement-$(hostname).txt"
printf 'local_rank pid cpus_allowed mems_allowed home_node home_share total_kB\n' > "${out}"
for pid in $(pgrep -u "$(id -un)" -x simpleFoam); do
  local_rank=
  while IFS= read -r -d '' entry; do [[ "${entry}" == PMI_LOCAL_RANK=* ]] && local_rank=${entry#PMI_LOCAL_RANK=}; done 2> /dev/null < "/proc/${pid}/environ"
  [[ "${local_rank}" =~ ^[0-9]+$ ]] || continue
  cpus=$(awk '/^Cpus_allowed_list:/ {print $2}' "/proc/${pid}/status")
  mems=$(awk '/^Mems_allowed_list:/ {print $2}' "/proc/${pid}/status")
  home=$(( local_rank / 16 ))
  # numa_maps counts the pages of each mapping per node (N<node>=<pages>) in units of that mapping's page size.
  share=$(awk -v home="${home}" '{size = 4; for (i = 1; i <= NF; i++) if ($i ~ /^kernelpagesize_kB=/) size = substr($i, 19); for (i = 1; i <= NF; i++) if ($i ~ /^N[0-9]+=/) {split(substr($i, 2), f, "="); kb[f[1]] += f[2] * size; total += f[2] * size}} END {printf "%.4f %d", (total > 0 ? kb[home] / total : 0), total}' "/proc/${pid}/numa_maps")
  printf '%s %s %s %s %s %s\n' "${local_rank}" "${pid}" "${cpus}" "${mems}" "${home}" "${share}" >> "${out}"
done
