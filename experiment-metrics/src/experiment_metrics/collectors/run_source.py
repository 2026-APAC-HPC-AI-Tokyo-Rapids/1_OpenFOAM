from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from ..command import run
from ..context import Context
from ..model import Metric


def collect_start(context: Context, command: list[str]) -> list[Metric]:
    result = [Metric("run.started_at", datetime.now(UTC).isoformat())]
    if command:
        result.append(Metric("run.command.executable", command[0]))
        result.extend(
            Metric(f"run.command.arg.{index}", argument)
            for index, argument in enumerate(command[1:])
        )

    repository = Path(os.environ.get("GITHUB_WORKSPACE", context.case_dir))
    if "GITHUB_REPOSITORY" not in os.environ:
        result.append(
            Metric("git.repository", _git(repository, ["remote", "get-url", "origin"]))
        )
    if "GITHUB_SHA" not in os.environ:
        result.append(
            Metric("git.commit", _git(repository, ["rev-parse", "--verify", "HEAD"]))
        )
    dirty = run(
        [
            "git",
            "-C",
            str(repository),
            "status",
            "--porcelain=v1",
            "--untracked-files=normal",
        ]
    )
    result.append(
        Metric(
            "git.is_dirty", "" if dirty.returncode else str(bool(dirty.stdout)).lower()
        )
    )
    return result


def collect_end(
    exit_code: int,
    outcome: str | None,
    elapsed_sec: str | None = None,
) -> list[Metric]:
    normalized = outcome or ("succeeded" if exit_code == 0 else "failed")
    result = [
        Metric("run.finished_at", datetime.now(UTC).isoformat()),
        Metric("run.outcome", normalized),
        Metric("run.exit_code", str(exit_code)),
    ]
    if elapsed_sec is not None:
        result.extend(
            [
                Metric("run.elapsed_sec", elapsed_sec),
                Metric("perf.pipeline.wall_time_sec", elapsed_sec),
            ]
        )
    if exit_code < 0:
        result.append(Metric("run.signal", str(abs(exit_code))))
    return result


def _git(repository: Path, argv: list[str]) -> str:
    result = run(["git", "-C", str(repository), *argv])
    lines = result.stdout.strip().splitlines()
    return lines[0] if result.returncode == 0 and lines else ""
