from __future__ import annotations

import argparse
import os
from pathlib import Path

from .manifest import RunManifest
from .placement import capture_rank_placement


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openfoam-rank-wrapper")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-ranks", type=int, required=True)
    parser.add_argument("--expected-nodes", type=int, required=True)
    parser.add_argument("--placement-root", type=Path, required=True)
    parser.add_argument("--global-rank-env", required=True)
    parser.add_argument("--local-rank-env", required=True)
    parser.add_argument("--local-size-env", required=True)
    parser.add_argument("--bind-local-rank", action="store_true")
    parser.add_argument("--capture-only", action="store_true")
    parser.add_argument("--profile-rank", type=int)
    parser.add_argument("--profile-wrapper", type=Path)
    parser.add_argument("solver_argv", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    solver = (
        arguments.solver_argv[1:]
        if arguments.solver_argv[:1] == ["--"]
        else arguments.solver_argv
    )
    if arguments.capture_only and (solver or arguments.profile_rank is not None or arguments.profile_wrapper is not None):
        raise ValueError("配置記録専用モードではsolverやプロファイラを起動できません")
    if not arguments.capture_only and (not solver or not Path(solver[0]).is_absolute()):
        raise ValueError("rank wrapper requires an absolute solver executable")
    if (arguments.profile_rank is None) != (arguments.profile_wrapper is None):
        raise ValueError("profile rank and wrapper must be specified together")
    if arguments.profile_rank is not None and (
        arguments.profile_rank < 0
        or arguments.profile_rank >= arguments.expected_ranks
        or not arguments.profile_wrapper.is_absolute()
        or not os.access(arguments.profile_wrapper, os.X_OK)
    ):
        raise ValueError("rank wrapper profile selection is invalid")
    manifest = RunManifest.load(arguments.manifest)
    run_dir = manifest.path.parents[1]
    placement_root = arguments.placement_root.resolve()
    if (
        placement_root != (run_dir / "source/placement").resolve()
        or arguments.expected_ranks <= 0
        or arguments.expected_nodes <= 0
        or arguments.expected_ranks % arguments.expected_nodes
    ):
        raise ValueError("rank wrapper paths are outside the bound run")
    rank = _rank(arguments.global_rank_env)
    local_rank = _rank(arguments.local_rank_env)
    local_size = _rank(arguments.local_size_env, positive=True)
    if rank >= arguments.expected_ranks or local_rank >= local_size:
        raise ValueError("rank wrapper environment is outside expected axes")
    ranks_per_node = arguments.expected_ranks // arguments.expected_nodes
    if local_size != ranks_per_node:
        raise ValueError("rank wrapper local size differs from expected axes")
    if arguments.bind_local_rank:
        os.sched_setaffinity(0, {local_rank})
        if os.sched_getaffinity(0) != {local_rank}:
            raise RuntimeError("rank wrapper could not bind the local rank")
    capture_rank_placement(
        placement_root / f"rank-{rank}.json",
        run_id=manifest.run_id,
        global_rank=rank,
        node_ordinal=rank // ranks_per_node,
        local_rank=local_rank,
        local_size=local_size,
    )
    if arguments.capture_only:
        return 0
    if rank == arguments.profile_rank:
        wrapper = str(arguments.profile_wrapper)
        os.execv(wrapper, [wrapper, *solver])
    os.execv(solver[0], solver)


def _rank(name: str, *, positive: bool = False) -> int:
    if not name or not name.replace("_", "a").isalnum() or name[0].isdigit():
        raise ValueError("rank wrapper environment name is invalid")
    value = os.environ.get(name)
    if value is None or not value.isdecimal():
        raise ValueError(f"rank wrapper requires {name}")
    rank = int(value)
    if (positive and rank <= 0) or (not positive and rank < 0):
        raise ValueError(f"rank wrapper has invalid {name}")
    return rank


if __name__ == "__main__":
    raise SystemExit(main())
