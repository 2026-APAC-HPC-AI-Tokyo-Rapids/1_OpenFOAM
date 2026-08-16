#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "usage: $0 work-root publish-root results-root build-command [argument ...]" >&2
  exit 64
fi

work_root=$1
publish_root=$2
results_root=$3
shift 3
modes=(false false true true false false true)

rm -rf -- "${work_root:?}" "${publish_root:?}" "${results_root:?}"
install -d "${work_root}" "${publish_root}" "${results_root}"

cleanup() {
  status=$?
  trap - EXIT INT TERM
  rm -rf -- "${work_root:?}" "${publish_root:?}"
  exit "${status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'trial\tmode\trole\tbuild_elapsed_ns\tcommand_elapsed_ns\n' > "${results_root}/timings.tsv"

for index in "${!modes[@]}"
do
  trial=$((index + 1))
  mode=${modes[$index]}
  role=measured
  if [[ ${trial} -eq 1 ]]; then
    role=warmup
  fi
  label=$(printf '%02d-%s-%s' "${trial}" "${role}" "${mode}")
  export BUILD_DIR="${work_root}/${label}"
  export BUILD_ARCHIVE_DIR="${publish_root}"
  export BUILD_PROFILER_TIMING_FILE="${BUILD_DIR}/build-elapsed-ns.txt"
  if [[ "${mode}" == true ]]; then
    export CCACHE_RESHARE=true
  else
    unset CCACHE_RESHARE || true
  fi

  command_start_ns=$(date +%s%N)
  "$@" > "${results_root}/${label}.console.log" 2>&1
  command_end_ns=$(date +%s%N)
  build_elapsed_ns=$(< "${BUILD_PROFILER_TIMING_FILE}")
  command_elapsed_ns=$((command_end_ns - command_start_ns))
  cp -a "${BUILD_DIR}/logs" "${results_root}/${label}-logs"
  ccache --print-stats > "${results_root}/${label}.ccache-stats"
  printf '%s\t%s\t%s\t%s\t%s\n' "${trial}" "${mode}" "${role}" "${build_elapsed_ns}" "${command_elapsed_ns}" >> "${results_root}/timings.tsv"
  printf 'trial=%s mode=%s role=%s build_seconds=%d command_seconds=%d\n' "${trial}" "${mode}" "${role}" "$((build_elapsed_ns / 1000000000))" "$((command_elapsed_ns / 1000000000))"
  rm -rf -- "${BUILD_DIR:?}"
done

trap - EXIT
rm -rf -- "${work_root:?}" "${publish_root:?}"
