# DIC cell-gather experiment

## Hypothesis and change

Profiling identified `DICPreconditioner::precondition` as the largest sampled
single-node hotspot.  OpenFOAM source commit
`8ad5ef43ff4e38d89934b591c9bb8b68a7eccec9` replaces coefficient-oriented
forward and backward substitution traversals with stable cell-oriented gathers.
The forward pass uses lower/losort groups; the backward pass reverses
owner-start groups.  Dependency direction and the within-cell operand order are
unchanged.

The expected saving is approximately `6F - 3N` scalar transfers per
preconditioner application, in exchange for using existing addressing arrays.
The change was checked with the exact production translation unit at
`-O3`, and 20,000 randomized legal LDU addressings produced bitwise-identical
outputs at both `-O0` and `-O3` before E2E submission.

## Controlled E2E evidence

Consumer commit `c82722d00102bbe6bc35f8f7d3dd1d6a5844cb74` pins the source
branch.  Actions `31659543299` performed the only new build and recorded exact
source OID `8ad5ef43...` in its sidecar.  Archive #320 is 476,654,230 bytes with
SHA-256 `7055fa1ca4a12c558c443dc09dc86fe362ef178ce181212c112a94546921560b`.
Both four-node Actions runs reused that exact archive by hardlink; neither
rebuilt OpenFOAM.

| Actions | Run ID | Layout | FVOPS_trim | s/step | Official status |
|---|---|---|---:|---:|---|
| `31659543299` | `r-e0cb4a181bc3ad7738985ad1fafd8f04` | 1 node, 120 ranks | 1.6865 M | 37.947 | VALID |
| `31660570936` | `r-21605c23d19327d9335d776493dce131` | 4 nodes, 448 ranks | 8.1373 M | 7.865 | VALID |
| `31660990599` | `r-c0fa3178779bb27f5f949bf1540f372b` | 4 nodes, 448 ranks | 8.1607 M | 7.843 | VALID |

All runs found `End`, reported no NaN/Inf, completed 5/5 steps and 10/10
pressure solves, and retained exactly 321 iterations for every solve.  The
one-node pressure residual lines are lexically identical to baseline.  Its
workload manifest, mesh-cache manifest, and normalized decomposition log also
match baseline.  Four-node placement was exactly four groups of 112 ranks, with
the tracked balanced CPU list on every node.  Every preparation and solver PJM
terminated; fixed artifacts and official results were archived on the home
server before transient GitHub artifacts were removed.

## Interpretation and decision

The established five-run four-node baseline is 7.9850--8.0050 M with a median
of 7.9900 M.  The two DIC samples are 8.1373 and 8.1607 M: both exceed the
entire baseline range, their mean is 8.1490 M, and the mean improvement over
the baseline median is 1.99%.  This clears the predeclared 1% advancement
threshold and reproduces on different node allocations.  The one-node sample
is inside the broader one-node baseline range, so no single-node speedup is
claimed.

Advance this change as the current source-level candidate.  Before merging,
review the additional addressing-memory cost and run the final combined-build
qualification if it is composed with any other accepted source candidate.
