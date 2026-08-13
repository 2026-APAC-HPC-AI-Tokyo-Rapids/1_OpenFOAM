# Symmetric `Amul` CSR experiment

## Hypothesis and change

The ordinary symmetric `lduMatrix` path did not materialize `lowerCSRPtr_`, so
`Amul` selected the face-scatter loop even though a cell-gather traversal could
be constructed from the symmetric upper coefficients.  OpenFOAM source commit
`e59ba58271d52d44d360b59ef28f1b35f4200569` makes the symmetric path lazily
construct and reuse the existing lower-CSR addressing.  The experiment changes
only this source-level traversal; workload, precision, label width, partition,
rank placement, MPI settings, parser, and toolchain remain fixed.

The expected benefit was contiguous per-cell accumulation.  The costs are one
scalar per internal face plus CSR addressing, a first-use materialization, and
an additional indirect coefficient lookup.  The branch was compiled and its
focused `lduMatrixCSR` test translation unit built before the production run.

## E2E evidence

Consumer commit `61cdabe7e04b45252b493ac1181a58baa74e22bc`
pinned the source branch and requested a new build.  Actions
`31659543636` built exact source OID `e59ba582...`, published archive #321
(476,642,133 bytes, SHA-256
`35e637d522212a4ac421baa8ad1b159ba765be5bf58c435c3bf187336dfa1f79`),
and completed the Actions -> PJM -> official parser -> fixed artifact -> home
archive path.  Actions `31660852551` hardlinked and reused that exact archive.

| Actions | Run ID | Layout | FVOPS_trim | s/step | Official status |
|---|---|---|---:|---:|---|
| `31659543636` | `r-2c55b7851f775b43a486f3df9ab8973d` | 1 node, 120 ranks | 1.5570 M | 41.105 | VALID |
| `31660852551` | `r-3822d451989fd1bf7af157bb276d535b` | 1 node, 120 ranks | 1.6035 M | 39.913 | VALID |

Both runs found `End`, had no NaN/Inf, completed 5/5 steps and 10/10 pressure
solves, and retained exactly 321 iterations for every solve.  Their pressure
residual lines are lexically identical to the unchanged baseline.  Workload
manifest, mesh-cache manifest, and normalized `decomposePar` log also match the
baseline.  Placement records cover ranks and CPUs 0--119 exactly on one node.
Both solver and preparation PJMs terminated, and both artifact sets were
archived before GitHub's transient copies were removed.

## Decision

The two-run mean is 1.5803 M FVOPS.  Both samples are below the five-run
baseline range of 1.6410--1.7021 M; the mean is 7.1% below the baseline median
of 1.7009 M.  The regression reproduced despite exact numerical equivalence.
The likely explanation is that CSR materialization, storage, and coefficient
indirection cost more than the gather traversal saves for this matrix.

Reject this candidate and do not spend a four-node run on it.  Keep the branch
and raw evidence for traceability; do not merge the source change.
