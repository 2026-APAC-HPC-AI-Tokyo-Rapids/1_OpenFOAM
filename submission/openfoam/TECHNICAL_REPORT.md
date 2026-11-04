# OpenFOAM `occDrivAerStaticMesh` on NSCC ASPIRE-2A: technical report

Tokyo Rapids with RIKEN, 2026 APAC HPC-AI Competition, OpenFOAM HPC task

This report explains our OpenFOAM submission in full: what limited the speed at each stage, what we changed, why each
change keeps the computation the same, and how we measured and checked each claim. It follows the order of our interview
slides (the OpenFOAM part of the deck in `../presentation/`) and adds the numbers, the job-by-job results and the reasoning
that the slides have no room for. [`README.md`](README.md) is the short version, with the commands to run everything again.

| | |
|---|---|
| Task and rules | https://github.com/hpcac/2026-APAC-HPC-AI: [2. OpenFOAM HPC Task Rules](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/2.%20OpenFOAM%20HPC%20Task%20Rules.md) with its addendum F0 – F5, the [README addendum](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/README.md#addendum-2026-09-25) (R1 – R5) and [5. Common Baselines](https://github.com/hpcac/2026-APAC-HPC-AI/blob/main/5.%20Common%20Baselines.md) |
| Our repository | https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/1_OpenFOAM (private): the scripts, every experiment as a commit, and the reasons in the commit messages |
| Raw record of every run | https://mizuha-dev.com/files/openfoam-artifacts/, one folder per GitHub Actions run ID. `<run ID>/aspire2a/openfoam-aspire2a-occdrivaer-65m-result-<run ID>-1/` holds the parsed result (`result.txt`) and the run's `coefficient.dat`; the folder beside it holds the full run record (`run-artifacts.tar.zst` with its manifest) |
| This folder | logs, dictionaries, scripts, MPI profiles, patches and the F3 evidence (Appendix B) |

Every time in this report is the official metric, `Average wall-clock time per time step` at the end of `simpleFoam.log`
(steps 2 to N), from benchmark runs without any profiler, unless it is marked as measured under a profiler. A mean is over
the repeated jobs of one configuration, and SD is
the standard deviation between those jobs as a percentage of the mean. Times per step have four significant figures and
changes one decimal. Appendix A lists every job with its run ID.

Where each slide of the OpenFOAM part is explained:

| Slides | Section |
|---|---|
| OpenFOAM on ASPIRE-2A | 1 |
| Criteria for keeping a change | 3 |
| Our Baseline | 4 |
| Profiling Baseline, MPI calls on 4 nodes | 5 |
| Basic decomposition, Decomposition results | 6.1 |
| CPU and memory pinning, Pinning results | 6.2 – 6.4 |
| Scotch on the node tree, Node tree results | 6.5 |
| Basic results, MPI after Basic, What did not help in Basic | 6.6 – 6.8 |
| Profiling Basic, Measuring the memory limit | 7.1, 7.2 |
| Bonus multiLevel decomposition, multiLevel results | 7.3 |
| Source changes by intent (1/2, 2/2), Two source changes in pictures | 7.4 |
| Bonus results | 7.5 – 7.7 |
| What did not help in the Bonus | 7.8, 11 |
| Scaling from 1 to 4 nodes | 8 |

## Contents

1. Summary
2. Task, machine and setup
3. How we measured and decided
4. Our Baseline and the official results
5. Profiling the Baseline
6. Basic
7. Bonus
8. Scaling from 1 to 4 nodes
9. Drag coefficient
10. Reproducibility
11. What limits a step now, and what is not proven
12. Conclusion

Appendix A. The jobs behind every comparison; Appendix B. Where the evidence is; References

## 1. Summary

Table 1. Results on 4 nodes (512 ranks, 150 steps).

| | s/step | SD | Jobs | Change |
|---|---:|---:|---:|---|
| Official `hierarchical` (organisers' common baseline) | 3.415 | | 1 | |
| Official `scotch` (organisers' common baseline) | 3.576 | | 1 | |
| Our Baseline: unmodified v2512, case defaults | 3.650 | 4.1% | 3 | |
| **Basic**: unmodified v2512 | **2.898** | 0.07% | 5 | **−20.6%** from our Baseline |
| **Bonus**: `multiLevel` and fourteen source changes | **2.360** | 0.16% | 3 | **−18.6%** from Basic, −35.3% from our Baseline |

The official results are the organisers' untuned runs for ASPIRE-2A in "5. Common Baselines": the site `OpenFOAM/2512`
module, the case defaults and the full Allrun chain, one job per method, with default MPI settings and no binding. Our
Baseline runs our own build and scripts with the case defaults, so the changes from it are what our optimisations did.
Against the official results, Basic is 15.1% below `hierarchical` and 19.0% below `scotch`.

**Basic: the ranks were waiting for each other.** In our Baseline, MPI took 46% of each rank's time, and 42% of the time
went to waiting for other ranks in `MPI_Waitall` and `MPI_Allreduce`. Every rank had the same number of cells, yet the
slowest computed 2.1 times as long as the fastest. Two things made the ranks uneven. The case-default `hierarchical`
decomposition gives some ranks more work, and the CPU binding that the launcher sets is removed during `MPI_Init` on
ASPIRE-2A, which left the median rank with only 9% of its memory on its own NUMA domain. We changed the decomposition to
`scotch` (−6.1%), pinned every rank and its memory from the job script (−14.9%), and mapped the `scotch` decomposition onto
the sockets and NUMA domains of the node with `scotch`'s own coefficients (−0.7%). The SD between jobs fell from 4.1% to
0.07%.

**Bonus: memory bandwidth set the speed.** After Basic, MPI took 19% of the time. The cores ran only 0.4 to 0.7
instructions per cycle, and no compiler setting changed a step by more than 0.13%. Users cannot read the memory-controller
counters on ASPIRE-2A, so we measured the limit by moving the ranks. Half the cores on all memory channels took the same
time per step, while half the channels made a step 2.2 times longer, as much as the STREAM bandwidth fell on the same
nodes. The Bonus therefore moves fewer bytes per step: a `multiLevel` decomposition that follows the machine (−0.8%) and
fourteen source changes that remove copies, zero fills, repeated passes over the same arrays, values nobody reads, and two of
the three global sums per CG iteration on the coarsest level (−9.4% for the first four, −9.3% for the other ten). None of
them changes the iteration counts, the convergence tests or the discretisation. The first four are bit-identical. With all
fourteen, Cd stays within 0.0005% of the unmodified code at 1, 2 and 4 nodes, where F3 allows ±0.5%.

What we found:

1. **The launcher's binding does not survive `MPI_Init` on ASPIRE-2A.** We saw it in `/proc` during the solve: none of
   the 512 ranks stayed on its own core. Binding the memory before each rank starts and re-pinning the CPU from outside,
   both in the job script, fixes it. Either half alone does not help.
2. **Pinning and `scotch` help each other.** With both, the slowest rank computes 1.06 times as long as the median rank,
   against 1.46 in our Baseline.
3. **The data exchanged is not the bottleneck.** 92% fewer faces between nodes, or 55% more network bandwidth, did not
   shorten a step. The MPI time is waiting for the slowest rank.
4. **After Basic, memory bandwidth sets the speed of a step.** We showed it by experiment, because the counters that would
   show it directly are not readable.
5. **The same computation with fewer bytes.** On 1 node, the first four changes cut the demand refills from DRAM by 17%
   while the instructions fall by only 4%, and a step gets 12% shorter.
6. **Basic runs 4.61 times faster on 4 nodes than on 1.** On 4 nodes each rank's cell arrays fit in L3, and the DRAM refills
   per cell and step fall by 30%.
7. **It can be reproduced.** Re-runs of the submitted scripts from the public sources gave a byte-identical
   `coefficient.dat` at every node count and times within 0.4% of our means.

## 2. Task, machine and setup

### 2.1 The task

- Case: the official OHC-1 `occDrivAerStaticMesh`, coarse mesh of 65,334,765 cells (Zenodo record 15012221), solved with
  `simpleFoam` (steady, incompressible, k-ω SST) in OpenFOAM v2512.
- Chain, as in `Allrun`: `decomposePar -constant`, `restore0Dir -processor`, `renumberMesh -constant -overwrite -parallel`,
  `potentialFoam -initialiseUBCs -parallel`, `applyBoundaryLayer -ybl 0.0450244 -parallel` and `simpleFoam -parallel`,
  with `controlDict.noWrite` (`endTime` 40, 80 and 150 on 1, 2 and 4 nodes) and `fvSolution.fixedIter`.
- `fvSolution.fixedIter` sets `tolerance 0` and `relTol 0` for every solver and `minIter` = `maxIter` = 35 on the coarsest
  level, so every iteration count is fixed: for `p`, 12 GAMG cycles with Gauss–Seidel smoothing and exactly 35 PCG
  iterations (DIC) on the coarsest level; for each component of `U`, 15 `smoothSolver` iterations of one Gauss–Seidel sweep;
  for `k` and `omega`, 8 each. Every step does the same work, so a mean over the steps is a fair measure, and a 40-step
  profile shows the same pattern as a 150-step run.
- Metric: the 4-node `Average wall-clock time per time step`. The organisers re-run our Basic.
- Basic (addendum F1): unmodified official v2512. The build, the job scripts, MPI and UCX settings, rank placement and
  affinity, runtime switches, and the decomposition method (`hierarchical` or `scotch`) with that method's coefficients are
  free. `renumberMesh` runs exactly as written, with its default method.
- Bonus (F2, F3): other decomposition methods and source changes, proven to be the same computation. The proof is Cd from
  `coefficient.dat`, bit-identical to or within ±0.5% of a pre-change baseline with the same configuration, at 1, 2 and 4
  nodes. The speedup is measured against our own Basic.

### 2.2 The machine

We chose NSCC ASPIRE-2A. We competed on Gadi last year and wanted to learn the other contest machine, and OpenFOAM uses very
many files: one build is about 36,000 files, and every decomposed case adds thousands more. Our Gadi project allows about
212,000 files, and in August three runs setting up at once hit that limit. On ASPIRE-2A we have 100 TB and 200 million
files, so we could keep every build, case and run record.

Table 2. A standard CPU node of ASPIRE-2A.

| | |
|---|---|
| Processors | 2 × AMD EPYC 7713 (Zen 3), 64 cores each, 2.0 GHz base |
| Memory | 512 GB DDR4-3200 on 16 channels, 409.6 GB/s peak. STREAM triad: about 290 GB/s with one thread per L3, about 270 to 275 GB/s with all 128 cores |
| NUMA domains and caches | 8 NUMA domains, each with 16 cores and 2 memory channels; 32 MB of L3 shared by 8 cores (4 MB per core); 512 KB of L2 per core |
| Network | HPE Slingshot-10, 100 Gb/s, dragonfly topology |
| Software | PBS Pro, the PALS launcher, Cray PE with GCC 11.2 (`PrgEnv-gnu/8.3.3`) and Cray MPICH 8.1.15 |
| Counters | The core counters are readable. The memory-controller (uncore) counters and IBS are not (`perf_event_paranoid=2`) |

Every benchmark run on ASPIRE-2A used 128 MPI ranks per node, one per physical core, without SMT, on exclusive nodes,
except the placement experiment (section 7.2) and the test of two ranks per core (section 6.8).

### 2.3 How we built and ran

Table 3. How we built and ran OpenFOAM. The same for our Baseline, Basic and the Bonus, except where a row says otherwise.

| | |
|---|---|
| Source | The official `OpenFOAM-v2512.tgz` (SHA-256 `ae9a0a13…`), unmodified for our Baseline and Basic. The Bonus applies the patches of `bonus/patches/` before the build |
| Build (`build/build.pbs`) | GCC 11.2, `WM_COMPILE_OPTION=Opt` (`-O3`), double precision, 32-bit labels, no `wmake/rules` changes and no fast-math flags. AMD's math library AOCL-LibM is linked through `FOAM_EXTRA_LDFLAGS`. Scotch 6.1.0 without MPI. One run with the site module was as fast (0.08% apart) |
| MPI | Cray MPICH 8.1.15 over UCX. In September every 2- and 4-node run with the default OFI crashed at `MPI_Finalize`. With the workaround the organisers found later, OFI ran but was 0.8% slower (section 6.8) |
| Decomposition | Our Baseline: `hierarchical`, with the case's own (16 8 4) on 4 nodes and (16 8 1) and (16 8 2) on 1 and 2 nodes. Basic: `scotch` mapped onto the node (section 6.5). Bonus: `multiLevel` (2 4 16), (2 2 4 16) and (4 2 4 16) (section 7.3) |
| Placement | 128 ranks per node, rank r of a node on core r. Our Baseline: the launcher's binding only (`mpiexec --cpu-bind depth -d 1`, as the site recommends). Basic and Bonus: also `numactl --membind` for each rank and a watcher that re-pins each rank with `taskset` (section 6.2) |
| Storage | Mesh, builds and run directories on the shared Lustre `/scratch`. Each node copies the decomposed case to node-local `$TMPDIR`, and the solver reads and writes only there (`-hostRoots`, `-ioRanks`). File I/O in the timed steps is about 0.01% of the run time |
| Jobs (`run/submit.sh`) | Two PBS jobs per run: `prepare.pbs` on 4 cores (case setup, `decomposePar`, `restore0Dir`), then `solve.pbs` on the nodes (`renumberMesh`, `potentialFoam`, `applyBoundaryLayer`, `simpleFoam`). F1 allows the chain to be split into jobs |

## 3. How we measured and decided

### 3.1 Benchmark runs and profile runs

Every time in this report comes from a benchmark run without a profiler, except the few marked as measured under one.
Profilers changed a step by −1% to +6%, so profiles only answer where the time goes and why. They ran as separate jobs, with the same placement as the benchmark runs
of their configuration.

Table 4. What each tool measured.

| Tool | Where it ran | What it tells |
|---|---|---|
| Official metric | every benchmark run | the time per step |
| IMB-MPI1 after the solver | every benchmark run | the network bandwidth and the time of a global sum between the nodes of that job |
| CrayPAT 22.04 (`pat_run -g mpi`) | profile runs, 4 nodes, 40 steps | the time and count of every MPI call on every rank |
| OpenFOAM's own profiling (`profiling {}`, `parProfiling`) | profile runs | the time of each solver stage and the computation of each of the 512 ranks |
| AMD uProf 5.3, timer and `data_access` | profile runs, one rank per NUMA domain | CPU time per function and the core counters |
| `/proc` sampler inside the job | profile runs | whether each rank is on its own core, where its memory pages are, I/O bytes and context switches |
| Call-stack samples (`eu-stack`) | profile runs on 4 nodes, 48 of the 512 ranks | which phase of a step each rank is in, and whether it is inside MPI |

### 3.2 Run-to-run variation

ASPIRE-2A varies between jobs. Over 92 jobs in 29 repeated configurations from 21 September to 5 October, most jobs lay
within 0.4% of the median of their configuration, but two September jobs were 84% and 91% slower. One slow `scotch` job
(5.03 s/step, 27 September) once made us reject `scotch`, which jobs run in turns later showed to be 10.5% faster. The same
commit measured in two periods differed by −0.35% to +0.19%, as much as several of our gains. So we never decide from one
job, and every candidate runs with a control in the same period, in turns wherever we could (section 3.3 lists the
exceptions). This cost little, because the jobs of each kept candidate became the control of the next change.

Pinned ranks made the jobs far steadier: 29 pinned `scotch` jobs on 4 nodes in early October had an SD of 0.19%, and the
five Basic jobs have 0.07%.

### 3.3 Criteria for keeping a change

1. Candidate and control ran in turns in the same period, with at least 3 jobs each on 4 nodes.
2. We kept a change only if every candidate job was faster than every control job.
3. A source change had to keep the computation the same, as the rules require (F3, section 7.5).

If a change has no effect, the chance that every candidate job beats every control job is 1 in C(n + m, n): 1 in 20 for 3
jobs against 3, 1 in 70 for 4 against 4, and 1 in 252 for 5 against 5. With an SD of 0.19% and normal noise, a simulation
(200,000 trials each) passes 3 against 3 in 62% of the trials for a gain of twice the SD (about 0.4%), 89% for three times
(about 0.6%), 98% for four times and 99.8% for five times (about 1%). We set no fixed minimum gain. We began with a 1%
minimum before we had measured the spread, and dropped it once we had. Of the 13 changes we kept, 11 gained 1% or more; the
other two are the node mapping (−0.7%, 5 against 5) and `0012` (−0.3%, 3 against 3).

Some comparisons did not run in turns, and we say so where they appear:

- `scotch` against `hierarchical` without pinning (section 6.1). The decision to keep `scotch` rests on the comparison in
  turns once the ranks were pinned (−10.5%, section 6.4).
- Pinned `hierarchical` against our Baseline (section 6.3). In turns with its own unpinned jobs, pinning gained 11.2%.
- `multiLevel` against plain `scotch`, and `0001` against `multiLevel` (sections 7.3 and 7.4). They ran on the same day,
  but mostly one configuration after the other rather than in turns (Appendix A.3).
- `multiLevel` against Basic (section 7.3). Each was compared with plain `scotch` in its own period.
- `0013` – `0015` and `0016`, measured a few days after their controls (section 7.6). All ten later changes together ran in
  turns in the final measurement (−9.3%).

## 4. Our Baseline and the official results

Our Baseline is our own build of unmodified v2512 with the case's own settings: the `hierarchical` decomposition and the
launcher's binding only. It uses the same build, scripts and measurement as everything after it.

Table 5. Our Baseline and the official results at 1, 2 and 4 nodes.

| Nodes (ranks, steps) | Our Baseline, s/step | SD | Jobs | Official `hierarchical` | Official `scotch` |
|---|---:|---:|---:|---:|---:|
| 1 (128, 40) | 14.57 | 2.0% | 6 | 14.67 | 14.05 |
| 2 (256, 80) | 7.427 | 2.0% | 3 | 7.118 | 7.196 |
| 4 (512, 150) | 3.650 | 4.1% | 3 | 3.415 | 3.576 |

- The three 4-node jobs of our Baseline took 3.600, 3.531 and 3.817 s/step.
- The official results are one job per method. The organisers' five 4-node `scotch` jobs with the case defaults (the full
  chain, the chain split into two jobs, and three runs of `simpleFoam` only) ranged from 3.191 to 3.576 s/step, mean 3.296:
  a 12% range (Appendix A.7).
- On 1 node the official `hierarchical` run used (16 4 2) and our Baseline (16 8 1), so there the two also differ in the
  decomposition. On 2 and 4 nodes both used (16 8 2) and (16 8 4).
- Our Baseline is 6.9% slower than the official `hierarchical` run. Our Baseline asks the launcher to pin each rank,
  `MPI_Init` removes the binding, and each rank's memory ends up spread over all eight NUMA domains; the official runs ask
  for no binding at all. We think this is why, but the build and the MPI transport differ too, so we have not isolated it.
- The flow video on our slide "Our Baseline" comes from a visualisation run of the same official case on 4 nodes of the
  Genkai supercomputer (448 ranks, `scotch`, 150 iterations) with field output added; benchmark runs write no fields. It is
  a picture of the flow, not a measurement.

## 5. Profiling the Baseline

### 5.1 Possible bottlenecks

We measured each kind of possible bottleneck separately, on 4 nodes.

Table 6. Each possible bottleneck of our Baseline, how we measured it and what we found.

| Possible bottleneck | How we measured it | What we found |
|---|---|---|
| MPI | CrayPAT, OpenFOAM profiling | 46% of each rank's time. `MPI_Waitall` and `MPI_Allreduce` took 70.7 s of a rank's 169.6 s (42%), waiting for other ranks |
| Outside MPI | CrayPAT, AMD uProf | The other 54%, computing and waiting for memory, which the readable counters cannot separate |
| Placement | `/proc` of every rank during the solve | 0 of 512 ranks on their own core; the median rank had 8.7% of its memory pages on its own NUMA domain (12.5% if spread evenly over 8) |
| Network transfer | IMB after every run, MPI call counts | One 8-byte global sum over 512 ranks takes about 12 µs, and a step has about 1,600, so about 0.02 s per step |
| File I/O and OS noise | Timers, I/O bytes, interrupt counts | File I/O 0.01% of the timed steps; interrupt handling 0.8% of each core's time |

- The CrayPAT run took 3.850 s/step under the profiler. Its process time per rank (169.57 s) covers the mesh read, the
  set-up and 40 steps.
- Per step, a rank sends about 14,000 messages and joins about 1,600 global sums, because every solver iteration exchanges
  halo values with the neighbouring subdomains and takes a global sum (`U`: 15 iterations for each of 3 components; `k` and
  `omega`: 8 each; `p`: 12 GAMG cycles with 35 CG iterations on the coarsest level).
- In uProf, the Gauss–Seidel smoothing, the residual and the matrix–vector product took about a quarter of the time outside
  MPI.

### 5.2 MPI calls on 4 nodes

Table 7. The three MPI calls made most often (CrayPAT, 512 ranks, 40 steps).

| Call | Calls per rank | Calls, all ranks | Time, all ranks |
|---|---:|---:|---:|
| `MPI_Isend` | 566,107 | 290 M | 839 s |
| `MPI_Irecv` | 566,107 | 290 M | 167 s |
| `MPI_Test` | 563,646 | 289 M | 24 s |

Table 8. The three MPI calls that took the most time (the same run).

| Call | Time per rank | Time, all ranks | Share of MPI | Calls per rank |
|---|---:|---:|---:|---:|
| `MPI_Waitall` | 43.1 s | 22,069 s | 55% | 52,933 |
| `MPI_Allreduce` | 27.6 s | 14,140 s | 35% | 63,085 |
| `MPI_Bcast` | 2.5 s | 1,289 s | 3% | 1,219 |
| All MPI calls | 78.3 s | 40,069 s | 100% | 1,815,336 |

- The most frequent calls are the non-blocking halo exchange with the neighbouring subdomains: 93% of the calls, 2.6% of
  the MPI time.
- `MPI_Waitall` and `MPI_Allreduce` wait for other ranks and took 90% of the MPI time. The MPI time per rank ranged from
  34.8 to 112.1 s.
- The cells were equal (the largest subdomain had 0.002% more than the mean), but the fastest rank computed for 1.34 s per
  step and the slowest for 2.88 s, median 1.96 s (OpenFOAM profiling of all 512 ranks, loop time minus `Pstream`).
- Every global sum makes all ranks meet, so a step lasts as long as the slowest rank's computation, and the other ranks
  wait for the difference.
- `analysis/pat-report-baseline.txt` is the CrayPAT report, and `analysis/pat-report-baseline-calls.txt` lists every MPI
  function, including those the default report leaves out.

### 5.3 Why we started with MPI

Outside MPI was the larger share, but 42 of the 46 percentage points of MPI were waiting for the slowest rank, and a rank
is slow because of how the mesh is cut and where it runs. Both can be changed in Basic, in `decomposeParDict` and in the job
script. Making the computation itself faster would mostly need changes to the source, which is Bonus work; the compiler
settings that Basic allows changed nothing (section 6.8). And `/proc` had shown that the pinning was broken. Pinning a
memory-bound code also speeds up its computation, because its memory becomes local.

## 6. Basic

Basic made three changes, in the order we made them: the decomposition, the pinning, and the mapping of the decomposition
onto the node. Our own build, UCX and the node-local copy of the case were already in our Baseline.

### 6.1 Decomposition: `hierarchical` and `scotch`

To balance the work, the usual first step in OpenFOAM is the decomposition ("try this first" in the task rules).

```
method  hierarchical;          // our Baseline, the case default
hierarchicalCoeffs
{
    n  (16 8 4);
}

method  scotch;                // scotch with its defaults
```

`hierarchical` cuts the mesh along the coordinate axes into exactly equal numbers of cells and does not look at the faces.
`scotch` partitions the mesh as a graph, with cells as vertices and shared faces as edges. It keeps the cells within 1% of
equal and cuts as few faces as it can. With more compact subdomains we expected the work per rank (cells, faces and boundary
work) to even out.

Table 9. Cells and faces of the subdomains on 4 nodes, from `decomposePar.log` (rank r on node r/128, socket r/64 and NUMA
domain r/16).

| | `hierarchical` | `scotch` | Change |
|---|---:|---:|---:|
| Cells in the largest subdomain | 127,609 | 128,975 | +1.1% |
| Faces between nodes | 2.33 M | 0.34 M | −85.5% |
| Faces between sockets | 2.47 M | 0.49 M | −80.0% |
| Faces between NUMA domains | 3.63 M | 1.05 M | −71.1% |
| Faces between subdomains in all | 4.31 M | 2.93 M | −32.0% |

The mean subdomain has 127,607 cells. `hierarchical` has many faces between nodes because its four layers along z fall onto
the four nodes.

Result without pinning: our Baseline took 3.650 s/step and `scotch` 3.428 s/step (SD 2.0%, 6 jobs), 6.1% less.

These two were not run in turns: our Baseline ran nine days after the six `scotch` jobs. Five of the six were faster than
all three Baseline jobs, and all six were faster than the same `hierarchical` setting measured again in the pinning
experiment (3.670 s/step, 3 jobs). The comparison on which we kept `scotch` ran in turns once every rank was pinned, and
`scotch` was 10.5% faster (section 6.4).

The six unpinned `scotch` jobs are every unpinned job of the pinning experiment (section 6.3). Two asked the launcher for
both CPU and memory binding, and four for the CPU binding only, as our Baseline did, with the case prepared in its own job.
In all of them `MPI_Init` removed the binding.

### 6.2 CPU and memory pinning

- **Expected.** A node has two CPUs with four NUMA domains each, and each domain has 16 cores and two memory channels.
  Linux places a memory page on the NUMA domain of the core that first writes it and does not move it later. A rank that
  stays on its core keeps its data in the memory of its own domain, the closest.
- **Found.** During the solve of our Baseline, no rank stayed on its own core. Each of the 512 was allowed on all 256 CPUs
  of its node, and the median rank had 8.7% of its pages on its own domain.
- **Cause.** The launcher had bound each rank, but the binding was gone after `MPI_Init`. A diagnostic job (PBS 24944881,
  2 nodes) recorded every rank bound to one CPU just before `MPI_Init` and allowed on 256 CPUs just after, with the site's
  recommended options (`--cpu-bind depth -d 1`) and with both OFI and UCX. We did not find which part of the site's MPI
  stack removes it.
- **Fixed, in the job script only** (`run/solve.pbs`):
  - `run/exec-local-numa.sh` starts each rank as `numactl --membind=<the NUMA domain of its core>`. A memory policy set
    before `exec` belongs to the process, and `MPI_Init` does not remove it.
  - `run/keep-rank-affinity.sh`, one watcher per node, looks at the node's `simpleFoam` processes every 0.1 s and puts the
    main thread of any rank that is not on its own core back there with `taskset`. In the Basic jobs it made 128 re-pins
    per node, the last 13 to 16 s after the start, once `MPI_Init` had removed the binding. The PBS output prints
    `bound=128/128` for every node when every rank is on its core.

With both, every rank stayed on its core (128 of 128 on every node) and the median rank had 58% of its pages on its own
domain (Basic before the node mapping, node 0). We think the rest are pages that several ranks share, such as shared
libraries and MPI's shared buffers, which can live on one domain only; we have not verified this.

This is Basic work: F1 lists job scripts, rank placement and affinity. Our first fix was an `LD_PRELOAD` interposer that
re-pinned each rank right after `MPI_Init`, which would be Bonus work. It is as fast as `numactl` with the watcher (2.919
against 2.917 s/step with `scotch`). We used it in earlier experiments, among them the pinned `hierarchical` jobs and the
pinned `scotch` jobs run in turns with them (sections 6.3 and 6.4), but no Basic or Bonus result uses it.

### 6.3 Pinning results

Table 10. Each placement of the ranks on 4 nodes. Changes are against the unpinned row of the same decomposition.

| Decomposition | Pinned | During the solve | s/step | SD | Jobs | Change |
|---|---|---|---:|---:|---:|---|
| `scotch` | neither | 0 of 128 ranks on their own core, 7% of pages local | 3.428 | 2.0% | 6 | |
| `scotch` | CPU only, by the watcher | 128 of 128 | 3.474 | 2.0% | 3 | 1.3% slower |
| `scotch` | memory only, by `numactl` | 0 of 128, 57% local | 4.380 | | 1 | 27.8% slower |
| `scotch` | CPU and memory, as in Basic | 128 of 128, 58% local | 2.917 | 0.13% | 3 | **−14.9%** |
| `hierarchical` (16 8 4) | neither (our Baseline) | 0 of 512, 8.7% local | 3.650 | 4.1% | 3 | |
| `hierarchical` (16 8 4) | CPU and memory | | 3.257 | 1.1% | 3 | **−10.7%** |

- Pinning only the CPU did not help. Without `numactl`, a rank's memory follows wherever the rank first touches it, and
  the watcher's last re-pin came 12 to 16 s after the start. We think the pages that a rank first touched before it was
  back on its core stayed on other domains, since Linux does not move them; we have not measured this run's pages.
- Pinning only the memory did not help either. The memory is on the right domain, but the rank runs on other domains'
  cores, so nearly every access is remote.
- Pinning both made a step 14.9% shorter with `scotch` and 10.7% shorter with `hierarchical`.
- The pinned jobs varied far less: the SD fell from 4.1% to 1.1% with `hierarchical` and from 2.0% to 0.13% with `scotch`.
  Without pinning, the slowest rank appears in a different place in each run. With a smaller spread, the criterion of
  section 3.3 can see smaller gains, such as the 0.7% of the node mapping.
- Two more placements ran in the same experiment: the launcher's memory binding with the watcher took 3.469 s/step (2 jobs,
  40% of pages local), and the `LD_PRELOAD` re-pin 2.919 s/step (2 jobs, 51%).
- The pinned `hierarchical` jobs and our Baseline ran ten days apart, not in turns; their ranges do not overlap. In turns
  with its own unpinned jobs (3.670 s/step), pinning made a `hierarchical` step 11.2% shorter.

### 6.4 Pinning and decomposition together

Table 11. Time per step on 4 nodes, each decomposition without and with pinning.

| s/step | Not pinned | Pinned | Pinning |
|---|---:|---:|---:|
| `hierarchical` (16 8 4) | 3.650 | 3.257 | −10.7% |
| `scotch` | 3.428 | 2.915 | −15.0% |
| `scotch` against `hierarchical` | −6.1% | **−10.5%** | |

The two pinned values ran in turns, 3 jobs each. Against the `numactl` jobs of Table 10 (2.917 s/step), pinning `scotch`
gives −14.9%.

Table 12. The slowest rank's computation against the median rank's, 4 nodes.

| Run | Slowest / median |
|---|---:|
| `hierarchical`, not pinned (our Baseline) | 1.46 |
| `hierarchical`, pinned | 1.16 |
| `scotch`, pinned (Basic before the node mapping) | 1.06 |

Each fix gained more once the other was in place. Without pinning, the slowest ranks were those that the placement slowed
down, so a better decomposition saved less. With pinning, the slowest ranks were those whose subdomains held more work,
which `scotch` evened out; with `hierarchical`, a rank's extra computation followed the number of wall faces it held, on
the car's surface. The ratios come from two tools (OpenFOAM's profiling and CrayPAT), so we read them as a trend.

Table 13. `hierarchical` against `scotch` at 1, 2 and 4 nodes, both pinned, in turns, 3 jobs each.

| Nodes | `hierarchical`, s/step | `scotch`, s/step | Change |
|---:|---:|---:|---:|
| 1 | 13.52 | 13.35 | −1.3% |
| 2 | 6.528 | 6.368 | −2.5% |
| 4 | 3.257 | 2.915 | −10.5% |

`scotch` was faster at every node count and gained more on more nodes. We think the straight cuts of `hierarchical` become
more uneven as the subdomains get smaller, but we have not checked.

### 6.5 Scotch on the node tree

```
method  scotch;
scotchCoeffs
{
    domains         (2 4 16);
    domainWeights   (0.125 0.0625 0.015625);
    strategy        "m{vert=10240,low=r{job=t,map=t,poli=S,bal=0.010000,sep=…}x{bal=0.010000}f{bal=0.010000,move=80}";
}
```

Through `scotchCoeffs`, the coefficients of the `scotch` method that Basic allows, we gave Scotch the layout of a node.
Unmodified v2512's `scotchDecomp` builds a tree-leaf target architecture from `domains` and `domainWeights` and maps the
decomposition onto it in the same Scotch run, not as a second step.

- `domains (2 4 16)` is 2 sockets, 4 NUMA domains per socket and 16 cores per domain. Their product (128) is smaller than the
  number of subdomains on 2 and 4 nodes, so `scotchDecomp` adds the nodes as a top level with weight 1.
- `domainWeights` are the relative costs of a link at each level. Scotch turns them into integer link costs of 64 between
  nodes, 8 between sockets, 4 between NUMA domains and 1 between cores.
- `strategy` is Scotch 6.1's default mapping strategy for 512 parts with an imbalance of 0.01, plus the terms Scotch adds
  when balance is enforced, which end with an exact balancing pass `x{bal=0.01}`. The full string is in
  `dicts/decomposeParDict` and `run/prepare.pbs`.

Subdomains that share many faces then end up on the same NUMA domain, socket and node.

Table 14. Cells and faces of the subdomains on 4 nodes.

| | `scotch` | Node tree | Change |
|---|---:|---:|---:|
| Cells in the largest subdomain | 128,975 | 128,883 | −0.1% |
| Faces between nodes | 0.34 M | 0.26 M | −22.7% |
| Faces between sockets | 0.49 M | 0.39 M | −21.3% |
| Faces between NUMA domains | 1.05 M | 0.94 M | −10.4% |
| Faces between subdomains in all | 2.93 M | 3.02 M | +3.3% |
| Neighbours of a subdomain, at most | 66 | 40 | |

Result, 5 jobs each in turns: plain `scotch` took 2.918 s/step (SD 0.22%, 2.912 to 2.926) and the node tree 2.898 s/step
(SD 0.07%, 2.894 to 2.900), 0.7% less. Every node-tree job was faster than every plain `scotch` job, and the node-tree jobs
varied less. This is our Basic. On 1 and 2 nodes the mapping changed a step by less than 0.3%. A first test gave −0.66%
without `strategy` and −0.82% with it, below the 1% we then required, so we measured it again with 5 jobs each before we
adopted it.

### 6.6 Basic results

Table 15. Each step to Basic on 4 nodes, in the order of the work.

| | s/step | SD | Jobs | Change |
|---|---:|---:|---:|---:|
| Official `hierarchical` | 3.415 | | 1 | |
| Official `scotch` | 3.576 | | 1 | |
| Our Baseline | 3.650 | 4.1% | 3 | |
| `scotch`, not pinned | 3.428 | 2.0% | 6 | −6.1% |
| `scotch`, CPU and memory pinned | 2.917 | 0.13% | 3 | −14.9% |
| `scotch` on the node tree: **Basic** | **2.898** | 0.07% | 5 | −0.7% |
| Basic against our Baseline | | | | **−20.6%** |

- The node tree's −0.7% is against its own control in the same period (2.918 s/step). Against the pinned `scotch` row
  above it is −0.66%.
- The three steps multiply to 2.897 s/step (3.650 × 0.9393 × 0.8509 × 0.9931), close to the measured 2.898.
- The SD between jobs fell from 4.1% to 0.07%. The organisers' five `scotch` jobs spread over 12%, our five Basic jobs over
  0.18%. It is not UCX: our jobs with the organisers' OFI transport also lay within 0.26%.

Table 16. Basic at 1, 2 and 4 nodes.

| Nodes (ranks, steps) | Basic, s/step | SD | Jobs | Cd at the last step | Against our Baseline |
|---|---:|---:|---:|---|---:|
| 1 (128, 40) | 13.36 | 0.02% | 3 | 0.43957921531324928 | −8.3% |
| 2 (256, 80) | 6.372 | 0.08% | 3 | 0.33409590047442955 | −14.2% |
| 4 (512, 150) | 2.898 | 0.07% | 5 | 0.29301591596528520 | −20.6% |

The means to more digits are 13.364504, 6.371748 and 2.897638 s/step (`scaling/scaling.txt`). Every job of a node count
wrote a byte-identical `coefficient.dat`. The gain grows with the node count mainly because of the decomposition (Table
13), and the node mapping helped only on 4 nodes.

### 6.7 MPI after Basic

We profiled Basic the same way as our Baseline. The profile is of Basic before its node mapping (plain `scotch`, pinned),
which changes a step by 0.7%; it ran at 3.063 s/step under CrayPAT.

Table 17. MPI per rank, CrayPAT, 4 nodes, 40 steps: our Baseline against Basic before its node mapping.

| | Our Baseline | Basic | Change |
|---|---:|---:|---:|
| `MPI_Isend` calls | 566,107 | 597,033 | +5.5% |
| `MPI_Irecv` calls | 566,107 | 597,033 | +5.5% |
| `MPI_Test` and other calls | 565,883 | 596,475 | +5.4% |
| `MPI_Waitall` time | 43.1 s | 10.2 s | −76% |
| `MPI_Allreduce` time | 27.6 s | 12.9 s | −53% |
| `MPI_Bcast` time | 2.5 s | 1.4 s | −44% |
| All MPI time | 78.3 s | 26.7 s | −66% |
| MPI's share of the process time | 46% | 19% | |
| Slowest / median computation per rank | 1.46 | 1.063 | |

- The most frequent calls stayed the same three, with about 5% more calls. We think `scotch`'s subdomains have more
  neighbours; we have not checked.
- The wait in `MPI_Waitall` fell by 76% because the ranks now finish their computation at about the same time.
  `MPI_Allreduce` is now the largest MPI call (48% of the MPI time), then `MPI_Waitall` (38%).
- The default report of Basic (`analysis/pat-report-basic.txt`) leaves out calls that take little time, such as
  `MPI_Test`. So the third row is all MPI calls minus the six calls the Basic report lists, counted the same way for both.

### 6.8 What did not help in Basic

Table 18. Each Basic idea we tried and did not keep, against its control on 4 nodes.

| Idea | Time per step | Why it did not help |
|---|---|---|
| Compiler flags `-march=znver3`, `-O2` and LTO | no change, at most 0.1% slower (3 jobs each) | the loops wait for memory, not for instructions (section 7.2) |
| AMD compilers AOCC 5.0 with AOCL 5.1 | no change, within 0.1% (3 jobs each) | the same |
| GCC profile-guided optimisation | 0.1% slower (0.08% on 1 node), Cd bit-identical | the same |
| UCX over RC instead of UD between nodes: IMB bandwidth (1 MiB `Sendrecv`) from 6.7 to 10.4 GB/s, 55% more | no change, within 0.1% (4 jobs each) | a step does not wait for transfers |
| Rank reordering (`MPICH_RANK_REORDER_METHOD=3`) of the same `hierarchical` subdomains, with 92% fewer faces between nodes | 0.1% slower (3 jobs each) | the subdomains, and with them the slowest rank, stayed the same |
| The default OFI transport with the organisers' workarounds | 0.8% slower (`FI_OFI_RXM_USE_SRX=0`, 3 jobs each) and 0.5% slower (`FI_VERBS_PREFER_XRC=0`, 1 job each), the same Cd | not faster than UCX |
| OpenFOAM's communication switches (`topoControl`, `nbx.tuning`, `pbufs.tuning`) | no gain; `commsType scheduled` crashed in GAMG | the MPI time is waiting for the slowest rank |
| glibc `malloc` thresholds | 0.4% faster, within the spread (3 jobs) | too small to separate from the spread; not tested again |
| Two ranks per core (SMT) | 5.7 times slower | some steps stalled for minutes; cause not isolated |

- None of these goes after what limited a step. The compilers speed up instructions while the cores wait for memory
  (section 7.2), and the network changes cannot shorten the wait for the slowest rank.
- A rank's `MPI_Waitall` time follows its own computation (R² = 0.77), and 13 of the 16 slowest ranks have no neighbours on
  other nodes.
- The rank reordering cut the faces between nodes from 2,331,023 to 196,190 (fewer than `scotch`'s 337,324) and those
  between NUMA domains by 73%, yet a step went from 3.257 to 3.261 s/step. So the gain of `scotch` came from evening out the
  computation per rank, not from fewer faces between nodes.
- `renumberMesh` runs in Basic exactly as `Allrun` writes it, with its default method (F1, and F5: "Can I add `-dict` to
  `renumberMesh`? Not in Basic"), so every job used Cuthill–McKee (`renumberMesh.log`: `Using renumber-method:
  CuthillMcKee [default]`). Other orders are discussed in section 7.8.

## 7. Bonus

### 7.1 Profiling Basic

Table 19. Each possible bottleneck after Basic, how we measured it and what we found.

| Possible bottleneck | How we measured it | What we found after Basic |
|---|---|---|
| MPI | CrayPAT | 19% of the time, down from 46%, still mostly waiting |
| Outside MPI | CrayPAT | The other 81%, computing and waiting for memory |
| Computing | AMD uProf core counters | 0.4 to 0.7 instructions per cycle, where a Zen 3 core can dispatch 6, and about 0.1 flop per byte in the heaviest loops: the cores were mostly waiting |
| Memory bandwidth | Memory-controller counters | Not readable by users on ASPIRE-2A |

- The heaviest loops are the sparse-matrix sweeps: Gauss–Seidel, the residual b − Ax and the matrix–vector product. Per
  internal face they do about 4 floating-point operations and read two coefficients (16 B), an address (4 B) and cell
  values, 30 to 40 B in all: about 0.1 flop per byte. A node needs about 14 flop per byte to keep its cores busy (128 cores
  × 2.0 GHz × 16 flop per cycle ≈ 4.1 TFLOP/s, against about 290 GB/s).
- CPU utilisation cannot separate computing from waiting: the OS counts a core as busy while it waits for memory, and MPI
  spins while it waits, so every core would show nearly 100%.
- We cannot draw a measured roofline either, because placing the solver on it needs the DRAM bytes from the
  memory-controller counters. We measured the limit by experiment instead.

### 7.2 Measuring the memory limit

We changed only where the ranks run (4 nodes, 150 steps, every rank pinned with its memory on its own domain, 2 jobs per
placement except one for full128 of Basic and of the first four changes):

- **full128**: 128 ranks per node, as submitted.
- **spread64**: 64 ranks per node, 4 on each L3, on all 16 L3s and all 16 memory channels: half the cores.
- **packed64**: the same 64 ranks and the same decomposition as spread64, 8 on each L3, on 8 L3s and 8 channels (the first
  two NUMA domains of each socket): half the memory system.

STREAM triad (c = a + 3b) ran in the same jobs after the solver, on the same nodes and with the same placement.

Table 20. Time per step under the three placements on 4 nodes.

| s/step | full128 | spread64 | packed64 | spread64 / full128 | packed64 / spread64 |
|---|---:|---:|---:|---:|---:|
| Basic before the node mapping | 2.920 | 2.887 | 6.347 | 0.99 | 2.20 |
| `multiLevel` without the source changes | 2.869 | 2.874 | 6.321 | 1.00 | 2.20 |
| `multiLevel` with the first four changes | 2.595 | 2.649 | 5.598 | 1.02 | 2.11 |
| STREAM triad per node, same nodes | 274 GB/s | 279 GB/s | 125 GB/s | | 2.2 times lower |

- If the computation, or the latency of each core's memory requests, set the speed, half the cores would have taken twice
  as long. They took 0.99 to 1.02 times as long.
- With half the channels, a step took 2.11 to 2.20 times as long, while the STREAM bandwidth on the same nodes fell 2.22
  times (278.5 to 125.4 GB/s, means over the nodes).
- So memory bandwidth sets the speed of a step. This is also why no compiler setting helped in Basic.
- MPI is 19% of a step, but it follows the bandwidth too: most of it is waiting for the slowest rank, whose computation is
  limited by bandwidth. Fitting a step as a part that scales with 1/bandwidth plus a fixed part, to spread64 and packed64,
  leaves a fixed part of less than 0.1 s per step.
- The first four changes gained 7.9% on 16 channels and 11.4% on 8. They help most where bandwidth is scarcest, which is
  what removing memory traffic predicts.
- Limits. packed64 also halves the L3, so DRAM bandwidth and L3 capacity are not separated; both are the memory side. Half
  the cores also means 256 subdomains instead of 512. A coarser decomposition can save some communication, but the part of
  a step that does not scale with bandwidth is less than 0.1 s, far too small to hide a doubling of the work per core. We
  take only the ratio between placements from STREAM, and assume that the bandwidth OpenFOAM can use changes in the same
  ratio on the same channels.
- We did not put 128 ranks on 8 channels. Those channels belong to 4 NUMA domains with 64 cores, so it would mean two ranks
  per core, which alone made a step 5.7 times slower (Table 18). With 64 ranks, 8 and 16 channels differ only in the
  channels. 32 ranks per node would change the decomposition and give each rank four times the data, mixing in cache
  effects, and half the cores were already as fast as all of them.
- spread64 used cores 0 – 3, 8 – 11, …, 120 – 123 of each node, and packed64 cores 0 – 31 and 64 – 95, so both sockets
  carried 32 ranks in both placements. spread64 and packed64 wrote a byte-identical `coefficient.dat` (Appendix A.5).

### 7.3 `multiLevel` decomposition

```
method  multiLevel;
multiLevelCoeffs
{
    method   scotch;
    domains  (4 2 4 16);     // 2 nodes: (2 2 4 16), 1 node: (2 4 16)
}
```

Basic maps one `scotch` run onto the node tree. `multiLevel`, another decomposition method and so Bonus work (F2), runs
`scotch` separately at each level: it first divides the mesh among the 4 nodes, then each part between 2 sockets, then
among 4 NUMA domains and then among 16 cores. Each node, socket and NUMA domain becomes one compact block. `run/prepare.pbs`
appends the `multiLevelCoeffs` block for the node count, and `bonus/dicts/` has the 4-node files.

Table 21. Cells and faces of the subdomains on 4 nodes.

| | Basic | `multiLevel` | Change |
|---|---:|---:|---:|
| Cells in the largest subdomain | 128,883 | 129,985 | +0.9% |
| Faces between nodes | 0.26 M | 0.21 M | −20.2% |
| Faces between sockets | 0.39 M | 0.33 M | −15.5% |
| Faces between NUMA domains | 0.94 M | 0.78 M | −17.0% |
| Faces between subdomains in all | 3.02 M | 2.81 M | −7.0% |

Result: `multiLevel` took 2.873 s/step (SD 0.16%, 4 jobs, 2.868 to 2.879) against Basic's 2.898 s/step (2.894 to 2.900),
0.8% less. Every `multiLevel` job was faster than every Basic job. The two did not run in turns. Each was compared with
plain `scotch` in its own period, and plain `scotch` took 2.918 s/step both times: Basic ran in turns with it and was 0.7%
faster (5 jobs each), and `multiLevel` ran on the same day as its 4 control jobs, but before and after them rather than in
turns, and was 1.5% faster.

- We have not separated how much each part of the decomposition contributes. Rank reordering cut the faces between nodes by
  92% and did not help (section 6.8), so fewer faces between nodes alone do not explain the gain.
- With unmodified source, `multiLevel` needs no extra baseline, and its Cd is checked like Basic's (section 9).

### 7.4 Fourteen source changes

As memory bandwidth limits a step, the changes make a step move fewer bytes. None of them changes the iteration counts, the
convergence tests or their meaning, the number of steps or the discretisation, and every solve does its full work.

How we found them. The first four came from the heaviest loops: call-stack samples pointed to the residual copy in
`smoothSolver` (`0001`) and to boundary exchanges whose result is thrown away (`0003`). For the other ten, we regrouped the
call-stack samples of the Bonus with the first four changes by phase, function and call path, read the v2512 source behind
each, and ranked the candidates.

Table 22. Where a step of the Bonus with the first four changes went: 2,396 call-stack samples from 48 of the 512 ranks on
4 nodes.

| Phase of a step | Share of the samples | Share of the phase inside MPI |
|---|---:|---:|
| `p` solve (GAMG) | 31.8% | 53% |
| k-ω SST correction | 26.9% | 23% |
| `U` solve (Gauss–Seidel) | 20.5% | 19% |
| `U` assembly | 11.8% | 12% |
| `p` assembly | 6.6% | 29% |
| Other (function objects, corrections, continuity errors) | 2.5% | |

- The k-ω SST correction was mostly field algebra over the cells, which led to `0013`. The coarsest GAMG level took 6.6% of
  the samples, nearly all of them inside MPI and mostly in global sums, which led to `0012`. The Gauss–Seidel sweeps and
  residuals led to `0011` and `0016`.
- Call-stack samples put more of the time in MPI than CrayPAT's timers do (31% of the samples against 20% of the time in the
  same profile run), so we take MPI's share of a step from CrayPAT.

Table 23. The fourteen changes by intent, each with its change of a step on 4 nodes against the configuration just before
it. Changes measured together share one value.

| Intent | Change | What it removes | 4 nodes |
|---|---|---|---:|
| Fewer passes over the data | `0002` | Gauss–Seidel read the shared matrix of `U` three times, once per component | −2.3% |
| | `0004` | interpolated face fields and product fields built before every face sum of the Gauss gradient and the Laplacian correction | −2.8% |
| | `0006` | a temporary product field, its copy and a re-read of `upper` when the Laplacian builds its coefficients and diagonal | with 0008 – 0010: −2.0% |
| | `0009` | three whole-field passes for `muEff*dev2(T(grad(U)))` | with 0006, 0008, 0010: −2.0% |
| | `0013` | 67 of the 80 passes over the cells in each k-ω SST correction | with 0014, 0015: −2.5% |
| | `0015` | two passes over the finest GAMG level per cycle: the correction is added, and the next residual restricted, in the loops that already compute them | with 0013, 0014: −2.5% |
| | `0016` | one matrix pass and one interface exchange per component and iteration: the residual is formed inside the last Gauss–Seidel sweep | −3.8% |
| No copies or zero fills | `0001` | `smoothSolver` built each residual in a new field and copied it; GAMG copied the source and then subtracted | −3.4% |
| | `0011` | the copy of the source into a work array in every Gauss–Seidel sweep | −1.0% |
| | `0014` | the zero fill of face coefficients that are written before they are read, and a copy of the whole `U` matrix in the momentum predictor | with 0013, 0015: −2.5% |
| No values that nobody reads | `0003` | six callers built the boundary values of a surface integral, exchanged them across processors and used only the cell values | −1.3% |
| | `0008` | patch loops and a global reduction in every step that only found, each time, that `p` needs no reference level | with 0006, 0009, 0010: −2.0% |
| | `0010` | a full-volume `devReff()` field in the `wallShearStress` function object, of which only the wall values were read | with 0006, 0008, 0009: −2.0% |
| Fewer global sums | `0012` | two of the three global sums per iteration of the coarsest-level PCG (Chronopoulos/Gear form): 36 instead of 105 per solve of 35 iterations | −0.3% |

The two changes drawn on our slides:

- `0002`: for the `U` equation solved with `smoothSolver` and Gauss–Seidel, a new `smoothSolver::solveGaussSeidelComponents`
  smooths the three components in one pass over the shared matrix arrays. In a segregated solve the components are
  independent, and each sees the same operations in the same order. It gained 6.4% on 1 node, 4.1% on 2 and 2.3% on 4.
- `0001`: `smoothSolver` uses the existing in-place `lduMatrix::residual` instead of the overload that returns a new field
  which is then copied, and GAMG forms its finest-level residual with one `subtract(r, source, Apsi)`. The same function
  computes the same residual; only an allocation and a copy go away. It gained 2.2%, 2.9% and 3.4% on 1, 2 and 4 nodes.

Why the result is the same. Eleven of the changes keep every arithmetic expression and its order, so they cannot change a
result. Three change the order of some floating-point operations and are judged by F3 (next section): `0011` adds the
source once at the end of each cell's sum instead of first; `0012` computes the same Krylov iterates in exact arithmetic
but turns one inner product into a recurrence; `0016` reuses, in the next sweep, the processor-interface values received
for the residual, which can change rounding on those interfaces. In all of them the convergence tests keep their meaning for
any tolerance. `bonus/README.md` describes each change with the argument that its result is the same.

Two points that judges may ask about:

- `0003` skips no check. At six call sites that read only cell values, it replaces `fvc::div` and `fvc::surfaceIntegrate`
  with `fvc::surfaceIntegrateInternal`. The same `surfaceIntegrate` loop gives the same cell values, and only the boundary
  values that nobody reads, with their exchange, are skipped. Boundary conditions, every exchange the solution uses and the
  bounding of `k` and `omega` are unchanged, and the bounding messages appear in the logs as before.
- `0010` changes a function object whose output the benchmark case neither writes nor logs. We checked it on a serial test
  case (151,600 cells, 40 steps): with and without `0010`, `coefficient.dat` and the final `U`, `p`, `k`, `omega`, `nut`,
  `cp` and `wallShearStress` fields were bit-identical.

The numbers `0005` and `0007` are not part of the Bonus.

### 7.5 Proof that the computation is the same (F3)

The pre-change baseline has the Bonus configuration with the changes removed: the same `multiLevel` decomposition and
coefficients, the same rank and node counts, and unmodified v2512 (exactly the Basic binaries). Its `simpleFoam.log` and
`coefficient.dat` are in `bonus/f3-baseline/<n>node/`, and those of the Bonus in `bonus/results/<n>node/`. The proof has two
steps.

1. **`0001` – `0004` are bit-identical.** With these four changes (commit `fa4f5b0`), `coefficient.dat` is byte-identical
   to the pre-change baseline at 1, 2 and 4 nodes. As the iteration counts are fixed, a wrong residual would not show in
   `coefficient.dat`, so we compared the solver logs too: every residual (16 digits), iteration count, continuity error and
   bounding message is identical in all 371, 771 and 1,475 lines. Only host names, paths, dates and timings differ.
2. **All fourteen stay within ±0.5%.**

Table 24. Cd at the last step: the final Bonus against the pre-change baseline.

| Nodes (steps) | Pre-change baseline and `fa4f5b0`: Cd, SHA-256 of `coefficient.dat` | Bonus, all 3 jobs: Cd, SHA-256 | Difference |
|---|---|---|---:|
| 1 (40) | 0.43827636195043501, `36d35283…` | 0.43827636195094927, `00d481ab…` | +1.2 × 10⁻¹² (relative) |
| 2 (80) | 0.32285935413723610, `2a49a26d…` | 0.32285928314184348, `d9fe4e04…` | −0.00002% |
| 4 (150) | 0.29138777754153217, `8952a056…` | 0.29138659643758436, `34749b4c…` | −0.00041% |

- The largest difference, −0.00041% on 4 nodes, is more than 1,000 times smaller than the ±0.5% that F3 allows. Over all
  150 iterations on 4 nodes, the two Cd histories never differ by more than 0.00048% (at iteration 149).
- On 4 nodes we also checked each group against the configuration before it. `0006` and `0008` – `0010` leave
  `coefficient.dat` byte-identical (`8952a056…`). `0011` changes Cd by −0.0009%, and `0012` brings it to −0.0004% from
  `fa4f5b0`. `0013` – `0016` leave it byte-identical to the `0012` result (`34749b4c…`). So on 4 nodes the whole difference
  comes from `0011` and `0012`.
- Every job of the same configuration and node count wrote a byte-identical `coefficient.dat`.

### 7.6 Bonus results

Table 25. Each step from Basic to the Bonus on 4 nodes.

| | s/step | SD | Jobs | Change |
|---|---:|---:|---:|---:|
| Basic | 2.898 | 0.07% | 5 | |
| `multiLevel` instead of the node tree | 2.873 | 0.16% | 4 | −0.8% |
| + the first four changes (`fa4f5b0`) | 2.603 | 0.19% | 3 | −9.4% |
| + the ten other changes: **Bonus** | **2.360** | 0.16% | 3 | −9.3% |
| Bonus against Basic | | | | **−18.6%** |

- `multiLevel` and Basic did not run in turns (section 7.3).
- The `fa4f5b0` row is the three jobs that ran in turns with the Bonus in the final measurement (26 October). The first
  four changes had been measured one by one, each against the configuration before it: −3.4%, −2.3%, −1.3% and −2.8%. The
  same commit gave 2.599 s/step on 6 and 7 October, 0.15% from its 26 October jobs, so the machine had not changed between
  the Basic jobs (15 and 16 October) and the final measurement.
- Against the official results, the Bonus is 30.9% below `hierarchical` and 34.0% below `scotch`.

Table 26. The Bonus at 1, 2 and 4 nodes against Basic.

| Nodes (ranks, steps) | Basic, s/step | Bonus, s/step | Bonus SD | Bonus against Basic | Speedup |
|---|---:|---:|---:|---:|---:|
| 1 (128, 40) | 13.36 | 10.23 | 0.32% | −23.4% | 1.31× |
| 2 (256, 80) | 6.372 | 4.992 | 0.25% | −21.7% | 1.28× |
| 4 (512, 150) | 2.898 | 2.360 | 0.16% | −18.6% | 1.23× |

The Bonus means to more digits are 10.233606, 4.992196 and 2.359976 s/step, 3 jobs each.

Table 27. The effect of each change, against the configuration just before it. These are separate experiments and should
not be added up. On 1 and 2 nodes most values are single jobs.

| Change | Compared with | 1 node | 2 nodes | 4 nodes |
|---|---|---:|---:|---:|
| `multiLevel`, unmodified source | plain `scotch` | −0.5% | −0.4% | −1.5% |
| + `0001` | `multiLevel`, unmodified | −2.2% | −2.9% | −3.4% |
| + `0002` | the row above | −6.4% | −4.1% | −2.3% |
| + `0003` | the row above | −1.4% | −1.9% | −1.3% |
| + `0004` | the row above | −2.9% | −2.3% | −2.8% |
| + `0006`, `0008` – `0010` | `fa4f5b0` | | | −2.0% |
| + `0011` | the row above | | | −1.0% |
| + `0012` | the row above | | | −0.3% |
| + `0013` – `0015` | the row above | | | −2.5% \* |
| + `0016` | the row above | | | −3.8% \* |
| All of `0006` – `0016` (the Bonus) | `fa4f5b0`, in turns (final measurement) | −12.2% | −11.4% | −9.3% |

\* Measured a few days after the configuration it is compared with, not in turns with it.

### 7.7 Why the changes help

Table 28. Core counters on 1 node: the first four changes against the same build without them (AMD uProf `data_access`, one
rank per NUMA domain except rank 0, which also writes the output; 2 jobs each; computation only, with the MPI, UCX and
`Pstream` libraries left out).

| Per rank, whole run | Without the changes | With the first four | Change |
|---|---:|---:|---:|
| Time per step under uProf | 13.299 s | 11.666 s | −12.3% |
| Cycles | 450.2 G | 401.6 G | −10.8% |
| Instructions | 162.1 G | 155.5 G | −4.1% |
| L1 data accesses | 90.8 G | 85.5 G | −5.8% |
| L1 demand refills from L2 | 0.800 G | 0.798 G | −0.2% |
| L1 demand refills from L3 | 0.116 G | 0.114 G | −1.7% |
| L1 demand refills from DRAM | 0.493 G | 0.408 G | −17.2% |
| L2 accesses from L1 misses, including prefetches | 6.35 G | 5.74 G | −9.6% |
| Instructions per cycle | 0.360 | 0.387 | +7.5% |

- The changes remove little arithmetic (4% of the instructions) and much data movement (17% of the demand refills from
  DRAM). That is what the same math with less data moved predicts.
- Demand refills do not count hardware prefetches. The prefetchers bring the streamed arrays from DRAM into L2, so their
  loads appear among the L2 accesses, which fell by 10%.
- The two jobs of each side agree within about 4% on every counter, and both sides write the same `coefficient.dat`. The
  counters are sampled and multiplexed (13 events).
- On 4 nodes, CrayPAT shows the same from the side of time: from `0001` alone to `0001` – `0004`, the computation per rank
  fell from 104.2 to 94.9 s (40 steps), while the MPI time stayed at about 23.5 s.
- The changes gain most where memory is scarcest. The first four gained 7.9% on 16 channels and 11.4% on 8 (section 7.2),
  and the gains are larger on 1 node, where each rank holds four times the data: `0002` gained 6.4% on 1 node and 2.3% on 4,
  `0006` – `0016` 12.2% and 9.3%.
- We have not measured the ten later changes with counters.

### 7.8 What did not help in the Bonus

Table 29. Each Bonus idea we tried and did not keep, against its control on 4 nodes.

| Idea | Time per step | What we learned |
|---|---|---|
| Cell weights to balance the work of faces: `multiLevel` with weights from each cell's share of points (× 2, × 12); `scotch` with weight 2 on boundary cells | 2.2% and 6.1% slower (1 job against 4); 6.5% slower (3 against 6) | the weights unbalance the cell counts (the largest subdomain has 7% more cells than the mean with × 2); even cell counts matter most |
| METIS with two constraints, cells and faces (through `method manual`) | 1.5% slower (2 against 3) | better face balance, but 18% more faces between subdomains |
| GAMG coarsest level gathered on one rank (`processorAgglomerator masterCoarsest`) | 5.0% slower (40 steps) | gathering to one rank and solving there costs more than the global sums it saves |
| The same with one master per node (`nProcessorsPerMaster 128`) or per NUMA domain (16) | 1.0% slower and 0.3% faster (1 job each, Cd within 0.002%) | the coarsest level makes 81% of the `MPI_Allreduce` calls, but at about 12 µs each their latency adds up to only about 0.6% of a step; the rest of its time is waiting for other ranks |
| UCX over RC between nodes | 0.2% faster, within the spread (4 against 4) | the ranges overlap |
| Gauss–Seidel sweep of the interior cells while the interface values are in flight | 8.3% slower (3 jobs), Cd 1.2% lower | fails F3: on 512 ranks, changing the order in which cells see their neighbours' new values moves Cd far beyond rounding |
| `bound()` averaging only over the bounded cells | not run | it needs one more global sum per call, which costs more than it saves |
| Other cell orders in `renumberMesh` | not run on ASPIRE-2A | the default order already keeps neighbours in cache (below) |
| Overlapping the halo exchange with computation | under 1% available (call-stack samples) | we skipped the unused exchanges instead (`0003`) |

None of these reduces the bytes a step moves from memory, so none made a step faster. Balancing the faces unbalanced the
cells, and fewer ranks in the global sums did not shorten the wait.

Table 30. Every decomposition we measured on 4 nodes, each against its own control.

| Decomposition (tier) | Against | Time per step |
|---|---|---|
| `hierarchical` (4 8 16) in the order zyx (Basic) | the case default | 0.4% slower (1 job) |
| `hierarchical` with rank reordering (Basic) | without reordering | 0.1% slower (3 against 3) |
| `scotch` (Basic, kept) | `hierarchical` | 10.5% faster (3 against 3) |
| `scotch` mapped onto the node (Basic, kept) | plain `scotch` | 0.7% faster (5 against 5) |
| `scotch` with a quality strategy (Basic) | the mapped `scotch` | no gain (1 job) |
| `multiLevel` (4 128) (Bonus) | plain `scotch` | 1.1% faster (2 against 2) |
| `multiLevel` (4 2 4 16) (Bonus, kept) | plain `scotch` | 1.5% faster (4 against 4) |
| `multiLevel` (4 2 8 8) (Bonus) | `multiLevel` (4 2 4 16) | 0.7% slower (1 against 1, 40 steps) |
| `multiLevel` with weights by point share, × 2 and × 12 (Bonus) | the same with `0001` | 2.2% and 6.1% slower (1 against 4) |
| `multiLevel` with weight 3 on wheel and underbody cells (Bonus) | `multiLevel` | 11% and 64% slower, Cd −2.6% |
| `scotch` with weight 2 on boundary cells (Bonus) | plain `scotch` | 6.5% slower (3 against 6) |
| METIS with two constraints, cells and faces (Bonus) | `multiLevel` with `0001` | 1.5% slower (2 against 3) |
| `kahip`, METIS and `ptscotch` on their own | | not run: the build had only stub libraries for them |

Other orders in `renumberMesh`. Basic must run it as written, so every job used the default, Cuthill–McKee. For the Bonus we
judged the other orders from what renumbering does. It gives neighbouring cells nearby numbers, so that a loop over the
faces finds a cell's neighbours in cache, and with Cuthill–McKee they already are.

- In Basic's 4-node log, Cuthill–McKee brought the bandwidth (the largest number distance between neighbours) from 128,811
  to 14,165, and the profile from 2.27 × 10¹¹ to 1.66 × 10¹¹, about 2,500 per cell.
- A face loop therefore works within a window of about 2,500 cells; for `U` and `grad(U)` that is about 240 KB, inside the
  512 KB L2 of a core. One field of a rank's 128,000 cells is about 1 MB, inside its 4 MB share of L3 on 4 nodes.
- What still comes from DRAM is each array once per pass, and no order changes that. Reversing the order keeps every
  neighbour distance, and the other orders put neighbours farther apart.
- Every order would change Cd, because the Gauss–Seidel sweeps go through the cells in their numbered order, so each would
  need its own F3 check.

As extra information from another machine, we measured the other orders on Genkai.

Table 31. `renumberMesh` orders on Genkai: the official case on 4 nodes with 112 ranks each (plain `scotch`, 448
subdomains), unmodified v2512, 40 iterations, every order once per round in a rotated order, 4 rounds.

| Order | s/step | Against the default | Cd at iteration 40 | Bandwidth, largest |
|---|---:|---|---:|---:|
| Cuthill–McKee (default) | 1.958 | | 0.43768 | 11,347 |
| Reverse Cuthill–McKee | 1.954 | 0.2% faster, within the spread (faster in 3 rounds, slower in 1) | 0.43190 (−1.3%) | 11,347 |
| None | 1.972 | 0.7% slower | 0.43240 (−1.2%) | 146,078 |
| Spring | 2.022 | 3.3% slower | 0.43483 (−0.7%) | 68,712 |
| Random | 2.166 | 10.6% slower | 0.43805 (+0.1%) | 147,291 |

As the principle says, no order beat the default, and every order changed Cd. Genkai has 2 MB of L2 per core against
ASPIRE-2A's 512 KB, so this shows a trend, not an ASPIRE-2A time. The scripts and raw results are in
`presentation/openfoam/renumber/` of our repository.

## 8. Scaling from 1 to 4 nodes

This is strong scaling: the same mesh of 65,334,765 cells on 128, 256 and 512 ranks. The runs take 40, 80 and 150 steps, but
the metric is per step, so the node counts compare directly.

Table 32. Time per step, and how many times faster than on 1 node.

| | 1 node, s/step | 2 nodes, s/step | 4 nodes, s/step | 2 nodes, times faster | 4 nodes, times faster |
|---|---:|---:|---:|---:|---:|
| Official `hierarchical` (1 job each) | 14.67 | 7.118 | 3.415 | 2.06× | 4.30× |
| Official `scotch` (1 job each) | 14.05 | 7.196 | 3.576 | 1.95× | 3.93× |
| Our Baseline | 14.57 | 7.427 | 3.650 | 1.96× | 3.99× |
| Basic | 13.36 | 6.372 | 2.898 | 2.10× | 4.61× |
| Bonus | 10.23 | 4.992 | 2.360 | 2.05× | 4.34× |

As parallel efficiencies on 4 nodes, these are 1.07, 0.98, 1.00, 1.15 and 1.08.

Basic and the Bonus run more than 4 times faster on 4 nodes. We profiled Basic before its node mapping at 1, 2 and 4 nodes
with uProf `data_access` on one rank per NUMA domain (8, 16 and 32 ranks), and divided each count by the number of ranks, the
steps and the cells per rank.

Table 33. Per cell and step.

| | 1 node | 2 nodes | 4 nodes | 4 nodes / 1 node |
|---|---:|---:|---:|---:|
| Cycles | 24,235 | 22,860 | 20,418 | 0.843 |
| L1 demand refills from DRAM | 24.6 | 20.7 | 17.1 | 0.697 |
| L1 demand refills from L3 of the same CCX | 5.4 | 6.3 | 9.4 | 1.75 |
| Instructions per cycle | 0.528 | 0.583 | 0.666 | |

Table 34. By function, 4 nodes against 1 node (the 30 most sampled addresses, 46 to 52% of the cycles).

| Function | Cycles | Refills from DRAM |
|---|---:|---:|
| `GaussSeidelSmoother::smooth` | 0.715 | 0.301 |
| `lduMatrix::residual` | 0.687 | 0.404 |
| `lduMatrix::Amul` | 0.616 | 0.419 |
| cell-field `multiply` (streaming) | 0.797 | 0.948 |

- The cycles per cell and step fall to 0.843 on 4 nodes, and the time per cell and step to 0.873 (4.58 times faster for this
  configuration): the same direction and size.
- Only the sparse-matrix kernels read much less from DRAM per cell. They read and write cell arrays (`psi`, the source, the
  diagonal) in the order of the face addressing. Per rank these arrays are about 4 MB on 1 node, 2 MB on 2 nodes and 1 MB on
  4 nodes, against 4 MB of L3 per core. The face arrays (coefficients and addressing), about 16 MB per rank even on 4
  nodes, fit at no node count. On 4 nodes the scattered reads of cell arrays come from L3 instead of DRAM, while a loop that
  streams through cell fields (`multiply`) reads almost as much from DRAM per cell as on 1 node (0.948).
- The Bonus scales less than Basic (4.34 against 4.61 times) because its changes remove memory traffic, which costs most on
  1 node: the Bonus took 23.4% off Basic on 1 node and 18.6% on 4. The 4-node Bonus is not slower; the 1-node Bonus gained
  more.
- The official `hierarchical` runs also scale 4.30 times. They are single unpinned jobs, their 1-node run used (16 4 2)
  (section 4), and we have not looked into them.
- uProf wrote its reports on the login node after the job, when the node-local OpenFOAM libraries were gone. We mapped the
  addresses to functions with `nm` of the same libraries from the build that the runs used.

## 9. Drag coefficient

At 40, 80 and 150 steps the flow has not converged, and Cd depends on the decomposition. The organisers' notes give 0.7%,
3.0% and 3.5% between `hierarchical` and `scotch`.

Table 35. Cd at the last step, against the Sanity check of the task rules.

| Steps (nodes) | OHC-1 values | Our Baseline (`hierarchical`) | `scotch` with its defaults | **Basic** (node tree) | Bonus (`multiLevel`) |
|---|---|---:|---:|---:|---:|
| 40 (1) | 0.433 – 0.436 | 0.43305 | 0.43599 | **0.43958** | 0.43828 |
| 80 (2) | 0.334 – 0.345 | 0.33733 | 0.32714 | **0.33410** | 0.32286 |
| 150 (4) | 0.284 – 0.292 | 0.27356 | 0.28405 | **0.29302** | 0.29139 |

- Every column but the Bonus runs unmodified source, and only the decomposition differs. The Bonus differs from its
  unmodified pre-change baseline by at most 0.0005% (section 7.5), so to five digits it shows the values of `multiLevel`
  without the changes.
- Every value lies within 4% of the OHC-1 range, on either side. Basic is a little above it at 40 and 150 steps (by 0.8%
  and 0.3%) and the Bonus at 40 steps (by 0.5%). `multiLevel` (0.323) and plain `scotch` (0.327) are below it at 80 steps,
  and our Baseline (0.2736) at 150 steps. The organisers' own runs scatter the same way: their `scotch` run gives 0.327 at
  80 steps and their `hierarchical` run 0.2739 at 150.
- With the same decomposition, our Cd differs slightly from the organisers': 0.284049 against 0.283983 with `scotch` at 150
  steps (0.023%), and 0.27356 against 0.27392 with `hierarchical` (0.13%). Running the site module with our scripts
  reproduced the organisers' `scotch` value to every digit (0.28398300763231610), so the difference comes from our build,
  for example AMD's math library, not from the method.
- Every job of the same configuration and node count wrote a byte-identical `coefficient.dat`.

Table 36. Cd over the iterations on 4 nodes, from `coefficient.dat`.

| Iteration | Basic | Bonus | Bonus without its source changes | Official `hierarchical` | Official `scotch` |
|---:|---:|---:|---:|---:|---:|
| 1 | 1.19529 | 1.20342 | 1.20342 | 1.09641 | 1.20777 |
| 10 | 0.43362 | 0.43189 | 0.43189 | 0.44024 | 0.43188 |
| 20 | 0.44214 | 0.44197 | 0.44197 | 0.44601 | 0.44357 |
| 40 | 0.44229 | 0.43422 | 0.43422 | 0.43721 | 0.43547 |
| 60 | 0.38866 | 0.38023 | 0.38023 | 0.38689 | 0.37921 |
| 80 | 0.33696 | 0.32665 | 0.32665 | 0.34182 | 0.33677 |
| 100 | 0.31010 | 0.30685 | 0.30685 | 0.31387 | 0.30629 |
| 120 | 0.29798 | 0.29948 | 0.29948 | 0.29590 | 0.30032 |
| 150 | 0.29302 | 0.29139 | 0.29139 | 0.27392 | 0.28398 |

The decompositions give different curves from the first iterations on and end a few per cent apart at 150 iterations, while
the Bonus and its pre-change baseline lie on top of each other.

## 10. Reproducibility

The scripts in `build/` and `run/` are those of our final measurements. They do what our measured runs did to the case and
to the processes, in the same order and with the same flags, and leave out only what our CI added to record or check, such
as the placement records and the IMB test after the solver. We ran them again from the public sources, as `README.md`
describes.

Table 37. Re-runs of the submitted scripts from the public sources.

| Configuration (re-run) | Nodes | PBS jobs (prepare, solve) | Re-run, s/step | Recorded mean, s/step | Change | `coefficient.dat` |
|---|---:|---|---:|---:|---:|---|
| Basic (2026-10-16) | 1 | 25838142, 25838143 | 13.413150 | 13.364504 | +0.36% | byte-identical |
| Basic (2026-10-16) | 2 | 25838144, 25838145 | 6.390324 | 6.371748 | +0.29% | byte-identical |
| Basic (2026-10-16) | 4 | 25838146, 25838147 | 2.904620 | 2.897638 | +0.24% | byte-identical |
| Bonus (2026-10-26) | 1 | 25992065, 25992066 | 10.201813 | 10.233606 | −0.31% | byte-identical |
| Bonus (2026-10-26) | 2 | 25992067, 25992068 | 4.980185 | 4.992196 | −0.24% | byte-identical |
| Bonus (2026-10-26) | 4 | 25992069, 25992070 | 2.365118 | 2.359976 | +0.22% | byte-identical |

- Every step of every job ended with `End` and returned 0, and every solve job printed `bound=128/128` for every node.
- The Basic re-run ran on other hosts and was 0.24 to 0.36% slower than our means, within the ±0.5% in which
  most of our October jobs lie. The Bonus re-run built the fourteen patches of `bonus/patches/` into the public sources (PBS
  build job 25990973) and is within 0.31% of our means at every node count.
- Provenance: Basic is commit `16c62ac` (tag `issue63-basic-final-20261016`) and the Bonus commit `1bc34b9` (tag
  `issue69-bonus-final-20261026`) of our repository. Every measured run was started by GitHub Actions, and its raw record
  is on our artifact server under its run ID (Appendix A).

## 11. What limits a step now, and what is not proven

What limits a step now:

- Memory traffic, and the ranks that read the most from DRAM. On 4 nodes the computation cycles of the 32 ranks profiled
  with uProf follow their refills from DRAM (r = +0.69) and from L2 (r = +0.76), not their instructions (r = −0.09) or their cells
  (r = +0.24). The slowest and the fastest rank execute about the same number of instructions, but the slowest reads more
  than twice as many lines from DRAM. Refills from remote DRAM are 0.3% of all refills.
- The computation per rank still varies by about 6%: in OpenFOAM's profiling of all 512 ranks of Basic before the node
  mapping, the slowest rank computed 1.063 times as long as the median. The cells of a rank are within about 1% of the mean
  and do not explain it (r = +0.06 over those ranks), the wall faces of a rank explain a little (r = +0.43, 2.8% of the
  work), and nodes and NUMA domains show no systematic difference.
- MPI is 19% of a step, mostly waiting for those ranks.

What we would do next, with a few per cent expected in all:

- Move fewer bytes still: fusing the assembly of `U`, `k` and `omega` across terms would remove more passes over the face
  arrays.
- Improve the data locality of the slowest subdomains. Weights, cheaper global sums and a faster network did not help them.
- Larger gains would need a different computation, which the rules do not allow.

What is proven, and what is not:

- The times: every change we kept ran in turns with its control, at least 3 jobs each on 4 nodes, and every candidate job
  beat every control job, with the exceptions listed in section 3.3.
- The computation: the first four changes give a bit-identical `coefficient.dat` and identical solver logs, and all
  fourteen keep Cd within 0.0005%.
- The lost binding: seen directly in `/proc` during the solve.
- The memory limit: shown by experiment, not by counters. On 1 node, the core counters agree for the first four changes.
- Not shown: the DRAM traffic in bytes (the memory-controller counters are not readable); how much of the memory effect is
  DRAM bandwidth and how much L3 capacity; counters for the ten later changes; an MPI profile of Basic after its node
  mapping and of the final Bonus; which part of the site's MPI stack removes the binding; why 58% rather than all of a rank's
  pages are local; why the gain of `scotch` grows with the node count; and the cause of the SMT stalls.

## 12. Conclusion

With the same case, the same math and the same work per step, the speed of OpenFOAM on ASPIRE-2A was limited by two things
in turn. First by balance and placement: the case-default `hierarchical` decomposition gave some ranks more work, and the
launcher's binding was lost at `MPI_Init`, so most ranks waited for the slowest one. A `scotch` decomposition, pinning from
the job script and the mapping of `scotch` onto the node made Basic 2.898 s/step, 20.6% below our Baseline, with an SD of
0.07% between jobs. Then by memory bandwidth, which we showed by moving the ranks rather than with counters we cannot read.
The Bonus moves fewer bytes for the same computation and reaches 2.360 s/step, 18.6% below Basic and 35.3% below our
Baseline, with Cd within 0.0005% of the unmodified code. Every change we kept was measured in repeated jobs against a
control in the same period (section 3.3), and the submitted scripts reproduce our results from the public sources.

## Appendix A. The jobs behind every comparison

The raw record of a job is at `https://mizuha-dev.com/files/openfoam-artifacts/<Actions run ID>/`. For example, the first
Basic job's parsed result is
https://mizuha-dev.com/files/openfoam-artifacts/38711144961/aspire2a/openfoam-aspire2a-occdrivaer-65m-result-38711144961-1/result.txt.
The organisers' jobs (A.7) are in `4.3-aspire2a-logs/` of the task repository.

### A.1 Basic: every 4-node job of every step

Each cell lists the jobs as s/step (GitHub Actions run ID). Mean and SD are over the jobs of the row.

| Group | Jobs: s/step (Actions run ID) | Mean | SD |
|---|---|---:|---:|
| Our Baseline: `hierarchical` (16 8 4), launcher binding only | 3.6003 (38218885545)<br>3.5313 (38219700707)<br>3.8170 (38219731754) | 3.6495 | 4.08% |
| `scotch`, not pinned (PALS `--cpu-bind` and `--mem-bind`; or `--cpu-bind` only with the case prepared in its own job) | 3.3763 (37131371136)<br>3.4137 (37131937125)<br>3.5561 (37117905768)<br>3.3593 (37123797027)<br>3.4248 (37124558353)<br>3.4368 (37125347729) | 3.4278 | 2.03% |
| `scotch`, CPU only (watcher with `taskset`) | 3.5488 (37127003025)<br>3.4098 (37127540803)<br>3.4629 (37128534595) | 3.4738 | 2.02% |
| `scotch`, memory only (`numactl --membind`) | 4.3796 (37133155192) | 4.3796 |  |
| `scotch`, CPU and memory (`numactl --membind` + watcher, as in Basic) | 2.9191 (37133158165)<br>2.9123 (37135716945)<br>2.9189 (37136333280) | 2.9168 | 0.13% |
| `scotch`, CPU and memory with an `LD_PRELOAD` re-pin after `MPI_Init` (not used in Basic) | 2.9154 (37133683583)<br>2.9228 (37128819151) | 2.9191 | 0.18% |
| `scotch`, PALS `--mem-bind local` + watcher | 3.4498 (37131382899)<br>3.4875 (37132444869) | 3.4687 | 0.77% |
| `hierarchical` (16 8 4), not pinned, in turns with the two rows below | 3.6983 (36973596442)<br>3.5850 (36995859798)<br>3.7270 (36996824227) | 3.6701 | 2.05% |
| `hierarchical` (16 8 4), pinned (`LD_PRELOAD` re-pin) | 3.2912 (36969734412)<br>3.2593 (36976077930)<br>3.2217 (36982402075) | 3.2574 | 1.07% |
| `scotch`, pinned (`LD_PRELOAD` re-pin), in turns with the row above | 2.9154 (36969734733)<br>2.9227 (36975429131)<br>2.9054 (36981344530) | 2.9145 | 0.30% |
| plain `scotch`, pinned: control of the node tree | 2.9119 (38712273361)<br>2.9237 (38713137760)<br>2.9120 (38714020871)<br>2.9257 (38717653229)<br>2.9152 (38721645165) | 2.9177 | 0.22% |
| **Basic**: `scotch` on the node tree, pinned (in turns with the row above) | 2.8985 (38711144961)<br>2.8981 (38712708404)<br>2.8996 (38713582982)<br>2.8976 (38714454251)<br>2.8944 (38719816024) | 2.8976 | 0.07% |

### A.2 `hierarchical` against `scotch` at 1, 2 and 4 nodes, both pinned, in turns

| Nodes | `hierarchical`: s/step (Actions run ID) | `scotch`: s/step (Actions run ID) | Change |
|---:|---|---|---:|
| 1 | 13.5115 (37183458233)<br>13.5302 (37184299734)<br>13.5271 (37185144775) | 13.3497 (37182501846)<br>13.3302 (37183875746)<br>13.3579 (37184748743) | −1.3% |
| 2 | 6.5303 (37176268510)<br>6.5199 (37183009577)<br>6.5344 (37183761260) | 6.3619 (37180519996)<br>6.3729 (37182526314)<br>6.3689 (37183402459) | −2.5% |
| 4 | 3.2912 (36969734412)<br>3.2593 (36976077930)<br>3.2217 (36982402075) | 2.9154 (36969734733)<br>2.9227 (36975429131)<br>2.9054 (36981344530) | −10.5% |

### A.3 Bonus: every 4-node comparison of a change against the configuration before it

Each candidate's jobs became the control of the next change, so the same run IDs appear twice. The last row group is the final
measurement, in which the Bonus and the first four changes (`fa4f5b0`) ran in turns at every node count. Actions run IDs
grow with the start time. The first two rows ran on one day in blocks: three `multiLevel` jobs (`7325738`) before the four
plain `scotch` controls, then the `0001` jobs around the last `multiLevel` job (`2eacff5`).

| Change (commit) | Control: s/step (Actions run ID) | Candidate: s/step (Actions run ID) | Change | Every candidate job faster |
|---|---|---|---:|---|
| `multiLevel` (4 2 4 16), unmodified source (`2eacff5`, `7325738`) against plain `scotch` | 2.9217 (37200996533)<br>2.9155 (37202026690)<br>2.9185 (37202900063)<br>2.9165 (37206922099) | 2.8731 (37209554319)<br>2.8724 (37182901138)<br>2.8793 (37184168749)<br>2.8682 (37184562437) | −1.5% | yes |
| + 0001 (`e2730db`) | 2.8731 (37209554319)<br>2.8724 (37182901138)<br>2.8793 (37184168749)<br>2.8682 (37184562437) | 2.7738 (37207676657)<br>2.7772 (37209542974)<br>2.7778 (37209996357)<br>2.7749 (37217223164) | −3.4% | yes |
| + 0002 (`57b6567`) | 2.7797 (37305040569)<br>2.7834 (37345231360)<br>2.7808 (37345278528) | 2.7242 (37296670512)<br>2.7153 (37345205903)<br>2.7131 (37345255660) | −2.3% | yes |
| + 0003 (`20d285b`) | 2.7129 (37397902111)<br>2.7039 (37402844900)<br>2.7074 (37402875569) | 2.6692 (37400128139)<br>2.6764 (37402860649)<br>2.6719 (37410978169) | −1.3% | yes |
| + 0004 (`fa4f5b0`) | 2.6725 (37458489079)<br>2.6760 (37458531796)<br>2.6758 (37458570685) | 2.5972 (37445116747)<br>2.5990 (37458511102)<br>2.6018 (37458551410) | −2.8% | yes |
| + 0006, 0008, 0009, 0010 (`4b1ed6a`) | 2.5970 (39731990374)<br>2.5978 (39732710493)<br>2.5972 (39733427785) | 2.5450 (39727727733)<br>2.5461 (39732349951)<br>2.5459 (39733070522) | −2.0% | yes |
| + 0011 (`45a4e7b`) | 2.5450 (39727727733)<br>2.5461 (39732349951)<br>2.5459 (39733070522) | 2.5212 (39731943495)<br>2.5188 (39736859696)<br>2.5176 (39737620563) | −1.0% | yes |
| + 0012 (`f99771e`) | 2.5212 (39731943495)<br>2.5188 (39736859696)<br>2.5176 (39737620563) | 2.5142 (39731945548)<br>2.5129 (39737232797)<br>2.5077 (39738020584) | −0.3% | yes |
| + 0013, 0014, 0015 (`af6b217`), a few days after its control | 2.5142 (39731945548)<br>2.5129 (39737232797)<br>2.5077 (39738020584) | 2.4489 (40197285037)<br>2.4499 (40200109666)<br>2.4494 (40200396658) | −2.5% | yes |
| + 0016 (`1bc34b9`, the Bonus), a few days after its control | 2.4489 (40197285037)<br>2.4499 (40200109666)<br>2.4494 (40200396658) | 2.3594 (40220163039)<br>2.3521 (40223201266)<br>2.3577 (40223483985) | −3.8% | yes |
| Final measurement, 1 node: Bonus (`1bc34b9`) against `fa4f5b0` | 11.6488 (40228873327)<br>11.6497 (40229838120)<br>11.6528 (40230800958) | 10.2660 (40229032746)<br>10.2338 (40230000382)<br>10.2010 (40230955174) | −12.2% | yes |
| Final measurement, 2 nodes: Bonus (`1bc34b9`) against `fa4f5b0` | 5.6313 (40228543612)<br>5.6502 (40229521100)<br>5.6292 (40230481997) | 4.9945 (40228699031)<br>4.9787 (40229680305)<br>5.0034 (40230638939) | −11.4% | yes |
| Final measurement, 4 nodes: Bonus (`1bc34b9`) against `fa4f5b0` | 2.5998 (40228230008)<br>2.6088 (40229199928)<br>2.6009 (40230160947) | 2.3627 (40228389428)<br>2.3615 (40229360674)<br>2.3557 (40230323116) | −9.3% | yes |

### A.4 The submitted Basic and Bonus jobs

These are the jobs of `scaling/scaling.txt`; `*` marks the job whose logs are in `results/<n>node/` (Basic) or
`bonus/results/<n>node/` (Bonus). Every job of a configuration and node count wrote a byte-identical `coefficient.dat`.

| Configuration | Nodes | PBS job | Actions run ID | s/step | Cd at the last step |
|---|---:|---|---|---:|---|
| Basic | 1 | 25836835.pbs101 | 38834816429 | 13.367984 | 0.43957921531324928 |
| Basic | 1 | 25837254.pbs101 | 38845610732 | 13.362960 | 0.43957921531324928 |
| Basic | 1 | 25837534.pbs101 \* | 38848172882 | 13.362568 | 0.43957921531324928 |
| Basic | 2 | 25836889.pbs101 | 38844320208 | 6.376214 | 0.33409590047442955 |
| Basic | 2 | 25837416.pbs101 \* | 38846886410 | 6.365990 | 0.33409590047442955 |
| Basic | 2 | 25837681.pbs101 | 38849528232 | 6.373041 | 0.33409590047442955 |
| Basic | 4 | 25827199.pbs101 | 38711144961 | 2.898459 | 0.29301591596528520 |
| Basic | 4 | 25827285.pbs101 | 38713582982 | 2.899615 | 0.29301591596528520 |
| Basic | 4 | 25827343.pbs101 | 38714454251 | 2.897560 | 0.29301591596528520 |
| Basic | 4 | 25827444.pbs101 | 38712708404 | 2.898113 | 0.29301591596528520 |
| Basic | 4 | 25827680.pbs101 \* | 38719816024 | 2.894442 | 0.29301591596528520 |
| Bonus | 1 | 25988347.pbs101 | 40229032746 | 10.265991 | 0.43827636195094927 |
| Bonus | 1 | 25988352.pbs101 | 40230000382 | 10.233839 | 0.43827636195094927 |
| Bonus | 1 | 25988437.pbs101 \* | 40230955174 | 10.200988 | 0.43827636195094927 |
| Bonus | 2 | 25988434.pbs101 | 40228699031 | 4.994481 | 0.32285928314184348 |
| Bonus | 2 | 25988421.pbs101 \* | 40229680305 | 4.978716 | 0.32285928314184348 |
| Bonus | 2 | 25988505.pbs101 | 40230638939 | 5.003391 | 0.32285928314184348 |
| Bonus | 4 | 25988197.pbs101 | 40228389428 | 2.362703 | 0.29138659643758436 |
| Bonus | 4 | 25988237.pbs101 | 40229360674 | 2.361476 | 0.29138659643758436 |
| Bonus | 4 | 25988381.pbs101 \* | 40230323116 | 2.355747 | 0.29138659643758436 |

### A.5 The placement experiment (section 7.2)

| Configuration | Placement | PBS job | Actions run ID | s/step | SHA-256 of `coefficient.dat` (first 16) |
|---|---|---|---|---:|---|
| Basic before the node mapping | full128 | 25752904 | 38068088448 | 2.9197 | `5d71f5fe7fd4f59b` |
| Basic before the node mapping | spread64 | 25752936 | 38068068048 | 2.8939 | `244c734c6cf8562c` |
| Basic before the node mapping | spread64 | 25753354 | 38069891682 | 2.8792 | `244c734c6cf8562c` |
| Basic before the node mapping | packed64 | 25752894 | 38068070854 | 6.3482 | `244c734c6cf8562c` |
| Basic before the node mapping | packed64 | 25753438 | 38069894076 | 6.3457 | `244c734c6cf8562c` |
| `multiLevel` without the patches | full128 | 25753298 | 38068133546 | 2.8698 | `8952a056c8de917d` |
| `multiLevel` without the patches | full128 | 25753445 | 38070069463 | 2.8678 | `8952a056c8de917d` |
| `multiLevel` without the patches | spread64 | 25753297 | 38068079768 | 2.8883 | `a14798a6187e1c47` |
| `multiLevel` without the patches | spread64 | 25753516 | 38070645417 | 2.8604 | `a14798a6187e1c47` |
| `multiLevel` without the patches | packed64 | 25753432 | 38069940799 | 6.3198 | `a14798a6187e1c47` |
| `multiLevel` without the patches | packed64 | 25753510 | 38070647833 | 6.3216 | `a14798a6187e1c47` |
| `multiLevel` with the first four changes | full128 | 25752897 | 38068090820 | 2.5949 | `8952a056c8de917d` |
| `multiLevel` with the first four changes | spread64 | 25752892 | 38068073632 | 2.6376 | `a14798a6187e1c47` |
| `multiLevel` with the first four changes | spread64 | 25753345 | 38069896510 | 2.6596 | `a14798a6187e1c47` |
| `multiLevel` with the first four changes | packed64 | 25752926 | 38068077010 | 5.6013 | `a14798a6187e1c47` |
| `multiLevel` with the first four changes | packed64 | 25753433 | 38069898756 | 5.5954 | `a14798a6187e1c47` |

### A.6 Compiler options against GCC `-O3` (section 6.8)

| Option | Jobs: s/step (Actions run ID) | Mean |
|---|---|---:|
| control (GCC -O3, scotch) | 2.9119 (37117603016)<br>2.9172 (37118028466)<br>2.9019 (37123341442) | 2.9103 |
| -march=znver3 | 2.9114 (37117567270)<br>2.9103 (37118751920)<br>2.9122 (37119270873) | 2.9113 |
| AOCC 5.0 / AOCL 5.1 | 2.9238 (37118928102)<br>2.9083 (37120577347)<br>2.9016 (37121011866) | 2.9112 |
| -O2 | 2.9083 (37129742960)<br>2.9127 (37136034132)<br>2.9114 (37136599208) | 2.9108 |
| LTO (-flto=auto) | 2.9221 (37129745193)<br>2.9112 (37136036583)<br>2.9089 (37136667909) | 2.9141 |

### A.7 The official runs (organisers' jobs, from the ASPIRE-2A application notes)

| Method | Nodes | Run | Setting | PBS jobs | s/step | Cd at the last step |
|---|---:|---|---|---|---:|---|
| `hierarchical` | 1 | full chain | defaults | 25702859 | 14.6688 | 0.43893232842064450 |
| `hierarchical` | 2 | full chain | defaults | 25702861 | 7.1177 | 0.33686897165236618 |
| `hierarchical` | 4 | full chain | defaults | 25705409 | 3.4145 | 0.27391974323989648 |
| `scotch` | 1 | full chain | defaults | 25702860 | 14.0486 | 0.43598883601901173 |
| `scotch` | 2 | full chain | defaults | 25702862 | 7.1959 | 0.32712980974126155 |
| `scotch` | 4 | full chain | defaults | 25705410 | 3.5760 | 0.28398300763231610 |
| `scotch` | 1 | full chain, split | defaults | 25702985+25702986 | 14.6110 | 0.43598883601901173 |
| `scotch` | 2 | full chain, split | defaults | 25702988+25702989 | 7.4231 | 0.32712980974126155 |
| `scotch` | 4 | full chain, split | defaults | 25702990+25705411 | 3.1907 | 0.28398300763231610 |
| `scotch` | 1 | simpleFoam only | defaults | 25702987 | 14.8077 | 0.43598883601901173 |
| `scotch` | 4 | simpleFoam only | defaults | 25705412 | 3.2925 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | defaults | 25705413 | 3.2129 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | defaults | 25705414 | 3.2082 | 0.28398300763231610 |
| `hierarchical` | 2 | full chain | FI_VERBS_PREFER_XRC=0 | 25710708 | 6.9597 | 0.33686897165236618 |
| `scotch` | 2 | full chain | FI_VERBS_PREFER_XRC=0 | 25710709 | 6.8263 | 0.32712980974126155 |
| `hierarchical` | 4 | full chain | FI_VERBS_PREFER_XRC=0 | 25710710 | 3.5116 | 0.27391974323989648 |
| `scotch` | 4 | full chain | FI_VERBS_PREFER_XRC=0 | 25710711 | 3.2448 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | FI_VERBS_PREFER_XRC=0 | 25710712 | 3.3733 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | FI_VERBS_PREFER_XRC=0 | 25710713 | 3.2206 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | FI_VERBS_PREFER_XRC=0 | 25710714 | 3.3003 | 0.28398300763231610 |
| `hierarchical` | 2 | full chain | FI_OFI_RXM_USE_SRX=0 | 25710715 | 7.1716 | 0.33686897165236618 |
| `scotch` | 2 | full chain | FI_OFI_RXM_USE_SRX=0 | 25710716 | 7.1955 | 0.32712980974126155 |
| `hierarchical` | 4 | full chain | FI_OFI_RXM_USE_SRX=0 | 25710717 | 3.4404 | 0.27391974323989648 |
| `scotch` | 4 | full chain | FI_OFI_RXM_USE_SRX=0 | 25710718 | 3.2108 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | FI_OFI_RXM_USE_SRX=0 | 25710719 | 3.2666 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | FI_OFI_RXM_USE_SRX=0 | 25710720 | 3.3871 | 0.28398300763231610 |
| `scotch` | 4 | simpleFoam only | FI_OFI_RXM_USE_SRX=0 | 25710721 | 3.1762 | 0.28398300763231610 |

## Appendix B. Where the evidence is

| Claim | Evidence in this folder |
|---|---|
| Basic results, every job | `results/<n>node/` (the logs of one job per node count, from `decomposePar.log` to `simpleFoam.log`, its `coefficient.dat` and PBS output), `scaling/scaling.txt` (every job with its PBS ID) |
| Case files | `dicts/` (4 nodes), `results/1node/` and `results/2node/` (`caseDefinition`, `controlDict`) |
| Build and run | `build/build.pbs`, `run/submit.sh`, `run/prepare.pbs`, `run/solve.pbs`, `run/environment.sh`, `run/exec-local-numa.sh`, `run/keep-rank-affinity.sh` |
| MPI profiles | `analysis/pat-report-*.txt`, `analysis/README.md` |
| Hardware counters | `analysis/README.md` |
| Bonus changes and the proof | `bonus/patches/`, `bonus/dicts/`, `bonus/results/<n>node/`, `bonus/f3-baseline/<n>node/`, `bonus/README.md` |
| Slides | the OpenFOAM part of the deck in `../presentation/` |
| Raw records of every run | https://mizuha-dev.com/files/openfoam-artifacts/ |

## References

1. 2026 APAC HPC-AI Competition, task rules with the addendum of 2026-09-25: https://github.com/hpcac/2026-APAC-HPC-AI
   ("README", "2. OpenFOAM HPC Task Rules", "5. Common Baselines").
2. Competition organisers, "4.3 OpenFOAM Application Notes - ASPIRE-2A", with the reference runs in `4.3-aspire2a-logs/`, in
   the same repository.
3. OpenFOAM HPC Technical Committee, `occDrivAerStaticMesh` (OpenFOAM HPC Challenge OHC-1),
   https://develop.openfoam.com/committees/hpc, commit `84c26243`; the mesh: https://zenodo.org/records/15012221.
4. F. Pellegrini, Scotch and PT-Scotch Graph Partitioning Software, user's guide, version 6.1 (mapping strategies and
   tree-leaf target architectures).
5. A. T. Chronopoulos and C. W. Gear, "s-step iterative methods for symmetric linear systems", Journal of Computational and
   Applied Mathematics 25 (1989); P. Ghysels and W. Vanroose, "Hiding global synchronization latency in the preconditioned
   Conjugate Gradient algorithm", Parallel Computing 40 (2014).
6. J. D. McCalpin, STREAM: Sustainable Memory Bandwidth in High Performance Computers, https://www.cs.virginia.edu/stream/.
