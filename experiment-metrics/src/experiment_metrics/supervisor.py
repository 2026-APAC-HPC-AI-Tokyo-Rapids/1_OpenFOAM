from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from .environment import capture_snapshot
from .fact import Fact, canonical_json
from .manifest import RunManifest
from .recording import Recorder


def start_supervisor(manifest_path: Path, state_path: Path, *, job_id: str) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    if state_path.resolve() != (run_dir / "domain/supervisor-state.json").resolve():
        raise ValueError("supervisor state is outside the bound run")
    if re.fullmatch(r"[0-9]+(?:[.][A-Za-z0-9.-]+)?", job_id) is None:
        raise ValueError("supervisor requires a scheduler job ID")
    started_at = _utc_now()
    snapshot = run_dir / "source/env/job-entry.snapshot"
    capture_snapshot(snapshot)
    entry = {
        "schema_version": "job-entry/v1",
        "subject_kind": "regular_run",
        "run_id": manifest.run_id,
        "scheduler_job_id": job_id,
        "entry_utc": started_at,
        "environment_snapshot": _member(snapshot, run_dir),
    }
    _atomic_json(run_dir / "control/job-entry.json", entry, replace=False)
    state = {
        "schema_version": "supervisor-state/v1",
        "run_id": manifest.run_id,
        "started_at": started_at,
        "started_monotonic_ns": time.monotonic_ns(),
        "pipeline_started_monotonic_ns": None,
        "pipeline_finished_monotonic_ns": None,
    }
    _atomic_json(state_path, state, replace=False)
    return state_path


def mark_pipeline(state_path: Path, mark: str) -> Path:
    state = _state(state_path)
    now = time.monotonic_ns()
    if mark == "start":
        if state["pipeline_started_monotonic_ns"] is not None:
            raise ValueError("pipeline start was already recorded")
        state["pipeline_started_monotonic_ns"] = now
    elif mark == "finish":
        started = state["pipeline_started_monotonic_ns"]
        if (
            not isinstance(started, int)
            or state["pipeline_finished_monotonic_ns"] is not None
            or now < started
        ):
            raise ValueError("pipeline finish has no valid start")
        state["pipeline_finished_monotonic_ns"] = now
    else:
        raise ValueError("pipeline mark must be start or finish")
    _atomic_json(state_path, state, replace=True)
    return state_path


def finish_supervisor(
    manifest_path: Path,
    state_path: Path,
    *,
    exit_code: int,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    state = _state(state_path)
    if state["run_id"] != manifest.run_id or not isinstance(exit_code, int):
        raise ValueError("supervisor finish identity is invalid")
    finished_ns = time.monotonic_ns()
    started_ns = state["started_monotonic_ns"]
    if finished_ns < started_ns:
        raise ValueError("supervisor monotonic clock moved backwards")
    entry = _json(run_dir / "control/job-entry.json")
    facts: list[Fact] = [
        Fact("run.started_at", state["started_at"]),
        Fact("run.finished_at", _utc_now()),
        Fact(
            "run.elapsed_sec",
            Decimal(finished_ns - started_ns) / Decimal(1_000_000_000),
        ),
        Fact("run.exit_code", exit_code),
        Fact("scheduler.job_entry_job_id", entry["scheduler_job_id"]),
    ]
    pipeline_start = state["pipeline_started_monotonic_ns"]
    pipeline_finish = state["pipeline_finished_monotonic_ns"]
    if isinstance(pipeline_start, int) and isinstance(pipeline_finish, int):
        facts.append(
            Fact(
                "perf.pipeline.wall_time_sec",
                Decimal(pipeline_finish - pipeline_start) / Decimal(1_000_000_000),
            )
        )
    with Recorder.open(
        manifest.path,
        "scheduler.supervisor",
        run_dir,
        fragment_id="supervisor",
    ) as recorder:
        for fact in facts:
            recorder.record(fact)
    state_path.unlink()
    return recorder.fragment_path


def _state(path: Path) -> dict[str, object]:
    value = _json(path)
    required = {
        "schema_version",
        "run_id",
        "started_at",
        "started_monotonic_ns",
        "pipeline_started_monotonic_ns",
        "pipeline_finished_monotonic_ns",
    }
    if (
        set(value) != required
        or value["schema_version"] != "supervisor-state/v1"
        or not isinstance(value["run_id"], str)
        or not isinstance(value["started_at"], str)
        or not isinstance(value["started_monotonic_ns"], int)
    ):
        raise ValueError("supervisor state has an invalid schema")
    return value


def _member(path: Path, run_dir: Path) -> dict[str, object]:
    import hashlib

    raw = path.read_bytes()
    return {
        "path": path.relative_to(run_dir).as_posix(),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _atomic_json(path: Path, document: object, *, replace: bool) -> None:
    if path.exists() and not replace:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as stream:
        stream.write(canonical_json(document) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)
