from experiment_metrics.model import Metric
from experiment_metrics.sender import _insert_id, _rows


def test_rows_have_only_three_table_columns() -> None:
    rows = _rows(
        "run-1",
        [Metric("mesh.cell_count", "100"), Metric("vector", ["1", "2", "3"])],
    )
    assert rows[0]["json"] == {
        "run": "run-1",
        "key": "mesh.cell_count",
        "value": "100",
    }
    assert rows[1]["json"] == {
        "run": "run-1",
        "key": "vector",
        "value": "['1', '2', '3']",
    }


def test_insert_id_is_stable() -> None:
    metric = Metric("key", "")
    assert _insert_id("run", metric) == _insert_id("run", metric)
