#!/usr/bin/env bash

# Build only the OpenFOAM components used by occDrivAerStaticMesh:
# decomposition, official preprocessing, validation, and simpleFoam.
set -euo pipefail

: "${WM_PROJECT_DIR:?}"
: "${WM_THIRD_PARTY_DIR:?}"

if [[ $# -ne 2 || ! $1 =~ ^[1-9][0-9]*$ ]]; then
  echo "usage: $0 build-parallelism experiment-metrics-native-root" >&2
  exit 64
fi
build_parallelism=$1
experiment_metrics_native_root=$2

export WM_NCOMPPROCS="${build_parallelism}"
cd "${WM_PROJECT_DIR}"

# Bootstrap wmake and the sole required external library.
"${WM_DIR}/src/Allmake"
"${WM_THIRD_PARTY_DIR}/makeSCOTCH" -no-mpi

# applyBoundaryLayer links both incompressible and thermophysical libraries.
# Build the complete upstream v2512 library layer so this official utility and
# simpleFoam use a consistent ABI; applications remain limited to the task.
src/Allwmake

for application in applications/utilities/parallelProcessing/decomposePar applications/utilities/mesh/manipulation/checkMesh applications/utilities/mesh/manipulation/renumberMesh applications/solvers/basic/potentialFoam applications/utilities/preProcessing/applyBoundaryLayer applications/solvers/incompressible/simpleFoam
do
  wmake -j "${build_parallelism}" "${application}"
done

# These v2 probes are compiled against this exact OpenFOAM tree and placed in
# FOAM_APPBIN so the published build archive, not the runner workspace, owns
# the runtime executable bytes.
native_tree="${WM_PROJECT_DIR}/applications/utilities/experimentMetricsV2"
install -d "${native_tree}"
for utility in mesh-facts partition-audit
do
  cp -a "${experiment_metrics_native_root}/${utility}" "${native_tree}/${utility}"
  wmake -j "${build_parallelism}" "${native_tree}/${utility}"
done

# Fail the build here instead of discovering a missing binary during runtime
# provisioning. Also ensure all shared-library dependencies resolve.
for application in simpleFoam decomposePar checkMesh renumberMesh potentialFoam applyBoundaryLayer mesh-facts partition-audit
do
  executable="${FOAM_APPBIN}/${application}"
  if ldd "${executable}" | grep -q 'not found'; then
    ldd "${executable}" >&2
    exit 1
  fi
done
