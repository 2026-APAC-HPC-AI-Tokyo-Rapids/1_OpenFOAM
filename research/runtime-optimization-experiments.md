# cavity3D-64M runtime optimization experiment ledger

This ledger is updated after every completed experiment or decisive static
investigation.  Timing claims use official valid bench results only.

## Status

- Current phase: Phase 0 noise confirmation and Phase 1 full-core screening.
- Current build: existing OpenFOAM v2606 Icx/Intel MPI archive; reuse intended.
- Current production preset: one node, 120 total ranks, Scotch,
  `I_MPI_FABRICS=shm`.
- Active hypothesis: the fixed 120-rank canary configuration underuses two- and
  four-node allocations; full physical-core layouts should dominate before
  smaller MPI runtime adjustments matter.
- The first full-core screen at commit `948e11f` is complete.  Two nodes/240
  ranks produced 3.3997 M FVOPS and four nodes/480 ranks produced 6.8139 M;
  both were valid.  A concurrent one-node repeat produced 1.6996 M.
- Repeat full-core workflows `31634782784` (2/240) and `31634785406`
  (4/480) are active at commit `a5390da`.  The next controlled factor is
  four nodes/448 ranks, with one CPU deliberately reserved in each NUMA domain.

## Prior evidence admitted to the study

| Evidence | Changed factor | Result | Decision |
|---|---|---|---|
| Actions 256 / run `r-c4bb4bb3c51a6a6724aa7177ea1d01e6` | 1 node, 120 Scotch ranks | VALID, 1.6398 M FVOPS | baseline sample |
| Actions 257 / run `r-fef72f7255e44a077f5fa2b1b115b0df` | 2 nodes, still 120 ranks | VALID, 3.1718 M FVOPS | canary only; not full-core baseline |
| Actions 258 / run `r-c2aef4bc0f5dd083a8790751af269342` | 4 nodes, still 120 ranks | VALID, 4.9488 M FVOPS | canary only; not full-core baseline |
| Actions 277 / run `r-efdfb255f9d7c78e7eb9c7df59bcab5c` | repeat 1 node/120 | VALID, 1.6392 M FVOPS | agrees within 0.04% |
| Actions 278 / run `r-49e4a417a55f2278a211f483d720b391` | VTune rank 0 | VALID profile; DIC 45.8%, Amul 26.1% | locality dominates sampled rank |
| Actions 279 / run `r-6227d22fbc780cd0ad71df88fd19ed2c` | post-merge 1 node/120 | VALID, 1.6270 M FVOPS | baseline sample; about 0.8% below 1.6398 M |
| Actions 280 / run `r-321efbd20828499c944ad987c4170a68` | named `scotch-1n-120r` preset and content-addressed 120-way case cache | VALID, 1.6400 M FVOPS, 39.025 s/step | new preset path agrees with prior baseline; advance to concurrent full-core screening |
| Actions 281 / run `r-0af1f803cd25cfc680fed74ca4a2e067` | 2 nodes, 240 Scotch ranks | VALID, 3.3997 M FVOPS, 18.825 s/step | 7.2% above the old 2-node/120-rank canary; repeat before accepting because current one-node range is 4.4% |
| Actions 282 / run `r-91ee8cc4584bd7464cfc3a82b2a405fa` | 4 nodes, 480 Scotch ranks | VALID, 6.8139 M FVOPS, 9.393 s/step | 37.7% above the old 4-node/120-rank canary; retain full-core layout |
| Actions 283 / run `r-0cb4e46f0158a5bf0437f6c1bf5b1106` | 1-node named-preset repeat, cache hit | VALID, 1.6996 M FVOPS, 37.655 s/step | unexpectedly fast but valid; use the observed 4.4% range as the provisional noise threshold |
| Actions 284 / run `r-c500507dc433575dde90bfcb4073be8f` | 2-node/240-rank repeat, cache hit | VALID, 3.4015 M FVOPS, 18.815 s/step | agrees with the first 3.3997 M result within 0.05%; accept full-core two-node layout |
| Actions 285 / run `r-95df043fc37d34b11df231699019ce85` | 4-node/480-rank repeat, cache hit | VALID, 7.8264 M FVOPS, 8.178 s/step | 14.9% above the first repeat; full-core gain is certain but four-node noise requires alternating repeats |
| Actions 286 / run `r-8bf1d07cc38e52ced65c4cf1095bfc52` | 4 nodes, 448 Scotch ranks, balanced NUMA reserve | VALID, 8.0025 M FVOPS, 7.997 s/step | 2.25% above the adjacent 480-rank result but within observed four-node range; repeat before adoption |

## Infrastructure observation: Actions 280

- Date and commit: 2026-08-13 JST, `948e11f`.
- Actions / PJM: `31627088350`; preparation job `6467089`; solver job
  `6467176`.
- Case preparation: cache miss; `blockMesh` plus 120-way Scotch decomposition
  completed in the 30-minute PJM limit.  The Actions preparation job took
  20m29s and published cache
  `daba43a5b54c39cda0874fdff2f9c7f6d06200d8e34f8266eada33194b3a235f`.
- Solver: official result `STATUS: VALID`, `FVOPS_trim=1.6400M`,
  `s_per_step=39.025`, `trim_time=156.1s`, five of five steps and 120 ranks on
  one node.
- Integrity: `run-success` exists; all required Actions jobs succeeded; fixed
  v2 and official result artifacts were uploaded and copied to the home
  archive; GitHub copies were then removed as designed.  PJM job `6467176` was
  absent from `pjstat` after completion.
- Interpretation: the preset/cache generalization did not measurably perturb
  the reference result.  Case preparation, not the five-step solver, dominated
  this first cache-miss pipeline, so immutable decomposition reuse is material
  to the experiment campaign.
- Decision: retain this result as a Phase 0 sample and proceed without a build
  to `scotch-2n-240r` and `scotch-4n-480r`.  One additional 1-node repeat was
  submitted to complete the planned current-workflow noise sample count.

## Phase 0 result: provisional noise range

The five comparable valid one-node results currently available are 1.6270,
1.6392, 1.6398, 1.6400, and 1.6996 M FVOPS.  Their median is 1.6398 M and their
minimum-to-maximum span is 4.4% of the median.  The most recent result is 3.6%
above the median, so it cannot be discarded as an invalid outlier without a
measured environmental cause.  Until alternating repeats narrow this range,
candidate improvements below 4.4% are treated as indistinguishable.

## Phase 1 screen: full physical cores

All three concurrently dispatched workflows reached terminal success,
including official parsing, fixed artifact upload, and home-server archival.
The preparation jobs remained serialized to protect the shared filesystem;
solver work could proceed as soon as its own immutable cache was published.

| Actions | Nodes/ranks | Prepare PJM/cache | Solver PJM/run | Official result | Solver/pipeline wall |
|---:|---:|---|---|---|---|
| 281 (`31629648195`) | 2 / 240 | `6467212`, cache miss, `a69a992f...` | `6467289`, `r-0af1f803cd25cfc680fed74ca4a2e067` | VALID, 3.3997 M, 18.825 s/step | 121.824 / 123.490 s |
| 282 (`31629651069`) | 4 / 480 | `6467287`, cache miss, `25d0ec32...` | `6467377`, `r-91ee8cc4584bd7464cfc3a82b2a405fa` | VALID, 6.8139 M, 9.393 s/step | 56.860 / 58.525 s |
| 283 (`31629672240`) | 1 / 120 | `6467376`, cache hit, `daba43a5...` | `6467389`, `r-0cb4e46f0158a5bf0437f6c1bf5b1106` | VALID, 1.6996 M, 37.655 s/step | 202.274 / 203.950 s |

The 240-way Scotch partition has 3,529,391 unique interface faces, 1,372 rank
pairs, 11.43 mean and 19 maximum neighbours, 264,000--269,332 cells/rank, and
303,351 faces crossing the consecutive 120-rank node boundary.  The 480-way
partition has 4,653,839 unique interface faces, 2,998 rank pairs, 12.49 mean
and 23 maximum neighbours, 131,931--134,666 cells/rank, and 727,567 faces
crossing the three consecutive 120-rank node boundaries.  Captured placement
confirms exactly 120 local ranks and one distinct CPU per rank on each node.

Relative to the old fixed-120-rank canaries, 240 ranks improved two-node FVOPS
by 7.2%, while 480 ranks improved four-node FVOPS by 37.7%.  Relative to the
1.6400 M validation run, the first full-core results scale by 2.07x and 4.15x.
The four-node result is decisively beyond measured noise and full-core rank
occupancy is retained.  The smaller two-node gain requires a repeat.  The next
decomposition phase should target the rapidly increasing interface count and
make rank groups correspond to node and NUMA geometry.

## Phase 2 setup: balanced 112 ranks/node

The compute-node hardware capture maps NUMA nodes 0--7 to consecutive 15-CPU
ranges `0-14`, `15-29`, ..., `105-119`.  A generic 448-rank launch would use
CPUs 0--111 and concentrate all eight idle CPUs at the end of the final NUMA
domain.  Preset `scotch-4n-448r` instead binds local ranks to
`0-13,15-28,30-43,45-58,60-73,75-88,90-103,105-118`, reserving the final CPU
of every NUMA domain.  This changes rank count and balanced CPU reservation
together as the intended Phase 2 resource layout; decomposition remains
Scotch and transport remains `shm:ofi`.  Captured per-rank placement must show
exactly this set on all four nodes before its score is compared with 480 ranks.

Actions 286 (`31635007954`) verified the intended placement on all four nodes:
112 distinct CPUs per node and CPUs 14, 29, 44, 59, 74, 89, 104, and 119
absent.  Preparation PJM `6467443` published cache `1170485d...`; solver PJM
`6467537` produced run `r-8bf1d07cc38e52ced65c4cf1095bfc52` with official
`STATUS: VALID`, 8.0025 M FVOPS, 51.385 s solver wall, and 53.056 s pipeline
wall.  The 448-way partition has 4,537,155 interface faces, 2,797 rank pairs,
139,315--144,285 cells/rank, and 704,792 faces crossing consecutive 112-rank
node groups.  Actions and home-server artifact archival both succeeded and no
experiment-owned PJM job remained.

This single result is 2.25% above the adjacent 7.8264 M 480-rank repeat, but
the two 480-rank results themselves span 14.9%.  Therefore reserving one core
per NUMA domain remains promising rather than accepted.  It disproves the
stronger assumption that using fewer than all cores must clearly regress this
workload and warrants an alternating 448/480 repeat after the partition screen.

## Phase 3 setup: geometric partition screen

Two 480-rank candidates keep node count, rank count, Intel MPI settings, and
cell arithmetic fixed against the Scotch baseline:

- `hierarchical-4n-480r` uses a direct `(6 8 10)` split with `xyz` order.
  For the uniform 400-cubed mesh its analytical axis-plane interface count is
  3,360,000 faces, 27.8% below Scotch's measured 4,653,839, before accounting
  for processor-boundary representation details.
- `multilevel-node-numa-4n-480r` applies `(1 2 2)` across the four node rank
  groups, `(2 4 1)` across eight NUMA groups per node, then `(3 1 5)` across
  15 ranks per NUMA group.  The product is the same `(6 8 10)` final grid, but
  its rank numbering is designed to make consecutive 120-rank node placement
  correspond to the outer geometric domains.

Geometric case generation is intentionally implemented in a separate prepare
script and cache identity.  Extending the established Scotch prepare script
would change its script digest and unnecessarily invalidate the published
120-, 240-, and 480-way Scotch caches or the in-flight 448-way cache.  Both
geometric candidates remain serialized with other shared-filesystem
preparation, and a solver failure cannot delete their valid immutable caches.

The first direct-hierarchical run, Actions 287 (`31635570359`), completed its
solver and official parser successfully at 7.8745 M FVOPS and 8.127 s/step
(`r-0724eeff7878fb21867b61f6f7e2f1f5`, solver PJM `6467689`).  Solver and
pipeline walls were 52.711 and 54.402 s, and artifacts were archived.  However,
the separate mesh-facts stage rejected the effective dictionary because the
requested-partition v1 contract admitted only Scotch.  Thus the score is valid
but the run is incomplete for partition comparison.  The observed failure is
addressed by requested-partition v2, whose method enum is exactly `scotch`,
`hierarchical`, or `multiLevel`; method-specific dictionaries remain preserved
only in the raw source copy and identified by its SHA-256.  Both geometric
candidates must be rerun through the updated E2E parser before an adoption
decision.

## Experiment template

### Experiment ID

- Date and commit:
- Actions run / PJM job / run ID:
- Hypothesis:
- Comparison baseline:
- Single changed factor:
- Nodes / ranks / ranks per node:
- Decomposition and ordering:
- MPI/OpenFOAM runtime settings:
- Official result and validity:
- Solver and pipeline wall time:
- Partition and placement observations:
- Artifact and BigQuery status:
- Interpretation:
- Decision and next experiment:
