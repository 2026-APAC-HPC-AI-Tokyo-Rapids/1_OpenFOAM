# Bonus: NUMA-aware multiLevel decomposition and fourteen source patches

The Bonus runs use the same machine, modules, compiler flags, MPI launch and CPU/NUMA placement as Basic (`../README.md`,
`../REPORT.md`). Two things differ, and nothing else.

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

## What changed

The patches remove memory traffic: temporary fields, copies, extra passes over the same arrays, and boundary exchanges whose
result is thrown away. None of them changes the iteration counts, the convergence tests, the number of time steps or the
discretisation. Eleven keep every arithmetic expression and its order, so they cannot change a result; three (`0011`, `0012`,
`0016`) change the order of some floating-point operations and are judged by F3 with the drag coefficient (next section).
The numbers `0005` and `0007` are not in the Bonus (`0005`: `../REPORT.md`, Appendix A).

| Patch | What it changes | Why the result is the same |
|---|---|---|
| `0001-drop-redundant-solver-copies` | `smoothSolver` evaluates the residual with the existing in-place `lduMatrix::residual` overload, not with the overload that returns a new field which is then copied. GAMG forms its finest-level residual with one `subtract(r, source, Apsi)` instead of a copy followed by `-=`. | The same function computes the same residual. Only an allocation and a copy go away. `source - Apsi` is the same subtraction per cell. |
| `0002-smooth-vector-components-together` | For the vector (U) equation solved with `smoothSolver` + `GaussSeidel`, a new `smoothSolver::solveGaussSeidelComponents` smooths the three components in one pass over the shared matrix arrays (`fvMatrix<vector>::solveSegregated` uses it only in that case). | The components are independent in a segregated solve. Each component sees the same operations in the same order. Its boundary updates, residual normalisation and convergence test are as before. |
| `0003-skip-discarded-boundary-updates` | New `fvc::surfaceIntegrateInternal` builds only the internal field of a surface integral. It is used at six call sites that read only internal values: the non-orthogonal correction of the Laplacian, the `fvm::Sp` term of bounded convection, the corrected convection term, the continuity error, the `pEqn` source in `simpleFoam`, and `divU` in kOmegaSST. `gaussConvectionScheme::fvmDiv` builds lower, upper and diagonal in one face loop. | `fvc::div` computed the same internal values with the same `surfaceIntegrate` loop and then also built and exchanged boundary values, which these callers discarded. The fused face loop uses the same expressions in the same order. |
| `0004-fuse-gauss-gradient-and-product-integrate` | When the gradient interpolation is exactly `linear`, `gaussGrad` computes the face value `λ(φ_P − φ_N) + φ_N` inside the face-sum loop instead of first building an interpolated surface field. Coupled patches use the same `lerp`. `surfaceIntegrateInternal(a, b)` forms the face product `a·b` inside the integration loop. It is used for the Laplacian correction of U, k and omega, and for the corrected convection term of U. | These are the same expressions that `linear` interpolation and the separate product field evaluated. The values are summed in the same face order. No temporary surface field is created. |
| `0006-fuse-laplacian-coefficients-and-diagonal` | `gaussLaplacianScheme::fvmLaplacianUncorrected` writes `upper = deltaCoeffs·gammaMagSf` and subtracts it from both diagonals in one face loop. | The temporary product field, its copy and `negSumDiag`'s re-read of `upper` did the same operations per face in the same order. |
| `0008-decide-pressure-reference-once` | `simpleFoam` keeps the answer of `setRefCell` (whether `p` needs a reference level, a property of its patch types) and calls `adjustPhi` and `setReference` only when it does. | Each call evaluated `needReference` (a loop over the patches and a global reduction) every step. With this case's outlet the answer is false and the calls did nothing else; when it is true, the same cells get the same modification. |
| `0009-fuse-divdevreff-tensor-expression` | `linearViscousStress::divDevRhoReff` forms `muEff·dev2(T(grad(U)))` with one loop over the cells and one per patch, instead of three whole-field passes. | The same inline primitives (`T`, `dev2`, scalar × tensor) are applied to the same operands in the same order. The field keeps the name that selects the `div` scheme. |
| `0010-wall-shear-stress-on-patches-only` | The `wallShearStress` function object, which reads `devReff()` only on the wall patches, evaluates `(−nuEff)·devTwoSymm(grad U)` on those patches for linear eddy-viscosity models, as the `forces` function object already does, instead of building the full-volume field. | `nuEff` on a patch is `nut + nu` on that patch, the values the volume expression used there; the negation is exact. Other models keep the volume path. |
| `0011-gauss-seidel-accumulator-instead-of-copy` | Every Gauss–Seidel sweep copied the source into a work array before the interface update and the sweep overwrote it. A separate accumulator, zero between sweeps, now receives the interface terms and the lower-neighbour scatter; each cell reads `source + acc` and resets `acc` in the same cache line. | **F3.** The same terms are summed, but `source` is added once at the end instead of first: one re-association per cell, so the last bits can differ. |
| `0012-pcg-one-reduction-per-iteration` | Every PCG solve with the DIC preconditioner (here the GAMG coarsest level of `p`) uses the Chronopoulos/Gear form of CG (Ghysels and Vanroose, 2014): the two CG scalars and the residual norm are reduced together, one global reduction per iteration instead of three. | **F3.** The same Krylov iterates in exact arithmetic; one inner product becomes a recurrence, so rounding differs. Initial guess, preconditioner, convergence test, `minIter`/`maxIter`, the singularity test and the reported residuals keep their meaning, for any tolerance. Other preconditioners keep the original loop. |
| `0013-fuse-komegasst-cell-expressions` | `kOmegaSSTBase::correct` evaluates `F1`, `F2`/`F23`, `S2`, `GbyNu`, `Pk`, the blended coefficients, `DkEff`/`DomegaEff`, `CDkOmega` and `correctNut` each in one cell loop and one loop per patch, instead of one pass per operator: 13 instead of 80 traversals of the cells per call. | The same primitives (`sqrt`, `tanh`, `sqr`, `pow4`, `min`/`max` with the original operand order) on the same operands in the same association. `volatile` temporaries keep the rounding of the former separate products, so the compiler cannot form new fused multiply-adds. Matrix assembly, solves and `bound()` are untouched. |
| `0014-skip-zero-fill-of-overwritten-coefficients` | The Gauss convection and Laplacian schemes, which write every face coefficient before reading it, get their `upper`/`lower` and patch coefficients without the zero fill. The momentum predictor solves with the pressure gradient added to the source in place and restores it, instead of copying the whole `U` matrix. | No arithmetic changes: only storage that is written before it is read is no longer zeroed, and the source gets the same `V·rhs` that `operator==` added. The solver restores the diagonal bit for bit, so `A()`, `H()` and `H1()` see the original matrix. |
| `0015-gamg-scale-and-restrict-in-place` | GAMG adds the scaled correction to `psi` in the loop that already computes it, and restricts the next cycle's residual to the coarse level while it is formed. | The same operations; coarse cells are summed in the same ascending fine-cell order. The first cycle, processor agglomeration and coarser levels keep the original path. |
| `0016-gauss-seidel-residual-from-sweep` | With `GaussSeidel` and one sweep per iteration, the residual after an iteration's last sweep is assembled inside that sweep, and the processor-interface values received for it are reused by the next sweep. Per component and iteration, one matrix pass and one interface exchange go away. | **F3.** The residual is still formed completely, summed and tested after every iteration, at the same place and with the same meaning; tolerance-controlled solves stop at the same iteration. `psi` is unchanged in exact arithmetic; on processor interfaces the reused contribution can change rounding. Other smoothers and settings run the original code. |

## Proof that it is the same computation (F3)

The pre-change baseline has the Bonus configuration with the patches removed: the same `multiLevel` decomposition and
coefficients, the same rank and node counts, and unmodified v2512. It ran with exactly the Basic binaries. Its
`simpleFoam.log` and `coefficient.dat` are in `f3-baseline/<n>node/`. Those of the Bonus are in `results/<n>node/`.

The proof has two steps.

1. **`0001`–`0004` are bit-identical to the unmodified baseline.** With only these four patches (commit `fa4f5b0`),
   `coefficient.dat` is byte-identical to the baseline at 1, 2 and 4 nodes, and every solver log line (residuals to 16
   digits, iteration counts, continuity errors, the bounding of `k` and `omega`) is identical.
2. **All fourteen patches stay within ±0.5% of it.** Cd at the last step of the final Bonus against `fa4f5b0`, from the
   final measurement (2026-10-26):

| Nodes (steps) | Baseline and `fa4f5b0`: Cd, SHA-256 of `coefficient.dat` | Bonus: Cd, SHA-256 of `coefficient.dat` (all 3 jobs) | Cd difference |
|---|---|---|---:|
| 1 (40) | 0.43827636195043501, `36d35283…` | 0.43827636195094927, `00d481ab…` | +1.2 × 10⁻¹² (relative) |
| 2 (80) | 0.32285935413723610, `2a49a26d…` | 0.32285928314184348, `d9fe4e04…` | −0.00002% |
| 4 (150) | 0.29138777754153217, `8952a056…` | 0.29138659643758436, `34749b4c…` | −0.00041% |

- The largest difference, −0.00041% on 4 nodes, is more than 1,000 times smaller than the ±0.5% that F3 allows.
- On 4 nodes we also checked each group against the configuration just before it. `0006`, `0008`–`0010` give a byte-identical
  `coefficient.dat` (`8952a056…`). `0011` changes it (Cd −0.0009%), and `0012` changes it again (−0.0004% against
  `fa4f5b0`). `0013`–`0016` leave it byte-identical to the `0012` result (`34749b4c…`). So on 4 nodes, the whole difference
  comes from `0011` and `0012`.
- Every job of the same configuration and node count gave a byte-identical `coefficient.dat`.
- The decomposition change alone does not change the source. The rules check it with the Sanity check table, which gives about
  0.43 / 0.34 / 0.28 – 0.29 at 40 / 80 / 150 steps.

| Steps | Sanity reference | `scotch` with its defaults | Basic: `scotch` mapped onto the node | multiLevel (baseline) |
|---:|---:|---:|---:|---:|
| 40 | ~0.43 | 0.43598848994661615 | 0.43957921531324928 | 0.43827636195043501 |
| 80 | ~0.34 | 0.32713924728038718 | 0.33409590047442955 | 0.32285935413723610 |
| 150 | ~0.28 – 0.29 | 0.28404934573921931 | 0.29301591596528520 | 0.29138777754153217 |

- All three ran unmodified source; only the decomposition differs. At these step counts the decomposition moves Cd by a few
  per cent (the organisers' notes give 0.7%, 3.0% and 3.5% between `hierarchical` and `scotch`).
- At 80 steps, `multiLevel` gives 0.323 and `scotch` with its defaults 0.327, a little below the reference values (0.334 –
  0.345 in the table); Basic gives 0.334. At 40 and 150 steps, all three are close to the reference.

## Speedup against our Basic result (same machine)

| Nodes (ranks, steps) | Basic mean s/step | Bonus mean s/step | Change | Speedup |
|---|---:|---:|---:|---:|
| 1 (128, 40) | 13.364504 (3 runs) | 10.233606 (3 runs) | −23.43% | 1.306 × |
| 2 (256, 80) | 6.371748 (3 runs) | 4.992196 (3 runs) | −21.65% | 1.276 × |
| 4 (512, 150) | 2.897638 (5 runs) | 2.359976 (3 runs) | −18.56% | 1.228 × |

Every run with its PBS job ID is in `../scaling/scaling.txt`. `results/<n>node/` holds the fastest Bonus run of each node count.
The range across the repeated Bonus runs is 0.64% (1 node), 0.49% (2 nodes) and 0.29% (4 nodes).

The Basic means were measured in October before the final Bonus runs. In the final measurement, `fa4f5b0` ran alternated with
the Bonus and gave 11.650451, 5.636920 and 2.603134 s/step, within 0.15% of its own means of 2026-10-07 (11.668460, 5.640683,
2.599353), so the machine had not changed in between.

### Contribution of each change

Each row compares a configuration with the one before it. For 4 nodes, each side has at least 3 runs. The rows are separate
experiments and should not be added up. The cumulative effect is the measured Bonus against Basic above.

| Change (commit) | Compared with | 1 node | 2 nodes | 4 nodes |
|---|---|---:|---:|---:|
| multiLevel decomposition, unmodified source (`2eacff5`) | `scotch` with its defaults (Basic before the mapping) | −0.45% | −0.38% | −1.54% |
| + 0001 (`e2730db`) | multiLevel, unmodified | −2.19% | −2.94% | −3.39% |
| + 0002 (`57b6567`) | `e2730db` | −6.39% | −4.13% | −2.29% |
| + 0003 (`20d285b`) | `57b6567` | −1.40% | −1.88% | −1.31% |
| + 0004 (`fa4f5b0`) | `20d285b` | −2.88% | −2.29% | −2.82% |
| + 0006, 0008 – 0010 (`4b1ed6a`) | `fa4f5b0` | | | −1.99% |
| + 0011 (`45a4e7b`) | `4b1ed6a` | | | −1.04% |
| + 0012 (`f99771e`) | `45a4e7b` | | | −0.30% |
| + 0013 – 0015 (`af6b217`) | `f99771e` | | | −2.48% \* |
| + 0016 (`1bc34b9`) | `af6b217` | | | −3.80% \* |
| All of 0006 – 0016 (`1bc34b9`) | `fa4f5b0`, alternated (final measurement) | −12.16% | −11.44% | −9.34% |

\* Measured a few days after the configuration it is compared with, not alternated with it. The last row, alternated, is the
measured effect of `0006`–`0016` together.

`0002` gains most on 1 node (−6.4%) and least on 4 nodes (−2.3%), and so do `0006`–`0016` together (−12.2% on 1 node, −9.3% on
4). This fits memory-bound kernels: with fewer nodes, each rank's arrays fit less well in cache, so every pass that is removed
saves more DRAM traffic. Hardware counters on 1 node support this for `0001`–`0004` together: the demand refills from DRAM fall
by 17% while the instructions fall by 4% (`../analysis/README.md`, "Hardware counters"). We have not measured each patch, or
`0006`–`0016`, with counters.

## Tried and not adopted

Each candidate was compared with the configuration it would have changed, on 4 nodes. We adopt a change only if it is at
least 1% faster than its control.

| Candidate | Result | What we learned |
|---|---|---|
| `multiLevel` with cell weights (1 + the cell's share of its points) | +2.2% (weight × 2), +6.1% (× 12) | Static weights unbalance the cell counts; even cell counts matter most. |
| METIS with two constraints (cells and faces) | +1.46% | Better face balance, but 18% more processor faces. |
| GAMG coarsest level gathered on one master for all 512 ranks (`processorAgglomerator masterCoarsest`) | +4.95% (40 steps) | Gathering to one rank and solving there costs more than the global sums it saves. |
| The same with one master per node (`nProcessorsPerMaster 128`) or per NUMA domain (`16`) | +1.02%, −0.25% (single runs; Cd within 0.002% of the control) | The coarsest level issues 81% of the `MPI_Allreduce` calls, but moving it changes little: the MPI time is mostly waiting for slower ranks. |
| UCX over RC between nodes instead of UD | −0.16% (4 runs each, ranges overlapping) | Below our threshold; the same check on Basic gave −0.01%. |
| Gauss–Seidel sweep of the interior cells while the interface values are in flight | +8.32% (3 runs), Cd −1.20% | Fails F3: on 512 ranks, changing the order in which cells see their neighbours' new values moves Cd far beyond rounding. It was also slower. |
| `bound()` averaging only over the cells it bounds | not run | It needs an extra global reduction per call, which costs more than the averaging it saves. |

## Files

- `patches/`: the fourteen source patches.
- `dicts/`: `caseDefinition` and `decomposeParDict` of the 4-node run.
- `results/<n>node/`: the fastest Bonus run of each node count: `simpleFoam.log`, `coefficient.dat`, the logs of the
  preparation steps (`decomposePar.log`, `renumberMesh.log`, `potentialFoam.log`, `applyBoundaryLayer.log`) and the PBS
  output (`job-output.log`). `1node/` and `2node/` also hold the `caseDefinition`, `controlDict` and `decomposeParDict` of
  that run; this `decomposeParDict` is the copy our scripts recorded, with `$nCores` and `$decompositionMethod` replaced by
  their values.
- `f3-baseline/<n>node/`: `simpleFoam.log` and `coefficient.dat` of the pre-change baseline.
