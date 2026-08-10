-- BigQuery Standard SQL.
--
-- Fixed-width consumer projection.  JSON-valued facts stay as JSON text so the
-- raw Fact remains the sole owner of the complete object.  Missing or
-- conflicted keys become NULL; no placeholder or reason column is invented.
CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_run_consumer_v2` AS
WITH raw_runs AS (
  SELECT DISTINCT CAST(`run` AS STRING) AS run_id
  FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_metrics`
  WHERE `run` IS NOT NULL
),
conflict_summary AS (
  SELECT
    `run` AS run_id,
    COUNT(DISTINCT `key`) AS conflict_key_count
  FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_run_fact_conflicts_v2`
  GROUP BY run_id
),
pivoted AS (
  SELECT
    `run` AS run_id,
    MAX(IF(`key` = 'run.identity.run_id', `value`, NULL)) AS identity_run_id,
    MAX(IF(`key` = 'run.identity.run_purpose', `value`, NULL)) AS run_purpose,
    MAX(IF(`key` = 'run.identity.repository_id', `value`, NULL)) AS repository_id,
    MAX(IF(`key` = 'run.instrumentation_bundle_sha256', `value`, NULL)) AS instrumentation_bundle_sha256,
    SAFE_CAST(MAX(IF(`key` = 'collection_complete', `value`, NULL)) AS BOOL) AS collection_complete,

    MAX(IF(`key` = 'run.stage.block_mesh.launch', `value`, NULL)) AS stage_block_mesh_launch_json,
    MAX(IF(`key` = 'run.stage.decompose_par.launch', `value`, NULL)) AS stage_decompose_par_launch_json,
    MAX(IF(`key` = 'run.stage.solver.launch', `value`, NULL)) AS stage_solver_launch_json,
    MAX(IF(`key` = 'run.stage.check_mesh.launch', `value`, NULL)) AS stage_check_mesh_launch_json,
    MAX(IF(`key` = 'run.stage.mesh_facts.launch', `value`, NULL)) AS stage_mesh_facts_launch_json,
    MAX(IF(`key` = 'run.stage.partition_audit.launch', `value`, NULL)) AS stage_partition_audit_launch_json,
    MAX(IF(`key` = 'run.stage.minimal_hardware_capture.launch', `value`, NULL)) AS stage_minimal_hardware_launch_json,
    MAX(IF(`key` = 'run.stage.network_imb_mpi1.launch', `value`, NULL)) AS stage_network_imb_mpi1_launch_json,
    MAX(IF(`key` = 'run.stage.block_mesh.termination', `value`, NULL)) AS stage_block_mesh_termination_json,
    MAX(IF(`key` = 'run.stage.decompose_par.termination', `value`, NULL)) AS stage_decompose_par_termination_json,
    MAX(IF(`key` = 'run.stage.solver.termination', `value`, NULL)) AS stage_solver_termination_json,
    MAX(IF(`key` = 'run.stage.check_mesh.termination', `value`, NULL)) AS stage_check_mesh_termination_json,
    MAX(IF(`key` = 'run.stage.mesh_facts.termination', `value`, NULL)) AS stage_mesh_facts_termination_json,
    MAX(IF(`key` = 'run.stage.partition_audit.termination', `value`, NULL)) AS stage_partition_audit_termination_json,
    MAX(IF(`key` = 'run.stage.minimal_hardware_capture.termination', `value`, NULL)) AS stage_minimal_hardware_termination_json,
    MAX(IF(`key` = 'run.stage.network_imb_mpi1.termination', `value`, NULL)) AS stage_network_imb_mpi1_termination_json,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.block_mesh.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_block_mesh_wall_time_sec,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.decompose_par.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_decompose_par_wall_time_sec,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.solver.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_solver_wall_time_sec,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.check_mesh.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_check_mesh_wall_time_sec,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.mesh_facts.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_mesh_facts_wall_time_sec,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.partition_audit.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_partition_audit_wall_time_sec,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.minimal_hardware_capture.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_minimal_hardware_wall_time_sec,
    SAFE_CAST(MAX(IF(`key` = 'perf.stage.network_imb_mpi1.wall_time_sec', `value`, NULL)) AS FLOAT64) AS stage_network_imb_mpi1_wall_time_sec,

    MAX(IF(`key` = 'solver.runtime_header', `value`, NULL)) AS solver_runtime_header_json,
    MAX(IF(`key` = 'solver.step_timings', `value`, NULL)) AS solver_step_timings_json,
    MAX(IF(`key` = 'solver.pressure_solves', `value`, NULL)) AS solver_pressure_solves_json,
    MAX(IF(`key` = 'solver.log_markers', `value`, NULL)) AS solver_log_markers_json,
    MAX(IF(`key` = 'network.imb_mpi1.process_count', `value`, NULL)) AS network_imb_process_count_text,
    MAX(IF(`key` = 'network.imb_mpi1.message_size.min_bytes', `value`, NULL)) AS network_imb_min_bytes_text,
    MAX(IF(`key` = 'network.imb_mpi1.message_size.max_bytes', `value`, NULL)) AS network_imb_max_bytes_text,
    MAX(IF(`key` = 'network.imb_mpi1.iteration.max_per_sample', `value`, NULL)) AS network_imb_max_per_sample_text,
    MAX(IF(`key` = 'network.imb_mpi1.iteration.time_limit_sec', `value`, NULL)) AS network_imb_time_limit_sec_text,
    MAX(IF(`key` = 'network.imb_mpi1.iteration.policy', `value`, NULL)) AS network_imb_iteration_policy,
    MAX(IF(`key` = 'software.imb_mpi1.version', `value`, NULL)) AS software_imb_version
  FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_run_facts_v2`
  GROUP BY run_id
)
SELECT
  runs.run_id,
  pivoted.identity_run_id,
  pivoted.run_purpose,
  pivoted.repository_id,
  pivoted.instrumentation_bundle_sha256,
  pivoted.collection_complete,
  COALESCE(conflicts.conflict_key_count, 0) > 0 AS has_conflicts,
  COALESCE(conflicts.conflict_key_count, 0) AS conflict_key_count,
  pivoted.stage_block_mesh_launch_json,
  pivoted.stage_decompose_par_launch_json,
  pivoted.stage_solver_launch_json,
  pivoted.stage_check_mesh_launch_json,
  pivoted.stage_mesh_facts_launch_json,
  pivoted.stage_partition_audit_launch_json,
  pivoted.stage_minimal_hardware_launch_json,
  pivoted.stage_network_imb_mpi1_launch_json,
  pivoted.stage_block_mesh_termination_json,
  pivoted.stage_decompose_par_termination_json,
  pivoted.stage_solver_termination_json,
  pivoted.stage_check_mesh_termination_json,
  pivoted.stage_mesh_facts_termination_json,
  pivoted.stage_partition_audit_termination_json,
  pivoted.stage_minimal_hardware_termination_json,
  pivoted.stage_network_imb_mpi1_termination_json,
  pivoted.stage_block_mesh_wall_time_sec,
  pivoted.stage_decompose_par_wall_time_sec,
  pivoted.stage_solver_wall_time_sec,
  pivoted.stage_check_mesh_wall_time_sec,
  pivoted.stage_mesh_facts_wall_time_sec,
  pivoted.stage_partition_audit_wall_time_sec,
  pivoted.stage_minimal_hardware_wall_time_sec,
  pivoted.stage_network_imb_mpi1_wall_time_sec,
  JSON_VALUE(pivoted.stage_solver_termination_json, '$.kind') AS solver_termination_kind,
  SAFE_CAST(JSON_VALUE(pivoted.stage_solver_termination_json, '$.code') AS INT64) AS solver_exit_code,
  SAFE_CAST(JSON_VALUE(pivoted.stage_solver_termination_json, '$.signal') AS INT64) AS solver_signal,
  pivoted.solver_runtime_header_json,
  pivoted.solver_step_timings_json,
  pivoted.solver_pressure_solves_json,
  pivoted.solver_log_markers_json,
  SAFE_CAST(pivoted.network_imb_process_count_text AS INT64) AS network_imb_process_count,
  SAFE_CAST(pivoted.network_imb_min_bytes_text AS INT64) AS network_imb_min_bytes,
  SAFE_CAST(pivoted.network_imb_max_bytes_text AS INT64) AS network_imb_max_bytes,
  SAFE_CAST(pivoted.network_imb_max_per_sample_text AS INT64) AS network_imb_max_per_sample,
  SAFE_CAST(pivoted.network_imb_time_limit_sec_text AS INT64) AS network_imb_time_limit_sec,
  pivoted.network_imb_iteration_policy,
  pivoted.software_imb_version
FROM raw_runs AS runs
LEFT JOIN pivoted
  USING (run_id)
LEFT JOIN conflict_summary AS conflicts
  USING (run_id);
