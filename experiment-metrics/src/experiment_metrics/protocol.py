from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunProtocol:
    expected_stages: tuple[str, ...]
    expected_pstream_ranks: int

    @classmethod
    def load(cls, path: Path, purpose: str) -> RunProtocol:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
        root = document.get("protocol")
        variants = document.get("variant")
        if (
            not isinstance(root, dict)
            or set(root) != {"schema_version"}
            or root["schema_version"] != "openfoam-v2-run-protocol/v1"
            or not isinstance(variants, dict)
            or set(variants) != {"bench", "profile"}
        ):
            raise ValueError("protocol must contain exactly its v1 fields")
        variant = variants.get(purpose)
        if not isinstance(variant, dict):
            raise ValueError(f"protocol has no {purpose} variant")
        stages = variant.get("expected_stages")
        ranks = variant.get("expected_pstream_ranks")
        if (
            not isinstance(stages, list)
            or not stages
            or not all(isinstance(stage, str) and stage for stage in stages)
            or len(set(stages)) != len(stages)
            or any(not stage.replace("_", "").isalnum() for stage in stages)
            or not isinstance(ranks, int)
            or isinstance(ranks, bool)
            or ranks <= 0
        ):
            raise ValueError("protocol expected instances are invalid")
        return cls(tuple(stages), ranks)


def default_protocol_path(registry_path: Path) -> Path:
    return registry_path.with_name("openfoam-v2-protocol.toml")
