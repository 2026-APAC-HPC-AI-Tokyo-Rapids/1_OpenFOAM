# OpenFOAM motorBike runtime profiling

> Historical record: this campaign predates the Issue #18 migration. The active workload is the pinned v2512 `occDrivAerStaticMesh` task in `benchmark/workload.json`; the motorBike results below are not comparable to it.

## Purpose

This document records runtime profiling and launch-option tuning for the
OpenFOAM v2606 `simpleFoam` motorBike test on Genkai. The optimization scope is
limited to MPI layout, MPI/OpenFOAM runtime switches, and profiler launch
options. No OpenFOAM source optimization is included.

Historical APS and VTune results are kept outside GitHub artifacts:

```text
~/openfoam-profile/<github-run-id>-<pjm-job-id>/
```

New VTune-only profile runs use the purpose-specific location:

```text
/home/pj26000080/share/openfoam-vtune/<run-id>-<pjm-job-id>/rank-<profile-rank>/
```

The shared profile root and every per-run directory have mode `2770`. At the time of
this report the profile tree occupies approximately 3.0 GiB.

## Test configuration

- OpenFOAM v2606, `simpleFoam`, Intel oneAPI 2025.1.3 and Intel MPI 2021.15.
- The current default is one Genkai CPU node with 120 MPI ranks. The earlier
  scaling and profiling campaign below used up to two nodes.
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

## One-node 120-rank MPI tuning

The current production constraint is one node and 120 MPI ranks, one rank per
physical core. Intel MPI 2021.15 did not automatically reduce this job to its
shared-memory-only transport: the baseline debug log reported the `mlx`
libfabric provider even though all ranks were on one node. Explicitly setting
the following in `scripts/run-openfoam.pjm` avoids that unnecessary provider:

```bash
export I_MPI_FABRICS=shm
```

The settings were changed and pushed as separate commits, so every row is a
separate Actions and PJM job. `Launcher wall` includes MPI initialization and
finalization as well as the solver.

| Run | MPI setting | Solver clock | Launcher wall | Result |
|---:|---|---:|---:|---|
| #141 | Intel MPI defaults | 111 s | 120.81 s | Baseline; debug output selected `mlx` |
| #142 | `I_MPI_FABRICS=shm` | **101 s** | **104.45 s** | Fastest SHM-only trial |
| #143 | `I_MPI_PIN_DOMAIN=core`, `I_MPI_PIN_ORDER=scatter` | 105 s | 114.60 s | Same effective CPU list as the default |
| #144 | `I_MPI_PIN_DOMAIN=core`, `I_MPI_PIN_ORDER=compact` | 106 s | 115.96 s | Same effective CPU list as the default |
| #145 | `I_MPI_ADJUST_ALLREDUCE=1` (recursive doubling) | Did not finish | Did not finish | Reached only Time=943 before the 25-minute PJM limit |
| #146 | `I_MPI_ADJUST_ALLREDUCE=9` (Knomial) | 112 s | 120.21 s | Slower than automatic selection |
| #147 | `I_MPI_ADJUST_ALLREDUCE=11` (SHM Knomial preset) | 106 s | 116.53 s | Does not force the transport to SHM |
| #148 | Intel MPI collective autotuning | 107 s | 115.93 s | Autotuning overhead and result are worse than SHM |
| #149 | `I_MPI_FABRICS=shm`, repeat | 107 s | 109.30 s | Confirms the benefit with normal run-to-run variation |
| #150 | SHM plus Knomial Allreduce | 103 s | 105.43 s | Within noise of SHM alone; extra forcing is not justified |
| #151 | SHM-only solver configuration, debug disabled | **101 s** | **103.46 s** | Successful solver verification |
| #152 | SHM applied before every MPI phase | **101 s** | **104.06 s** | Final successful end-to-end verification |

The baseline pinned ranks 0-119 to logical CPUs 0-119. Explicit `core` pinning
produced the same list, so the small timing differences between pinning orders
are noise rather than a different placement. The useful optimization is
transport selection, not pinning.

Moving the SHM setting before all MPI preprocessing commands in #152 reduced
the Actions log-stream interval from 201 seconds in baseline #141 to 165
seconds. Earlier SHM runs that applied the setting only to `simpleFoam` took
185-189 seconds over the same interval. The final placement therefore benefits
`snappyHexMesh`, `topoSet`, and `potentialFoam` as well as the main solver.

For this job, forcing one Allreduce algorithm globally is counterproductive.
OpenFOAM calls Allreduce with different message sizes and contexts, so Intel
MPI's size-dependent automatic selection should remain enabled. Recursive
doubling was especially unsuitable and did not finish within the PJM time
limit. The final configuration therefore sets only `I_MPI_FABRICS=shm`; it
leaves pinning, collective algorithm selection, and collective autotuning at
their defaults.

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
| #134 | 2 | 120 | Intel MPI collective autotuner | 58 s | 64.33 s | Slower than the 120-rank default |
| #135 | 2 | 90 | Default | 68 s | 73.72 s | Too little compute parallelism |
| #136 | 2 | 150 | Default | 55 s | 65.31 s | Solver is close to 120 ranks, but launch overhead is higher |
| #137 | 2 | 180 | Default | 57 s | 71.72 s | Communication overhead is rising |
| #138 | 2 | 135 | Default | 54 s | 64.88 s | Fast solver, but slower launch-to-finish than 120 ranks |
| #139 | 2 | 165 | Default | 53 s | 68.10 s | Fast solver, but significantly higher MPI overhead |
| #140 | 2 | 120 | Final default verification | 56 s | 63.31 s | Reproduced #125 exactly |

The major result is not a pinning tweak: reducing the two-node job from 240 to
120 total ranks cuts solver time from 105 to 56 seconds, about 47%. Reducing
further to 60 ranks raises it to 76 seconds. Higher counts down to 165 can
slightly reduce the solver-only time, but MPI initialization/finalization grows
faster. The 120-rank run has the lowest measured launcher wall time and the
joint-lowest measured end-to-end PJM time. It is therefore the best operational
default.

The Actions log-stream step, which closely covers the complete PJM execution,
measured 272 seconds at 240 ranks, 133 seconds at 120 ranks, 133 seconds at 60
ranks, 138 seconds at 90 ranks, 154 seconds at both 135 and 150 ranks, 171
seconds at 165 ranks, and 177 seconds at 180 ranks. The 60-rank run only ties
120 ranks end-to-end because its slower solver is offset by cheaper startup and
preprocessing; 120 ranks provides much higher solver throughput without
increasing total job time.

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

The corresponding 120-rank aggregate statistics include approximately:

- 96.0 million `MPI_Allreduce` calls.
- 99.6 million `MPI_Waitall` calls.
- 1.13 billion `MPI_Isend` calls.
- 105 GB transferred between the two nodes.

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

1. When restricted to one node, use 120 MPI ranks and set
   `I_MPI_FABRICS=shm`. Intel MPI 2021.15 otherwise selected its `mlx`
   libfabric provider in the measured job. In the earlier unconstrained
   comparison, two nodes with 120 total ranks were still faster, but that is
   outside the current one-node constraint.
2. Keep Intel MPI's default process placement unless repeated measurements show
   a stable scatter advantage. `scatter` improved only about 1 second and
   `bunch` was slower.
3. Keep OpenFOAM's default `topoControl=0`. Intel MPI already performs
   topology-aware collectives, and forcing OpenFOAM's three-stage hierarchical
   reduction was slower.
4. Keep `nPollProcInterfaces=0`. Dispatching completed interfaces with `-1`
   slowed this workload by about 9%.
5. Intel MPI autotuning is worth testing only after the rank count is correct.
   It improved the poor 240-rank layout by about 2 seconds, but slowed the
   120-rank layout from 56 to 58 seconds. Tuning files are topology-specific
   and should only be reused with the same node count, ranks per node, fabric
   and MPI version.
6. For a new case, begin with a rank-count sweep based on cells/rank, then use
   APS to quantify MPI time and imbalance. Run VTune on the most compute-heavy
   rank after identifying it from APS.
7. Store full VTune result directories in `/home/pj26000080/share/openfoam-vtune`; publish validated
   text/CSV summaries through the profile artifact and metrics paths.
8. If source changes become allowed later, investigate the Gauss-Seidel
   smoother, limited gradient calculation, `lduMatrix` residual/multiply, and
   the very high frequency of global reductions. The current work does not
   modify these algorithms.

Intel documents APS through `I_MPI_STATS`/`aps`, selective MPI-rank profiling
through `mpirun -gtool`, process pinning with
`I_MPI_PIN_PROCESSOR_LIST`, and collective autotuning with
`I_MPI_TUNING_MODE=auto`:

- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-15/communication-fabrics-control.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-16/other-environment-variables.html>
- <https://www.intel.com/content/www/us/en/docs/vtune-profiler/cookbook/2024-0/profiling-mpi-applications.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-12/environment-variables-for-process-pinning.html>
- <https://www.intel.com/content/www/us/en/docs/mpi-library/developer-reference-linux/2021-11/autotuning.html>

## Profiling implementation

Push-triggered runs are always benchmarks and launch the solver without an
external profiler. Manual workflow dispatches select either `bench` or
`profile`; profile runs attach VTune hotspots collection to the MPI rank chosen
by the `profile_rank` workflow input (default 0) for a bounded window without
changing the source or build archive. Rank 0 remains useful for compute-hotspot
discovery, but representative communication conclusions require additional
interior and cross-node-boundary ranks because APS already showed rank 0 is
atypical.

Full VTune results remain under `/home/pj26000080/share/openfoam-vtune`. The validated report,
collection status, JSON fact, and bounded Actions summary are retained in the
profile artifact set and experiment-metrics stream. VTune executable identity
and version are owned once by the build-provision observation.
