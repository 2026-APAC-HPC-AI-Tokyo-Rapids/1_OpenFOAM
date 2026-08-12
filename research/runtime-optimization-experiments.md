# cavity3D-64M runtime optimization experiment ledger

This ledger is updated after every completed experiment or decisive static
investigation.  Timing claims use official valid bench results only.

## Status

- Current phase: infrastructure preparation before Phase 0.
- Current build: existing OpenFOAM v2606 Icx/Intel MPI archive; reuse intended.
- Current production preset: one node, 120 total ranks, Scotch,
  `I_MPI_FABRICS=shm`.
- Active hypothesis: the fixed 120-rank canary configuration underuses two- and
  four-node allocations; full physical-core layouts should dominate before
  smaller MPI runtime adjustments matter.

## Prior evidence admitted to the study

| Evidence | Changed factor | Result | Decision |
|---|---|---|---|
| Actions 256 / run `r-c4bb4bb3c51a6a6724aa7177ea1d01e6` | 1 node, 120 Scotch ranks | VALID, 1.6398 M FVOPS | baseline sample |
| Actions 257 / run `r-fef72f7255e44a077f5fa2b1b115b0df` | 2 nodes, still 120 ranks | VALID, 3.1718 M FVOPS | canary only; not full-core baseline |
| Actions 258 / run `r-c2aef4bc0f5dd083a8790751af269342` | 4 nodes, still 120 ranks | VALID, 4.9488 M FVOPS | canary only; not full-core baseline |
| Actions 277 / run `r-efdfb255f9d7c78e7eb9c7df59bcab5c` | repeat 1 node/120 | VALID, 1.6392 M FVOPS | agrees within 0.04% |
| Actions 278 / run `r-49e4a417a55f2278a211f483d720b391` | VTune rank 0 | VALID profile; DIC 45.8%, Amul 26.1% | locality dominates sampled rank |
| Actions 279 / run `r-6227d22fbc780cd0ad71df88fd19ed2c` | post-merge 1 node/120 | VALID, 1.6270 M FVOPS | baseline sample; about 0.8% below 1.6398 M |

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
