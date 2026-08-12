from pathlib import Path

from experiment_metrics.protocol import RunProtocol


REGISTRY = Path(__file__).parents[1] / "registry"


def test_scotch_full_core_presets_are_self_consistent() -> None:
    expected = {
        "scotch-1n-120r": (1, 120, "shm"),
        "scotch-2n-240r": (2, 240, "shm:ofi"),
        "scotch-4n-480r": (4, 480, "shm:ofi"),
    }

    for preset, (nodes, ranks, transport) in expected.items():
        path = REGISTRY / f"openfoam-v2-protocol-{preset}.toml"
        for purpose in ("bench", "profile"):
            protocol = RunProtocol.load(path, purpose)
            assert protocol.nodes == nodes
            assert protocol.ranks == ranks
            assert protocol.ranks_per_node == 120
            assert protocol.transport_policy == transport
