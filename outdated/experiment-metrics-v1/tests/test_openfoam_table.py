from pathlib import Path

from experiment_metrics.readers.openfoam_table import read_table, split_tokens, vector


def test_split_tokens_keeps_vector_as_one_value() -> None:
    assert split_tokens("3000 (1 2 3) 4") == ["3000", "(1 2 3)", "4"]


def test_read_table_selects_header_and_rows(tmp_path: Path) -> None:
    table_path = tmp_path / "coefficient.dat"
    table_path.write_text(
        "# Time Cd Cl CmPitch\n2999 0.4 0.1 0.01\n3000 0.5 0.2 0.02\n",
        encoding="utf-8",
    )
    table = read_table(table_path)
    assert table.last()["Cd"] == "0.5"
    assert len(table.tail(100)) == 2


def test_vector_returns_empty_components_for_missing_value() -> None:
    assert vector("") == ["", "", ""]
