# OpenFOAM HPC task — Tokyo Rapids with RIKEN

- Platform: NSCC ASPIRE-2A CPU nodes, queue `normal`, exclusive nodes. Each node has 2 × AMD EPYC 7713 (64 cores each, Zen 3).
  It has 8 NUMA domains of 16 cores and 32 MB of L3 per 8-core CCX. All runs use 128 MPI ranks per node, 1 rank per core, no SMT.
- Case: official `occDrivAerStaticMesh` 65M (65,334,765 cells), `simpleFoam`, 40 / 80 / 150 iterations on 1 / 2 / 4 nodes.
- Metric: `Average wall-clock time per time step` in `simpleFoam.log` (steps 2 to N). Lower is better.

| Nodes (ranks, steps) | Basic: s/step, mean of runs | Bonus: s/step, mean of runs | Bonus vs Basic |
|---|---:|---:|---:|
| 1 (128, 40) | 13.364347 (3 runs) | 11.668460 (3 runs) | −12.69 % |
| 2 (256, 80) | 6.366659 (3 runs) | 5.640683 (3 runs) | −11.40 % |
| **4 (512, 150)** | **2.919579** (5 runs) | **2.599353** (3 runs) | **−10.97 %** |

- **Basic** (this folder): unmodified OpenFOAM v2512 rebuilt on ASPIRE-2A, `scotch` decomposition, MPI ranks pinned to cores
  and their memory to the local NUMA domain. This is the result for the organisers' re-run.
- **Bonus** (`bonus/`): the same build and runtime setup with a NUMA-aware `multiLevel` decomposition and four source patches
  that remove redundant memory traffic. `coefficient.dat` is bit-identical to the pre-change baseline at 1, 2 and 4 nodes (F3).
  See `bonus/README.md`.

```
README.md            this file
build/build.pbs      the build of OpenFOAM v2512 (Basic; the Bonus adds bonus/patches)
run/                 job scripts of the whole Allrun chain, 1 / 2 / 4 nodes, Basic and Bonus
dicts/               caseDefinition, controlDict, decomposeParDict of the 4-node run (Basic)
results/<n>node/     logs and coefficient.dat of one run per node count (Basic)
scaling/scaling.txt  every run with its PBS job ID, means, speedup and efficiency (Basic and Bonus)
analysis/            MPI profiles (CrayPAT) and our reading of them
bonus/               Bonus patches, results and F3 evidence
```

## How to run it

On an ASPIRE-2A login node, in this folder. The scripts need nothing else from us.

1. Get the sources on the login node:

   ```bash
   mkdir -p sources
   curl -L -o sources/OpenFOAM-v2512.tgz https://dl.openfoam.com/source/v2512/OpenFOAM-v2512.tgz
   curl -L -o sources/thirdparty-common-v2512.tar.gz https://gitlab.com/openfoam/core/thirdparty-common/-/archive/v2512/thirdparty-common-v2512.tar.gz
   ```

2. Build (one 16-core job; 53 and 70 minutes in our re-run). `OPENFOAM_DIR` is a new directory on `/scratch`:

   ```bash
   qsub -P <project> -v SOURCE_DIR=$PWD/sources,OPENFOAM_DIR=<dir>/build-basic build/build.pbs
   qsub -P <project> -v SOURCE_DIR=$PWD/sources,OPENFOAM_DIR=<dir>/build-bonus,PATCH_DIR=$PWD/bonus/patches build/build.pbs
   ```

3. Edit the settings at the top of `run/submit.sh`, or set them in the environment:
   - `PROJECT`;
   - `OPENFOAM_DIR`: by default `<dir>/build-basic` or `<dir>/build-bonus`, chosen by the second argument of `submit.sh`;
   - `CASE_SOURCE`: the official case, `incompressible/simpleFoam/occDrivAerStaticMesh` of
     https://develop.openfoam.com/committees/hpc (commit `84c26243`);
   - `MESH_ARCHIVE`: `polyMesh_65M.tar.gz` from https://zenodo.org/records/15012221;
   - `WORK_ROOT`: where the runs go.
4. Submit the runs:

   ```bash
   run/submit.sh 1          # Basic, 1 node; also 2 and 4
   run/submit.sh 4 bonus    # Bonus, 4 nodes
   ```

   Each call submits two jobs and prints the new case directory under `WORK_ROOT`. The second job starts when the first has
   succeeded. In our re-run the first job (4 cores) took 10 – 14 minutes and the second 11 – 13 minutes.
5. The case directory then holds `logFiles/` (`10_decomposePar.log` … `50_simpleFoam.log`, with the `Average` line at the end
   of `50_simpleFoam.log`) and `postProcessing/forceCoeffsAll/0/coefficient.dat`. The PBS outputs are next to it.

## Basic

### Which v2512 and how it is built (`build/build.pbs`)

We rebuild the official source rather than use the site module.

- Sources:
  - OpenFOAM: the official `OpenFOAM-v2512.tgz` (SHA-256 `ae9a0a133a2e996b88bd1d0f3cc229e3c49968c368feae61bd3ec63deaf337aa`),
    unmodified. Its sources are file-for-file those of the tag `OpenFOAM-v2512` (commit `5a55da3f`) that our measured runs built.
  - ThirdParty: `thirdparty-common` at tag `v2512` (commit `1eb94326`).
  - Scotch 6.1.0: the sources of the site installation (`/app/apps/openfoam/2512/ThirdParty-v2512/sources/scotch/scotch_6.1.0`),
    built with `makeSCOTCH -no-mpi`.
- Modules: `PrgEnv-gnu/8.3.3` (GCC 11.2.0), `craype-x86-milan`, `aocl/4.0.0-gcc11.2`, `craype-network-ucx`, `cray-mpich-ucx/8.1.15`.
  `run/environment.sh` loads the same modules for the jobs.
- OpenFOAM environment: `WM_COMPILER=Gcc WM_MPLIB=CRAY-MPICH WM_PRECISION_OPTION=DP WM_LABEL_SIZE=32 WM_COMPILE_OPTION=Opt`
  (`WM_OPTIONS=linux64GccDPInt32Opt`). No `wmake/rules` changes.
  - `FOAM_EXTRA_CXXFLAGS` is empty.
  - `FOAM_EXTRA_LDFLAGS="-Wl,--no-as-needed -L${AOCL_ROOT}/lib -lalm"` links AMD AOCL-LibM. IEEE double precision is kept; no
    fast-math flags are used.
- Built targets: `wmake`, Scotch, all libraries (`src/Allwmake`), and the applications of Allrun: `decomposePar`,
  `renumberMesh`, `potentialFoam`, `applyBoundaryLayer` and `simpleFoam`.
- The build runs in node-local storage and is then copied to `OPENFOAM_DIR`. With `PATCH_DIR`, the `*.patch` files are applied
  to the OpenFOAM sources in name order before the build (Bonus).

### Case files (`dicts/`)

These are the files OpenFOAM read in the 4-node run. Only the edits that Basic (F1) allows were made:

- `caseDefinition`: `nCores 512`, `decompositionMethod scotch`. There is no `scotchCoeffs`, so scotch runs with its defaults.
  Everything else is as shipped.
- `controlDict`: the shipped `controlDict.noWrite` with `endTime 150`. All function objects are kept.
- `decomposeParDict`: the shipped file, unchanged. It takes `numberOfSubdomains` and `method` from `caseDefinition`.
- The 1- and 2-node runs differ only in `nCores` (128, 256) and `endTime` (40, 80). Their `caseDefinition` and
  `controlDict` are in `results/1node/` and `results/2node/`.
- As in `Allrun`: `fvSolution` is the shipped `fvSolution.fixedIter`, and `0/` comes from `0.orig/`. `fvSchemes` and the mesh
  are unchanged.

### Preparation chain and solver run (`run/`)

`run/submit.sh NODES [basic|bonus]` submits two jobs, as in the organisers' ASPIRE-2A notes:

1. **`run/prepare.pbs`** (4 cores, 120 GB, shared node): copies the case, extracts the 65M mesh into `constant/`, copies
   `controlDict.noWrite` and `fvSolution.fixedIter`, sets `endTime`, `nCores` and `decompositionMethod`, then runs
   `decomposePar -constant` and `restore0Dir -processor`.
2. **`run/solve.pbs`** (all nodes, `place=excl`, started with `-W depend=afterok`): copies the decomposed case to node-local
   storage (`$TMPDIR`) on every node, then runs `renumberMesh -constant -overwrite -parallel`,
   `potentialFoam -initialiseUBCs -parallel`, `applyBoundaryLayer -ybl 0.0450244 -parallel` and `simpleFoam -parallel`.

Every Allrun step runs with Allrun's switches. All OpenFOAM commands also use `-fileHandler uncollated`. On 2 and 4 nodes they
add `-hostRoots '((".*" "$TMPDIR"))'` and `-ioRanks` with the first rank of each node, so each node reads and writes its own
local copy of the case.

MPI launch and placement:

- `mpiexec -n <ranks> -ppn 128 --cpu-bind depth -d 1` (Cray PALS).
- Each rank is started through `run/exec-local-numa.sh`, which runs `numactl --membind=$((PMI_LOCAL_RANK / 16))`. This places
  the rank's memory on the NUMA domain of its core.
- On ASPIRE-2A, the CPU binding requested from PALS is removed from outside the process during `MPI_Init`. One watcher per node
  (`run/keep-rank-affinity.sh`) re-pins each `simpleFoam` main thread to CPU `PMI_LOCAL_RANK` with `taskset`. The PBS output
  of `solve.pbs` reports `bound=128/128` for every node.
- qsub resources: `-q normal -l select=<nodes>:ncpus=128:mpiprocs=128:ompthreads=1:mem=400gb -l place=excl`, 40 minutes.
- MPI is Cray MPICH 8.1.15 over UCX (`craype-network-ucx`, `cray-mpich-ucx/8.1.15`), not the default OFI provider. The signal 7
  (SIGBUS) at `MPI_Finalize` that the organisers' ASPIRE-2A notes describe for 2 and 4 nodes does not occur. Every step of
  every run returned 0. We also tried the default OFI provider with each of the two workarounds in those notes, with
  everything else as in Basic. Both completed without the signal and gave the same Cd, but were slower on 4 nodes:
  `FI_OFI_RXM_USE_SRX=0` by 0.77 % (2.9421 against 2.9197 s/step, 3 alternated runs each, ranges not overlapping) and
  `FI_VERBS_PREFER_XRC=0` by 0.50 % (2.9338 against 2.9192 s/step, one run each). Basic stays on UCX.

### Results (`results/<n>node/`)

One run per node count, the fastest of the repeated runs. The files are:

- `simpleFoam.log` and `coefficient.dat` (copied from `postProcessing/forceCoeffsAll/0/`).
- `decomposePar.log`, `renumberMesh.log`, `potentialFoam.log` and `applyBoundaryLayer.log`.
- `job-output.log`: the PBS job output.
- `caseDefinition` and `controlDict` (1 and 2 nodes): the files that run read. The 4-node ones are in `dicts/`, and
  `decomposeParDict` is the shipped file at every node count.

`scaling/scaling.txt` lists every run with its PBS job ID.

| Nodes | Runs (PBS job IDs, `.pbs101`; first = in `results/`) | Mean s/step | Min – max (range) | Cd at last step |
|---|---|---:|---|---|
| 1 | 25681549, 25688005, 25688040 | 13.364347 | 13.343864 – 13.390329 (0.35 %) | 0.43598848994661615 |
| 2 | 25688187, 25681550, 25688036 | 6.366659 | 6.353589 – 6.377541 (0.38 %) | 0.32713924728038718 |
| 4 | 25681428, 25681323, 25681500, 25682005, 25691889 | 2.919579 | 2.915547 – 2.925664 (0.35 %) | 0.28404934573921931 |

- The runs were made on 2026-10-04 and 2026-10-05 (UTC).
- `coefficient.dat` is identical across all runs of the same node count.
- Sanity check of Cd (reference about 0.43 / 0.34 / 0.28 – 0.29 at 40 / 80 / 150 steps):
  - 40 and 150 steps: close to the reference.
  - 80 steps: 0.327, a little below the reference values (0.334 – 0.345).
- The range across repeated runs (0.35 – 0.38 %) is the run-to-run variability. It is a different quantity from the
  step-to-step variation within one run.
- For comparison, the organisers' vanilla reference runs on ASPIRE-2A with `scotch` (site module, default MPI settings, no
  binding; tasks 4.3) gave 3.191 – 3.576 s/step on 4 nodes, 7.196 – 7.423 on 2 nodes and 14.049 – 14.808 on 1 node.

### These scripts against the measured runs

The runs above were started by our CI, whose scripts also recorded measurements for us. `build/` and `run/` keep exactly what
those runs did to the case and to the processes, in the same order and with the same flags. They leave out:

- steps that only measured or checked: rank placement and hardware records, `ldd` checks, an IMB network test after the solver;
- `checkMesh -constant` before `decomposePar` (not part of Allrun), and copying `0.orig` to `0` before `decomposePar` (`restore0Dir`
  replaces those fields anyway);
- the reuse of a decomposed case between runs (every run here makes its own);
- a node-local copy of the build in each job (the timed steps do not read the build), and `ccache` in the build.

We re-ran `build/` and `run/` on 2026-10-07 exactly as "How to run it" describes: the sources downloaded from the URLs above,
both builds with `build/build.pbs`, and every run with `run/submit.sh`. A GitHub Actions job (run 37584763848) only called them
and collected the logs.

| Configuration | Nodes | PBS jobs (prepare, solve) | s/step | Recorded runs: mean (min – max) | Change | `coefficient.dat` |
|---|---:|---|---:|---|---:|---|
| Basic | 1 | 25714167, 25714168 | 13.332891 | 13.364347 (13.343864 – 13.390329) | −0.24 % | identical |
| Basic | 2 | 25714169, 25714170 | 6.371243 | 6.366659 (6.353589 – 6.377541) | +0.07 % | identical |
| Basic | 4 | 25714171, 25714172 | 2.919982 | 2.919579 (2.915547 – 2.925664) | +0.01 % | identical |
| Bonus | 1 | 25714175, 25714176 | 11.644042 | 11.668460 (11.665328 – 11.670959) | −0.21 % | identical |
| Bonus | 2 | 25714177, 25714178 | 5.649779 | 5.640683 (5.633468 – 5.644714) | +0.16 % | identical |
| Bonus | 4 | 25714179, 25714180 | 2.600607 | 2.599353 (2.597249 – 2.601808) | +0.05 % | identical |

- "identical": byte for byte the same file as every recorded run of that configuration and node count.
- Every step of every job ended with `End` and returned 0. In every solve job the watcher re-pinned each of the 128 ranks of
  every node once.
- The profile mode ran too (`analysis/README.md`).

### How we arrived at the Basic setup

Each comparison ran on 4 nodes with 150 steps, with 3 runs per side in the same period unless noted.

- **Decomposition**: `scotch` (2.9145 s/step) against the case default `hierarchical (16 8 4)` (3.2574): −10.5 %. On 2 nodes,
  6.3679 against 6.5282 (−2.5 %); on 1 node, 13.3459 against 13.5229 (−1.3 %).
- **CPU and NUMA placement**: without the fix above, the memory of unpinned ranks spreads to remote NUMA domains, and runs were
  16 – 19 % slower (4 nodes, scotch: 3.40 – 3.47 against 2.917 s/step). An `LD_PRELOAD` interposer that pins after `MPI_Init` gave the same speed as `numactl` + `taskset`. Basic does
  not allow `LD_PRELOAD`, so Basic uses `numactl` + `taskset`.
- **Not adopted** (against a scotch control of 2.9122):
  - Changes of less than 1 %: `-march=znver3` 2.9113, AOCC 5.0 2.9112, `-O2` 2.9108, LTO 2.9141.
  - No gain: the OpenFOAM communication switches we tried (`topoControl`, `nbx.tuning`, `pbufs.tuning`). `commsType scheduled`
    stopped with a floating-point exception in GAMG, so we could not use it.
  - SMT with 2 ranks per core (1024 ranks) was about 5.7 times slower. We stopped that run after 22 steps.
- **Checked later, each against Basic runs in the same period** (not adopted):
  - GCC profile-guided optimisation (`-fprofile-generate` on the official 1-node run, then `-fprofile-use`): 2.917802 against
    2.913900 s/step on 4 nodes (+0.13 %), 13.334152 against 13.324118 on 1 node (+0.08 %), one run each.
    `coefficient.dat` bit-identical.
  - UCX over RC between nodes (`UCX_TLS=rc,sm,self`) instead of the default UD: 2.9192 against 2.9194 s/step (−0.01 %,
    4 alternated runs each). The IMB bandwidth rose (1 MiB Sendrecv, 6.7 to 10.4 GB/s), so the transfer between nodes is not
    what a step waits for.

## Scaling (`scaling/scaling.txt`)

| Nodes | Basic s/step | Speedup | Efficiency | Bonus s/step | Speedup | Efficiency |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 13.364347 | 1.000 | 1.000 | 11.668460 | 1.000 | 1.000 |
| 2 | 6.366659 | 2.099 | 1.050 | 5.640683 | 2.069 | 1.034 |
| 4 | 2.919579 | 4.577 | 1.144 | 2.599353 | 4.489 | 1.122 |

The efficiency is above 1 for both. This fits the per-rank data fitting better in cache as the node count grows. We have not
measured that with hardware counters. The Bonus patches cut memory traffic (on 1 node, 17 % fewer demand refills from DRAM with
4 % fewer instructions; `analysis/README.md`), and they gain most on 1 node (see `bonus/README.md`).

## Analysis (`analysis/`)

MPI profiles (CrayPAT, `-g mpi`) of the Basic configuration and of the Bonus before and after the source patches, with our
reading of them. `run/submit.sh 4 basic craypat` reruns such a profile. See `analysis/README.md`.

## Provenance

- Repository: `2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM` (private).
  - Basic commit `6396eeb619048e90f48ae79ff12f6bdd79defe02` (tag `issue38-basic-final-20261005`).
  - Bonus commit `fa4f5b04a9e1fa323c5d2c2eb39fa800b3a5f892` (tag `issue51-bonus-fused-gradient-20261006`).
  - The scripts in `build/` and `run/`: directory `submission/openfoam/` of the repository.
- Every run was started by GitHub Actions. The complete raw records of each run are in our artifact archive.
