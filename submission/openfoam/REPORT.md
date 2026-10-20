# Making the same math faster: OpenFOAM `occDrivAerStaticMesh` on NSCC ASPIRE-2A

Technical report, 2026 APAC HPC-AI Competition, HPC track — Tokyo Rapids with RIKEN

This report explains our OpenFOAM submission: what limited the speed, what we changed, why each change keeps the computation,
and how we checked every claim. [`README.md`](README.md) is the short version, with the commands to run it again.
The figures are in `figures/`; the raw logs are in `results/`, `scaling/`, `analysis/` and `bonus/`.

## 1. Summary

On 4 ASPIRE-2A nodes, the official case takes 3.65 s per step with the case defaults on our own build of v2512. Our
**Basic** submission, unmodified OpenFOAM v2512, takes **2.898 s per step**, 21 % less. Our **Bonus**, which adds four
source changes that keep every arithmetic operation, takes **2.599 s**, 29 % less, with a `coefficient.dat` bit-identical to
the unpatched run. All three use the same build, scripts and measurement, so the differences are our optimisations. The
spread between repeated jobs falls from 8 % to 0.2 %.

| 4 nodes, 150 steps | s/step | Against our baseline |
|---|---:|---:|
| Our baseline (case-default `hierarchical`, launcher binding only) | 3.650 | — |
| **Basic** | **2.898** | **−20.6 %** |
| **Bonus** | **2.599** | **−28.8 %** |

For reference, the organisers' vanilla runs on the same machine took 3.30 s per step with `scotch`. They use the site build,
the default MPI transport and no binding, so we show them as context, not as the comparison (section 5).

What we found and did:

1. **The CPU binding is lost at `MPI_Init`.** On ASPIRE-2A, the binding that the launcher sets is removed from outside every
   process while MPI initialises. The ranks then move between cores, and most of their memory ends up on other NUMA domains
   (median 9 % local). We put the placement back with the job script alone: −11 %.
2. **Every rank gets the same work.** The case-default `hierarchical` split cuts thin slabs, and the ranks next to the car get
   more work. `scotch` cuts compact blocks (−10.5 %). Mapping the `scotch` split onto the sockets and NUMA domains of each
   node cuts the faces between nodes by 23 % (−0.7 %).
3. **After that, memory bandwidth sets the speed.** We cannot read the memory-controller counters, so we moved the ranks
   instead: half the cores on all memory channels change nothing, while the same ranks on half the channels make a step
   2.2× slower, as much as the bandwidth drops.
4. **Bonus: the same arithmetic, fewer bytes.** A node-aware `multiLevel` split and four source changes remove copies, the
   second and third pass over the same matrix, boundary values that nobody reads, and temporary face fields. The results are
   bit-identical, every solver log line is identical, and the cores load 17 % fewer cache lines from DRAM: −10.3 % against
   Basic.
5. **The scaling is explained.** The parallel efficiency is 1.15 on 4 nodes because the cell arrays that the sparse-matrix
   kernels gather fit in L3 there: per cell and step, a rank needs 30 % fewer refills from DRAM than on 1 node.
6. **It can be reproduced.** The submitted scripts rebuild everything from public sources and run with plain `qsub`. Running
   them again gave a byte-identical `coefficient.dat` at every node count.

## 2. The task

The case is the official OHC-1 `occDrivAerStaticMesh` (65,334,765 cells), solved with `simpleFoam` (steady RANS, k-ω SST)
through the case's `Allrun` chain: `decomposePar`, `restore0Dir`, `renumberMesh`, `potentialFoam`, `applyBoundaryLayer` and
`simpleFoam`. The case uses `fvSolution.fixedIter` and `controlDict.noWrite`, and runs 40 / 80 / 150 steps on 1 / 2 / 4 nodes.
The scored quantity is the `Average wall-clock time per time step` of the 4-node run (steps 2 to 150); the organisers re-run
our Basic submission and rank it among the teams on the same machine.

`fvSolution.fixedIter` fixes every iteration count: for `p`, 12 GAMG V-cycles with 35 PCG iterations on the coarsest level;
for each of the three components of `U`, 15 Gauss–Seidel sweeps; for `k` and `omega`, 8 each. Every step therefore does the
same work. A mean over the steps is a fair measure, and a 40-step profile run represents a 150-step run.

The rules allow two tiers. **Basic** runs the unmodified official v2512 source and tunes only built-in controls: the build,
the job scripts and rank placement, and the decomposition (`hierarchical` or `scotch`, with that method's settings).
**Bonus** may change the source or use other decompositions, if the team proves that the result is the same computation
(Cd from `coefficient.dat` bit-identical to its own unchanged baseline, or within ±0.5 %, at 1, 2 and 4 nodes).

## 3. The machine

| | ASPIRE-2A standard CPU node |
|---|---|
| Processors | 2 × AMD EPYC 7713 (Zen 3), 64 cores each, 2.0 GHz base |
| Memory | 512 GB DDR4-3200 on 16 channels: 409.6 GB/s peak, about 290 GB/s measured (STREAM triad) |
| Caches and NUMA | 8 NUMA domains of 16 cores; 32 MB of L3 per 8-core CCX (4 MB per core) |
| Network | HPE Slingshot-10 (100 Gb/s), dragonfly topology |
| Software | Cray PE: GCC 11.2 (`PrgEnv-gnu/8.3.3`), Cray MPICH 8.1.15, PBS Pro, PALS launcher |

STREAM saturates the node's bandwidth with one core per L3 (16 threads: 289 – 291 GB/s); with all 128 cores it gives
269 – 273 GB/s. Users cannot read the memory-controller counters or IBS (`perf_event_paranoid=2`); the core counters are
available.

We chose ASPIRE-2A because OpenFOAM writes many files. One build is about 36,000 files, and every decomposed case adds
thousands more. Gadi allows 0.2 M files and 1 TB per project; ASPIRE-2A allows 200 M files and 100 TB.

All our runs use 128 MPI ranks per node, one per physical core, no SMT, and exclusive nodes.

## 4. How we measured

**Benchmark runs and profile runs are separate.** Every number in this report comes from benchmark runs without a profiler,
read with the official metric. Profilers change a step by −1 % to +6 %, so profiles answer only "where" and "why", in
separate runs:

| Tool | Runs | Question it answers |
|---|---|---|
| Official metric | every benchmark run | How long does a step take? |
| IMB-MPI1 | after the solver, in every benchmark run | How fast is the network between these nodes? |
| CrayPAT (`pat_run -g mpi`) | profile runs, 4 nodes, 40 steps | Which MPI calls take the time, on each rank? |
| OpenFOAM profiling | profile runs | Which solver stage takes the time, on all 512 ranks? |
| AMD uProf | profile runs | Which functions use the CPU? Core hardware counters |
| `/proc` sampler in the job | profile runs | Is each rank on its own core? Where is its memory? |

**Every change is compared with a control in the same period.** Candidate and control jobs run alternately, at least 3 of
each on 4 nodes, and a change is kept only if every job with it was faster than every job without it. Every change we
adopted meets this rule on 4 nodes. We started with a 1 % minimum as well, and dropped it once we knew the run-to-run spread:
in early October, 29 pinned `scotch` jobs on 4 nodes had a standard deviation of 0.19 %, and 72 of 81 October jobs in
repeated configurations lie within ±0.5 % of their configuration's median. Single jobs can still go wrong — two September jobs were 84 % and 91 % slower
than usual — so we never decide from one job.

## 5. The baseline, and what slows it down

The baseline is our own build of v2512 with the case's defaults: the `hierarchical` split (16 8 1) / (16 8 2) / (16 8 4) on
1 / 2 / 4 nodes, 128 ranks per node, and the launcher's binding (`mpiexec --cpu-bind depth`), as the site recommends. It uses
the same build, scripts and measurement as everything after it, so every later change is measured against it. The
organisers' reference runs, in the last two columns, are context only: they use the site module, the default MPI transport
and no binding.

| Nodes (steps) | Baseline s/step (jobs) | Spread | Organisers, `hierarchical` | Organisers, `scotch` (mean) |
|---|---:|---:|---:|---:|
| 1 (40) | 14.57 (6) | 5.5 % | 14.67 | 14.49 |
| 2 (80) | 7.43 (3) | 4.0 % | 7.12 | 7.31 |
| 4 (150) | 3.65 (3) | 7.8 % | 3.415 | 3.30 |

![Baseline scaling against the organisers' reference](figures/fig23_baseline_scaling.png)

*Figure 1. Baseline: linear scaling from 1 to 4 nodes (efficiency 1.00), but up to 8 % apart between jobs of the same setup.
It is 7 % slower than the organisers' `hierarchical` run on 4 nodes. We think the lost binding (below) is why, but the build
and the MPI transport also differ, so we have not isolated it.*

The profiles of the 4-node baseline show one chain of causes (Figure 2):

1. **The binding is lost at `MPI_Init`.** During the solve, none of the 512 ranks was bound to its own core: every rank was
   allowed on all 256 CPUs of its node. The median rank had 9 % of its memory pages on its own NUMA domain, about what random
   placement over 8 domains gives (12.5 %). The binding requested at launch had been removed while MPI initialised.
2. **The computation becomes uneven.** The computation per rank (time outside MPI) ranged from 54 to 115 s over 40 steps;
   the slowest rank took 1.46 times the median.
3. **Everyone waits.** MPI took 46 % of the time; 55 % of that was `MPI_Waitall` and 35 % `MPI_Allreduce`, the calls that
   wait for other ranks. Every solver iteration exchanges halo values and takes a global sum, so a rank sends about 14,000
   messages and joins about 1,600 global sums per step. Whenever one rank is slow, the other 511 wait.

![Binding lost, uneven computation, waiting](figures/fig24_baseline_chain.png)

*Figure 2. What slows the baseline down, from `/proc`, OpenFOAM's own profiling and CrayPAT (4 nodes, 40 steps).*

The MPI profile of the same 4-node baseline (CrayPAT, `pat_run -g mpi`, 512 ranks, 40 steps) gives the three most used MPI
calls by number of calls and by CPU time. Values are per rank, the mean of the 512 ranks; the totals over all 512 ranks
are in brackets.

| | Most calls | Calls per rank (total) | Most CPU time | Seconds per rank (total) |
|---|---|---:|---|---:|
| 1 | `MPI_Isend` | 566,107 (289.8 M) | `MPI_Waitall` | 43.1 (22,069) |
| 2 | `MPI_Irecv` | 566,107 (289.8 M) | `MPI_Allreduce` | 27.6 (14,140) |
| 3 | `MPI_Test` | 563,646 (288.6 M) | `MPI_Bcast` | 2.5 (1,289) |
| All MPI | | 1,815,336 (929.5 M) | | 78.3 (40,069) |

The most frequent calls are the non-blocking halo exchange with the neighbouring subdomains, 93 % of all MPI calls. The
time goes to the calls that wait for other ranks: `MPI_Waitall` and `MPI_Allreduce` take 90 % of the MPI time. It is
waiting, not transfer: the MPI time per rank ranges from 35 to 112 s, while the cell counts are equal within 0.002 %.

The data exchanged is not the bottleneck. Cutting the faces between nodes by 92 % or raising the network bandwidth by 55 %
did not make a step faster (section 10).

## 6. Basic: placement and decomposition

### 6.1 Putting the binding back (−11 %)

Linux places a memory page on the NUMA domain of the core that first writes it, and does not move it later. A rank that is
not on its own core when it allocates its mesh and fields keeps that data in remote memory for the whole run. The fix needs
both the memory and the CPU placement, and only the job script:

- Each rank starts through `run/exec-local-numa.sh`, which runs `numactl --membind=<the NUMA domain of its core>`. A memory
  policy set before `exec` belongs to the process, so `MPI_Init` does not remove it.
- One watcher per node (`run/keep-rank-affinity.sh`) puts the main thread of every `simpleFoam` process back on the core of
  its local rank with `taskset`, as soon as the process appears. The PBS output reports `bound=128/128` for every node.

Each half alone is not enough. With `scotch` on 4 nodes, re-pinning only the CPUs gave 3.47 s/step, because the data
allocated in the first 12 – 16 seconds stayed remote; binding only the memory gave 4.38, because the ranks then ran on other
domains' cores; both together gave 2.92. With the case-default split, pinning took a step from 3.670 to 3.257 s (−11.2 %,
3 jobs each, same period). That comparison pinned with an `LD_PRELOAD` interposer right after `MPI_Init`, which gives the
same speed as `numactl` and `taskset`; the rules count `LD_PRELOAD` as Bonus work, so Basic uses `numactl` and `taskset`.

![Placement variants](figures/fig06_pinning.png)

*Figure 3. Placement variants on 4 nodes with `scotch`. Only the variants that place both the memory and the CPU of every
rank from the start reach 2.91 – 2.92 s/step; the others are 16 – 19 % slower on average, and binding only the memory 50 %.*

The organisers' ASPIRE-2A notes do not mention the binding, and their reference runs are not pinned. Their 5 vanilla `scotch`
jobs on 4 nodes range from 3.19 to 3.58 s/step, a spread of 12 %.

### 6.2 `scotch` instead of `hierarchical` (−10.5 %)

`hierarchical` cuts the domain into slabs along the coordinate axes. Ranks whose slabs hold much of the car's surface get many
wall faces and more work: the computation per rank varied by 1.16 (slowest / median, CrayPAT, both pinned). `scotch` cuts
compact blocks: the faces between subdomains fall by 32 % (4.31 M to 2.93 M), the imbalance falls to 1.06, and the median
rank's `MPI_Waitall` time halves (18.7 s to 9.4 – 10.8 s).

| Nodes | `hierarchical` (3 jobs) | `scotch` (3 jobs) | Change |
|---:|---:|---:|---:|
| 1 | 13.5229 | 13.3459 | −1.3 % |
| 2 | 6.5282 | 6.3679 | −2.5 % |
| 4 | 3.2574 | 2.9145 | −10.5 % |

![hierarchical and scotch subdomains](figures/decomposition-subdomains-baseline-vs-basic.png)

*Figure 4. The 512 subdomains on 4 nodes: case-default `hierarchical` (left) and `scotch` (right).*

One early `scotch` job took 5.03 s/step and made us reject `scotch` at first. Alternated jobs in one period reversed that
decision; since then we never decide from a single job.

### 6.3 Mapping the split onto the node (−0.7 %)

By default Scotch partitions onto a flat set of parts. Through `scotchCoeffs`, the settings of the `scotch` method that Basic
allows, we give it the shape of a node instead (Scotch's tree-leaf target):

```
scotchCoeffs
{
    domains         (2 4 16);
    domainWeights   (0.125 0.0625 0.015625);
    strategy        "m{vert=10240,low=r{job=t,map=t,poli=S,bal=0.010000,sep=…}x{bal=0.010000}f{bal=0.010000,move=80}";
}
```

- `domains (2 4 16)` is 2 sockets, 4 NUMA domains per socket and 16 cores per domain. On 2 and 4 nodes, OpenFOAM's
  `scotchDecomp` adds the nodes as the top level with weight 1. `domainWeights` are the relative costs of a link at each
  level.
- `strategy` is Scotch 6.1's default mapping strategy for 512 parts with imbalance 0.01, plus the terms Scotch adds when
  balance is enforced, which end with an exact balancing pass `x{bal=0.01}`. The full string is in `dicts/decomposeParDict`.

| 4 nodes, from `decomposePar` | `scotch` defaults | Mapped onto the node | Change |
|---|---:|---:|---:|
| Faces between subdomains | 2,927,022 | 3,022,295 | +3.3 % |
| … between nodes | 337,324 | 260,748 | −22.7 % |
| … between sockets | 492,282 | 387,196 | −21.3 % |
| … between NUMA domains | 1,047,405 | 938,403 | −10.4 % |
| Neighbours of a subdomain (max) | 66 | 40 | |
| Largest subdomain against the mean | 1.0107 | 1.0100 | |

On 4 nodes, five alternated jobs on each side gave 2.897638 s/step (2.894442 – 2.899615) against 2.917726
(2.911949 – 2.925723): −0.69 %. Every job with the mapping was faster than every job without it, and the jobs varied less
(standard deviation 0.0019 against 0.0065 s/step). On 1 and 2 nodes the mapping changes little (+0.00 % and +0.08 %).

### 6.4 The Basic result

| 4 nodes | Baseline | Basic |
|---|---:|---:|
| s/step (jobs) | 3.650 (3) | **2.898 (5)**: −20.6 % |
| Spread between jobs | 7.8 % | 0.18 % |
| Ranks on their own core during the solve | 0 of 512 | 128 of 128 on every node |
| Memory on the rank's own NUMA domain (median) | 9 % | 58 % |
| Computation per rank, slowest / median* | 1.46 | 1.06 |
| MPI share of the time* | 46 % | 19 % |

\* Profiles of Basic before the mapping of section 6.3, which changes a step by 0.7 %.

After pinning, 58 % rather than 100 % of a rank's pages are local. We think the rest are pages that several ranks share, such
as shared libraries and MPI's shared buffers, which can live on only one domain; we have not verified this.

| Nodes (steps) | Basic s/step (jobs) | Spread | Cd at the last step | Against our baseline |
|---|---:|---:|---|---:|
| 1 (40) | 13.364504 (3) | 0.04 % | 0.43957921531324928 | −8.3 % |
| 2 (80) | 6.371748 (3) | 0.16 % | 0.33409590047442955 | −14.2 % |
| 4 (150) | 2.897638 (5) | 0.18 % | 0.29301591596528520 | −20.6 % |

![The path on 4 nodes](figures/fig16_journey.png)

*Figure 5. Each change on 4 nodes, against its own control in the same period. The changes are separate experiments and are
not added up.*

## 7. What limits the speed after Basic

To find out whether the cores or the memory system set the speed, we changed only where the ranks run (4 nodes, 150 steps,
2 jobs each, every rank pinned with its memory on its own domain):

- **full128**: 128 ranks per node, as submitted.
- **spread64**: 64 ranks per node, 4 per L3, on all 16 L3s and all 16 memory channels: half the cores.
- **packed64**: the same 64 ranks and the same split, 8 per L3, on 8 L3s and 8 channels: half the memory system.

| s/step | full128 | spread64 | packed64 | spread64 / full128 | packed64 / spread64 |
|---|---:|---:|---:|---:|---:|
| Basic (before the mapping) | 2.920 | 2.887 | 6.347 | 0.99 | 2.20 |
| Bonus without the patches | 2.869 | 2.874 | 6.321 | 1.00 | 2.20 |
| Bonus | 2.595 | 2.649 | 5.598 | 1.02 | 2.11 |
| Triad bandwidth per node, same nodes | 274 GB/s | 279 GB/s | 125 GB/s | | 0.45 |

![Cores or memory](figures/fig19_cores_or_memory.png)

*Figure 6. Halving the cores changes nothing; halving the memory channels slows a step as much as the bandwidth drops.*

If the computation or the latency of each core's memory requests set the speed, halving the cores would have doubled the time.
It changed by −1 % to +2 %. Halving the channels made a step 2.11 – 2.20 times slower, while the triad bandwidth on the same
nodes fell by 2.22 times. The step time follows the memory bandwidth. The same experiment halves the L3 too, so it cannot
separate DRAM bandwidth from L3 capacity; both are the memory side.

The arithmetic intensity agrees. The sparse-matrix sweeps that dominate the step (Gauss–Seidel, the residual, the
matrix–vector product) do about 4 floating-point operations per internal face, for which they read two coefficients (16 B),
an address (4 B) and cell values: 30 – 40 B in all, about 0.1 flop per byte. A node needs about 14 flop per byte to keep its
cores busy (128 cores × 2.0 GHz × 16 flop ≈ 4.1 TFLOP/s against 290 GB/s). The sweeps sit far under the bandwidth roof of a
roofline model, and the cores mostly wait: the measured IPC is 0.4 – 0.7. Compiler flags, another compiler and profile-guided
optimisation all changed a step by at most 0.13 % (section 10).

We cannot draw a measured roofline on ASPIRE-2A. The DRAM traffic in bytes needs the memory-controller counters, which users
cannot read, and the core counters count only demand refills, not the lines that the hardware prefetchers bring in.

So the next step has to move fewer bytes.

## 8. Bonus: the same arithmetic with fewer bytes

The Bonus uses the same build flags, runtime and placement as Basic. Two things change: the decomposition, and four source
patches applied to the official v2512 tree before the build. `bonus/README.md` has the full description, and `bonus/patches/`
the patches.

### 8.1 A split that follows the machine

`multiLevel` decomposes level by level with `scotch` at every level: nodes, then the 2 sockets of a node, then the 4 NUMA
domains of a socket, then the 16 cores of a domain (`(4 2 4 16)` on 4 nodes, `(2 2 4 16)` on 2, `(2 4 16)` on 1). It is a
different decomposition method, so it is Bonus work. Against `scotch` with its defaults, the faces between nodes fall by 38 %,
between sockets by 34 % and between NUMA domains by 26 %, and the total by 3.9 % (2.81 M). Without the source patches it is
1.54 % faster on 4 nodes (4 jobs each).

### 8.2 Four source changes

The profiles (call-stack samples of 48 ranks, uProf hotspots) showed where the step reads data that it does not need.

| Change | What it removes | Why the result is the same |
|---|---|---|
| No copies in the solvers (`0001`) | `smoothSolver` built each residual in a new field and copied it; GAMG copied the source and then subtracted | The same function computes the same residual in place; `source − A·psi` is the same subtraction per cell |
| U components in one pass (`0002`) | Gauss–Seidel read the shared matrix of `U` three times, once per component | The components are independent; each sees the same operations in the same order |
| No unused boundary updates (`0003`) | Six callers built boundary values of a surface integral, exchanged them across processors and used only the cell values | The cell values come from the same loop; only values nobody reads are skipped |
| Fused face loops (`0004`) | Interpolated face fields and product fields built before every summation | The same face expressions are evaluated inside the summation loop, in the same face order |

![U components in one pass](figures/fig25_u_in_one_pass.png)

*Figure 7. The second change: the three components of `U` share one matrix, so one pass over it updates all three.*

### 8.3 Proof that it is the same computation

We built the pre-change baseline that the rules require: the same `multiLevel` split, rank counts and node counts, with the
four patches removed. At 1, 2 and 4 nodes, the Bonus `coefficient.dat` is byte-identical to that baseline's (SHA-256
`36d35283…`, `2a49a26d…`, `8952a056…`). Because the iteration counts are fixed, an error in a residual or in the continuity
error would not show in `coefficient.dat`, so we compared the solver logs too: every residual (16 digits), every iteration
count, the continuity errors and the bounding of `k` and `omega` are identical in all 371, 771 and 1,475 lines. Only host
names, paths, dates and timings differ. Each patch was also checked on its own against the configuration just before it.

### 8.4 Results

| Nodes (steps) | Basic | Bonus | Bonus against Basic | `coefficient.dat` against the pre-change baseline |
|---|---:|---:|---:|---|
| 1 (40) | 13.364504 (3 jobs) | 11.668460 (3 jobs) | −12.69 % | bit-identical |
| 2 (80) | 6.371748 (3 jobs) | 5.640683 (3 jobs) | −11.47 % | bit-identical |
| 4 (150) | 2.897638 (5 jobs) | 2.599353 (3 jobs) | −10.29 % | bit-identical |

Each change against the configuration just before it, in the same period (4 nodes: 3 – 4 jobs each; most 1- and 2-node values
are single jobs):

| Change | 1 node | 2 nodes | 4 nodes |
|---|---:|---:|---:|
| `multiLevel` against `scotch` with its defaults | −0.45 % | −0.38 % | −1.54 % |
| + no copies in the solvers | −2.19 % | −2.94 % | −3.39 % |
| + U components in one pass | −6.39 % | −4.13 % | −2.29 % |
| + no unused boundary updates | −1.40 % | −1.88 % | −1.31 % |
| + fused face loops | −2.88 % | −2.29 % | −2.82 % |

### 8.5 Why the changes help

**Hardware counters, 1 node.** AMD uProf (`data_access`) on one rank per NUMA domain, the final Bonus build against the same
build without the patches, 2 jobs each, computation only (MPI, UCX and `Pstream` left out):

| Per rank, whole run | Without the patches | With the patches | Change |
|---|---:|---:|---:|
| Cycles | 450.2 G | 401.6 G | −10.8 % |
| Instructions | 162.1 G | 155.5 G | −4.1 % |
| L1 data accesses | 90.8 G | 85.5 G | −5.8 % |
| L1 demand refills from DRAM | 0.493 G | 0.408 G | −17.2 % |
| L2 accesses, including prefetches | 6.35 G | 5.74 G | −9.6 % |
| IPC | 0.360 | 0.388 | +7.5 % |

The patches remove little arithmetic (4 % of the instructions) and much data movement (17 % of the refills from DRAM).

![Counters with and without the patches](figures/fig17_counters.png)

*Figure 8. The same math with less data moved: cycles follow the DRAM refills, not the instructions.*

**CrayPAT, 4 nodes.** From the first patch alone to the final Bonus, the computation per rank falls from 104.2 to 94.9 s
(40 steps) while the MPI time stays at about 23.5 s: the patches shorten the computation and leave the communication as it was.

**Less memory per core, more gain.** In the placement experiment of section 7, the patches gain 7.9 % on all 16 channels and
11.4 % on 8 channels. They help most where bandwidth is scarcest, which is what removing memory traffic predicts. They also
gain most on 1 node (U in one pass: −6.4 % on 1 node, −2.3 % on 4), where each rank holds four times more data.

## 9. Scaling

| Nodes | Baseline | Efficiency | Basic | Efficiency | Bonus | Efficiency |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 14.57 | 1.00 | 13.365 | 1.000 | 11.668 | 1.000 |
| 2 | 7.43 | 0.98 | 6.372 | 1.049 | 5.641 | 1.034 |
| 4 | 3.65 | 1.00 | 2.898 | 1.153 | 2.599 | 1.122 |

![Before and after, 1 / 2 / 4 nodes](figures/fig22_before_after_scaling.png)

*Figure 9. Faster at every node count; the parallel efficiency of Basic rises from 1.00 to 1.15.*

The efficiency above 1 comes from the caches. We profiled Basic (before the mapping) at 1, 2 and 4 nodes with uProf
(`data_access`, one rank per NUMA domain) and normalised by the number of ranks, steps and cells per rank:

| Per cell and step | 1 node | 2 nodes | 4 nodes | 4 nodes / 1 node |
|---|---:|---:|---:|---:|
| Cycles | 24,235 | 22,860 | 20,418 | 0.843 |
| L1 demand refills from DRAM | 24.6 | 20.7 | 17.1 | 0.697 |
| L1 demand refills from L3 (same CCX) | 5.4 | 6.3 | 9.4 | 1.75 |

The cycles per cell fall to 0.843 on 4 nodes; the time per cell falls to 0.873 (efficiency 1.145 for this configuration).
The gain is in the sparse-matrix kernels, which read and write cell arrays in the order of the face addressing: from 1 to
4 nodes their refills from DRAM fall to 0.30 (Gauss–Seidel), 0.40 (residual) and 0.42 (matrix–vector product), while a loop
that streams through cell fields stays at 0.95. Those cell arrays are about 4 MB per rank on 1 node, 2 MB on 2 nodes and
1 MB on 4 nodes, against 4 MB of L3 per core. The face arrays (about 16 MB per rank even on 4 nodes) fit at no node count.

The same counters explain most of the imbalance that is left. On 4 nodes, the computation cycles of 32 ranks follow their
refills from DRAM (r = +0.69) and from L2 (r = +0.76), not their instructions (r = −0.09) or their cells (r = +0.24): the
slowest and the fastest rank execute about the same number of instructions, but the slowest reads more than twice as many lines
from DRAM. How well each subdomain's data fits in cache sets its speed.

## 10. What did not help

| Idea (tier) | Result, 4 nodes | Why it did not help |
|---|---|---|
| `-march=znver3`, AOCC 5.0, `-O2`, LTO (Basic) | within ±0.1 % | The loops wait on memory, not on instructions |
| GCC profile-guided optimisation (Basic) | +0.13 % (+0.08 % on 1 node), Cd bit-identical | The same |
| Default OFI transport with the organisers' workarounds (Basic) | +0.77 % (3 v 3), +0.50 % (1 v 1); same Cd, no SIGBUS | Not faster than UCX |
| UCX over RC instead of UD between nodes | −0.01 % (Basic), −0.16 % (Bonus), 4 v 4 | IMB bandwidth rose 55 %, but a step does not wait on transfers |
| OpenFOAM communication switches (`topoControl`, `nbx.tuning`, `pbufs.tuning`) | no gain; `commsType scheduled` crashed in GAMG | MPI time is waiting for the slowest rank |
| Rank reordering (`MPICH_RANK_REORDER_METHOD=3`) | +0.1 %, with 92 % fewer faces between nodes | Fewer bytes between nodes do not shorten the wait |
| GAMG coarsest level on fewer ranks (Bonus) | −0.25 % to +4.95 % | 81 % of the global sums, but about 0.6 % of the time |
| Weighted cells (×2, ×12), METIS with two constraints (Bonus) | +1.5 % to +6.1 % | Uneven cell counts, or 18 % more faces between subdomains |
| glibc `malloc` thresholds (Basic) | −0.4 % (3 jobs) | Too small to separate from the spread with 3 jobs; not re-tested |
| SMT, 2 ranks per core (Basic) | about 5.7× slower | Stalls of minutes; cause not isolated |
| Overlapping halo exchange with computation | under 1 % available (call-stack samples) | Led to skipping the unused exchanges instead (`0003`) |
| File I/O in the timed steps | about 0.01 % of a step | Not a factor |

Two further numbers from the profiles support the table. One 8-byte global sum over 512 ranks takes about 12 µs, so the
1,600 global sums of a step cost about 0.02 s, under 1 % of a step; the rest of the MPI time is waiting. And a rank's wait in
`MPI_Waitall` follows its own computation (R² = 0.77), not its number of neighbours. Interrupt handling takes 0.8 % of every
core's time; changing that needs root.

## 11. Correctness and the drag coefficient

At 40, 80 and 150 steps the flow has not converged, and Cd depends on the decomposition. The organisers' notes give 0.7 %,
3.0 % and 3.5 % between `hierarchical` and `scotch`.

| Steps | OHC-1 values | Baseline (`hierarchical`) | `scotch` defaults | **Basic** (mapped `scotch`) | Bonus (`multiLevel`) |
|---:|---|---:|---:|---:|---:|
| 40 | 0.433 – 0.436 | 0.43305 | 0.43599 | **0.43958** | 0.43828 |
| 80 | 0.334 – 0.345 | 0.33733 | 0.32714 | **0.33410** | 0.32286 |
| 150 | 0.284 – 0.292 | 0.27356 | 0.28405 | **0.29302** | 0.29139 |

- Every column except the Bonus uses unmodified source; the Bonus is bit-identical to its unmodified baseline (section 8.3).
  The mapping moves Cd by +0.8 %, +2.1 % and +3.2 % from `scotch` with its defaults, within what the organisers report for a
  change of method.
- With the same decomposition, our Cd at 150 steps (0.284049, `scotch` defaults) differs from the organisers' (0.283983) by a
  relative 2.3 × 10⁻⁴. With the site module, our scripts and the same decomposition, we got their value exactly
  (0.28398300763231610). The difference comes from our build, which links AMD's math library, not from the method.
- Every job of the same configuration and node count produced a byte-identical `coefficient.dat`.

## 12. Reproducibility

The scripts in `build/` and `run/` do exactly what our measured runs did to the case and to the processes, in the same order
and with the same flags; they leave out only what measured or checked (placement records, `ldd` checks, an IMB test after the
solver). We re-ran them twice from the public sources, exactly as `README.md` describes:

| Configuration | Nodes | PBS jobs (prepare, solve) | s/step | Recorded mean | Change | `coefficient.dat` |
|---|---:|---|---:|---:|---:|---|
| Basic (2026-10-16) | 1 | 25838142, 25838143 | 13.413150 | 13.364504 | +0.36 % | identical |
| Basic (2026-10-16) | 2 | 25838144, 25838145 | 6.390324 | 6.371748 | +0.29 % | identical |
| Basic (2026-10-16) | 4 | 25838146, 25838147 | 2.904620 | 2.897638 | +0.24 % | identical |
| Bonus (2026-10-07) | 1 | 25714175, 25714176 | 11.644042 | 11.668460 | −0.21 % | identical |
| Bonus (2026-10-07) | 2 | 25714177, 25714178 | 5.649779 | 5.640683 | +0.16 % | identical |
| Bonus (2026-10-07) | 4 | 25714179, 25714180 | 2.600607 | 2.599353 | +0.05 % | identical |

Every step of every job ended with `End` and returned 0, and every solve job reported `bound=128/128` on every node. The
Basic re-run ran on other hosts on another day and is 0.24 – 0.36 % slower than our means, within the ±0.5 % in which most of
our October jobs lie. Every recorded job, with its PBS job ID, is listed in `scaling/scaling.txt`.

## 13. Limitations and next steps

- **Not measured.** The DRAM traffic in bytes, the share of the peak bandwidth that a step uses, and how much of the memory
  effect is DRAM bandwidth and how much is L3 capacity. The memory-controller counters are not available to users on
  ASPIRE-2A.
- **The remaining imbalance.** The computation per rank still varies by 6 % (slowest / median 1.063), and MPI is 19 % of a step,
  mostly waiting. The counters tie it to how much each rank reads from DRAM (section 9), not to its cells, so a better
  balance would have to come from data locality per subdomain (renumbering, or weights from measured per-rank times), not
  from equal cell counts.
- **Remaining source changes.** Fusing the assembly of `U`, `k` and `omega` across terms, the GAMG residual with its
  restriction, or the Laplacian coefficients with the diagonal would each remove a pass or two over the face arrays. We expect
  a few per cent from them together. Gains of 10 % would need a different computation, which the rules prohibit.

## 14. Conclusion

Within the rules — the same case, the same math, the same work per step — the speed on ASPIRE-2A was set by two things in
turn. First by placement and balance: the launcher's binding is lost at `MPI_Init`, and the case-default split gives the ranks
near the car more work. Putting the binding back and using a `scotch` split mapped onto the node made Basic 2.898 s per step,
21 % below our baseline, with a 0.2 % spread between jobs. Then by memory bandwidth, shown by moving ranks
rather than by counters we cannot read: the Bonus moves fewer bytes for the same arithmetic and reaches 2.599 s, bit-identical
to its unmodified baseline. Every number here comes from alternated, repeated benchmark jobs, and the submitted scripts
reproduce them from public sources.

## Appendix A. Not counted: residual norms that the fixed iterations never use

*This result is not part of our Bonus submission.*

`fvSolution.fixedIter` sets `tolerance 0` and `relTol 0` for `U`, `k` and `omega`, and `minIter = maxIter = 35` for the
coarsest-level PCG of `p`. The convergence check can then never stop a solve early, so the residual norm that the solvers
compute after every sweep — a residual pass and a global sum — is used only after the last one. A patch that computes it once,
after the last iteration, gave 2.250 s/step against 2.595 for the final Bonus on 4 nodes (−13.3 %, 3 jobs each, ranges not
overlapping). `coefficient.dat` was bit-identical at 1, 2 and 4 nodes, and all 1,323 solver log lines were identical.

We do not count it. It helps only the benchmark's fixed-iteration setting: the case's other dictionary, `fvSolution.fixedTol`,
which uses ordinary tolerances, runs the original code. The rules also prohibit "less work per step", and the skipped norms
could be read as work. The idea itself exists in OpenFOAM: with a negative `nSweeps`, v2512's `smoothSolver` runs a fixed
number of sweeps and computes no residual. What the result does show is the cost of convergence checking at this scale:
about 13 % of a Bonus step on 512 ranks.

## Appendix B. Where the evidence is

| Claim | Evidence in this folder |
|---|---|
| Basic results, all jobs | `results/<n>node/` (fastest job per node count), `scaling/scaling.txt` (every job, PBS IDs) |
| Case changes | `dicts/` (4 nodes), `results/1node/` and `results/2node/` (`caseDefinition`, `controlDict`) |
| Build and run | `build/build.pbs`, `run/*.pbs`, `run/*.sh` |
| MPI profiles | `analysis/pat-report-*.txt`, `analysis/README.md` |
| Hardware counters | `analysis/README.md` |
| Bonus changes and proof | `bonus/patches/`, `bonus/dicts/`, `bonus/results/<n>node/`, `bonus/f3-baseline/<n>node/`, `bonus/README.md` |

## References

1. OpenFOAM HPC Technical Committee, `occDrivAerStaticMesh` (OpenFOAM HPC Challenge OHC-1),
   https://develop.openfoam.com/committees/hpc, commit `84c26243`.
2. 2026 APAC HPC-AI Competition, task rules and addendum of 2026-09-25 (README, OpenFOAM HPC Task Rules).
3. Competition organisers, OpenFOAM application notes for ASPIRE-2A (tasks 4.3), including the vanilla reference runs.
4. F. Pellegrini, *Scotch and PT-Scotch Graph Partitioning Software*, user's guide, version 6.1 (mapping strategies and
   tree-leaf target architectures).
