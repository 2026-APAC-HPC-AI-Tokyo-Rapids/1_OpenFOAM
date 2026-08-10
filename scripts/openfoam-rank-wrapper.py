#!/usr/bin/env python3
"""Exec one OpenFOAM rank under the profile ``perf stat`` contract.

This is deliberately a direct ``execvpe`` wrapper: no shell, retry, fallback
solver, or second measurement path is permitted.  The launch sidecar is
written before replacement by perf and contains the exact child argv and
launch-effective environment/affinity.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import tempfile
from pathlib import Path


EVENTS = "cycles,instructions,branches,branch-misses,cache-misses"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openfoam-rank-wrapper")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-ranks", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--perf", required=True, type=Path)
    parser.add_argument("--solver", required=True, type=Path)
    parser.add_argument("solver_argv", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    solver_argv = (
        arguments.solver_argv[1:]
        if arguments.solver_argv[:1] == ["--"]
        else arguments.solver_argv
    )
    if not arguments.run_id or arguments.run_id in {".", ".."}:
        raise ValueError("run ID must be nonempty")
    if arguments.expected_ranks <= 0:
        raise ValueError("expected ranks must be positive")
    if (
        not arguments.perf.is_absolute()
        or not arguments.solver.is_absolute()
        or not arguments.output.is_absolute()
    ):
        raise ValueError("perf, solver, and output paths must be absolute")
    rank = _env_rank("PMI_RANK")
    if rank >= arguments.expected_ranks:
        raise ValueError("PMI_RANK is outside expected ranks")
    local_rank = _env_rank("MPI_LOCALRANKID")
    local_size = _env_rank("MPI_LOCALNRANKS", positive=True)
    if local_rank >= local_size:
        raise ValueError("local rank is outside local size")
    output = _render_output(arguments.output, rank)
    run_root = _run_root(output, arguments.run_id)
    child_argv = (
        str(arguments.perf),
        "stat",
        "--no-big-num",
        "-x,",
        "-o",
        str(output),
        "-e",
        EVENTS,
        "--",
        str(arguments.solver),
        *solver_argv,
    )
    _write_sidecar(
        output.with_suffix(".json"),
        {
            "schema_version": "openfoam-rank-launch/v1",
            "run_id": arguments.run_id,
            "global_rank": rank,
            "local_rank": local_rank,
            "local_size": local_size,
            "hostname": socket.gethostname(),
            "cpu_affinity": sorted(os.sched_getaffinity(0)),
            "numa_mems": _numa_mems(),
            "argv": list(child_argv),
            "environment": dict(sorted(os.environ.items())),
            "output_member": _member_for_output(output, rank),
        },
    )
    _write_environment_delta(run_root, rank)
    _write_sidecar(
        run_root / f"source/placement/rank-{rank}.json",
        {
            "schema_version": "rank-placement/v1",
            "run_id": arguments.run_id,
            "global_rank": rank,
            "node_ordinal": rank // local_size,
            "local_rank": local_rank,
            "local_size": local_size,
            "hostname": socket.gethostname(),
            "cpu_affinity": sorted(os.sched_getaffinity(0)),
            "numa_mems": _numa_mems(),
        },
    )
    os.execvpe(str(arguments.perf), list(child_argv), os.environ.copy())
    return 127


def _env_rank(name: str, *, positive: bool = False) -> int:
    value = os.environ.get(name)
    if value is None or not value.isdecimal():
        raise ValueError(f"rank wrapper requires {name}")
    rank = int(value)
    if (positive and rank <= 0) or (not positive and rank < 0):
        raise ValueError(f"rank wrapper has invalid {name}")
    return rank


def _render_output(template: Path, rank: int) -> Path:
    value = str(template)
    if "{rank}" not in value:
        raise ValueError("output must contain the {rank} sink token")
    try:
        rendered = value.format(rank=rank)
    except (KeyError, ValueError) as error:
        raise ValueError("output has an invalid rank sink template") from error
    output = Path(rendered)
    if not output.is_absolute() or not output.name:
        raise ValueError("rendered output must be an absolute file")
    return output


def _numa_mems() -> str | None:
    try:
        lines = Path("/proc/self/status").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        if line.startswith("Mems_allowed_list:"):
            return line.partition(":")[2].strip() or None
    return None


def _member_for_output(output: Path, rank: int) -> str:
    """Return the contract member, independent of the absolute runtime root."""

    if output.name != f"rank-{rank}.csv":
        raise ValueError("output must be a rank CSV")
    return f"profile/raw/perf/{output.stem}.csv"


def _run_root(output: Path, run_id: str) -> Path:
    if (
        output.parent.name != "perf"
        or output.parent.parent.name != "raw"
        or output.parent.parent.parent.name != "profile"
    ):
        raise ValueError("profile output is outside the fixed run layout")
    root = output.parents[3]
    if root.name != run_id:
        raise ValueError("profile output run differs from --run-id")
    return root


def _write_environment_delta(run_root: Path, rank: int) -> None:
    common_path = run_root / "source/env/host-exec.snapshot"
    common_raw = common_path.read_bytes()
    common = _parse_snapshot(common_raw)
    current = dict(os.environb)
    changed = [
        {"name_b64": _b64(name), "value_b64": _b64(current[name])}
        for name in sorted(current)
        if common.get(name) != current[name]
    ]
    removed = [_b64(name) for name in sorted(set(common) - set(current))]
    _write_sidecar(
        run_root / f"source/env/rank-{rank}.delta.json",
        {
            "schema_version": "rank-env-delta/v1",
            "common_snapshot_sha256": hashlib.sha256(common_raw).hexdigest(),
            "rank": rank,
            "added_or_changed": changed,
            "removed_names_b64": removed,
        },
    )


def _parse_snapshot(raw: bytes) -> dict[bytes, bytes]:
    if not raw or not raw.endswith(b"\0"):
        raise ValueError("host environment snapshot is invalid")
    fields = raw.split(b"\0")
    if fields[-1] != b"" or len(fields) % 2 != 1:
        raise ValueError("host environment snapshot field count is invalid")
    pairs = list(zip(fields[:-1:2], fields[1:-1:2], strict=True))
    names = [name for name, _ in pairs]
    if any(not name or b"=" in name for name in names) or names != sorted(set(names)):
        raise ValueError("host environment snapshot names are not canonical")
    return dict(pairs)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _write_sidecar(path: Path, value: dict[str, object]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


if __name__ == "__main__":
    raise SystemExit(main())
