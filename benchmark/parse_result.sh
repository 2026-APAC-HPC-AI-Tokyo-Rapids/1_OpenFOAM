#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 9 ]]; then
  echo "usage: $0 SOLVER_LOG CHECK_MESH_LOG RANKS NODES ITERATIONS EXPECTED_CELLS RELEASE WORKLOAD_ID DISTRIBUTION" >&2
  exit 64
fi
solver_log=$1
check_mesh_log=$2
ranks=$3
nodes=$4
iterations=$5
expected_cells=$6
release=$7
workload_id=$8
distribution=$9
[[ "${ranks}" =~ ^[1-9][0-9]*$ && "${nodes}" =~ ^[124]$ && "${iterations}" =~ ^[1-9][0-9]*$ && "${expected_cells}" =~ ^[1-9][0-9]*$ ]]
(( ranks % nodes == 0 ))
case "${nodes}" in
  1) expected_iterations=40 ;;
  2) expected_iterations=80 ;;
  4) expected_iterations=150 ;;
esac
[[ "${iterations}" == "${expected_iterations}" && "${release}" == v2512 && "${workload_id}" == occDrivAerStaticMesh-65M && "${distribution}" == OpenFOAM.com ]]

grep -Eq '^Exec[[:space:]]*:[[:space:]].*simpleFoam([[:space:]]|$)' "${solver_log}"
grep -Eq "(OPENFOAM=|OpenFOAM-)[v]?${release#v}([^0-9]|$)" "${solver_log}"
grep -Eq "^nProcs[[:space:]]*:[[:space:]]*${ranks}$" "${solver_log}"
test "$(grep -Ec '^Time = [0-9]+$' "${solver_log}")" = "${iterations}"
grep -qx "Time = ${iterations}" "${solver_log}"
test "$(grep -cx End "${solver_log}")" = 1
if grep -Eqi 'FOAM FATAL|floating point exception|segmentation fault|(^|[^[:alpha:]])nan([^[:alpha:]]|$)|(^|[^[:alpha:]])inf(inity)?([^[:alpha:]]|$)' "${solver_log}"; then
  echo "solver log contains a fatal or non-finite result" >&2
  exit 1
fi

cells=$(sed -n -E 's/^[[:space:]]*cells:[[:space:]]*([0-9]+).*$/\1/p' "${check_mesh_log}" | sort -u)
test "${cells}" = "${expected_cells}"
grep -Eq '^[[:space:]]*Mesh OK\.[[:space:]]*$' "${check_mesh_log}"

measured=$(sed -n -E 's/^[[:space:]]*Number of measured time steps = ([0-9]+).*$/\1/p' "${solver_log}" | tail -n 1)
average=$(sed -n -E 's/^[[:space:]]*Average wall-clock time per time step = ([0-9.eE+-]+).*$/\1/p' "${solver_log}" | tail -n 1)
stddev=$(sed -n -E 's/^[[:space:]]*Standard deviation of wall-clock time per time step = ([0-9.eE+-]+).*$/\1/p' "${solver_log}" | tail -n 1)
[[ "${measured}" =~ ^[0-9]+$ && -n "${average}" && -n "${stddev}" ]]
test "${measured}" = "$((iterations - 1))"

printf 'STATUS: VALID\n'
printf 'RESULT: average_wall_clock_seconds_per_iteration=%s standard_deviation=%s measured_iterations=%s configured_iterations=%s cells=%s ranks=%s nodes=%s workload_id=%s distribution=%s release=%s solver=simpleFoam\n' "${average}" "${stddev}" "${measured}" "${iterations}" "${cells}" "${ranks}" "${nodes}" "${workload_id}" "${distribution}" "${release}"
