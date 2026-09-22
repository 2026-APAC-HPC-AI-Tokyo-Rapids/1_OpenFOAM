from pathlib import Path

import pytest

from experiment_metrics.protocol import RunProtocol

REGISTRY = Path(__file__).parents[1] / "registry"


def test_selected_decomposition_presets_are_self_consistent() -> None:
    expected = {
        "scotch-1n-120r": (1, 120, "shm"),
        "scotch-2n-240r": (2, 240, "shm:ofi"),
        "scotch-4n-448r": (4, 448, "shm:ofi"),
        "gadi-scotch-1n-104r": (1, 104, "shm"),
        "gadi-scotch-2n-208r": (2, 208, "shm:ofi"),
        "gadi-scotch-4n-416r": (4, 416, "shm:ofi"),
        "aspire2a-scotch-1n-128r": (1, 128, "cray-mpich-ucx"),
        "aspire2a-scotch-2n-256r": (2, 256, "cray-mpich-ucx"),
        "aspire2a-scotch-4n-512r": (4, 512, "cray-mpich-ucx"),
        "aspire2a-multilevel-1n-128r": (1, 128, "cray-mpich-ucx"),
        "aspire2a-multilevel-2n-256r": (2, 256, "cray-mpich-ucx"),
        "aspire2a-multilevel-4n-512r": (4, 512, "cray-mpich-ucx"),
        "aspire2a-multilevel-poll-4n-512r": (4, 512, "cray-mpich-ucx"),
    }

    for preset, (nodes, ranks, transport) in expected.items():
        path = REGISTRY / f"openfoam-v2-protocol-{preset}.toml"
        for purpose in ("bench", "profile"):
            protocol = RunProtocol.load(path, purpose)
            assert protocol.nodes == nodes
            assert protocol.ranks == ranks
            expected_ranks_per_node = 128 if preset.startswith("aspire2a-") else (104 if preset.startswith("gadi-") else (112 if ranks == 448 else 120))
            assert protocol.ranks_per_node == expected_ranks_per_node
            assert protocol.transport_policy == transport
            expected_runtime = "poll-proc-interfaces" if "-poll-" in preset else "baseline"
            assert protocol.runtime_condition == expected_runtime
            assert protocol.workload_id == "occDrivAerStaticMesh-65M"
            assert protocol.solver == "simpleFoam"
            assert protocol.distribution == "OpenFOAM.com"
            assert protocol.release == "v2512"
            assert protocol.iteration_target == {1: 40, 2: 80, 4: 150}[nodes]


def test_runtime_condition_is_closed(tmp_path: Path) -> None:
    source = REGISTRY / "openfoam-v2-protocol-aspire2a-multilevel-poll-4n-512r.toml"
    protocol = tmp_path / "protocol.toml"
    workload = REGISTRY.parents[1] / "benchmark/workload.json"
    protocol.write_text(
        source.read_text()
        .replace("../../benchmark/workload.json", str(workload))
        .replace("poll-proc-interfaces", "unknown-condition")
    )
    with pytest.raises(ValueError, match="protocol expected instances are invalid"):
        RunProtocol.load(protocol, "bench")
