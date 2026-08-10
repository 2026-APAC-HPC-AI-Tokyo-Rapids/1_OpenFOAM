from __future__ import annotations

import argparse
import os
from pathlib import Path

from .environment import capture_rank_delta
from .manifest import RunManifest
from .placement import capture_rank_placement


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openfoam-rank-wrapper")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-ranks", type=int, required=True)
    parser.add_argument("--expected-nodes", type=int, required=True)
    parser.add_argument("--common-snapshot", type=Path, required=True)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--placement-root", type=Path, required=True)
    parser.add_argument("solver_argv", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    solver = (
        arguments.solver_argv[1:]
        if arguments.solver_argv[:1] == ["--"]
        else arguments.solver_argv
    )
    if not solver or not Path(solver[0]).is_absolute():
        raise ValueError("rank wrapper requires an absolute solver executable")
    manifest = RunManifest.load(arguments.manifest)
    run_dir = manifest.path.parents[1]
    environment_root = arguments.environment_root.resolve()
    placement_root = arguments.placement_root.resolve()
    if (
        environment_root != (run_dir / "source/env").resolve()
        or placement_root != (run_dir / "source/placement").resolve()
        or arguments.common_snapshot.resolve(strict=True)
        != (run_dir / "source/env/host-exec.snapshot").resolve(strict=True)
        or arguments.expected_ranks <= 0
        or arguments.expected_nodes <= 0
        or arguments.expected_ranks % arguments.expected_nodes
    ):
        raise ValueError("rank wrapper paths are outside the bound run")
    rank = _rank("PMI_RANK")
    local_rank = _rank("MPI_LOCALRANKID")
    local_size = _rank("MPI_LOCALNRANKS", positive=True)
    if rank >= arguments.expected_ranks or local_rank >= local_size:
        raise ValueError("rank wrapper environment is outside expected axes")
    ranks_per_node = arguments.expected_ranks // arguments.expected_nodes
    if local_size != ranks_per_node:
        raise ValueError("rank wrapper local size differs from expected axes")
    capture_rank_delta(
        arguments.common_snapshot,
        environment_root / f"rank-{rank}.delta.json",
        rank=rank,
    )
    capture_rank_placement(
        placement_root / f"rank-{rank}.json",
        run_id=manifest.run_id,
        global_rank=rank,
        node_ordinal=rank // ranks_per_node,
        local_rank=local_rank,
        local_size=local_size,
    )
    os.execv(solver[0], solver)


def _rank(name: str, *, positive: bool = False) -> int:
    value = os.environ.get(name)
    if value is None or not value.isdecimal():
        raise ValueError(f"rank wrapper requires {name}")
    rank = int(value)
    if (positive and rank <= 0) or (not positive and rank < 0):
        raise ValueError(f"rank wrapper has invalid {name}")
    return rank


if __name__ == "__main__":
    raise SystemExit(main())
