from __future__ import annotations

import json
from pathlib import Path

from experiment_metrics import init_run
from experiment_metrics.environment import capture_snapshot
from experiment_metrics.execution_context import record_execution_context
from experiment_metrics.fact import canonical_json

REGISTRY = Path(__file__).parents[1] / "registry/openfoam-v2.toml"
FIXTURES = Path(__file__).parent / "fixtures"
WORKLOAD = Path(__file__).parents[2] / "benchmark/workload.json"


def test_execution_context_validates_two_node_rank_and_transport_axes(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    manifest = init_run(None, tmp_path, identities, registry_path=REGISTRY)
    run_dir = manifest.parents[1]
    protocol = tmp_path / "protocol.toml"
    protocol.write_text(
        f"""
[protocol]
schema_version = "openfoam-v2-run-protocol/v2"
workload_definition = "{WORKLOAD}"
[variant.bench]
expected_stages = ["solver"]
nodes = 2
ranks = 2
resource_group = "test"
transport_policy = "ofi"
transport_environment = {{ I_MPI_FABRICS = "ofi" }}
[variant.profile]
expected_stages = ["solver"]
nodes = 2
ranks = 2
resource_group = "test"
transport_policy = "ofi"
transport_environment = {{ I_MPI_FABRICS = "ofi" }}
""".strip()
        + "\n"
    )
    env_root = run_dir / "source/env"
    placement_root = run_dir / "source/placement"
    env_root.mkdir(parents=True)
    placement_root.mkdir(parents=True)
    host = env_root / "host-exec.snapshot"
    common = {b"I_MPI_FABRICS": b"ofi", b"RUN_ID": run_dir.name.encode()}
    capture_snapshot(host, common)
    for rank, hostname in enumerate(("node-a", "node-b")):
        placement = {
            "schema_version": "rank-placement/v1",
            "run_id": run_dir.name,
            "global_rank": rank,
            "node_ordinal": rank,
            "local_rank": 0,
            "local_size": 1,
            "hostname": hostname,
            "cpu_affinity": [rank],
            "numa_mems": "0",
        }
        (placement_root / f"rank-{rank}.json").write_text(
            canonical_json(placement) + "\n"
        )
    request = run_dir / "control/scheduler-request.json"
    request.write_text(
        canonical_json(
            {
                "schema_version": "scheduler-request/v1",
                "nodes": 2,
                "ranks": 2,
                "iterations": 80,
                "workload_id": "occDrivAerStaticMesh-65M",
                "distribution": "OpenFOAM.com",
                "release": "v2512",
                "solver": "simpleFoam",
                "resource_group": "test",
                "runtime_condition": "baseline",
                "transport_policy": "ofi",
            }
        )
        + "\n"
    )
    accounting = run_dir / "control/scheduler-accounting.json"
    accounting.write_text(
        canonical_json(
            {
                "schema_version": "scheduler-accounting/v2",
                "nnumu": {"lexeme": "2", "value": 2},
            }
        )
        + "\n"
    )
    decomposition = run_dir / "source/mesh/decomposeParDict"
    decomposition.parent.mkdir(parents=True)
    decomposition.write_text("numberOfSubdomains 2;\n")
    solver = run_dir / "logs/solver.log"
    solver.write_text((FIXTURES / "solver-valid.log").read_text())

    fragment = record_execution_context(
        manifest_path=manifest,
        runtime_dir=run_dir,
        protocol_path=protocol,
        host_snapshot=host,
        placement_root=placement_root,
        scheduler_request=request,
        scheduler_accounting=accounting,
        decompose_dictionary=decomposition,
        solver_log=solver,
    )

    rows = [json.loads(line) for line in fragment.read_text().splitlines()]
    values = {row["key"]: row["value"] for row in rows}
    keys = set(values)
    assert "parallel.rank_placement" in keys
    assert values["env.I_MPI_FABRICS"] == "ofi"
    assert values["env.RUN_ID"] == run_dir.name
    assert not any(key.startswith("env.host_exec") for key in keys)
