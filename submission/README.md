# Tokyo Rapids with RIKEN OpenFOAM SUBMISSION

```
submission/
  ├── README.txt                  # including loaded site modules, or how you rebuilt if you did
  ├── build/
  │   └── build.sh                # only if you rebuilt
  ├── run/
  │   ├── 1node.sbatch            # full prep chain, not only simpleFoam
  │   ├── 2node.sbatch
  │   └── 4node.sbatch
  ├── dicts/
  │   ├── caseDefinition
  │   ├── decomposeParDict
  │   └── controlDict
  ├── results/
  │   ├── 1node/                  # text logs, including decomposePar
  │   ├── 2node/
  │   └── 4node/
  │       ├── simpleFoam.log
  │       └── coefficient.dat     # Cd; copy from postProcessing/forceCoeffsAll
  ├── scaling/
  └── analysis/                   # optional profiling write-up
```
