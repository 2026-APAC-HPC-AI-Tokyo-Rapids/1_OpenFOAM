-- BigQuery Standard SQL.
--
-- The source table deliberately remains the three-column raw Fact table.  Exact
-- duplicate rows are collapsed here.  A key with more than one distinct value
-- is excluded from this canonical relation; its lossless values are exposed by
-- openfoam_run_fact_conflicts_v2 instead.
CREATE OR REPLACE VIEW `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_run_facts_v2` AS
WITH distinct_facts AS (
  SELECT DISTINCT
    CAST(`run` AS STRING) AS run_id,
    CAST(`key` AS STRING) AS fact_key,
    CAST(`value` AS STRING) AS fact_value
  FROM `apac-hpc-ai-tokyo-rapids-26.openfoam_experiment_metrics.openfoam_metrics`
  WHERE `run` IS NOT NULL
    AND `key` IS NOT NULL
    AND `value` IS NOT NULL
),
key_cardinality AS (
  SELECT
    run_id,
    fact_key,
    COUNT(*) AS distinct_value_count
  FROM distinct_facts
  GROUP BY run_id, fact_key
)
SELECT
  facts.run_id AS `run`,
  facts.fact_key AS `key`,
  facts.fact_value AS `value`
FROM distinct_facts AS facts
JOIN key_cardinality AS cardinality
  USING (run_id, fact_key)
WHERE cardinality.distinct_value_count = 1;
