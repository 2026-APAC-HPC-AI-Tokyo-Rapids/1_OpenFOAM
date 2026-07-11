#!/usr/bin/env bash
# Execute one OpenFOAM motorBike case from a provisioned runtime tree.
# Usage: run-openfoam.sh PROVISION_DIR RUN_DIR MPI_PROCS

set -eo pipefail

provision_dir="$1"
run_dir="$2"
mpi_procs="$3"
script_dir="$(cd -- "$(dirname -- "$0")" && pwd)"

module purge
module load intel/2025.1.3 impi

# OpenFOAM initialization intentionally tolerates intermediate failures.
set +e
source "${provision_dir}/OpenFOAM/etc/bashrc" \
    WM_COMPILER=Icx \
    WM_MPLIB=INTELMPI \
    WM_LABEL_SIZE=64 \
    WM_PRECISION_OPTION=DP
set -e

# decomposePar loads KaHIP dynamically when using the scotch decomposition.
shopt -s globstar nullglob
kahip_libraries=("${provision_dir}"/**/libkahip.so)
if [[ "${#kahip_libraries[@]}" -eq 0 ]]; then
    echo "KaHIP shared library was not provisioned" >&2
    exit 1
fi
kahip_lib_dir="$(dirname -- "${kahip_libraries[0]}")"
export LD_LIBRARY_PATH="${kahip_lib_dir}:${FFTW_ARCH_PATH}/lib:${LD_LIBRARY_PATH:-}"

cp -r "${FOAM_TUTORIALS}/incompressible/simpleFoam/motorBike" "${run_dir}/"
cd "${run_dir}/motorBike"

# Keep this CI smoke test bounded while retaining the full meshing/solver path.
sed -i 's/^endTime.*/endTime         10;/' system/controlDict
sed -i 's/^writeInterval.*/writeInterval    10;/' system/controlDict
foamDictionary -entry numberOfSubdomains -set "${mpi_procs}" system/decomposeParDict.6
foamDictionary -entry method -set scotch system/decomposeParDict.6

decompose_args=(-decomposeParDict system/decomposeParDict.6)

mkdir -p constant/triSurface
cp -f "${FOAM_TUTORIALS}/resources/geometry/motorBike.obj.gz" constant/triSurface/
surfaceFeatureExtract
blockMesh
decomposePar "${decompose_args[@]}" -force
mpirun -np "${mpi_procs}" snappyHexMesh -parallel "${decompose_args[@]}" -overwrite
mpirun -np "${mpi_procs}" topoSet -parallel "${decompose_args[@]}"

for processor_dir in processor*; do
    [ -d "${processor_dir}" ] && cp -r 0.orig/* "${processor_dir}/0/"
done

mpirun -np "${mpi_procs}" potentialFoam -parallel "${decompose_args[@]}" -writephi
"${script_dir}/exec-profiler.sh" \
    mpirun -np "${mpi_procs}" simpleFoam -parallel "${decompose_args[@]}"
