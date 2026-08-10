from decimal import Decimal

import pytest

from experiment_metrics.fact import (
    Fact,
    canonical_json,
    encode_value,
    validate_encoded_value,
)


def test_canonical_json_is_sorted_and_uses_jcs_number_spelling() -> None:
    assert canonical_json({"z": 1.0, "a": [True, 1e-7, -0.0]}) == (
        '{"a":[true,1e-7,0],"z":1}'
    )


def test_decimal_is_explicit_registry_value_not_json_number() -> None:
    assert encode_value(Decimal("12.3400"), "decimal") == "12.34"
    with pytest.raises(TypeError):
        canonical_json(Decimal("1.2"))


def test_fact_is_transport_free() -> None:
    fact = Fact("probe.name", "value")
    assert fact.key == "probe.name"
    assert fact.logical_value == "value"


def test_encoded_value_validation_rejects_noncanonical_fragment_data() -> None:
    validate_encoded_value('{"a":1}', "json")
    with pytest.raises(ValueError, match="not canonical"):
        validate_encoded_value('{"a":1.0}', "json")
    with pytest.raises(ValueError, match="not canonical"):
        validate_encoded_value("01", "integer")
