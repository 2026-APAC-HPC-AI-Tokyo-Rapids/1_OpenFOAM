from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .manifest import SHA256


@dataclass(frozen=True, slots=True)
class RunProtocol:
    expected_stages: tuple[str, ...]
    nodes: int
    ranks: int
    resource_group: str
    transport_policy: str
    workload_id: str
    expected_workload_identity: str

    @property
    def expected_pstream_ranks(self) -> int:
        return self.ranks

    @property
    def ranks_per_node(self) -> int:
        return self.ranks // self.nodes

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
        required = {
            "expected_stages",
            "nodes",
            "ranks",
            "resource_group",
            "transport_policy",
            "workload_id",
            "expected_workload_identity",
        }
        if set(variant) != required:
            raise ValueError("protocol variant must contain exactly its v1 fields")
        stages = variant["expected_stages"]
        nodes = variant["nodes"]
        ranks = variant["ranks"]
        resource_group = variant["resource_group"]
        transport = variant["transport_policy"]
        workload_id = variant["workload_id"]
        workload_identity = variant["expected_workload_identity"]
        if (
            not isinstance(stages, list)
            or not stages
            or not all(isinstance(stage, str) and stage for stage in stages)
            or len(set(stages)) != len(stages)
            or any(not stage.replace("_", "").isalnum() for stage in stages)
            or not isinstance(ranks, int)
            or isinstance(ranks, bool)
            or ranks <= 0
            or not isinstance(nodes, int)
            or isinstance(nodes, bool)
            or nodes <= 0
            or ranks % nodes
            or not isinstance(resource_group, str)
            or not resource_group
            or not isinstance(transport, str)
            or not transport
            or (nodes > 1 and transport == "shm")
            or not isinstance(workload_id, str)
            or not workload_id
            or not isinstance(workload_identity, str)
            or SHA256.fullmatch(workload_identity) is None
        ):
            raise ValueError("protocol expected instances are invalid")
        return cls(
            tuple(stages),
            nodes,
            ranks,
            resource_group,
            transport,
            workload_id,
            workload_identity,
        )


def default_protocol_path(registry_path: Path) -> Path:
    return registry_path.with_name("openfoam-v2-protocol-scotch-1n-120r.toml")
