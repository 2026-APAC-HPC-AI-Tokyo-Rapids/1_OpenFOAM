# shellcheck shell=bash
# Sourced by prepare.pbs and solve.pbs: the modules of build/build.pbs and the OpenFOAM tree that it installed.
module purge
module load PrgEnv-gnu/8.3.3 craype-x86-milan aocl/4.0.0-gcc11.2
# Cray MPICH over UCX. With the default OFI transport, a rank dies with SIGBUS in MPI_Finalize on 2 and 4 nodes.
module swap craype-network-ofi craype-network-ucx
module swap cray-mpich cray-mpich-ucx/8.1.15
if [[ "${PROFILE:-}" == craypat ]]; then
  module use /opt/cray/pe/modulefiles
  module load perftools-base/22.04.0 perftools-preload
fi
# OpenFOAM's scripts use unset variables and return non-zero codes while they set up.
set +eu
source "${OPENFOAM_DIR}/OpenFOAM/etc/bashrc" WM_COMPILER=Gcc WM_MPLIB=CRAY-MPICH WM_LABEL_SIZE=32 WM_PRECISION_OPTION=DP WM_COMPILE_OPTION=Opt
source "${WM_PROJECT_DIR}/bin/tools/RunFunctions"
set -eu
