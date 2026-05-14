#!/bin/sh
#SBATCH -J "allrun"
#SBATCH -o /home/apacsc14/ni/hpc/results/%j-%x.out

cat $0

export openfoam_ver=v2412
export WORKDIR=/home/apacsc14/ni/hpc

c

cd $WORKDIR/hpc/incompressible/simpleFoam/occDrivAerStaticMesh

./Allrun
