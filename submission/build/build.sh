#!/usr/bin/env bash

cd "${WM_PROJECT_DIR}"
export WM_NCOMPPROCS=16

"${WM_DIR}/src/Allmake"
"${WM_THIRD_PARTY_DIR}/makeSCOTCH" -no-mpi
src/Allwmake
