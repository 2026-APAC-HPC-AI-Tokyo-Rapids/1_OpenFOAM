-- BigQuery Standard SQL.  Physical base tables are append-only publisher sinks.
-- The four underscore-prefixed columns are publisher lineage metadata; logical
-- relations expose only the closed projection/v1 payload fields.

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  run_id STRING NOT NULL, run_purpose STRING NOT NULL,
  repository_identity STRING NOT NULL, object_hash_algorithm STRING NOT NULL,
  score_reference_commit STRING, profile_base_commit STRING,
  source_head_commit STRING NOT NULL, source_track_manifest_sha256 STRING NOT NULL,
  source_member STRING NOT NULL, source_sha256 STRING NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  precision STRING NOT NULL, label_bits INT64 NOT NULL, compile_flags JSON NOT NULL,
  commits JSON NOT NULL, build_archive_sha256 STRING NOT NULL,
  toolchain_observations JSON NOT NULL, runtime_objects JSON NOT NULL,
  source_member STRING NOT NULL, source_sha256 STRING NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  run_id STRING NOT NULL, build_sidecar_sha256 STRING NOT NULL,
  executables JSON NOT NULL, ldd_sources JSON NOT NULL,
  launcher_version JSON NOT NULL, profiler_version JSON NOT NULL,
  resolved_libmpi_path STRING, resolved_libmpi_sha256 STRING,
  source_member STRING NOT NULL, source_sha256 STRING NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  subject_kind STRING NOT NULL, subject_id STRING NOT NULL,
  node_ordinal INT64 NOT NULL, hostname STRING NOT NULL,
  cpu_identity JSON NOT NULL, platform_settings JSON NOT NULL,
  source_member STRING NOT NULL, source_sha256 STRING NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  subject_kind STRING NOT NULL, subject_id STRING NOT NULL,
  workload_identity STRING NOT NULL, source_member STRING NOT NULL,
  source_sha256 STRING NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_members_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  subject_kind STRING NOT NULL, subject_id STRING NOT NULL,
  path STRING NOT NULL, content_b64 STRING NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  run_id STRING NOT NULL, node_ordinal INT64 NOT NULL, hostname STRING NOT NULL,
  record_kind STRING NOT NULL, numa_node_id INT64,
  postrun_mem_available_bytes INT64, cpulist STRING,
  mem_total_bytes INT64, mem_free_bytes INT64, source_members JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, schema_version STRING NOT NULL,
  run_id STRING NOT NULL, global_rank INT64 NOT NULL, event_name STRING NOT NULL,
  raw_count_lexeme STRING NOT NULL, count FLOAT64, unit STRING,
  running_ns_lexeme STRING NOT NULL, running_ns FLOAT64,
  percent_running_lexeme STRING NOT NULL, percent_running FLOAT64,
  metric_value_lexeme STRING NOT NULL, metric_unit STRING,
  source_member STRING NOT NULL, source_sha256 STRING NOT NULL
);

CREATE TABLE IF NOT EXISTS `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_base_v2` (
  _projection_id STRING NOT NULL, _source_instance_key STRING,
  _source_instance_sha256 STRING, _row_grain_key STRING NOT NULL,
  _payload_sha256 STRING NOT NULL, run_id STRING NOT NULL,
  benchmark STRING NOT NULL, process_count INT64 NOT NULL,
  message_bytes INT64 NOT NULL, iterations INT64 NOT NULL,
  time_min_us FLOAT64, time_avg_us FLOAT64, time_max_us FLOAT64,
  bandwidth_mbytes_per_sec FLOAT64, source_member STRING NOT NULL
);

-- Direct-lineage conflict views apply source-instance conflict before row-grain
-- conflict.  Exact payload replays therefore never become conflicts.
CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key)
LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_raw_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_source_tracks_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key) LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_raw_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provenance_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key) LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_raw_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_build_provisions_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key) LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_raw_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_minimal_hardware_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key) LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_raw_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;

-- Child rows have no direct source-instance identity.  A parent conflict or a
-- differing child payload at the same grain excludes the child from consumers.
CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_members_conflicts_v2` AS
WITH grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_members_base_v2`
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
), parent_conflicts AS (
  SELECT DISTINCT subject_kind, subject_id
  FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_conflicts_v2`
)
SELECT base.*, IF(parent_conflicts.subject_id IS NULL, 'row_grain', 'parent') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_members_base_v2` AS base
LEFT JOIN grain_conflicts USING (_row_grain_key)
LEFT JOIN parent_conflicts USING (subject_kind, subject_id)
WHERE grain_conflicts._row_grain_key IS NOT NULL OR parent_conflicts.subject_id IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_members_raw_v2` AS
SELECT members.* EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_members_base_v2` AS members
JOIN `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_manifests_raw_v2` AS parent
  USING (subject_kind, subject_id)
WHERE members._payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_workload_members_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY members._payload_sha256 ORDER BY members._payload_sha256) = 1;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key) LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_raw_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_profile_hardware_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key) LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_perf_counters_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_conflicts_v2` AS
WITH instance_conflicts AS (
  SELECT _source_instance_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_base_v2`
  GROUP BY _source_instance_key HAVING COUNT(DISTINCT _source_instance_sha256) > 1
), grain_conflicts AS (
  SELECT _row_grain_key FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_base_v2`
  WHERE _source_instance_key NOT IN (SELECT _source_instance_key FROM instance_conflicts)
  GROUP BY _row_grain_key HAVING COUNT(DISTINCT _payload_sha256) > 1
)
SELECT base.*, IF(instance_conflicts._source_instance_key IS NULL, 'row_grain', 'source_instance') AS conflict_kind
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_base_v2` AS base
LEFT JOIN instance_conflicts USING (_source_instance_key) LEFT JOIN grain_conflicts USING (_row_grain_key)
WHERE instance_conflicts._source_instance_key IS NOT NULL OR grain_conflicts._row_grain_key IS NOT NULL;

CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_v2` AS
SELECT * EXCEPT (_projection_id, _source_instance_key, _source_instance_sha256, _row_grain_key, _payload_sha256)
FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_base_v2`
WHERE _payload_sha256 NOT IN (SELECT _payload_sha256 FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.mpi_network_results_conflicts_v2`)
QUALIFY ROW_NUMBER() OVER (PARTITION BY _payload_sha256 ORDER BY _payload_sha256) = 1;
