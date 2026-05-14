#!/bin/bash
#SBATCH -J "build_openfoam"
#SBATCH -o /home/apacsc14/ni/hpc/results/%j-%x.out
# SBATCH -w g4
# SBATCH -t 01:00:00
# set -e

cat $0
date

export WORKDIR=/home/apacsc14/ni/hpc
cd $WORKDIR/programs

export openfoam_ver=v2412
# wget https://dl.openfoam.com/source/${openfoam_ver}/OpenFOAM-${openfoam_ver}.tgz
# wget https://dl.openfoam.com/source/${openfoam_ver}/ThirdParty-${openfoam_ver}.tgz
# tar xfp OpenFOAM-${openfoam_ver}.tgz
# tar xfp ThirdParty-${openfoam_ver}.tgz

source /scratch/public/hpcx/hpcx-v2.24-gcc-doca_ofed-redhat9-cuda12-x86_64/hpcx-init.sh
hpcx_load

export OMPI_CC=gcc
export OMPI_CXX=g++
export OMPI_FC=gfortran

date
source $WORKDIR/programs/OpenFOAM-${openfoam_ver}/etc/bashrc WM_COMPILER=Gcc WM_MPLIB=SYSTEMOPENMPI WM_LABEL_SIZE=64 WM_PRECISION_OPTION=DP
cd $WM_PROJECT_DIR
time ./Allwmake -j 64

date
cd $WM_PROJECT_DIR/applications/solvers/incompressible/simpleFoam
time wmake -j 64

date
cd $WM_PROJECT_DIR/applications/solvers/basic/potentialFoam
time wmake -j 64

date

