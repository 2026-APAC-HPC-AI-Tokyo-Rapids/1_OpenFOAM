# MPI profiling (CrayPAT)

## Method

- These are separate diagnostic runs, not the benchmark runs. Their timings are not used as results.
- Each run used 4 nodes and 512 ranks with the same placement as the benchmarks, and ran 40 `simpleFoam` steps.
- `pat_run -g mpi` (CrayPAT 22.04.0) traced every MPI call of every rank.
- In the final Bonus run, `eu-stack` also sampled the call stacks of 48 ranks, which stops those ranks for short moments.
- `pat-report-*.txt` are the `pat_report` text outputs.

| Report | Configuration | Commit (profiling run) | Actions run | s/step under CrayPAT |
|---|---|---|---|---:|
| `pat-report-basic.txt` | Basic before the mapping: `scotch` with its defaults, unmodified v2512 | `718acb3` | 37176272426 | 3.063 |
| `pat-report-bonus-before.txt` | multiLevel + patch 0001 | `e2730db` + profiling changes (`34f4c5d`) | 37261721692 | 2.874 |
| `pat-report-bonus-final.txt` | final Bonus: multiLevel + patches 0001 – 0004 | `fa4f5b0` + profiling changes (`ba5ba1b`) | 37529785072 | 2.712 |

## Other measurements we used

Each of these ran only in diagnostic runs or outside the timed steps. None of them affects the benchmark numbers.

- **Call-stack samples** (`eu-stack`): 48 ranks of the 4-node diagnostic runs (slow, median and one per NUMA domain). They tell
  which phase of the step each rank is in, and whether it is inside MPI. They pointed to the residual copy in `smoothSolver`
  (patch 0001) and to boundary exchanges whose result is discarded (patch 0003).
- **AMD uProf 5.3** (timer-based hotspots): one rank per NUMA domain, CPU time per function.
- **AMD uProf 5.3, `data_access`** (core hardware counters): the Bonus patches against the same build without them, on 1 node,
  and Basic at 1, 2 and 4 nodes. See the two "Hardware counters" sections below.
- **`/proc` sampler inside the job**: CPU affinity, NUMA page placement, I/O bytes and context switches per rank. It showed that
  the launcher's CPU binding is removed during `MPI_Init`. It also showed that file I/O in the timed steps is about 0.01 % of
  the run time.
- **IMB-MPI1** after the solver in every benchmark run: ping-pong bandwidth and `MPI_Allreduce` latency, as a network baseline
  for each job.
- **OpenFOAM's built-in profiling** (`profiling {}` and the `parProfiling` function object) in a 4-node, 40-step diagnostic run
  of the Basic configuration, with the result of every rank. Wall-clock share of a step for the median rank: p solve (GAMG)
  26 %, U solve 22 %, omega 5 %, k 4 %, function objects 2 %, everything outside the solvers (assembly, gradients, turbulence
  model) 41 %. The computation per rank varies by 6 % (max/median 1.063). Cell counts are balanced within 1 % and do not explain
  it (r = +0.06); the wall faces of a rank explain a little (r = +0.43, 2.8 % of the work); nodes and NUMA domains show no
  systematic difference.

## Reproducing a profile

A profile run is a mode of the normal job scripts (`../README.md`, "How to run it"):

```bash
../run/submit.sh 4 basic craypat    # the current Basic (pat-report-basic.txt was made before the mapping), Basic build
../run/submit.sh 4 bonus craypat    # like pat-report-bonus-final.txt: multiLevel, Bonus build
```

It runs the same Allrun chain with the same placement as a benchmark run, with three differences:

1. `endTime` is 40.
2. One warm-up `simpleFoam -postProcess` runs first. It compiles the coded function objects, so that the profile does not
   contain the compile.
3. `simpleFoam` runs under `pat_run -g mpi` (`perftools-base/22.04.0`, `perftools-preload`). The CrayPAT data goes to the case
   directory, as `simpleFoam+<id>/`.

Then, on a login node, the text report with the tables of the reports here:

```bash
module use /opt/cray/pe/modulefiles
module load perftools-base/22.04.0
pat_report -i <OPENFOAM_DIR>/OpenFOAM/platforms/linux64GccDPInt32Opt/bin/simpleFoam -O program_time,profile,load_balance,load_balance_cm,load_balance_sm,mpi_callers,mpi_sm_callers,mpi_coll_callers,mpi_dest_bytes -o pat-report.txt <case directory>/simpleFoam+*/
```

The profile of `pat-report-bonus-before.txt` needs a build with patch 0001 only: a `PATCH_DIR` that holds only
`../bonus/patches/0001-drop-redundant-solver-copies.patch`.

The three reports here were made through our CI. Its profile runs also recorded rank placement and hardware information, and
the final Bonus run sampled the call stacks of 48 ranks with `eu-stack`. None of these change the solver run that CrayPAT
measures.

We ran both profile modes with these scripts on 2026-10-07 (PBS 25714173 and 25714174 for Basic, then still without the
mapping, and 25714181 and 25714182 for the final Bonus), and made the reports with the `pat_report` command above:

| Per rank | Basic: report here | Basic: re-run | Final Bonus: report here | Final Bonus: re-run |
|---|---:|---:|---:|---:|
| s/step under CrayPAT | 3.063 | 3.065 | 2.712 | 2.701 |
| Process time | 137.57 s | 132.15 s | 118.46 s | 120.45 s |
| Traced MPI time | 26.84 s | 28.78 s | 23.63 s | 22.85 s |
| Global sums (`MPI_Allreduce`) | 12.89 s | 13.08 s | 11.35 s | 10.25 s |
| Halo waits (`MPI_Waitall`) | 10.25 s | 10.36 s | 8.45 s | 7.94 s |
| MPI calls | 1,908,283.4 | 1,908,283.4 | 1,748,358.9 | 1,748,358.9 |

- The number of MPI calls per rank is the same to the last digit. The times differ by up to 10 %; the s/step under CrayPAT
  by 0.4 % at most.
- In the re-run reports, Table 2 names each MPI call after the OpenFOAM function that makes it, in a group `ETC` instead of
  `MPI`: `Foam::PstreamDetail::allReduce<>` holds the `MPI_Allreduce` calls and `Foam::UPstream::waitRequests` the
  `MPI_Waitall` calls. The values above are taken from those rows.

## Results

The values below are means over the 512 ranks, from Tables 1, 2 and 4 of each report. MPI time is the `MPI` group of Table 2. Times are for the whole process, including
the mesh read and solver set-up.

| | Basic | Bonus before 0002 – 0004 | Final Bonus |
|---|---:|---:|---:|
| Process time | 137.57 s | 127.64 s | 118.46 s |
| MPI time | 26.75 s (19.4 %) | 23.39 s (18.3 %) | 23.52 s (19.9 %) |
| Process time − MPI time | 110.83 s | 104.25 s | 94.93 s |
| `MPI_Allreduce` | 12.89 s | 11.01 s | 11.35 s |
| `MPI_Waitall` | 10.25 s | 8.78 s | 8.45 s |
| MPI time of the max / median / min rank | 36.67 / 26.67 / 20.34 s | 34.13 / 23.48 / 15.24 s | 32.15 / 23.55 / 16.53 s |

## Reading

- **Most of the time is computation.** MPI is 18 – 20 % of the process time. Almost all of it is in two calls:
  - `MPI_Allreduce`: 47 – 48 %, mostly the global sums of the linear solvers.
  - `MPI_Waitall`: 36 – 38 %, the halo exchanges at processor boundaries.
- **Much of the MPI time is waiting for other ranks.**
  - The MPI time per rank ranges from about 15 – 20 s up to 32 – 37 s. Ranks that finish their local work early wait for the
    slowest one at the next exchange or reduction.
  - Tuning the MPI library cannot remove that part of the wait. Only better balance, or less work on the slowest ranks, can.
  - The OpenFOAM communication switches we tried gave no gain (`../REPORT.md`, section 10).
- **The Bonus patches shorten the computation and leave MPI as it was.** From "before 0002 – 0004" to the final Bonus, the
  computation drops by 8.9 % (104.25 s to 94.93 s). The MPI time stays at about 23.5 s. That is what the patches aim at: they
  remove passes over large arrays, copies and discarded boundary exchanges. They do not change the communication pattern.
- **Why we treat the solver as memory-bound.** The patches that remove array passes gain most on 1 node and least on 4 nodes. For
  example, 0002 gives −6.4 % on 1 node and −2.3 % on 4 nodes (see `../bonus/README.md`). With fewer nodes, more data per rank has
  to come from DRAM. On 1 node the hardware counters confirm it (below): with the patches, the demand refills from DRAM fall
  by 17 % while the instruction count falls by only 4 %. Across node counts the counters show the same thing from the other
  side: on 4 nodes, the refills from DRAM per cell and step are 30 % fewer than on 1 node (below).

## Hardware counters (AMD uProf, 1 node)

Do the patches move less data? We compared the final Bonus build (patches 0001 – 0004) with the same build without the patches,
in profile runs on 1 node (128 ranks, 40 steps, `multiLevel (2 4 16)`), 2 runs each. AMD uProf 5.3 (`data_access`) sampled the
core counters of one rank per NUMA domain. Rank 0 is left out, because it also writes the output. The values below are for the
computation: the whole process minus the MPI, UCX and `Pstream` libraries, whose time is mostly waiting. Each value is the mean
over the 7 ranks and the 2 runs.

| Counter (per rank, whole run) | Without the patches | With the patches | Change |
|---|---:|---:|---:|
| Time per step under uProf (s) | 13.299 | 11.666 | −12.3 % |
| Cycles | 450.2 G | 401.6 G | −10.8 % |
| Instructions | 162.1 G | 155.5 G | −4.1 % |
| L1 data accesses | 90.8 G | 85.5 G | −5.8 % |
| L1 demand refills from L2 | 0.800 G | 0.798 G | −0.2 % |
| L1 demand refills from L3 | 0.116 G | 0.114 G | −1.7 % |
| L1 demand refills from DRAM | 0.493 G | 0.408 G | −17.2 % |
| L2 accesses from L1 misses, including prefetches | 6.35 G | 5.74 G | −9.6 % |
| IPC (instructions per cycle) | 0.360 | 0.388 | +7.5 % |

- The patches remove little arithmetic (4 % of the instructions) and much data movement (17 % of the demand refills from DRAM).
  This is what "the same math with less data moved" predicts.
- The two runs of each side agree within about 4 % on every counter, and both sides give the same `coefficient.dat`.
- Limits: the counters are sampled and multiplexed (13 events). Refills count demand misses; lines that hardware prefetchers
  bring in are only in the L2 accesses. The memory-controller counters, which would give DRAM bytes, are not available to users
  on ASPIRE-2A.
- Runs: Actions 37580443881 and 37583693730 (without the patches), 37580444029 and 37580455271 (with them).

## Hardware counters across node counts (AMD uProf, Basic, 1 / 2 / 4 nodes)

Why is the parallel efficiency above 1? We profiled Basic before the mapping (`scotch` with its defaults) at 1, 2 and 4 nodes,
40 steps, with AMD uProf 5.3 `data_access` on one rank per NUMA domain (8, 16 and 32 ranks). Each value is the sum over the
profiled ranks divided by the number of ranks, the steps and the cells per rank.

| Per cell and step | 1 node | 2 nodes | 4 nodes | 4 nodes / 1 node |
|---|---:|---:|---:|---:|
| Cycles | 24,235 | 22,860 | 20,418 | 0.843 |
| L1 demand refills from DRAM | 24.6 | 20.7 | 17.1 | 0.697 |
| L1 demand refills from L3 (same CCX) | 5.4 | 6.3 | 9.4 | 1.75 |
| IPC | 0.528 | 0.583 | 0.666 | |

- The cycles per cell and step fall to 0.843 on 4 nodes. The time per cell and step falls to 0.873 (parallel efficiency 1.145),
  the same direction and size.
- By function (the top 30 sampled addresses, 46 – 52 % of the cycles), 4 nodes against 1 node:

  | Function | Cycles | Refills from DRAM |
  |---|---:|---:|
  | `GaussSeidelSmoother::smooth` | 0.715 | 0.301 |
  | `lduMatrix::residual` | 0.687 | 0.404 |
  | `lduMatrix::Amul` | 0.616 | 0.419 |
  | cell-field `multiply` (streaming) | 0.797 | 0.948 |

- Only the sparse-matrix kernels gain. They read and write cell arrays (`psi`, the source, the diagonal) in the order of the
  face addressing. Per rank these arrays are about 4 MB on 1 node, 2 MB on 2 nodes and 1 MB on 4 nodes, against 4 MB of L3
  per core. The face arrays (coefficients and addressing) are about 16 MB per rank even on 4 nodes and fit at no node count.
  Our reading: on 4 nodes the scattered reads of cell arrays come from L3 instead of DRAM. Loops that stream through cell
  fields gain nothing.
- The same 4-node data show where the remaining imbalance between ranks comes from. The computation cycles of the 32 ranks
  follow their refills from DRAM (r = +0.69) and from L2 (r = +0.76), not their instructions (r = −0.09) or their cells
  (r = +0.24). The slowest and the fastest rank execute about the same number of instructions; the slowest reads more than
  twice as many lines from DRAM. Refills from remote DRAM are 0.3 % of all refills.
- uProf wrote the reports on the login node after the job, when the node-local OpenFOAM libraries were gone. We mapped their
  addresses to functions with `nm` of the same libraries from the build that the runs used.
- Runs: Actions 38752334516, 38754565482 and 38756818916.
