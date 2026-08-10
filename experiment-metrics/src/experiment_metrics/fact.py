from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias

import rfc8785

LogicalValue: TypeAlias = (
    str | bool | int | Decimal | bytes | Mapping[str, object] | Sequence[object]
)


@dataclass(frozen=True, slots=True)
class Fact:
    """A domain observation before registry-driven encoding.

    The run ID, producer, persistence destination, and transport are all
    intentionally outside this object.
    """

    key: str
    logical_value: LogicalValue


def encode_value(value: LogicalValue, logical_type: str) -> str:
    if logical_type == "string":
        if not isinstance(value, str):
            raise TypeError("string facts require str values")
        return value
    if logical_type == "boolean":
        if not isinstance(value, bool):
            raise TypeError("boolean facts require bool values")
        return "true" if value else "false"
    if logical_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError("integer facts require int values")
        return str(value)
    if logical_type == "decimal":
        if not isinstance(value, Decimal) or not value.is_finite():
            raise TypeError("decimal facts require finite Decimal values")
        return _decimal_text(value)
    if logical_type == "bytes_base64":
        if not isinstance(value, bytes):
            raise TypeError("bytes_base64 facts require bytes values")
        return base64.b64encode(value).decode("ascii")
    if logical_type == "json":
        return canonical_json(value)
    raise ValueError(f"unsupported logical type: {logical_type}")


def canonical_json(value: object) -> str:
    """Encode strict RFC 8785 JSON; decimal facts stay outside JSON numbers."""

    _validate_json_value(value)
    try:
        return rfc8785.dumps(value).decode("utf-8")
    except (rfc8785.CanonicalizationError, UnicodeError) as error:
        raise ValueError(str(error)) from error


def validate_encoded_value(value: str, logical_type: str) -> None:
    """Reject corrupted fragment rows that were not written by ``Recorder``."""

    if logical_type == "string":
        return
    if logical_type == "boolean":
        if value not in {"true", "false"}:
            raise ValueError("boolean value is not canonical")
        return
    if logical_type == "integer":
        if not re.fullmatch(r"0|-?[1-9][0-9]*", value):
            raise ValueError("integer value is not canonical")
        return
    if logical_type == "decimal":
        try:
            decimal = Decimal(value)
        except Exception as error:  # Decimal has several public exception types.
            raise ValueError("decimal value is invalid") from error
        if not decimal.is_finite() or _decimal_text(decimal) != value:
            raise ValueError("decimal value is not canonical")
        return
    if logical_type == "bytes_base64":
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError as error:
            raise ValueError("base64 value is invalid") from error
        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("base64 value is not canonical")
        return
    if logical_type == "json":
        try:
            decoded = json.loads(
                value,
                object_pairs_hook=_unique_object,
                parse_constant=lambda constant: _reject_constant(constant),
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("JSON value is invalid") from error
        if canonical_json(decoded) != value:
            raise ValueError("JSON value is not canonical")
        return
    raise ValueError(f"unsupported logical type: {logical_type}")


def _validate_json_value(value: object) -> None:
    if value is None or isinstance(value, (bool, int, float, str)):
        return
    if isinstance(value, Decimal):
        raise TypeError("canonical JSON does not accept Decimal")
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("canonical JSON object keys must be strings")
        for child in value.values():
            _validate_json_value(child)
        return
    if isinstance(value, list):
        for child in value:
            _validate_json_value(child)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        raise TypeError("canonical JSON arrays must be lists")
    raise TypeError(f"value cannot be represented in canonical JSON: {type(value)!r}")


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(constant: str) -> None:
    raise ValueError(f"non-finite JSON number: {constant}")
