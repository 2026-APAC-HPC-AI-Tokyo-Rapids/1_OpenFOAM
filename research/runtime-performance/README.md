# OpenFOAM motorBike runtime profiling

## Purpose

This document records runtime profiling and launch-option tuning for the
OpenFOAM v2606 `simpleFoam` motorBike test on Genkai. The optimization scope is
limited to MPI layout, MPI/OpenFOAM runtime switches, and profiler launch
options. No OpenFOAM source optimization is included.

Raw APS and VTune results are kept outside GitHub artifacts:

```text
~/openfoam-profile/<github-run-id>-<pjm-job-id>/
```

The profile root and every per-run directory have mode `0700`. At the time of
this report the profile tree occupies approximately 2.4 GiB.

## Test configuration

- OpenFOAM v2606, `simpleFoam`, Intel oneAPI 2025.1.3 and Intel MPI 2021.15.
- Two Genkai CPU nodes by default.
- Each node: 2 sockets, 60 physical cores/socket, 120 physical cores and 240
  logical CPUs.
- Inter-node adapter reported by APS: ConnectX-7.
- Decomposition: Scotch.
- Simulation `endTime=3000`, one result write at `Time=3000`.
- Final mesh: 356,630 cells, 1,116,860 faces and 408,877 points.
- The mesh is very small for 240 MPI ranks:
  - 240 ranks: approximately 1,486 cells/rank.
  - 120 ranks: approximately 2,972 cells/rank.
  - 60 ranks: approximately 5,944 cells/rank.

The mesh is regenerated for every Actions run. Solver comparisons use the same
case and simulation time, but wall times should still be interpreted with the
normal run-to-run noise of a shared HPC system.

## Solver timing results

`Solver clock` is the final OpenFOAM `ClockTime`. `Launcher wall` is
`/usr/bin/time` around `mpirun`, so it also includes MPI initialization and
finalization. Instrumented APS/VTune runs are excluded from direct timing
comparisons.

| Run | Nodes | MPI ranks | Setting | Solver clock | Launcher wall | Result |
|---:|---:|---:|---|---:|---:|---|
| #117 | 1 | 120 | Default | 107 s | - | Baseline from the earlier test |
| #122 | 2 | 240 | Default | 105 s | 127.04 s | Two nodes give almost no benefit when the rank count is doubled |
| #123 | 2 | 240 | `allcores:map=scatter` | 104 s | 125.71 s | About 1 s faster; within normal noise |
| #124 | 2 | 240 | `allcores:map=bunch` | 107 s | 128.53 s | Slower than default |
| #125 | 2 | 120 | Default, 60 ranks/node | **56 s** | **63.31 s** | Best completed rank-count result |
| #126 | 2 | 60 | Default, 30 ranks/node | 76 s | 79.55 s | Too little compute parallelism |
| #129 | 2 | 240 | `topoControl=16` | 107 s | 127.30 s | OpenFOAM hierarchical reduction is slower |
| #130 | 2 | 240 | `nPollProcInterfaces=-1` | 114 s | 136.04 s | Readiness polling is about 9% slower |
| #131 | 2 | 240 | Intel MPI collective autotuner | 103 s | 128.89 s | About 2 s faster, but the gain is small |
| #135 | 2 | 90 | Default | Pending | Pending | Rank-count refinement |
| #136 | 2 | 150 | Default | Pending | Pending | Rank-count refinement |
| #137 | 2 | 180 | Default | Pending | Pending | Rank-count refinement |

The major result is not a pinning tweak: reducing the two-node job from 240 to
120 total ranks cuts solver time from 105 to 56 seconds, about 47%. Reducing
further to 60 ranks raises it to 76 seconds. The current optimum is therefore
near 120 ranks, with 90/150/180-rank runs used to refine it.

## APS: why 240 ranks are slow

The full-rank APS runs are #119 (240 ranks) and #133 (120 ranks). Raw data:

```text
~/openfoam-profile/30005026547-6264943/  # 240 ranks
~/openfoam-profile/30007072403-6265018/  # 120 ranks
```

| APS metric | 240 ranks | 120 ranks |
|---|---:|---:|
| Instrumented elapsed time | 179.02 s | 86.62 s |
| Average MPI time | 151.27 s (84.50%) | 51.80 s (59.86%) |
| MPI imbalance | 44.30 s (24.75%) | 15.57 s (18.00%) |
| `MPI_Allreduce` average | 56.04 s | 18.42 s |
| `MPI_Waitall` average | 59.06 s | 12.38 s |
| Inter-node transfer, both directions | 289,023.6 MB | 105,093.1 MB |
| Average DRAM bandwidth | 20.66 GB/s | 29.98 GB/s |
| DRAM bandwidth bound | 14.20% | 46.80% |
| DP vectorization | 23.55% | 20.20% |

At 240 ranks APS classifies the application as MPI-bound. The aggregate
function statistics include approximately:

- 210.6 million `MPI_Allreduce` calls.
- 189.3 million `MPI_Waitall` calls.
- 2.22 billion `MPI_Isend` calls.
- 289 GB transferred between the two nodes.

At 120 ranks the point-to-point call counts are approximately halved and
inter-node traffic falls by about 64%. Aggregate MPI time falls much more
sharply. Once MPI pressure is reduced, DRAM bandwidth becomes a meaningful
secondary constraint.

Rank 0 is atypical. In the 240-rank APS run its MPI fraction is about 51%,
whereas most ranks spend roughly 83-87% in MPI. This makes rank 0 a useful VTune
target for finding actual OpenFOAM compute hotspots, while the other ranks
mostly demonstrate communication and load-imbalance cost.

APS emitted a warning because one statistics stream per node was missing:
ranks 4 and 195 in the 240-rank run, and the analogous two records in the
120-rank run. APS still recognized the correct communicator sizes and produced
consistent high-level results, but exact aggregate call counts should be
treated as slightly underestimated.

## VTune hotspots

The most useful optimized-layout profile is #132: two nodes, 120 ranks, VTune
Hotspots on rank 0.

```text
~/openfoam-profile/30007051832-6265016/hotspots.<host>/
```

VTune measured 62.06 seconds elapsed and 59.26 seconds CPU time on the selected
rank. The leading hotspots are:

| Function | Module | CPU time | Share |
|---|---|---:|---:|
| `PMPI_Allreduce` | Intel MPI | 11.36 s | 19.2% |
| `PMPI_Waitall` | Intel MPI | 5.57 s | 9.4% |
| `Foam::GaussSeidelSmoother::smooth` | `libOpenFOAM` | 3.54 s | 6.0% |
| `ucp_worker_progress` | UCX | 2.84 s | 4.8% |
| `internal_Isend` | Intel MPI | 2.25 s | 3.8% |
| `cellLimitedGrad<...>::calcGrad` | `libfiniteVolume` | 1.40 s | 2.4% |
| `Foam::lduMatrix::residual` | `libOpenFOAM` | 1.11 s | 1.9% |
| `Foam::lduMatrix::Amul` | `libOpenFOAM` | 0.89 s | 1.5% |
| `linearUpwindV<...>::correction` | `libfiniteVolume` | 0.78 s | 1.3% |
| `Foam::fv::gaussGrad<double>::gradf` | `libfiniteVolume` | 0.75 s | 1.3% |

The 240-rank rank-0 profile showed still stronger MPI dominance:
`PMPI_Allreduce` 21.9%, `PMPI_Waitall` 11.3%, and `internal_Isend` 8.3%.
Reducing the rank count lowers all three, while the matrix smoother and
gradient work become more visible.

The HPC Characterization run agrees with APS that vectorization is low
(roughly 20-23% of DP operations), but floating point work is a small fraction
of total uOps and the full 240-rank run is not memory-bandwidth saturated.
Source-level vectorization is therefore not the first optimization target.
At 120 ranks, however, APS reports higher DRAM bandwidth pressure, so memory
locality is the next likely limit after MPI is reduced.

## Runtime tuning guidance

1. Use two nodes and approximately 120 total MPI ranks for this exact 356k-cell
   case. More ranks are not better; 240 ranks nearly doubles solver time.
2. Keep Intel MPI's default process placement unless repeated measurements show
   a stable scatter advantage. `scatter` improved only about 1 second and
   `bunch` was slower.
3. Keep OpenFOAM's default `topoControl=0`. Intel MPI already performs
   topology-aware collectives, and forcing OpenFOAM's three-stage hierarchical
   reduction was slower.
4. Keep `nPollProcInterfaces=0`. Dispatching completed interfaces with `-1`
   slowed this workload by about 9%.
5. Intel MPI autotuning is worth testing only after the rank count is correct.
   The 240-rank improvement was small. Tuning files are topology-specific and
   should only be reused with the same node count, ranks per node, fabric and
   MPI version.
6. For a new case, begin with a rank-count sweep based on cells/rank, then use
   APS to quantify MPI time and imbalance. Run VTune on the most compute-heavy
   rank after identifying it from APS.
7. Store raw profiler data in `~/openfoam-profile`; publish only text/CSV
   summaries through Actions artifacts.
8. If source changes become allowed later, investigate the Gauss-Seidel
   smoother, limited gradient calculation, `lduMatrix` residual/multiply, and
   the very high frequency of global reductions. The current work does not
   modify these algorithms.

Intel documents APS through `I_MPI_STATS`/`aps`, selective MPI-rank profiling
through `mpirun -gtool`, process pinning with
`I_MPI_PIN_PROCESSOR_LIST`, and collective autotuning with
`I_MPI_TUNING_MODE=auto`:

- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-16/other-environment-variables.html>
- <https://www.intel.com/content/www/us/en/docs/vtune-profiler/cookbook/2024-0/profiling-mpi-applications.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-12/environment-variables-for-process-pinning.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-11/autotuning.html>

## Profiling implementation

`scripts/exec-profiler.sh` owns the MPI launcher, profiling collection, timing,
and report generation. `scripts/run-openfoam.pjm` selects one analysis and one
runtime configuration per commit. Comparisons are intentionally performed as
separate commits/Actions runs rather than as multiple trials inside one batch
job.

VTune and APS results remain under `~/openfoam-profile`. Actions artifacts
contain only logs, timing files, and generated summaries.
