#!/bin/bash
# Submits one full run of the case: prepare.pbs (setup, decomposePar, restore0Dir on 4 cores), then solve.pbs (the parallel
# steps on full nodes) once prepare.pbs has succeeded.
#
#   ./submit.sh NODES [basic|bonus] [craypat]
#
# NODES is 1, 2 or 4. "bonus" runs the Bonus decomposition on the Bonus build. "craypat" makes a 40-step CrayPAT profile.
set -euo pipefail
nodes=${1:?usage: submit.sh NODES [basic|bonus] [craypat]}
configuration=${2:-basic}
profile=${3:-}
case "${nodes}" in 1|2|4) ;; *) echo "NODES must be 1, 2 or 4" >&2; exit 64 ;; esac
case "${configuration}" in basic|bonus) ;; *) echo "the configuration must be basic or bonus" >&2; exit 64 ;; esac
case "${profile}" in ""|craypat) ;; *) echo "the third argument can only be craypat" >&2; exit 64 ;; esac

# Settings. Edit them here or set them in the environment.
PROJECT=${PROJECT:-59000014}
# The tree that build/build.pbs installed: for "bonus", the build with PATCH_DIR=../bonus/patches.
OPENFOAM_DIR=${OPENFOAM_DIR:-/scratch/users/industry/ai-hpc/apacsc14/openfoam/submission/build-${configuration}}
# The official case, incompressible/simpleFoam/occDrivAerStaticMesh of https://develop.openfoam.com/committees/hpc (84c26243).
CASE_SOURCE=${CASE_SOURCE:-/scratch/users/industry/ai-hpc/apacsc14/openfoam/submission/occDrivAerStaticMesh}
# The 65M mesh, polyMesh_65M.tar.gz from https://zenodo.org/records/15012221.
MESH_ARCHIVE=${MESH_ARCHIVE:-/scratch/users/industry/ai-hpc/apacsc14/openfoam/aspire2a/workload/polyMesh_65M.tar.gz}
# Every run gets a new case directory here, and the two PBS outputs next to it.
WORK_ROOT=${WORK_ROOT:-/scratch/users/industry/ai-hpc/apacsc14/openfoam/submission/runs}

script_dir=$(cd "$(dirname "$0")" && pwd)
name="${configuration}-${nodes}node${profile:+-${profile}}"
case_dir="${WORK_ROOT}/$(date +%Y%m%d-%H%M%S)-${name}"
mkdir -p "${WORK_ROOT}"
variables="SCRIPT_DIR=${script_dir},OPENFOAM_DIR=${OPENFOAM_DIR},CASE_SOURCE=${CASE_SOURCE},MESH_ARCHIVE=${MESH_ARCHIVE},CASE_DIR=${case_dir},NODES=${nodes},CONFIGURATION=${configuration},PROFILE=${profile}"
prepare=$(qsub -P "${PROJECT}" -N "prep-${name}" -o "${case_dir}.prepare.log" -v "${variables}" "${script_dir}/prepare.pbs")
solve=$(qsub -P "${PROJECT}" -N "solve-${name}" -o "${case_dir}.solve.log" -W depend=afterok:"${prepare}" -l select="${nodes}":ncpus=128:mpiprocs=128:ompthreads=1:mem=400gb -v "${variables}" "${script_dir}/solve.pbs")
printf 'case=%s\nprepare=%s\nsolve=%s\n' "${case_dir}" "${prepare}" "${solve}"
