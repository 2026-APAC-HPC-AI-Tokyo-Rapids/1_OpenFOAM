# PCG residual-loop fusion experiment

## Hypothesis and change

OpenFOAM source commit `270d7da3a531dd97ece312d7742603fd828f0156`
fuses the residual L1 accumulation into the existing `psi`/residual update loop
in `PCG::scalarSolve`.  It removes one complete residual-array read per PCG
iteration while preserving ascending accumulation order, `solveScalar`, the
same `sumOp`, communicator, and message tag.  This is not pipelined CG and does
not alter the global-reduction count or algorithm.

For double precision the direct traffic saving is eight bytes per local cell
per iteration, approximately 14.3% of the explicit update-plus-norm stream.
The production translation unit compiled successfully and standalone `-O3`
comparisons were bitwise identical before E2E submission.

## Controlled E2E evidence

Consumer commit `3bbe28b4cac8062599a37daee0107f4182466820` pins the source
branch.  Actions `31659676841` performed the only new build and recorded exact
source OID `270d7da3...`.  The four-node runs reused build archive #322 rather
than rebuilding.

| Actions | Run ID | Layout | FVOPS_trim | s/step | Official status |
|---|---|---|---:|---:|---|
| `31659676841` | `r-5cf25f969d6a9ed04ddfbfcee5fefd06` | 1 node, 120 ranks | 1.6684 M | 38.360 | VALID |
| `31661117272` | `r-e69ed616e4319a647c98bc6350e1d306` | 4 nodes, 448 ranks | 8.1451 M | 7.857 | VALID |
| `31661484064` | `r-fd2f46dbb55e1d186ca1d05d7f24a335` | 4 nodes, 448 ranks | 8.1529 M | 7.850 | VALID |

All runs found `End`, reported no NaN/Inf, completed 5/5 steps and 10/10
pressure solves, and retained exactly 321 iterations for every solve.  The
one-node pressure residual lines are lexically identical to baseline; workload
and mesh-cache manifests also match.  Both four-node runs recorded all 448
placement records and used four nodes with the tracked 112-rank balanced
layout.  Every preparation and solver PJM terminated, and fixed artifacts were
copied to the home archive before the GitHub copies were removed.

## Interpretation and decision

The established five-run four-node baseline is 7.9850--8.0050 M with a median
of 7.9900 M.  The PCG samples are 8.1451 and 8.1529 M: both exceed the entire
baseline range, their mean is 8.1490 M, and the mean improvement over baseline
median is 1.99%.  This clears the predeclared 1% advancement threshold and
reproduces across node allocations.  The one-node value is inside the wider
one-node baseline range, so no one-node improvement is claimed.

Advance this candidate.  DIC cell-gather independently reached the same
two-run mean, but their effects cannot be assumed additive because both operate
inside every PCG iteration.  A combined DIC+PCG source branch therefore needs
its own new build, numerical qualification, and repeated four-node comparison
before either is proposed for merge.
