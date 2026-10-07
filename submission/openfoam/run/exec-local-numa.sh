#!/bin/bash
# Starts one MPI rank with its memory bound to the NUMA domain of its core: local rank r runs on core r, and a node has
# 16 cores per NUMA domain. On ASPIRE-2A the launcher's CPU and memory binding is removed during MPI_Init; a memory policy
# set before exec belongs to the process and stays.
set -euo pipefail

exec numactl --membind="$(( PMI_LOCAL_RANK / 16 ))" "$@"
