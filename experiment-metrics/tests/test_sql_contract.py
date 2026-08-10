from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / "sql"


def _read(name: str) -> str:
    return (SQL / name).read_text(encoding="utf-8").lower()


def test_openfoam_sql_contract_has_conflict_safe_layers() -> None:
    facts = _read("openfoam_run_facts_v2.sql")
    conflicts = _read("openfoam_run_fact_conflicts_v2.sql")
    consumer = _read("openfoam_run_consumer_v2.sql")

    assert "create or replace view" in facts
    assert "openfoam_run_facts_v2" in facts
    assert "select distinct" in facts
    assert "count(*)" in facts
    assert "distinct_value_count = 1" in facts
    assert "openfoam_metrics" in facts
    assert "as `run`" in facts
    assert "as `key`" in facts
    assert "as `value`" in facts

    assert "openfoam_run_fact_conflicts_v2" in conflicts
    assert "select distinct" in conflicts
    assert "having count(*) > 1" in conflicts
    assert "openfoam_metrics" in conflicts
    assert "as `run`" in conflicts
    assert "as `key`" in conflicts
    assert "as `value`" in conflicts

    assert "openfoam_run_consumer_v2" in consumer
    assert "openfoam_run_facts_v2" in consumer
    assert "openfoam_run_fact_conflicts_v2" in consumer
    assert "collection_complete" in consumer
    assert "has_conflicts" in consumer
    assert "solver_step_timings_json" in consumer
    assert "stage_solver_wall_time_sec" in consumer
    assert "any_value(" not in consumer


def test_openfoam_sql_is_read_only_ddl() -> None:
    for path in SQL.glob("openfoam_*_v2.sql"):
        text = path.read_text(encoding="utf-8").lower()
        assert "delete " not in text
        assert "insert " not in text
        assert "update " not in text
        assert "drop table" not in text


def test_artifact_projection_sql_covers_registry_physical_and_logical_relations() -> (
    None
):
    from experiment_metrics.registry import Registry

    registry = Registry.load(ROOT / "experiment-metrics/registry/openfoam-v2.toml")
    projection_sql = _read("openfoam_artifact_projections_v2.sql")

    for projection in registry.artifact_projections:
        assert f".{projection.base_table_id}`" in projection_sql
        assert f".{projection.relation_id}`" in projection_sql
        assert f".{projection.conflict_relation_id}`" in projection_sql
    assert "count(distinct _source_instance_sha256) > 1" in projection_sql
    assert "count(distinct _payload_sha256) > 1" in projection_sql
    assert "row_number() over (partition by _payload_sha256" in projection_sql
    assert "openfoam_workload_manifests_raw_v2` as parent" in projection_sql
