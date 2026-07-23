#!/usr/bin/env bash

set -euo pipefail

: "${OPENFOAM_MPI_PROCS:?}"
: "${OPENFOAM_PROFILE_ANALYSIS:?}"
: "${OPENFOAM_PROFILE_DIR:?}"
: "${OPENFOAM_PROFILE_LABEL:?}"
: "${OPENFOAM_PROFILE_RANK:=0}"
: "${PROVISION_DIR:?}"

analysis="${OPENFOAM_PROFILE_ANALYSIS}"
result_dir="${OPENFOAM_PROFILE_DIR}/${analysis}"
log_dir="${PROVISION_DIR}/logs"
timing_log="${log_dir}/time-${OPENFOAM_PROFILE_LABEL}.txt"
mkdir -p "${result_dir}" "${log_dir}"

case "${analysis}" in
  aps)
    /usr/bin/time -v -o "${timing_log}" \
      mpirun -np "${OPENFOAM_MPI_PROCS}" \
        aps \
        --result-dir="${result_dir}" \
        --collection-mode=all \
        --stat-level=5 \
        --mpi-imbalance=2 \
        --storage-format=compact \
        "$@"
    aps-report "${result_dir}" > "${OPENFOAM_PROFILE_DIR}/aps-report.txt"
    cp "${OPENFOAM_PROFILE_DIR}/aps-report.txt" \
      "${log_dir}/aps-report.txt"
    ;;
  hotspots|hpc-performance)
    collect_args=(
      -collect "${analysis}"
      -knob enable-stack-collection=true
    )
    if [[ "${analysis}" == hpc-performance ]]; then
      collect_args+=(
        -knob collect-memory-bandwidth=true
        -knob collect-affinity=true
      )
    fi

    /usr/bin/time -v -o "${timing_log}" \
      mpirun -np "${OPENFOAM_MPI_PROCS}" \
        -gtool "vtune ${collect_args[*]} -result-dir ${result_dir}:${OPENFOAM_PROFILE_RANK}" \
        "$@"

    vtune_result_dirs=()
    for candidate in "${result_dir}".*
    do
      [[ -d "${candidate}" ]] && vtune_result_dirs+=("${candidate}")
    done
    if [[ "${#vtune_result_dirs[@]}" -ne 1 ]]; then
      echo "Expected one host-qualified VTune result for ${result_dir}, found ${#vtune_result_dirs[@]}" >&2
      exit 1
    fi
    vtune_result_dir="${vtune_result_dirs[0]}"

    vtune -report summary \
      -result-dir "${vtune_result_dir}" \
      -report-output "${vtune_result_dir}/summary.txt"
    cp "${vtune_result_dir}/summary.txt" \
      "${log_dir}/vtune-${OPENFOAM_PROFILE_LABEL}-${analysis}-summary.txt"

    if [[ "${analysis}" == hotspots ]]; then
      vtune -report hotspots \
        -result-dir "${vtune_result_dir}" \
        -group-by function \
        -format csv \
        -report-output "${vtune_result_dir}/hotspots.csv"
      cp "${vtune_result_dir}/hotspots.csv" \
        "${log_dir}/vtune-${OPENFOAM_PROFILE_LABEL}-hotspots.csv"
    fi
    ;;
  none)
    /usr/bin/time -v -o "${timing_log}" \
      mpirun -np "${OPENFOAM_MPI_PROCS}" "$@"
    ;;
  *)
    echo "Unsupported profiler analysis: ${analysis}" >&2
    exit 2
    ;;
esac

cp "${timing_log}" "${OPENFOAM_PROFILE_DIR}/"
