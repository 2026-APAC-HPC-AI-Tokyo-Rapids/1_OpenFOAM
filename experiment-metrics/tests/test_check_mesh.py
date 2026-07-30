from experiment_metrics.readers.check_mesh import parse


def test_check_mesh_reads_values_without_checking_suffix() -> None:
    values = parse(
        "    points: 123 anything\n"
        "    cells: 45\n"
        "    Max skewness = 2.5 arbitrary text\n"
        "Mesh OK.\n"
    )
    assert values["mesh.point_count"] == "123"
    assert values["mesh.cell_count"] == "45"
    assert values["mesh.quality.max_skewness"] == "2.5"
    assert values["mesh.quality.valid"] == "true"
