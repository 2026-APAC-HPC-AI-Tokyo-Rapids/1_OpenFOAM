from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    project: str
    dataset: str
    table: str
    location: str


def load_bigquery_config(path: Path | None = None) -> BigQueryConfig:
    pyproject = path or _find_pyproject()
    with pyproject.open("rb") as stream:
        document = tomllib.load(stream)
    section = document["tool"]["experiment-metrics"]["bigquery"]
    values = {
        name: section[name] for name in ("project", "dataset", "table", "location")
    }
    if not all(isinstance(value, str) and value for value in values.values()):
        raise ValueError("BigQuery configuration values must be non-empty strings")
    return BigQueryConfig(**values)


def _find_pyproject() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("experiment-metrics pyproject.toml was not found")
