# Roofline cache-bandwidth calibration

The fresh ASPIRE-2A calibration completed successfully as PBS job `26004695.pbs101` on `x1001c5s0b0n0`, using one exclusive node and 128 pinned physical cores. PBS recorded exit status 0 and 17 seconds of wall time. A post-completion `qstat -u apacsc14` check listed no remaining calibration jobs.

The original supplied process combined the required four read measurements with an optional adaptive FP64 FMA phase under one 60-second timeout. The read phase completed and emitted valid checksums, but the process timed out in the optional FMA phase without a diagnostic line. The supplied disassembly confirmed that the compiler retained the 12 AVX2 `vfmadd132pd` instructions and eight AVX2 read accumulators. The corrected source keeps an explicit `fma` mode for audit while the calibration script invokes only `all_cache` and `one_per_l3`, so optional FMA cannot invalidate cache results.

Verified 128-core useful sequential-read medians are:

| Working set | Median | Three runs | Units |
|---|---:|---|---|
| L1, 16 KiB/core | 15,311.449 | 15,263.105 / 15,335.450 / 15,311.449 | GB/s useful bytes |
| L2, 256 KiB/core | 7,984.958 | 7,984.958 / 7,891.566 / 8,448.244 | GB/s useful bytes |
| L3, 2 MiB/core, 16 MiB/L3 group | 4,413.147 | 4,412.923 / 4,417.100 / 4,413.147 | GB/s useful bytes |
| DRAM, 256 MiB/core, 32 GiB total | 359.943 | 358.957 / 360.054 / 359.943 | GB/s useful bytes |

These are useful sequential read bytes, not interface-counter traffic and not solver-stage byte counts. The optional 16-thread one-per-L3 results are preserved as context only and are not extrapolated to the 128-core node.

The compute ceiling is nominal, not measured: 4,096 GFLOP/s from `128 cores × 2.00 GHz base × 16 FP64 FLOP/cycle` for the EPYC 7713 node. No empirical FP64 FMA result is used.

Artifacts:

- [summary.json](summary.json)
- [corrected source](src/cache_read_cache_only.c)
- [corrected PBS script](jobs/calibrate-cache-only.pbs)
- [raw run directory](raw/attempt-cache-only-20261026/)
- [original supplied source/script copies](raw/supplied/)

## Published evidence

The original text outputs and supplied input snapshots are retained under `raw/`. The compiled calibration executable and agent conversation/prompt files remain local; the executable can be rebuilt from the recorded source and compiler command. Cache bandwidth is a standalone useful-read measurement. The FP64 compute roof is nominal, not measured.
