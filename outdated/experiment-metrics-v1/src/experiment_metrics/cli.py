from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Callable

from .collectors import (
    artifact,
    case,
    mesh,
    parallel,
    platform,
    result,
    run_source,
    scheduler,
)
from .context import make_context
from .credentials import capture_from_environment
from .logging import warning
from .model import Metric
from .prepare import prepare_case
from .sender import send


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="experiment-metrics")
    commands = root.add_subparsers(dest="action", required=True)

    prepare = commands.add_parser("prepare-case")
    prepare.add_argument("--case-dir", default=".")

    collect = commands.add_parser("collect")
    collect.add_argument(
        "collector",
        choices=[
            "run-start",
            "run-end",
            "platform",
            "case",
            "parallel",
            "mesh",
            "solver-status",
            "solver-result",
            "artifact",
            "scheduler",
        ],
    )
    collect.add_argument("--case-dir", default=".")
    collect.add_argument("--job-id")
    collect.add_argument("--exit-code", type=int, default=0)
    collect.add_argument("--elapsed-sec")
    collect.add_argument("--outcome", choices=["succeeded", "failed", "cancelled"])
    collect.add_argument("--command", nargs=argparse.REMAINDER, default=[])

    stage = commands.add_parser("stage")
    stage.add_argument("name")
    stage.add_argument("command", nargs=argparse.REMAINDER)
    return root


def main(argv: list[str] | None = None) -> int:
    capture_from_environment()
    arguments = parser().parse_args(argv)
    if arguments.action == "prepare-case":
        prepare_case(make_context(arguments.case_dir).case_dir)
        return 0
    if arguments.action == "stage":
        return _stage(arguments.name, arguments.command)
    return _collect(arguments)


def _collect(arguments: argparse.Namespace) -> int:
    context = make_context(arguments.case_dir, arguments.job_id)
    collector: Callable[[], list[Metric]]
    match arguments.collector:
        case "run-start":
            command = _without_separator(arguments.command)
            collector = lambda: run_source.collect_start(context, command)
        case "run-end":
            collector = lambda: run_source.collect_end(
                arguments.exit_code, arguments.outcome, arguments.elapsed_sec
            )
        case "platform":
            collector = lambda: platform.collect(context.case_dir)
        case "case":
            collector = lambda: case.collect(context)
        case "parallel":
            collector = lambda: parallel.collect(context)
        case "mesh":
            collector = lambda: mesh.collect(context)
        case "solver-status":
            collector = lambda: result.collect_status(context, arguments.exit_code)
        case "solver-result":
            collector = lambda: result.collect(context)
        case "artifact":
            collector = lambda: artifact.collect(context)
        case "scheduler":
            job_id = arguments.job_id or ""
            collector = lambda: scheduler.collect(job_id)
        case _:
            raise AssertionError(arguments.collector)

    try:
        batch = collector()
        send(context.run, batch)
    except Exception as error:  # noqa: BLE001 - observability must not alter the experiment
        warning(f"{arguments.collector} collector failed: {error}")
    return 0


def _stage(name: str, argv: list[str]) -> int:
    command = _without_separator(argv)
    if not command:
        warning("stage command is empty")
        return 127
    started = time.monotonic_ns()
    try:
        completed = subprocess.run(command, check=False)
        returncode = completed.returncode
    except OSError as error:
        warning(f"stage {name} could not start: {error}")
        returncode = 127
    elapsed = (time.monotonic_ns() - started) / 1_000_000_000
    context = make_context(".")
    send(
        context.run,
        [
            Metric(f"perf.stage.{name}.wall_time_sec", repr(elapsed)),
            Metric(f"run.stage.{name}.exit_code", str(returncode)),
        ],
    )
    return returncode


def _without_separator(argv: list[str]) -> list[str]:
    return argv[1:] if argv and argv[0] == "--" else argv


if __name__ == "__main__":
    sys.exit(main())
