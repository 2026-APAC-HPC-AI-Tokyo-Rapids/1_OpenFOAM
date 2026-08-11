from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_direct_raw_migration_recreates_only_three_string_columns() -> None:
    sql = (ROOT / "sql/migrate_direct_raw.sql").read_text(encoding="utf-8")
    assert "DROP TABLE IF EXISTS" in sql
    assert "DROP VIEW IF EXISTS" in sql
    schema = (
        "openfoam_metrics`\n"
        "(run STRING NOT NULL, key STRING NOT NULL, value STRING NOT NULL)"
    )
    assert schema in sql


def test_runtime_has_no_merge_or_metrics_sidecar_implementation() -> None:
    package = ROOT / "experiment-metrics/src/experiment_metrics"
    assert not (package / "merge.py").exists()
    assert not (package / "projections.py").exists()
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    assert "metrics.jsonl" not in workflow
    assert " merge --manifest" not in workflow
    assert " publish --manifest" not in workflow
