# experiment-metrics v2

Each OpenFOAM producer writes a diagnostic JSONL fragment with atomic rename
and immediately appends the same `run`, `key`, `value` rows to BigQuery. Values
are encoded without an owner/type registry. BigQuery writes use 500-row chunks,
no `insertId`, no retry, and allow duplicates. Transport failures are warnings
and never change solver or workflow results.

The workflow creates a mode-0600 credential file inside the run directory and
passes only its path to PJM. Credential transport variables are omitted from
environment snapshots and the file is excluded from artifacts and removed at
cleanup. Runner and compute smoke rows verify both network paths before solver
work. Producer fragments remain diagnostic artifacts; there is no merge,
`metrics.jsonl`, physical projection, consumer view, conflict table, or replay.

The run protocol remains separate because node/rank/stage settings are required
to execute the job. OpenFOAM case preparation continues to use only the
prepare-script SHA cache identity.
