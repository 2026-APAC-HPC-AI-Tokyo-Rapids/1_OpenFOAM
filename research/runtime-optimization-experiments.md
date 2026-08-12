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
- Active Actions runs at commit `948e11f`: `31629648195` (2 nodes/240 ranks),
  `31629651069` (4 nodes/480 ranks), and `31629672240` (1-node noise repeat).
  They were dispatched concurrently; the shared-filesystem preparation stage
  remains serialized by the workflow's existing `queue: max` concurrency rule.

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
