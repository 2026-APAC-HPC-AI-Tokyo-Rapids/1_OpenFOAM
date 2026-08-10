from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class KeySpec:
    pattern: str
    owner: str
    logical_type: str
    required_for: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProducerSpec:
    identifier: str
    required_for: frozenset[str]


@dataclass(frozen=True, slots=True)
class Registry:
    schema_version: str
    keys: tuple[KeySpec, ...]
    producers: tuple[ProducerSpec, ...]

    @classmethod
    def load(cls, path: Path) -> Registry:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
        root = document.get("registry")
        if not isinstance(root, dict) or not isinstance(
            root.get("schema_version"), str
        ):
            raise ValueError("registry.schema_version is required")
        keys = tuple(_key_spec(item) for item in document.get("keys", []))
        producers = tuple(
            _producer_spec(item) for item in document.get("producers", [])
        )
        if not keys or not producers:
            raise ValueError("registry must declare keys and producers")
        if len({item.identifier for item in producers}) != len(producers):
            raise ValueError("registry producer IDs must be unique")
        return cls(root["schema_version"], keys, producers)

    def spec_for(self, key: str) -> KeySpec:
        matches = [item for item in self.keys if fnmatch.fnmatchcase(key, item.pattern)]
        if len(matches) != 1:
            raise ValueError(f"key {key!r} has {len(matches)} registry matches")
        return matches[0]

    def producer(self, identifier: str) -> ProducerSpec:
        matches = [item for item in self.producers if item.identifier == identifier]
        if len(matches) != 1:
            raise ValueError(f"unknown producer: {identifier}")
        return matches[0]

    def required_producers(self, purpose: str) -> frozenset[str]:
        return frozenset(
            item.identifier for item in self.producers if purpose in item.required_for
        )

    def required_keys(
        self, purpose: str, *, expected_pstream_ranks: int
    ) -> frozenset[str]:
        """Expand every required pattern, rejecting undeclared axis semantics."""

        required: set[str] = set()
        for item in self.keys:
            if purpose not in item.required_for:
                continue
            if "*" not in item.pattern:
                required.add(item.pattern)
            elif item.pattern in _PSTREAM_RANK_PATTERNS:
                required.update(
                    item.pattern.replace("*", str(rank))
                    for rank in range(expected_pstream_ranks)
                )
            else:
                raise ValueError(
                    f"required wildcard has no protocol axis expansion: {item.pattern}"
                )
        return frozenset(required)


def _key_spec(item: object) -> KeySpec:
    if not isinstance(item, dict):
        raise ValueError("registry keys must be objects")
    pattern = item.get("pattern")
    owner = item.get("owner")
    logical_type = item.get("logical_type")
    required_for = _purposes(item.get("required_for"))
    if not all(
        isinstance(value, str) and value for value in (pattern, owner, logical_type)
    ):
        raise ValueError("registry key pattern, owner, and logical_type are required")
    return KeySpec(pattern, owner, logical_type, required_for)


def _producer_spec(item: object) -> ProducerSpec:
    if not isinstance(item, dict):
        raise ValueError("registry producers must be objects")
    identifier = item.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("registry producer id is required")
    return ProducerSpec(identifier, _purposes(item.get("required_for")))


def _purposes(value: object) -> frozenset[str]:
    if not isinstance(value, list) or not all(
        item in {"bench", "profile"} for item in value
    ):
        raise ValueError("registry required_for must contain bench and/or profile")
    return frozenset(value)


_PSTREAM_RANK_PATTERNS = frozenset(
    {
        "solver.pstream.startup_applied.rank.*",
        "solver.pstream.runtime_current.rank.*",
        "solver.pstream.change_events.rank.*",
    }
)
