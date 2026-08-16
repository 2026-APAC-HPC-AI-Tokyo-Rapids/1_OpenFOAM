from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

from .fact import Fact, canonical_json
from .manifest import RunManifest
from .protocol import RunProtocol
from .recording import Recorder

_ACCOUNTING_FIELDS = (
    "jid",
    "st",
    "sdt",
    "elp",
    "ec",
    "sn",
    "pc",
    "nnumu",
    "mmszu",
    "uctmut",
    "sctmut",
)
_ACCOUNTING_HEADER = (
    "H",
    "JOB ID",
    "STATE",
    "JOB START DATE",
    "ELAPSE TIME (USE)",
    "EXIT CODE",
    "SIGNAL NO",
    "PJM CODE",
    "NODE NUM (USE)",
    "MAX MEMORY SIZE (USE)",
    "USER CPU TIME (USE)",
    "SYSTEM CPU TIME (USE)",
    "MAX MEMORY SIZE (USE)",
    "USER CPU TIME (USE)",
    "SYSTEM CPU TIME (USE)",
)
_ACCOUNTING_NODE_FIELDS = ("mmszu", "uctmut", "sctmut")
_JOB_ID = re.compile(r"^[0-9]+$")


@dataclass(frozen=True, slots=True)
class SubmissionOutcome:
    job_id: str | None
    returncode: int
    request_path: Path
    result_path: Path


def submit_run(
    *,
    manifest_path: Path,
    runtime_dir: Path,
    registry_path: Path,
    protocol_path: Path,
    pjm_script_repository_path: str,
    execution_script: Path,
    provision_dir: Path,
    profile_rank: int = 0,
    profile_analysis: str = "hotspots",
    execute: Callable[[list[str]], subprocess.CompletedProcess[bytes]] | None = None,
    pjsub_path: Path | None = None,
) -> SubmissionOutcome:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    if run_dir != manifest.path.parents[1]:
        raise ValueError("submission runtime differs from the bound manifest")
    protocol = RunProtocol.load(protocol_path, manifest.purpose)
    if profile_rank < 0 or profile_rank >= protocol.ranks:
        raise ValueError("profile rank must be within the protocol rank range")
    if manifest.purpose != "profile" and profile_rank != 0:
        raise ValueError("a nonzero profile rank requires a profile run")
    if profile_analysis not in {"hotspots", "hpc-performance", "memory-access"}:
        raise ValueError("unsupported VTune profile analysis")
    if manifest.purpose != "profile" and profile_analysis != "hotspots":
        raise ValueError("hardware characterization requires a profile run")
    relative = PurePosixPath(pjm_script_repository_path)
    if (
        not pjm_script_repository_path
        or relative.is_absolute()
        or ".." in relative.parts
    ):
        raise ValueError("PJM repository path is invalid")
    execution = execution_script.resolve(strict=True)
    pjsub = _launcher_path(pjsub_path or _which("pjsub"))
    environment = {
        "EXPERIMENT_METRICS_DIRECT_SEND": "0",
        "OPENFOAM_NODES": str(protocol.nodes),
        "OPENFOAM_RUN_PURPOSE": manifest.purpose,
        "OPENFOAM_VTUNE_ANALYSIS": profile_analysis,
        "OPENFOAM_VTUNE_RANK": str(profile_rank),
        "OPENFOAM_PROTOCOL_PATH": str(protocol_path.resolve(strict=True)),
        "OPENFOAM_MPI_PROCS": str(protocol.ranks),
        "OPENFOAM_RESOURCE_GROUP": protocol.resource_group,
        "OPENFOAM_TRANSPORT_POLICY": protocol.transport_policy,
        "PROVISION_DIR": str(provision_dir.resolve(strict=True)),
        "RUN_DIR": str(run_dir),
        "RUN_ID": manifest.run_id,
        "RUN_MANIFEST": str(manifest.path),
    }
    for name in ("EXPERIMENT_METRICS_BIGQUERY_CONFIG",):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    if any("," in value for value in environment.values()):
        raise ValueError("PJM exported values cannot contain commas")
    exported = ",".join(f"{name}={environment[name]}" for name in sorted(environment))
    argv = [
        str(pjsub),
        "-L",
        f"rscgrp={protocol.resource_group}",
        "-L",
        f"node={protocol.nodes}",
        "--mpi",
        f"proc={protocol.ranks}",
        "-x",
        exported,
        "-o",
        str(run_dir / "logs/%j.pjm.log"),
        "-j",
        "-N",
        "openfoam_run",
        str(execution),
    ]
    request = {
        "schema_version": "scheduler-request/v1",
        "subject_manifest_sha256": _sha256(manifest.path),
        "nodes": protocol.nodes,
        "ranks": protocol.ranks,
        "profile_rank": profile_rank,
        "profile_analysis": profile_analysis,
        "resource_group": protocol.resource_group,
        "transport_policy": protocol.transport_policy,
        "pjm_script": {
            "repository_path": pjm_script_repository_path,
            "sha256": _sha256(execution),
        },
        "argv": argv,
    }
    request_path = run_dir / "control/scheduler-request.json"
    _atomic_json(request_path, request)
    command = execute or _run
    completed = command(argv)
    source_root = run_dir / "source/scheduler"
    stdout = source_root / "submission.stdout"
    stderr = source_root / "submission.stderr"
    _atomic_bytes(stdout, completed.stdout)
    _atomic_bytes(stderr, completed.stderr)
    job_ids = re.findall(rb"\bJob ([0-9]+) submitted\.\s*", completed.stdout)
    job_id = job_ids[0].decode() if len(set(job_ids)) == 1 else None
    if completed.returncode != 0:
        job_id = None
    result = {
        "schema_version": "submission-result/v1",
        "request_sha256": _sha256(request_path),
        "outcome": _outcome(completed.returncode),
        "stdout": _member(stdout, run_dir),
        "stderr": _member(stderr, run_dir),
        "parsed_job_id": job_id,
    }
    result_path = run_dir / "control/submission-result.json"
    _atomic_json(result_path, result)
    with Recorder.open(
        manifest.path,
        registry_path,
        "runner.submission",
        run_dir,
        fragment_id="submission",
    ) as recorder:
        recorder.record(Fact("scheduler.request", request))
        if job_id is not None:
            recorder.record(Fact("scheduler.submit_job_id", job_id))
    return SubmissionOutcome(job_id, completed.returncode, request_path, result_path)


def capture_scheduler_terminal(
    *,
    manifest_path: Path,
    runtime_dir: Path,
    registry_path: Path,
    job_id: str,
    execute: Callable[[list[str]], subprocess.CompletedProcess[bytes]] | None = None,
    pjstat_path: Path | None = None,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    if run_dir != manifest.path.parents[1] or _JOB_ID.fullmatch(job_id) is None:
        raise ValueError("scheduler terminal identity is invalid")
    submission = _json(run_dir / "control/submission-result.json")
    entry = _json(run_dir / "control/job-entry.json")
    if (
        submission.get("parsed_job_id") != job_id
        or entry.get("scheduler_job_id") != job_id
    ):
        raise ValueError("submission and job-entry scheduler IDs differ")
    pjstat = _launcher_path(pjstat_path or _which("pjstat"))
    argv = [
        str(pjstat),
        "--history",
        "-S",
        "--choose",
        ",".join(_ACCOUNTING_FIELDS),
        "--data",
        "--delimiter",
        "\t",
        job_id,
    ]
    completed = (execute or _run)(argv)
    source_root = run_dir / "source/scheduler"
    stdout = source_root / "accounting.stdout"
    stderr = source_root / "accounting.stderr"
    _atomic_bytes(stdout, completed.stdout)
    _atomic_bytes(stderr, completed.stderr)
    terminal = {
        "schema_version": "scheduler-terminal/v1",
        "argv": argv,
        "outcome": _outcome(completed.returncode),
        "stdout": _member(stdout, run_dir),
        "stderr": _member(stderr, run_dir),
        "observed_terminal_utc": _utc_now(),
    }
    _atomic_json(run_dir / "control/scheduler-terminal.json", terminal)
    if completed.returncode != 0:
        raise ValueError("scheduler accounting command failed")
    accounting = parse_scheduler_accounting(completed.stdout, expected_job_id=job_id)
    path = run_dir / "control/scheduler-accounting.json"
    _atomic_json(path, accounting)
    with Recorder.open(
        manifest.path,
        registry_path,
        "runner.scheduler_postrun",
        run_dir,
        fragment_id="accounting",
    ) as recorder:
        recorder.record(Fact("scheduler.accounting", accounting))
    return path


def parse_scheduler_accounting(
    raw: bytes, *, expected_job_id: str
) -> dict[str, object]:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("scheduler accounting is not UTF-8") from error
    lines = [line.split("\t") for line in text.splitlines() if line]
    if lines and tuple(lines[0]) == _ACCOUNTING_HEADER:
        lines.pop(0)
    if len(lines) != 1:
        raise ValueError("scheduler accounting must contain exactly one data row")
    values = lines[0]
    if values and not values[0]:
        values = values[1:]
    common = values[: len(_ACCOUNTING_FIELDS)]
    node_values = values[len(_ACCOUNTING_FIELDS) :]
    if len(common) != len(_ACCOUNTING_FIELDS) or common[0] != expected_job_id:
        raise ValueError("scheduler accounting row has invalid columns or job ID")
    row = dict(zip(_ACCOUNTING_FIELDS, common, strict=True))
    node_count = _integer_value(row["nnumu"])
    if node_values and (
        node_count is None
        or node_count < 1
        or len(node_values) != node_count * len(_ACCOUNTING_NODE_FIELDS)
    ):
        raise ValueError("scheduler accounting has invalid per-node columns")
    node_usage = []
    for ordinal in range(node_count if node_values and node_count is not None else 0):
        offset = ordinal * len(_ACCOUNTING_NODE_FIELDS)
        node = dict(
            zip(
                _ACCOUNTING_NODE_FIELDS,
                node_values[offset : offset + len(_ACCOUNTING_NODE_FIELDS)],
                strict=True,
            )
        )
        node_usage.append(
            {
                "node_ordinal": ordinal,
                "mmszu": {
                    "lexeme": node["mmszu"],
                    "bytes": _unsigned_value(node["mmszu"]),
                },
                "uctmut": {
                    "lexeme": node["uctmut"],
                    "seconds": _milliseconds_value(node["uctmut"]),
                },
                "sctmut": {
                    "lexeme": node["sctmut"],
                    "seconds": _milliseconds_value(node["sctmut"]),
                },
            }
        )
    return {
        "schema_version": "scheduler-accounting/v2",
        "jid": row["jid"],
        "st": row["st"],
        "sdt": row["sdt"],
        "elp": {"lexeme": row["elp"], "seconds": _decimal_value(row["elp"])},
        "ec": {"lexeme": row["ec"], "value": _integer_value(row["ec"])},
        "sn": {"lexeme": row["sn"], "value": _integer_value(row["sn"])},
        "pc": {"lexeme": row["pc"], "value": _integer_value(row["pc"])},
        "nnumu": {
            "lexeme": row["nnumu"],
            "value": _integer_value(row["nnumu"]),
        },
        "mmszu": {"lexeme": row["mmszu"], "bytes": _unsigned_value(row["mmszu"])},
        "uctmut": {
            "lexeme": row["uctmut"],
            "seconds": _milliseconds_value(row["uctmut"]),
        },
        "sctmut": {
            "lexeme": row["sctmut"],
            "seconds": _milliseconds_value(row["sctmut"]),
        },
        "node_usage": node_usage,
    }


def _decimal_value(value: str) -> float | None:
    token = _numeric_token(value)
    try:
        parsed = Decimal(token)
    except (InvalidOperation, ValueError):
        return None
    return float(parsed) if parsed.is_finite() and parsed >= 0 else None


def _milliseconds_value(value: str) -> float | None:
    parsed = _decimal_value(value)
    return parsed / 1000 if parsed is not None else None


def _integer_value(value: str) -> int | None:
    token = _numeric_token(value)
    return int(token) if re.fullmatch(r"-?[0-9]+", token) else None


def _unsigned_value(value: str) -> int | None:
    parsed = _integer_value(value)
    return parsed if parsed is not None and parsed >= 0 else None


def _numeric_token(value: str) -> str:
    parenthesized = re.search(r"\(([-+]?[0-9]+(?:\.[0-9]+)?)\)", value)
    if parenthesized:
        return parenthesized.group(1)
    milliseconds = re.fullmatch(r"\s*([-+]?[0-9]+(?:\.[0-9]+)?)\s+ms\s*", value)
    return milliseconds.group(1) if milliseconds else value.strip()


def _run(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, check=False, capture_output=True)


def _which(name: str) -> Path:
    value = shutil.which(name)
    if value is None:
        raise FileNotFoundError(name)
    return Path(value)


def _launcher_path(path: Path) -> Path:
    """Return an absolute command path without dereferencing a multicall symlink."""

    absolute = Path(os.path.abspath(path))
    if not absolute.is_file():
        raise FileNotFoundError(absolute)
    return absolute


def _outcome(returncode: int) -> dict[str, object]:
    if returncode < 0:
        return {"kind": "signal", "signal": -returncode}
    return {"kind": "exit", "code": returncode}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _member(path: Path, run_dir: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(run_dir).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _atomic_json(path: Path, document: object) -> None:
    _atomic_bytes(path, (canonical_json(document) + "\n").encode())


def _atomic_bytes(path: Path, content: bytes) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)
