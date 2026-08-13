#!/usr/bin/env bash

# Build only the OpenFOAM components used by the selected cavity3D pipeline:
# blockMesh, decomposePar with Scotch, checkMesh, and icoFoam.
set -euo pipefail

: "${OPENFOAM_BUILD_PARALLELISM:?}"
: "${WM_PROJECT_DIR:?}"
: "${WM_THIRD_PARTY_DIR:?}"
: "${EXPERIMENT_METRICS_NATIVE_ROOT:?}"

export WM_NCOMPPROCS="${OPENFOAM_BUILD_PARALLELISM}"
cd "${WM_PROJECT_DIR}"

# Bootstrap wmake and the sole external library used by this task.
"${WM_DIR}/src/Allmake"
"${WM_THIRD_PARTY_DIR}/makeSCOTCH" -no-mpi

# OpenFOAM and Pstream form the base of every parallel executable.
wmakeLnInclude -u src/OpenFOAM
wmakeLnInclude -u "src/OSspecific/${WM_OSTYPE:-POSIX}"
src/OpenFOAM/Alltouch -check 2>/dev/null || true
src/OSspecific/"${WM_OSTYPE:-POSIX}"/Allwmake
src/Pstream/Allwmake
wmake -j "${OPENFOAM_BUILD_PARALLELISM}" src/OpenFOAM

# Shared mesh and finite-volume libraries required by the task commands.
for library in \
  src/fileFormats \
  src/surfMesh \
  src/meshTools \
  src/finiteArea \
  src/finiteVolume \
  src/mesh/blockMesh \
  src/mesh/extrudeModel \
  src/dynamicMesh \
  src/genericPatchFields \
  src/parallel/decompose/decompositionMethods \
  src/lagrangian/basic
do
  wmake -j "${OPENFOAM_BUILD_PARALLELISM}" "${library}"
done

# decomposePar links generic placeholders and loads the available backend at
# runtime. Its upstream Allwmake performs the required backend discovery and
# exports the detected Scotch include and library paths to wmake. Since only
# serial Scotch was installed above, the other real backends remain skipped.
src/parallel/decompose/AllwmakeLnInclude
for backend in kahipDecomp metisDecomp scotchDecomp
do
  wmake -j "${OPENFOAM_BUILD_PARALLELISM}" "src/dummyThirdParty/${backend}"
done
src/parallel/decompose/Allwmake

for application in \
  applications/utilities/mesh/generation/blockMesh \
  applications/utilities/parallelProcessing/decomposePar \
  applications/utilities/mesh/manipulation/checkMesh \
  applications/solvers/incompressible/icoFoam
do
  wmake -j "${OPENFOAM_BUILD_PARALLELISM}" "${application}"
done

# These v2 probes are compiled against this exact OpenFOAM tree and placed in
# FOAM_APPBIN so the published build archive, not the runner workspace, owns
# the runtime executable bytes.
native_tree="${WM_PROJECT_DIR}/applications/utilities/experimentMetricsV2"
install -d "${native_tree}"
for utility in mesh-facts partition-audit
do
  cp -a "${EXPERIMENT_METRICS_NATIVE_ROOT}/${utility}" "${native_tree}/${utility}"
  wmake -j "${OPENFOAM_BUILD_PARALLELISM}" "${native_tree}/${utility}"
done

# Fail the build here instead of discovering a missing binary during runtime
# provisioning. Also ensure all shared-library dependencies resolve.
for application in blockMesh decomposePar icoFoam checkMesh mesh-facts partition-audit
do
  executable="${FOAM_APPBIN}/${application}"
  test -x "${executable}"
  if ldd "${executable}" | grep -q 'not found'; then
    ldd "${executable}" >&2
    exit 1
  fi
done
