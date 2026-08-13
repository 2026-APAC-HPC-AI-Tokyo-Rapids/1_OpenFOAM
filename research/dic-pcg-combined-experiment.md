# Combined DIC cell-gather and PCG loop-fusion experiment

## Scope and rationale

This experiment combines only the two source candidates that independently
cleared the predefined four-node advancement threshold:

- cell-oriented DIC forward/back substitutions; and
- fusion of the PCG residual update and L1-norm pass.

OpenFOAM source commit `b6164259aca1a06da1352efc2b31bd6b43fe19e7`
contains both changes on the unmodified source baseline.  Symmetric `Amul` CSR
is deliberately excluded because two valid one-node measurements reproduced a
regression.  Workload, DP/Int64 build mode, toolchain, partition, placement,
MPI settings, and official parser are unchanged.

## Exact build and numerical qualification

Consumer commit `a0fba38483c9d4314804f2820da50a1820c399ec` pins the combined
source branch.  Push-triggered Actions `31661914834` selected a new build,
checked out the exact source OID above, and published archive #328:

- size: 476,470,983 bytes;
- SHA-256: `2849a7985b485360a532c301920d67c24632cb879df276444b84d68381a5e3c2`.

The one-node qualification run `r-68fc530086528eeeb9c77bbd7efc0acc`
was official `VALID` at 1.7834 M FVOPS and 35.888 s/step.  It found `End`, had
no NaN/Inf, completed 5/5 steps and 10/10 pressure solves, and retained exactly
321 iterations in every solve.  Its pressure residual lines are lexically
identical to the baseline.  Workload and mesh-cache manifests also match, and
all 120 rank/CPU placement records are exact.

## Repeated four-node result

Both four-node runs hardlinked and reused exact archive #328; neither rebuilt
OpenFOAM.

| Actions | Run ID | FVOPS_trim | s/step | Official status |
|---|---|---:|---:|---|
| `31662737506` | `r-1ec10cd2d04f8ac54f7a2c42938a10c7` | 8.4824 M | 7.545 | VALID |
| `31662737579` | `r-765790d354b02123a1b337e253635d44` | 8.4321 M | 7.590 | VALID |

Each run completed 5/5 steps and 10/10 solves at exactly 321 iterations, with
`End` present and no NaN/Inf.  The recorded residual trajectory matches the
same-layout baseline.  Each has exactly 448 placement records, four nodes with
112 ranks each, global ranks 0--447, local ranks 0--111, and the tracked
balanced singleton CPU-affinity sequence.  Preparation and solver PJMs are
terminal.  Official result, manifest, and fixed run bundle were copied to the
home archive and hash-checked before transient GitHub artifacts were removed.
No experiment PJM or temporary build/provision directory remains.

## Interpretation and decision

The established five-run four-node baseline has median 7.9900 M and range
7.9850--8.0050 M.  The combined mean is 8.4573 M, 5.85% above that median; both
samples exceed the entire baseline range.  The mean is also 3.78% above the
8.1490 M two-run mean reached independently by each single-source candidate.
Thus the benefits coexist and the combined build is materially stronger than
either candidate alone.

Advance the combined DIC+PCG source as the preferred implementation.  Its
correctness, build provenance, repeated four-node improvement, artifacts, and
cleanup satisfy the E2E gates.  Merge remains a separate user decision; the
experiment branches are retained for review and no change is applied to
`main` by this experiment.
