from pathlib import Path

from experiment_metrics.protocol import RunProtocol

REGISTRY = Path(__file__).parents[1] / "registry"


def test_selected_scotch_presets_are_self_consistent() -> None:
    expected = {
        "scotch-1n-120r": (1, 120, "shm"),
        "scotch-2n-240r": (2, 240, "shm:ofi"),
        "scotch-4n-448r": (4, 448, "shm:ofi"),
        "gadi-scotch-1n-104r": (1, 104, "openmpi-default"),
        "gadi-scotch-2n-208r": (2, 208, "openmpi-default"),
        "gadi-scotch-4n-416r": (4, 416, "openmpi-default"),
    }

    for preset, (nodes, ranks, transport) in expected.items():
        path = REGISTRY / f"openfoam-v2-protocol-{preset}.toml"
        for purpose in ("bench", "profile"):
            protocol = RunProtocol.load(path, purpose)
            assert protocol.nodes == nodes
            assert protocol.ranks == ranks
            expected_ranks_per_node = 104 if preset.startswith("gadi-") else (112 if ranks == 448 else 120)
            assert protocol.ranks_per_node == expected_ranks_per_node
            assert protocol.transport_policy == transport
