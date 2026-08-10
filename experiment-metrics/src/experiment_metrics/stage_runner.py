from __future__ import annotations

import subprocess
import time
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
    ) -> Termination:
        _validate(stage_name, argv, cwd, stderr_mode, stdout_path)
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
            with _stdout_stream(stdout_path) as stdout:
                completed = subprocess.run(
                    argv,
                    cwd=cwd,
                    check=False,
                    stdout=stdout,
                    stderr=subprocess.STDOUT if stderr_mode == "stdout" else None,
                )
            if completed.returncode < 0:
                termination = Termination("signal", signal=-completed.returncode)
            else:
                termination = Termination("exit", code=completed.returncode)
        except OSError:
            termination = Termination("spawn_error")
        elapsed = Decimal(time.monotonic_ns() - started) / Decimal(1_000_000_000)
        recorder.record(
            Fact(f"run.stage.{stage_name}.termination", termination.as_json())
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
) -> Termination:
    return StageRunner().run(
        stage_name,
        argv,
        cwd=cwd,
        stderr_mode=stderr_mode,
        recorder=recorder,
        stdout_path=stdout_path,
    )


def _validate(
    stage_name: str,
    argv: list[str],
    cwd: Path,
    stderr_mode: str,
    stdout_path: Path | None,
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
    if stdout_path is not None and (
        not stdout_path.parent.is_dir() or stdout_path.exists()
    ):
        raise ValueError("stage stdout path must have an existing parent and be new")


class _stdout_stream:
    """Open a binary stage capture only for the child invocation."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.stream: object | None = None

    def __enter__(self) -> object | None:
        if self.path is not None:
            self.stream = self.path.open("xb")
        return self.stream

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        if self.stream is not None:
            self.stream.close()  # type: ignore[union-attr]
        return False
