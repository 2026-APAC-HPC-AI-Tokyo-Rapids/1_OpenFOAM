# experiment-metrics v2

This package is the compute-local v2 collection core. It creates an immutable
run manifest, validates facts against a versioned registry, writes one atomic
fragment per producer, records exact stage execution facts, parses durable
OpenFOAM/Pstream/post-run sources, and merges fragments into `metrics.jsonl`.

The compute-facing paths are credential-free and write only the run directory.
Runner-only CLI branches lazily load artifact packaging and optional BigQuery
publication code; workflow submission and cloud credentials never cross into
PJM. Native OpenFOAM utilities and the Pstream hook produce source files only;
their parsers reduce those files to Facts after the timed stages finish.

Core interfaces include:

```python
init_run(...)
Recorder.open(...)
collect_once(...)
run_stage(...)
merge_run(...)
```

The registry is at `registry/openfoam-v2.toml`, and the fixed run protocol is
at `registry/openfoam-v2-protocol.toml`. Their ownership, logical types, and
expected stage instances are part of the on-disk fact contract.
