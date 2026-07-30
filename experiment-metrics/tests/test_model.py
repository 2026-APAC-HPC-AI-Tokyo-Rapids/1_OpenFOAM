from experiment_metrics.model import scalar


def test_scalar_encodes_supported_values() -> None:
    assert scalar(True) == "true"
    assert scalar(False) == "false"
    assert scalar(12) == "12"
    assert scalar(1.25) == "1.25"
    assert scalar(None) == ""


def test_scalar_replaces_non_finite_float_with_empty_value() -> None:
    assert scalar(float("nan")) == ""
    assert scalar(float("inf")) == ""
