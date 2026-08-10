from __future__ import annotations

import subprocess
import time
from contextlib import ExitStack
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .fact import Fact
from .recording import Recorder


@dataclass(frozen=True, slots=True)
class Termination:
    kind: str
    code: int | None = None
    signal: int | None = None

    def as_json(self) -> dict[str, object]:
        if self.kind == "exit":
            assert self.code is not None
            return {"kind": "exit", "code": self.code}
        if self.kind == "signal":
            assert self.signal is not None
            return {"kind": "signal", "signal": self.signal}
        return {"kind": "spawn_error"}


class StageRunner:
    """The sole owner of observed argv, monotonic timing, and termination."""

    def run(
        self,
        stage_name: str,
        argv: list[str],
        *,
        cwd: Path,
        stderr_mode: str,
        recorder: Recorder,
        stdout_path: Path | None = None,
        stderr_path: Path | None = None,
        timeout_sec: int | None = None,
    ) -> Termination:
        _validate(
            stage_name,
            argv,
            cwd,
            stderr_mode,
            stdout_path,
            stderr_path,
            timeout_sec,
        )
        recorder.record(
            Fact(
                f"run.stage.{stage_name}.launch",
                {
                    "schema_version": "stage-launch/v1",
                    "argv": argv,
                    "cwd": str(cwd),
                    "stderr_mode": stderr_mode,
                },
            )
        )
        started = time.monotonic_ns()
        try:
            with ExitStack() as stack:
                stdout = _capture_stream(stack, stdout_path)
                stderr = _capture_stream(stack, stderr_path)
                completed = subprocess.run(
                    argv,
                    cwd=cwd,
                    check=False,
                    stdout=stdout,
                    stderr=subprocess.STDOUT if stderr_mode == "stdout" else stderr,
                    timeout=timeout_sec,
                )
            if completed.returncode < 0:
                termination = Termination("signal", signal=-completed.returncode)
            else:
                termination = Termination("exit", code=completed.returncode)
        except subprocess.TimeoutExpired:
            termination = Termination("signal", signal=9)
        except OSError:
            termination = Termination("spawn_error")
        elapsed = Decimal(time.monotonic_ns() - started) / Decimal(1_000_000_000)
        recorder.record(
            Fact(
                f"run.stage.{stage_name}.termination",
                {
                    "schema_version": "stage-termination/v1",
                    "outcome": termination.as_json(),
                },
            )
        )
        recorder.record(Fact(f"perf.stage.{stage_name}.wall_time_sec", elapsed))
        return termination


def run_stage(
    stage_name: str,
    argv: list[str],
    *,
    cwd: Path,
    stderr_mode: str,
    recorder: Recorder,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    timeout_sec: int | None = None,
) -> Termination:
    return StageRunner().run(
        stage_name,
        argv,
        cwd=cwd,
        stderr_mode=stderr_mode,
        recorder=recorder,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        timeout_sec=timeout_sec,
    )


def _validate(
    stage_name: str,
    argv: list[str],
    cwd: Path,
    stderr_mode: str,
    stdout_path: Path | None,
    stderr_path: Path | None,
    timeout_sec: int | None,
) -> None:
    if not stage_name or any(
        not (character.isalnum() or character == "_") for character in stage_name
    ):
        raise ValueError("stage_name must use letters, digits, and underscores")
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("argv must be a non-empty string array")
    if not cwd.is_dir():
        raise ValueError("stage cwd must exist")
    if stderr_mode not in {"stdout", "separate"}:
        raise ValueError("stderr_mode must be stdout or separate")
    if stderr_mode == "stdout" and stderr_path is not None:
        raise ValueError("combined stderr cannot have a separate capture path")
    for label, path in (("stdout", stdout_path), ("stderr", stderr_path)):
        if path is not None and (not path.parent.is_dir() or path.exists()):
            raise ValueError(
                f"stage {label} path must have an existing parent and be new"
            )
    if isinstance(timeout_sec, bool) or (
        timeout_sec is not None
        and (not isinstance(timeout_sec, int) or timeout_sec <= 0)
    ):
        raise ValueError("stage timeout must be a positive integer")


def _capture_stream(stack: ExitStack, path: Path | None) -> object | None:
    """Open a binary capture only for the child invocation."""

    return stack.enter_context(path.open("xb")) if path is not None else None
