# 1_OpenFOAM_HPC_Task

## OpenFOAM source mirror

The Genkai workflow builds OpenFOAM from organization-managed repositories. It
uses the following read-only bare mirrors as a shared Git object cache:

```text
/fast/pj26000080/git-mirror/
├── 3_OpenFOAM_Src.git
└── 4_OpenFOAM_ThirdParty_Src.git
```

OpenFOAM is checked out from the organization-managed `master` branch, whose
current release line is v2606. The ThirdParty repository does not have a v2606
tag, so the workflow uses its `main` branch as specified by the source
repository policy.

### One-time initialization

Run the initial download once from an SSH session on a Genkai login node. This
is intentionally not part of the GitHub Actions workflow.

```bash
install -d -m 2775 /fast/pj26000080/git-mirror

git clone --mirror \
  https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/3_OpenFOAM_Src.git \
  /fast/pj26000080/git-mirror/3_OpenFOAM_Src.git
git clone --mirror \
  https://github.com/2026-APAC-HPC-AI-Tokyo-Rapids/4_OpenFOAM_ThirdParty_Src.git \
  /fast/pj26000080/git-mirror/4_OpenFOAM_ThirdParty_Src.git

chgrp -R pj26000080 /fast/pj26000080/git-mirror
chmod -R g+rwX /fast/pj26000080/git-mirror
git -C /fast/pj26000080/git-mirror/3_OpenFOAM_Src.git \
  config core.sharedRepository group
git -C /fast/pj26000080/git-mirror/4_OpenFOAM_ThirdParty_Src.git \
  config core.sharedRepository group
```

The project group owns the directory, and setgid mode on its parent keeps new
entries in that group. Both repositories are caches only; no build job pushes
to them.

### Routine operation

Each source repository updates its own bare mirror from a serialized GitHub
Actions workflow after a push. This repository treats both mirrors as read-only
and only clones from them when a new build is required, so Git objects are not
downloaded again for each build.

The ThirdParty Git repository does not contain unpacked dependency sources. Its
`download-v2606-sources.sh` script retrieves the required archives through the
existing shared source cache and expands them into the build tree. The workflow
does not copy `sources/` from the monolithic ThirdParty release archive.

## Lightweight VTune browser summary

Manual workflow runs accept a `profile_mode` input. Select `vtune-hotspots` to
collect a VTune Hotspots result for the `simpleFoam` stage. The raw result stays
under the private profile directory on Genkai. The bounded trace is uploaded as
a single asset in the rolling `vtune-latest` prerelease:

```text
openfoam-vtune-trace.json
```

The trace uses the Chrome Trace Event format and can be opened by
dragging it into <https://ui.perfetto.dev/>. It contains a bounded timeline and
the hottest functions, not raw samples or call stacks. VTune is inserted with
Intel MPI `-gtool` and observes rank 0 by default instead of the Hydra launcher.
The release link downloads the JSON directly without a ZIP extraction step.
The workflow does not upload PJM logs, solver logs, ParaView cases, or VTune
reports as Actions artifacts. Failure diagnostics are printed into the job log.
Full VTune results, the solver log, and the ParaView case archive stay under
`$HOME/openfoam-profile/<run-id>-<pjm-job-id>/` on Genkai; the exact path is
shown in the Actions run Summary.
The Actions run Summary also shows the ranked functions and CPU times directly
in the browser, so downloading the trace is only needed for the Perfetto view.
Some VTune versions produce no Timeline rows for a Hotspots result. In that
case the exporter reads the CSV report from standard output instead of
`-report-output`. The Perfetto trace contains actual VTune elapsed-time interval
start/end boundaries. It also parses the retained OpenFOAM solver log into
continuous `ClockTime` intervals with iteration ranges, residuals, linear-solver
iteration counts, and continuity errors. Forty measured VTune windows contain
ranked function details. Stable function and MPI/OpenFOAM category tracks use
sampled CPU-time counters. A profiling build additionally instruments six
OpenFOAM regions selected from the preceding Hotspots result with Intel ITT
Task scopes. Their real entry and exit timestamps come from
`CLOCK_MONOTONIC_RAW` and appear as exact function lanes in Perfetto. A
continuous occupancy series is derived from the same boundaries. Per-function
call count, inclusive wall time, p50/p95/p99/max duration, gap percentiles,
call rate, and the fraction of calls shorter than 100 microseconds distinguish
sustained bottlenecks from temporally fragmented work.

The release JSON contains one chronologically contiguous, bounded window of
exact calls plus whole-run statistics and occupancy series. The complete task
interval CSV remains next to the full VTune result on Genkai and is also stored
inside that result using VTune's external interval format. Nested instrumented
regions can overlap, so inclusive times across functions must not be added
together.

The defaults can be overridden in the PJM environment:

```text
OPENFOAM_VTUNE_RANK=0
OPENFOAM_VTUNE_TIME_BINS=300
OPENFOAM_VTUNE_TOP_FUNCTIONS=50
OPENFOAM_VTUNE_FUNCTION_BINS=40
OPENFOAM_VTUNE_FUNCTION_REPORT_LIMIT=0
OPENFOAM_VTUNE_FUNCTIONS_PER_WINDOW=8
OPENFOAM_VTUNE_TIME_SERIES_FUNCTIONS=12
OPENFOAM_VTUNE_MAX_TASK_EVENTS=1500
OPENFOAM_VTUNE_TASK_OCCUPANCY_BINS=60
OPENFOAM_VTUNE_MAX_TRACE_BYTES=500000
OPENFOAM_TASK_TRACE_MAX_EVENTS=1000000
```

`OPENFOAM_VTUNE_FUNCTION_REPORT_LIMIT=0` keeps every function reported in each
time window on Genkai. Only the bounded window details and selected time series
are copied into the release JSON.

To regenerate the lightweight JSON from a retained Genkai result without
rerunning OpenFOAM, set the manual workflow input `existing_profile_run_id` to
the retained profile directory name. This replaces the same rolling release
asset and creates no Actions artifact.

`perf-stat` remains the default profile mode for push runs and manual runs.
