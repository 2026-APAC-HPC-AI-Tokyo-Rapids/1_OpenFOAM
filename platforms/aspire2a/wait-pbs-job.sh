#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^[0-9]+([.][A-Za-z0-9.-]+)?$ ]]; then
  echo "使用方法: $0 PBS_JOB_ID" >&2
  exit 64
fi

job_id=$1
while true
do
  accounting=$(qstat -fx "${job_id}")
  state=$(sed -n 's/^[[:space:]]*job_state = //p' <<< "${accounting}")
  [[ "${state}" =~ ^[A-Z]$ ]]
  if [[ "${state}" == F ]]; then
    exit_status=$(sed -n 's/^[[:space:]]*Exit_status = //p' <<< "${accounting}")
    [[ "${exit_status}" =~ ^-?[0-9]+$ ]]
    printf 'job_id=%s\nstate=%s\nexit_status=%s\n' "${job_id}" "${state}" "${exit_status}"
    [[ "${exit_status}" -eq 0 ]]
    exit
  fi
  case "${state}" in Q|H|R|B|E) ;; *) echo "未対応のPBSジョブ状態です: ${state}" >&2; exit 65 ;; esac
  sleep 5
done
