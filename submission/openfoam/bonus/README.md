# Bonus: NUMA-aware multiLevel decomposition and four source patches

The Bonus runs use the same machine, modules, compiler flags, MPI launch and CPU/NUMA placement as Basic (`../README.md`). Two
things differ, and nothing else.

1. **Decomposition** (Bonus F2, "other decomposition methods"): `multiLevel` with `scotch` at every level. The levels follow
   the machine: nodes, 2 sockets per node, 4 NUMA domains per socket, 16 cores per NUMA domain.
   - 1 node: `domains (2 4 16)`
   - 2 nodes: `domains (2 2 4 16)`
   - 4 nodes: `domains (4 2 4 16)`

   `caseDefinition` sets `decompositionMethod multiLevel`, and the `multiLevelCoeffs` block is appended to the shipped
   `decomposeParDict` (Basic's `scotchCoeffs` is not added). `dicts/` has both files of the 4-node run. `controlDict` is the
   same as in Basic.
2. **Source** (Bonus F2, "changes to v2512 source"): the patches in `patches/` are applied in name order to the official v2512
   source before the build (`patch -p1`). The compile flags and toolchain are the same as for the Basic build.

The Bonus uses the same scripts as Basic (`../README.md`, "How to run it"):

- Build with `PATCH_DIR` set to this folder's `patches/`:
  `qsub -P <project> -v SOURCE_DIR=<sources>,OPENFOAM_DIR=<dir>/build-bonus,PATCH_DIR=$PWD/patches ../build/build.pbs`
- Run with `../run/submit.sh <nodes> bonus`. It selects `multiLevel` with the domains above and the Bonus build.

## What changed and why it is the same math

All four patches remove memory traffic: temporary fields, copies, extra passes over the same arrays, and boundary exchanges whose
result is thrown away. Each one keeps the arithmetic expressions and their order. The interface (processor boundary) updates the
solution uses, the global reductions and the convergence checks are unchanged.

| Patch | What it changes | Why the result is the same |
|---|---|---|
| `0001-drop-redundant-solver-copies` | `smoothSolver` evaluates the residual with the existing in-place `lduMatrix::residual` overload, not with the overload that returns a new field which is then copied. GAMG forms its finest-level residual with one `subtract(r, source, Apsi)` instead of a copy followed by `-=`. | The same function computes the same residual. Only an allocation and a copy go away. `source - Apsi` is the same subtraction per cell. |
| `0002-smooth-vector-components-together` | For the vector (U) equation solved with `smoothSolver` + `GaussSeidel`, a new `smoothSolver::solveGaussSeidelComponents` smooths the three components in one pass over the shared matrix arrays (`fvMatrix<vector>::solveSegregated` uses it only in that case). | The components are independent in a segregated solve. Each component sees the same operations in the same order. Its boundary updates, residual normalisation and convergence test are as before. |
| `0003-skip-discarded-boundary-updates` | New `fvc::surfaceIntegrateInternal` builds only the internal field of a surface integral. It is used at six call sites that read only internal values: the non-orthogonal correction of the Laplacian, the `fvm::Sp` term of bounded convection, the corrected convection term, the continuity error, the `pEqn` source in `simpleFoam`, and `divU` in kOmegaSST. `gaussConvectionScheme::fvmDiv` builds lower, upper and diagonal in one face loop. | `fvc::div` computed the same internal values with the same `surfaceIntegrate` loop and then also built and exchanged boundary values, which these callers discarded. The fused face loop uses the same expressions in the same order. |
| `0004-fuse-gauss-gradient-and-product-integrate` | When the gradient interpolation is exactly `linear`, `gaussGrad` computes the face value `λ(φ_P − φ_N) + φ_N` inside the face-sum loop instead of first building an interpolated surface field. Coupled patches use the same `lerp`. `surfaceIntegrateInternal(a, b)` forms the face product `a·b` inside the integration loop. It is used for the Laplacian correction of U, k and omega, and for the corrected convection term of U. | These are the same expressions that `linear` interpolation and the separate product field evaluated. The values are summed in the same face order. No temporary surface field is created. |

## Proof that it is the same computation (F3)

The pre-change baseline has the Bonus configuration with the patches removed. It uses the same `multiLevel` decomposition and
coefficients, the same rank and node counts, and unmodified v2512. It ran with exactly the Basic binaries. Its
`simpleFoam.log` and `coefficient.dat` are in `f3-baseline/<n>node/`. Those of the Bonus are in `results/<n>node/`.

| Nodes (steps) | Baseline run (PBS job) | Bonus runs (PBS jobs) | SHA-256 of `coefficient.dat`, all runs | Cd at last step |
|---|---|---|---|---|
| 1 (40) | 25682093 | 25709674, 25706195, 25709663 | `36d35283932995d8d4569da30cbc3d67d2c75a48e4ca0a1e3b47da9ae2e4adcb` | 0.43827636195043501 |
| 2 (80) | 25682094 | 25709665, 25706306, 25709682 | `2a49a26dd354f8414fd69ac007f8e8c9583c860eddc16602d372db4b7f81afe0` | 0.32285935413723610 |
| 4 (150) | 25682211 | 25706165, 25706131, 25706125 | `8952a056c8de917de48cbebaad1af41c2e0abf3382b63dcc666b2ef7c75838ed` | 0.29138777754153217 |

- `coefficient.dat` is bit-identical between the baseline and every Bonus run at all three node counts. F3 passes in its
  strongest form.
- We also checked each patch on its own against the configuration just before it, at 1, 2 and 4 nodes. Every one gave a
  bit-identical `coefficient.dat`.
- The decomposition change alone does not change the source. The rules check it with the Sanity check table, which gives about
  0.43 / 0.34 / 0.28 – 0.29 at 40 / 80 / 150 steps.

| Steps | Sanity reference | `scotch` with its defaults | Basic: `scotch` mapped onto the node | multiLevel (baseline and Bonus) |
|---:|---:|---:|---:|---:|
| 40 | ~0.43 | 0.43598848994661615 | 0.43957921531324928 | 0.43827636195043501 |
| 80 | ~0.34 | 0.32713924728038718 | 0.33409590047442955 | 0.32285935413723610 |
| 150 | ~0.28 – 0.29 | 0.28404934573921931 | 0.29301591596528520 | 0.29138777754153217 |

- All three ran unmodified source; only the decomposition differs. At these step counts the decomposition moves Cd by a few
  per cent (the organisers' notes give 0.7 %, 3.0 % and 3.5 % between `hierarchical` and `scotch`).
- At 80 steps, `multiLevel` gives 0.323 and `scotch` with its defaults 0.327, a little below the reference values (0.334 –
  0.345 in the table); Basic gives 0.334. At 40 and 150 steps, all three are close to the reference.

## Speedup against our Basic result (same machine)

| Nodes (ranks, steps) | Basic mean s/step | Bonus mean s/step | Change | Speedup |
|---|---:|---:|---:|---:|
| 1 (128, 40) | 13.364504 (3 runs) | 11.668460 (3 runs) | −12.69 % | 1.145 × |
| 2 (256, 80) | 6.371748 (3 runs) | 5.640683 (3 runs) | −11.47 % | 1.130 × |
| 4 (512, 150) | 2.897638 (5 runs) | 2.599353 (3 runs) | −10.29 % | 1.115 × |

Every run with its PBS job ID is in `../scaling/scaling.txt`. `results/<n>node/` holds the fastest Bonus run of each node count.
The range across the repeated Bonus runs is 0.05 % (1 node), 0.20 % (2 nodes) and 0.18 % (4 nodes).

### Contribution of each change

Each row compares a configuration with the one before it, measured in the same period. For 4 nodes, each side has at least 3
runs. Most 1- and 2-node values come from single runs. The rows are separate experiments and should not be added up. The
cumulative effect is the measured Bonus against Basic above.

| Change (commit) | Compared with | 1 node | 2 nodes | 4 nodes |
|---|---|---:|---:|---:|
| multiLevel decomposition, unmodified source (`2eacff5`) | `scotch` with its defaults (Basic before the mapping) | −0.45 % | −0.38 % | −1.54 % |
| + 0001 (`e2730db`) | multiLevel, unmodified | −2.19 % | −2.94 % | −3.39 % |
| + 0002 (`57b6567`) | `e2730db` | −6.39 % | −4.13 % | −2.29 % |
| + 0003 (`20d285b`) | `57b6567` | −1.40 % | −1.88 % | −1.31 % |
| + 0004 (`fa4f5b0`) | `20d285b` | −2.88 % | −2.29 % | −2.82 % |

0002 gains most on 1 node (−6.4 %) and least on 4 nodes (−2.3 %). This fits a memory-bound smoother. With fewer nodes, each
rank's arrays fit less well in cache, so reading the matrix once instead of three times saves more DRAM traffic. Hardware
counters on 1 node support this for the four patches together: the demand refills from DRAM fall by 17 % while the instructions
fall by 4 % (`../analysis/README.md`, "Hardware counters"). We have not measured each patch, or 4 nodes, with counters.

## Tried and not adopted

Each candidate was compared with the configuration it would have changed, on 4 nodes. We adopt a change only if it is at
least 1 % faster than its control.

| Candidate | Result | What we learned |
|---|---|---|
| `multiLevel` with cell weights (1 + the cell's share of its points) | +2.2 % (weight × 2), +6.1 % (× 12) | Static weights unbalance the cell counts; even cell counts matter most. |
| METIS with two constraints (cells and faces) | +1.46 % | Better face balance, but 18 % more processor faces. |
| GAMG coarsest level gathered on one master for all 512 ranks (`processorAgglomerator masterCoarsest`) | +4.95 % (40 steps) | Gathering to one rank and solving there costs more than the global sums it saves. |
| The same with one master per node (`nProcessorsPerMaster 128`) or per NUMA domain (`16`) | +1.02 %, −0.25 % (single runs; Cd within 0.002 % of the control) | The coarsest level issues 81 % of the `MPI_Allreduce` calls, but moving it changes little: the MPI time is mostly waiting for slower ranks. |
| UCX over RC between nodes instead of UD | −0.16 % (4 runs each, ranges overlapping) | Below our threshold; the same check on Basic gave −0.01 %. |

## Files

- `patches/`: the four source patches.
- `dicts/`: `caseDefinition` and `decomposeParDict` of the 4-node run.
- `results/<n>node/`: the fastest Bonus run of each node count: `simpleFoam.log`, `coefficient.dat`, the logs of the
  preparation steps (`decomposePar.log`, `renumberMesh.log`, `potentialFoam.log`, `applyBoundaryLayer.log`) and the PBS
  output (`job-output.log`). `1node/` and `2node/` also hold the `caseDefinition`, `controlDict` and `decomposeParDict` of
  that run; this `decomposeParDict` is the copy our scripts recorded, with `$nCores` and `$decompositionMethod` replaced by
  their values.
- `f3-baseline/<n>node/`: `simpleFoam.log` and `coefficient.dat` of the pre-change baseline.
