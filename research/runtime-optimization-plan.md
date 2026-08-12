# cavity3D-64M runtime optimization research plan

## Objective

Optimize the official five-step `cavity3D-64M` workload on Genkai without
changing its prescribed arithmetic or precision.  The primary result is the
official `FVOPS_trim` emitted by `benchmark/parse_result.sh`; every accepted
result must be `STATUS: VALID` and retain the complete Actions, PJM, raw run,
BigQuery, and artifact provenance paths.

The initial scope is input decomposition, MPI rank placement, Intel MPI and
OpenFOAM runtime settings, and cell ordering.  Source-level solver changes are
deferred until these lower-cost axes have been exhausted.

## Established baseline

The current workflow allocates one, two, or four nodes but always decomposes
the mesh into 120 Scotch domains.  The latest comparable valid results are:

| Nodes | Total ranks | Ranks/node | FVOPS_trim | s/step | Run ID |
|---:|---:|---:|---:|---:|---|
| 1 | 120 | 120 | 1.6398 M | 39.030 | `r-c4bb4bb3c51a6a6724aa7177ea1d01e6` |
| 2 | 120 | 60 | 3.1718 M | 20.177 | `r-fef72f7255e44a077f5fa2b1b115b0df` |
| 4 | 120 | 30 | 4.9488 M | 12.932 | `r-c2aef4bc0f5dd083a8790751af269342` |

PR 12's post-merge one-node run, Actions run `31624279389`, independently
produced 1.6270 M FVOPS and completed artifact archival.  The 1.6392 M repeat
(`r-efdfb255f9d7c78e7eb9c7df59bcab5c`) differs from the earlier result by less
than 0.04%, while the post-merge run was about 0.8% lower.  This is only an
initial noise indication, not a settled noise floor.

The current 120-way Scotch partition has approximately 1.0% maximum cell
imbalance, 2,650,146 unique interface faces, 633 rank pairs, 10.55 average
neighbours/rank, and 18 maximum neighbours.  Consecutive-rank placement yields
291,222 inter-node faces at two nodes and 578,906 at four nodes.

One-node VTune rank-0 sampling attributes about 45.8% of reported CPU time to
`DICPreconditioner::precondition`, 26.1% to `lduMatrix::Amul`, and 16.4% to
`PCG::scalarSolve`; the sampled MPI functions total only a few percent.  This
supports treating one-node work as memory/locality dominated while measuring,
rather than assuming, the multi-node communication balance.

## Invariants and evidence ownership

- Keep the seven workload-defining input files byte-identical.  Mesh geometry,
  five time steps, two pressure correctors, 321 PCG iterations, double
  precision, and `floatTransfer=0` are immutable.
- Use the same OpenFOAM archive until a source, toolchain, build dependency, or
  required executable changes.  Runtime, workflow, decomposition, parser, and
  documentation changes reuse the archive.
- Run experiments through GitHub Actions.  Direct SSH is read-only and limited
  to inspecting completed runs, scheduler state, caches, and diagnostics.
- Git/commit bodies own tracked settings and their rationale.  Actions and PJM
  logs own execution progress.  Genkai run directories and archived artifacts
  own raw output.  BigQuery owns comparison facts.  This document owns the
  hypotheses, decisions, and interpretation.
- Bench and profile runs are separate populations.  Instrumented timings are
  never used as competition scores.
- No speculative retry, fallback, locking, or auxiliary metadata is added.

## Experiment infrastructure

Before performance trials, replace the accidental 120-rank coupling with one
explicit experiment preset selected at workflow dispatch.  A preset completely
defines nodes, ranks, decomposition, OpenFOAM switches, Intel MPI overrides,
and optional renumbering.  The effective values are copied into the protocol,
manifest sources, decomposition dictionary, launch argv, placement capture,
and metrics.

Case reuse has two levels:

1. The immutable 64-million-cell serial `blockMesh` result.
2. A decomposed/ordered case keyed by the canonical preparation inputs:
   preparation implementation, total ranks, complete decomposition dictionary,
   renumbering dictionary (or none), OpenFOAM build identity, and workload
   identity.

Each prepared case is immutable after publication.  Preparation remains a
separate serialized Actions/PJM job.  Solver failures do not invalidate a
valid reusable case.  Static tests must reject rank/protocol/decomposition
mismatches before a PJM solver job is submitted.

The first implementation supports only named presets needed by this plan; it
does not expose arbitrary user-supplied MPI environment or dictionaries.

## Phased experiments

### Phase 0: measurement integrity and noise

Re-run the unchanged 1-node/120-rank Scotch baseline until at least five valid
bench samples exist under the current build and workflow.  Record best, median,
minimum, maximum, and relative range.  This verifies measurement stability and
the new preset path before expensive multi-node comparisons.

### Phase 1: fill physical cores

With Scotch and default pinning, compare:

| Preset | Nodes | Total ranks | Ranks/node | Purpose |
|---|---:|---:|---:|---|
| `scotch-1n-120r` | 1 | 120 | 120 | unchanged baseline |
| `scotch-2n-240r` | 2 | 240 | 120 | full physical cores |
| `scotch-4n-480r` | 4 | 480 | 120 | full physical cores |

Run each candidate twice for screening and the four-node candidate at least
five times if it succeeds.  The expected improvement is large enough that a
negative or negligible result is treated as evidence of a placement,
transport, or partition defect and investigated before proceeding.

### Phase 2: reserve one core per NUMA domain

At four nodes compare 480 ranks against 448 ranks (112/node).  The latter leaves
one physical core free in each of Genkai's eight 15-core NUMA domains.  Use
explicit CPU placement only to ensure that both layouts mean what their preset
claims; do not mix this trial with a decomposition change.  Advance 448 ranks
only if its median official FVOPS exceeds 480 by more than the measured noise.

Quarter-node layouts and SMT ranks are excluded initially: published task data
shows large losses from leaving many physical cores idle, and the allocated
nodes expose 120 online physical CPUs rather than a useful untested SMT tier.

### Phase 3: geometric and topology-aware decomposition

At the best four-node rank count, screen these partitions:

1. Scotch baseline.
2. Direct `hierarchical` geometric split.
3. Multi-level node-aware geometric split.
4. Multi-level node-then-NUMA-aware geometric split.
5. Outer geometric node split followed by inner Scotch, only if the pure
   geometric variants expose a meaningful cell or interface imbalance.

For 480 ranks, use the analytically balanced final grid `(6 8 10)`.  The
topology-aware candidate maps the first level to four nodes, the second to the
eight NUMA domains per node, and the third to 15 ranks per NUMA domain:

| Nodes | Node grid | NUMA grid/node | Rank grid/NUMA | Final grid |
|---:|---|---|---|---|
| 1 | `(1 1 1)` | `(4 1 2)` | `(1 5 3)` | `(4 5 6)` |
| 2 | `(1 1 2)` | `(1 2 4)` | `(5 3 1)` | `(5 6 8)` |
| 4 | `(1 2 2)` | `(2 4 1)` | `(3 1 5)` | `(6 8 10)` |

The exact axis ordering may be changed only after inspecting the actual
rank-to-CPU/NUMA map and calculating the resulting inter-node and inter-NUMA
interfaces.  Every prepared partition records cell balance, interface-face
count, neighbour count, and faces crossing the intended node/NUMA rank groups.
These are explanatory variables, not acceptance metrics.

Screen each candidate twice.  Compare the best candidate and Scotch with at
least five independent submissions each, alternating submission order.

### Phase 4: multi-node runtime switches

Profile the winning four-node layout.  In addition to rank 0, select the rank
with the highest inter-node face count and one representative interior rank.
Only pursue MPI switches when MPI wait/collective/transfer time is material.

Test one factor at a time in this order:

1. OpenFOAM `topoControl=16` versus default 0.
2. `commsType=scheduled` versus default `nonBlocking`.
3. Intel MPI collective autotuning generated and consumed only on the exact
   same node/rank/fabric topology.

Do not repeat known negative motorBike trials without new evidence:
`nPollProcInterfaces=-1`, globally forcing one Allreduce algorithm, disabling
pinning, or arbitrary compact/scatter changes.  Retain `I_MPI_FABRICS=shm` on
one node and `shm:ofi` on multiple nodes.

### Phase 5: cell ordering

After rank, placement, partition, and MPI settings stabilize, compare:

1. No renumbering.
2. Cuthill-McKee.
3. Block-local Cuthill-McKee with `blockSize=32768`.
4. `blockSize=65536` only if 32768 improves measured memory behaviour or FVOPS.

Prior published results found ordinary renumbering neutral to 1.4% slower, so
two negative candidates terminate this phase.  Adding `renumberMesh` to the
reduced runtime build is a build-content change and therefore requires a
`[require-build]` commit and a new archive.

### Phase 6: final qualification

Run the winning configuration at one, two, and four nodes at least five times
each.  Report official FVOPS distributions, 4-node/1-node strong scaling,
partition characteristics, placement, scheduler accounting, and profile-based
explanation.  Keep node-count-specific tuning only when it has repeated
evidence; prefer one coherent topology rule when results are statistically
equivalent.

## Decision rules

- A screening candidate advances only when all runs are valid and its median
  FVOPS exceeds the baseline median.
- A setting is adopted only when the repeated improvement exceeds the larger
  of the measured same-system relative range and 1%.  Below that boundary it
  is recorded as indistinguishable and the simpler setting wins.
- A proxy improvement alone never advances a candidate.
- Any invalid result stops that candidate until the first fatal command or
  error is identified and the full E2E path succeeds again.
- Stop an axis after two well-formed candidates fail to improve and profiling
  shows that axis cannot account for a material fraction of runtime.
- Cap the initial settings-level campaign at 50 bench runs.  Additional runs
  require a new profile-backed hypothesis.

## Per-run completion checklist

- Actions workflow and every required job reach terminal success.
- PJM job reaches terminal exit code zero and leaves no residual job.
- `run-success` exists.
- Official parser prints `STATUS: VALID` and one `RESULT:` line.
- Exact nodes, ranks, ranks/node, CPU affinity, and NUMA placement match preset.
- Workload identity and build provenance match the comparison group.
- Fixed artifact set is packaged, uploaded, and archived successfully.
- Required BigQuery facts are present.
- The experiment ledger records the hypothesis, changed factor, result,
  interpretation, and next decision.

## Completion status

The planned campaign completed on 2026-08-13.  Named presets, immutable case
caches, full-core and balanced-rank screens, topology-aware partitions, a
boundary-rank VTune profile, exact-topology Intel MPI autotuning, two
post-decomposition ordering candidates, and same-build five-run 1/2/4-node
qualification all traversed the required E2E path.  Decisions and complete
run populations are recorded in `runtime-optimization-experiments.md`.

The reproducible selected layouts are 1 x 120, 2 x 120, and 4 x 112 ranks
using Scotch, with the 4-node processor list reserving one CPU per NUMA domain.
Default Intel MPI collectives and no renumbering remain selected.  No further
candidate is admitted under the original stop conditions: MPI autotuning and
both ordering variants were below 1%, the conditional 65536-cell ordering
trial was not triggered, and the final qualification population is complete.
