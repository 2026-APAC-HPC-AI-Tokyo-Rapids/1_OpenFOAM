from pathlib import Path

from experiment_metrics.config import load_bigquery_config


def test_load_bigquery_config_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[tool.experiment-metrics.bigquery]\n"
        'project = "project-id"\n'
        'dataset = "dataset_id"\n'
        'table = "table_id"\n'
        'location = "asia-northeast1"\n',
        encoding="utf-8",
    )

    config = load_bigquery_config(pyproject)

    assert config.project == "project-id"
    assert config.dataset == "dataset_id"
    assert config.table == "table_id"
    assert config.location == "asia-northeast1"
