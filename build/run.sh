#!/bin/bash
set -e

cd ..
rm -rf programs/
mkdir programs
cd programs

export openfoam_ver=v2412
wget https://dl.openfoam.com/source/${openfoam_ver}/OpenFOAM-${openfoam_ver}.tgz
wget https://dl.openfoam.com/source/${openfoam_ver}/ThirdParty-${openfoam_ver}.tgz
tar xvfp OpenFOAM-${openfoam_ver}.tgz & \
tar xvfp ThirdParty-${openfoam_ver}.tgz

cd ../build
sbatch build.sh
squeue -l
