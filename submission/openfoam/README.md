# OpenFOAM HPC task — Tokyo Rapids with RIKEN

We made the official `occDrivAerStaticMesh` 65M case (`simpleFoam`, OpenFOAM v2512) faster on NSCC ASPIRE-2A without
changing what it computes. This file says what is in the folder, how to run it again, and what you should get.
[`REPORT.md`](REPORT.md) explains how we got there and why it works.

## Results

The metric is `Average wall-clock time per time step` at the end of `simpleFoam.log` (steps 2 to N). Lower is better.

The baseline is the same build, scripts and measurement with the case's own settings (the `hierarchical` split and the
launcher's binding only), so the change against it is what our optimisations did. Means of the repeated jobs (number of jobs):

| Nodes (ranks, steps) | Baseline | **Basic** | Bonus | Basic against baseline | Bonus against Basic |
|---|---:|---:|---:|---:|---:|
| 1 (128, 40) | 14.567 (6) | 13.364504 (3) | 11.668460 (3) | −8.3% | −12.69% |
| 2 (256, 80) | 7.427 (3) | 6.371748 (3) | 5.640683 (3) | −14.2% | −11.47% |
| **4 (512, 150)** | **3.650 (3)** | **2.897638 (5)** | **2.599353 (3)** | **−20.6%** | **−10.29%** |

For reference only: the organisers' vanilla runs on ASPIRE-2A (tasks 4.3) took 3.296 s/step on 4 nodes with `scotch`
(5 jobs, 3.191 – 3.576) and 3.415 with `hierarchical`. They use the site module, the default MPI transport and no binding,
so they differ from our runs in more than our optimisations.

- **Basic**: unmodified OpenFOAM v2512 rebuilt on ASPIRE-2A; `scotch` decomposition mapped onto the sockets and NUMA domains
  of each node; every MPI rank pinned to its core, with its memory on that core's NUMA domain.
- **Bonus**: the same build and runtime, plus a node-aware `multiLevel` decomposition and four source patches that move fewer
  bytes. `coefficient.dat` is bit-identical to the unpatched baseline at 1, 2 and 4 nodes.

## What is in this folder

```
README.md            this file: results, how to run, what to expect
REPORT.md            technical report: the analysis, every optimisation and the evidence
build/build.pbs      builds OpenFOAM v2512 from the official sources (the Bonus build adds bonus/patches)
run/                 the Allrun chain as two PBS jobs, for 1 / 2 / 4 nodes, Basic and Bonus
dicts/               caseDefinition, controlDict and decomposeParDict of the 4-node Basic run
results/<n>node/     logs and coefficient.dat of the fastest Basic run per node count
scaling/scaling.txt  every run with its PBS job ID, the means, speedup and efficiency
analysis/            MPI profiles (CrayPAT) and hardware-counter results
bonus/               the Bonus patches, dictionaries, results and the bit-identity evidence
figures/             the figures of REPORT.md
```

## How to run it

On an ASPIRE-2A login node, in this folder. The scripts need nothing else from us.

1. Get the sources:

   ```bash
   mkdir -p sources
   curl -L -o sources/OpenFOAM-v2512.tgz https://dl.openfoam.com/source/v2512/OpenFOAM-v2512.tgz
   curl -L -o sources/thirdparty-common-v2512.tar.gz https://gitlab.com/openfoam/core/thirdparty-common/-/archive/v2512/thirdparty-common-v2512.tar.gz
   ```

2. Build. Each build is one 16-core job of 1 – 2 hours; `OPENFOAM_DIR` is a new directory on `/scratch`:

   ```bash
   qsub -P <project> -v SOURCE_DIR=$PWD/sources,OPENFOAM_DIR=<dir>/build-basic build/build.pbs
   qsub -P <project> -v SOURCE_DIR=$PWD/sources,OPENFOAM_DIR=<dir>/build-bonus,PATCH_DIR=$PWD/bonus/patches build/build.pbs
   ```

3. Set `PROJECT`, `OPENFOAM_DIR`, `CASE_SOURCE`, `MESH_ARCHIVE` and `WORK_ROOT` at the top of `run/submit.sh`, or in the
   environment:
   - `CASE_SOURCE`: the official case, `incompressible/simpleFoam/occDrivAerStaticMesh` of
     https://develop.openfoam.com/committees/hpc (commit `84c26243`);
   - `MESH_ARCHIVE`: `polyMesh_65M.tar.gz` from https://zenodo.org/records/15012221;
   - `OPENFOAM_DIR`: by default `<dir>/build-basic` or `<dir>/build-bonus`, chosen by the second argument of `submit.sh`.
4. Submit:

   ```bash
   run/submit.sh 4          # Basic, 4 nodes (also 1 and 2)
   run/submit.sh 4 bonus    # Bonus, 4 nodes
   ```

   Each call submits two jobs and prints the new case directory. The first job (4 cores, 9 – 14 minutes) prepares and
   decomposes the case; the second (all nodes, 11 – 14 minutes) runs `renumberMesh`, `potentialFoam`, `applyBoundaryLayer`
   and `simpleFoam`.
5. Read the result: the `Average` line at the end of `<case>/logFiles/50_simpleFoam.log`, and
   `<case>/postProcessing/forceCoeffsAll/0/coefficient.dat`. The PBS outputs are next to the case directory.

## What you should get (Basic)

| Nodes | s/step of our jobs | Cd at the last step | `coefficient.dat` |
|---:|---|---|---|
| 1 | 13.3626 – 13.3680 | 0.43957921531324928 | byte-identical to `results/1node/coefficient.dat` |
| 2 | 6.3660 – 6.3762 | 0.33409590047442955 | byte-identical to `results/2node/coefficient.dat` |
| 4 | 2.8944 – 2.8996 | 0.29301591596528520 | byte-identical to `results/4node/coefficient.dat` |

- We re-ran exactly these scripts from the public sources on 2026-10-16, on other hosts: `coefficient.dat` was byte-identical
  at every node count, and the time was 0.24 – 0.36% above our means (4 nodes: 2.904620 s/step). Most of our October runs lie
  within ±0.5% of the median of their configuration, so expect about that spread.
- The PBS output of the second job prints `bound=128/128` for every node when every rank sits on its own core. If it does not,
  the placement has failed and a step will be 16 – 19% slower (`REPORT.md`, section 6.1).
- At these step counts the flow has not converged, and Cd depends on the decomposition. Another decomposition gives a Cd a few
  per cent different (`REPORT.md`, section 11).

## How it is built (`build/build.pbs`)

- Sources: the official `OpenFOAM-v2512.tgz` (SHA-256 `ae9a0a133a2e996b88bd1d0f3cc229e3c49968c368feae61bd3ec63deaf337aa`),
  unmodified; `thirdparty-common` at tag `v2512`; Scotch 6.1.0 from the site installation, built without MPI.
- Modules: `PrgEnv-gnu/8.3.3` (GCC 11.2.0), `craype-x86-milan`, `aocl/4.0.0-gcc11.2`, `craype-network-ucx`,
  `cray-mpich-ucx/8.1.15`. `run/environment.sh` loads the same modules for the jobs.
- `WM_OPTIONS=linux64GccDPInt32Opt` (GCC `-O3`, double precision, 32-bit labels), no `wmake/rules` changes, no fast-math
  flags. `FOAM_EXTRA_LDFLAGS` links AMD's math library AOCL-LibM.
- Only what the case needs: `wmake`, Scotch, the libraries in `src/`, and `decomposePar`, `renumberMesh`, `potentialFoam`,
  `applyBoundaryLayer` and `simpleFoam`.

## What we changed in the case (`dicts/`)

Only what Basic allows (addendum F1):

- `caseDefinition`: `nCores` (128 / 256 / 512) and `decompositionMethod scotch`.
- `controlDict`: the shipped `controlDict.noWrite` with `endTime` 40 / 80 / 150. All function objects are kept.
- `decomposeParDict`: the shipped file plus one `scotchCoeffs` block, the settings of the `scotch` method:
  `domains (2 4 16)`, `domainWeights (0.125 0.0625 0.015625)` and a `strategy` string. `run/prepare.pbs` appends it.
- As in `Allrun`: `fvSolution` is the shipped `fvSolution.fixedIter`, and `0/` comes from `0.orig/`. `fvSchemes` and the mesh
  are unchanged.

## Provenance

- Repository `2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM` (private): Basic commit `16c62ac1e809a5baed755002d79525dcbc3f330b`
  (tag `issue63-basic-final-20261016`), Bonus commit `fa4f5b04a9e1fa323c5d2c2eb39fa800b3a5f892`
  (tag `issue51-bonus-fused-gradient-20261006`). The scripts here are the directory `submission/openfoam/` of that repository.
- Every measured run was started by GitHub Actions; their complete raw records are in our artifact archive.
