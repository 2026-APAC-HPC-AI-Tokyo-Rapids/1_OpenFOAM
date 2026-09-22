from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .workload import load_workload_definition


@dataclass(frozen=True, slots=True)
class RunProtocol:
    expected_stages: tuple[str, ...]
    nodes: int
    ranks: int
    resource_group: str
    runtime_condition: str
    transport_policy: str
    transport_environment: dict[str, str]
    workload_id: str
    expected_workload_identity: str
    iteration_target: int
    expected_cells: int
    solver: str
    distribution: str
    release: str

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
            or set(root) != {"schema_version", "workload_definition"}
            or root["schema_version"] != "openfoam-v2-run-protocol/v2"
            or not isinstance(variants, dict)
            or set(variants) != {"bench", "profile"}
        ):
            raise ValueError("実験条件にv2で定義された項目以外が含まれています")
        variant = variants.get(purpose)
        if not isinstance(variant, dict):
            raise ValueError(f"protocol has no {purpose} variant")
        required = {
            "expected_stages",
            "nodes",
            "ranks",
            "resource_group",
            "transport_policy",
            "transport_environment",
        }
        allowed = required | {"runtime_condition"}
        if not required.issubset(variant) or not set(variant).issubset(allowed):
            raise ValueError("protocol variant must contain exactly its v1 fields")
        stages = variant["expected_stages"]
        nodes = variant["nodes"]
        ranks = variant["ranks"]
        resource_group = variant["resource_group"]
        runtime_condition = variant.get("runtime_condition", "baseline")
        transport = variant["transport_policy"]
        transport_environment = variant["transport_environment"]
        if not isinstance(root["workload_definition"], str):
            raise ValueError("実験条件の課題定義パスが無効です")
        workload_path = (path.parent / root["workload_definition"]).resolve(strict=True)
        workload = load_workload_definition(workload_path)
        workload_id = workload.workload_id
        workload_identity = workload.case_identity
        expected_cells = workload.expected_cells
        solver = workload.solver
        distribution = workload.distribution
        release = workload.release
        iteration_target = workload.iteration_for(nodes)
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
            or runtime_condition not in {"baseline", "poll-proc-interfaces"}
            or not isinstance(transport, str)
            or not transport
            or (nodes > 1 and transport == "shm")
            or not isinstance(transport_environment, dict)
            or not all(
                isinstance(name, str)
                and name
                and name.replace("_", "").isalnum()
                and isinstance(value, str)
                and value
                for name, value in transport_environment.items()
            )
        ):
            raise ValueError("protocol expected instances are invalid")
        return cls(
            tuple(stages),
            nodes,
            ranks,
            resource_group,
            runtime_condition,
            transport,
            dict(transport_environment),
            workload_id,
            workload_identity,
            iteration_target,
            expected_cells,
            solver,
            distribution,
            release,
        )


def default_protocol_path(registry_path: Path) -> Path:
    return registry_path.with_name("openfoam-v2-protocol-scotch-1n-120r.toml")
