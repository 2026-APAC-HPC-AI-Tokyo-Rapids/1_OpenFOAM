from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from .fact import Fact, canonical_json
from .manifest import RunManifest
from .protocol import RunProtocol
from .recording import Recorder
from .scheduler import SubmissionOutcome

PBS_JOB_ID = re.compile(r"^[0-9]+(?:[.][A-Za-z0-9.-]+)?$")


def submit_pbs_run(
    *,
    manifest_path: Path,
    runtime_dir: Path,
    protocol_path: Path,
    pbs_script_repository_path: str,
    execution_script: Path,
    provision_dir: Path,
    profile_tool: str = "vtune",
    profile_rank: int = 0,
    profile_analysis: str = "hotspots",
    execute: Callable[[list[str]], subprocess.CompletedProcess[bytes]] | None = None,
    qsub_path: Path | None = None,
) -> SubmissionOutcome:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    if run_dir != manifest.path.parents[1]:
        raise ValueError("submission runtime differs from the bound manifest")
    protocol = RunProtocol.load(protocol_path, manifest.purpose)
    if profile_tool not in {"uprof", "vtune"}:
        raise ValueError("unsupported profile tool")
    if profile_rank < 0 or profile_rank >= protocol.ranks:
        raise ValueError("profile rank must be within the protocol rank range")
    if manifest.purpose != "profile" and profile_rank != 0:
        raise ValueError("a nonzero profile rank requires a profile run")
    if profile_analysis not in {
        "hotspots",
        "hpc-performance",
        "memory-access",
        "memory-access-core",
    }:
        raise ValueError("unsupported VTune profile analysis")
    if manifest.purpose != "profile" and profile_analysis != "hotspots":
        raise ValueError("hardware characterization requires a profile run")
    relative = PurePosixPath(pbs_script_repository_path)
    if (
        not pbs_script_repository_path
        or relative.is_absolute()
        or ".." in relative.parts
    ):
        raise ValueError("PBS repository path is invalid")
    execution = execution_script.resolve(strict=True)
    qsub = _launcher_path(qsub_path or _which("qsub"))
    environment = {
        "OPENFOAM_MPI_PROCS": str(protocol.ranks),
        "OPENFOAM_ITERATIONS": str(protocol.iteration_target),
        "OPENFOAM_EXPECTED_CELLS": str(protocol.expected_cells),
        "OPENFOAM_DISTRIBUTION": protocol.distribution,
        "OPENFOAM_RELEASE": protocol.release,
        "OPENFOAM_SOLVER": protocol.solver,
        "OPENFOAM_WORKLOAD_ID": protocol.workload_id,
        "OPENFOAM_NODES": str(protocol.nodes),
        "OPENFOAM_PROTOCOL_PATH": str(protocol_path.resolve(strict=True)),
        "OPENFOAM_RESOURCE_GROUP": protocol.resource_group,
        "OPENFOAM_RUN_PURPOSE": manifest.purpose,
        "OPENFOAM_TRANSPORT_POLICY": protocol.transport_policy,
        "PROVISION_DIR": str(provision_dir.resolve(strict=True)),
        "RUN_DIR": str(run_dir),
        "RUN_ID": manifest.run_id,
        "RUN_MANIFEST": str(manifest.path),
    }
    if manifest.purpose == "profile":
        environment["OPENFOAM_PROFILE_TOOL"] = profile_tool
        if profile_tool == "vtune":
            environment["OPENFOAM_VTUNE_ANALYSIS"] = profile_analysis
            environment["OPENFOAM_VTUNE_RANK"] = str(profile_rank)
    if any("," in value or "\n" in value for value in environment.values()):
        raise ValueError("PBS exported values cannot contain commas or newlines")
    exported = ",".join(f"{name}={environment[name]}" for name in sorted(environment))
    if relative.parts[:2] == ("platforms", "aspire2a"):
        resource_arguments = [
            "-P",
            "59000014",
            "-q",
            protocol.resource_group,
            "-l",
            f"select={protocol.nodes}:ncpus=128:mpiprocs=128:mem=400gb",
            "-l",
            "place=excl",
        ]
    else:
        resource_arguments = [
            "-P",
            "hb15",
            "-q",
            protocol.resource_group,
            "-l",
            f"ncpus={protocol.ranks},mem={protocol.nodes * 400}GB,jobfs={protocol.nodes * 100}GB,storage=scratch/hb15",
        ]
    argv = [str(qsub), *resource_arguments, "-v", exported, "-o", str(run_dir / "logs/pbs.log"), "-j", "oe", "-N", "openfoam_run", str(execution)]
    request = {
        "schema_version": "scheduler-request/v1",
        "subject_manifest_sha256": _sha256(manifest.path),
        "nodes": protocol.nodes,
        "ranks": protocol.ranks,
        "iterations": protocol.iteration_target,
        "workload_id": protocol.workload_id,
        "distribution": protocol.distribution,
        "release": protocol.release,
        "solver": protocol.solver,
        "profile_tool": profile_tool if manifest.purpose == "profile" else None,
        "profile_rank": profile_rank,
        "profile_analysis": profile_analysis,
        "resource_group": protocol.resource_group,
        "transport_policy": protocol.transport_policy,
        "pbs_script": {
            "repository_path": pbs_script_repository_path,
            "sha256": _sha256(execution),
        },
        "argv": argv,
    }
    request_path = run_dir / "control/scheduler-request.json"
    _atomic_json(request_path, request)
    completed = (execute or _run)(argv)
    source_root = run_dir / "source/scheduler"
    stdout = source_root / "submission.stdout"
    stderr = source_root / "submission.stderr"
    _atomic_bytes(stdout, completed.stdout)
    _atomic_bytes(stderr, completed.stderr)
    tokens = completed.stdout.decode("utf-8", errors="replace").split()
    job_id = (
        tokens[0]
        if completed.returncode == 0
        and len(tokens) == 1
        and PBS_JOB_ID.fullmatch(tokens[0])
        else None
    )
    result = {
        "schema_version": "submission-result/v1",
        "request_sha256": _sha256(request_path),
        "outcome": {"kind": "exit", "code": completed.returncode},
        "stdout": _member(stdout, run_dir),
        "stderr": _member(stderr, run_dir),
        "parsed_job_id": job_id,
    }
    result_path = run_dir / "control/submission-result.json"
    _atomic_json(result_path, result)
    with Recorder.open(
        manifest.path,
        "runner.submission",
        run_dir,
        fragment_id="submission",
    ) as recorder:
        recorder.record(Fact("scheduler.request", request))
        if job_id is not None:
            recorder.record(Fact("scheduler.submit_job_id", job_id))
    return SubmissionOutcome(job_id, completed.returncode, request_path, result_path)


def capture_pbs_terminal(
    *,
    manifest_path: Path,
    runtime_dir: Path,
    protocol_path: Path,
    job_id: str,
    execute: Callable[[list[str]], subprocess.CompletedProcess[bytes]] | None = None,
    qstat_path: Path | None = None,
) -> Path:
    manifest = RunManifest.load(manifest_path)
    run_dir = runtime_dir.resolve(strict=True)
    protocol = RunProtocol.load(protocol_path, manifest.purpose)
    if run_dir != manifest.path.parents[1] or PBS_JOB_ID.fullmatch(job_id) is None:
        raise ValueError("PBS terminal identity is invalid")
    submission = _json(run_dir / "control/submission-result.json")
    entry = _json(run_dir / "control/job-entry.json")
    if (
        submission.get("parsed_job_id") != job_id
        or entry.get("scheduler_job_id") != job_id
    ):
        raise ValueError("submission and job-entry scheduler IDs differ")
    qstat = _launcher_path(qstat_path or _which("qstat"))
    argv = [str(qstat), "-fx", job_id]
    completed = (execute or _run)(argv)
    source_root = run_dir / "source/scheduler"
    stdout = source_root / "accounting.stdout"
    stderr = source_root / "accounting.stderr"
    _atomic_bytes(stdout, completed.stdout)
    _atomic_bytes(stderr, completed.stderr)
    terminal = {
        "schema_version": "scheduler-terminal/v1",
        "argv": argv,
        "outcome": {"kind": "exit", "code": completed.returncode},
        "stdout": _member(stdout, run_dir),
        "stderr": _member(stderr, run_dir),
        "observed_terminal_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    _atomic_json(run_dir / "control/scheduler-terminal.json", terminal)
    if completed.returncode != 0:
        raise ValueError("PBS accounting command failed")
    accounting = parse_pbs_accounting(
        completed.stdout,
        expected_job_id=job_id,
        expected_nodes=protocol.nodes,
        expected_ranks=protocol.ranks,
    )
    path = run_dir / "control/scheduler-accounting.json"
    _atomic_json(path, accounting)
    with Recorder.open(
        manifest.path,
        "runner.scheduler_postrun",
        run_dir,
        fragment_id="accounting",
    ) as recorder:
        recorder.record(Fact("scheduler.accounting", accounting))
    return path


def parse_pbs_accounting(
    raw: bytes, *, expected_job_id: str, expected_nodes: int, expected_ranks: int
) -> dict[str, object]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("PBS accounting is not valid UTF-8") from error
    job_ids = re.findall(r"^Job Id: (\S+)\s*$", text, flags=re.MULTILINE)
    if job_ids != [expected_job_id]:
        raise ValueError("PBS accounting job ID differs")
    attributes = dict(
        re.findall(
            r"^[ \t]+([A-Za-z_][A-Za-z0-9_.-]*) = ([^\r\n]*)$", text, flags=re.MULTILINE
        )
    )
    if _integer(attributes.get("Resource_List.ncpus")) != expected_ranks:
        raise ValueError("PBS accounting CPU allocation differs from protocol")
    walltime = attributes.get("resources_used.walltime", "")
    cpu_time = attributes.get("resources_used.cput", "")
    memory = attributes.get("resources_used.mem", "")
    return {
        "schema_version": "scheduler-accounting/v2",
        "jid": expected_job_id,
        "st": attributes.get("job_state", ""),
        "sdt": attributes.get("stime", ""),
        "elp": {"lexeme": walltime, "seconds": _duration(walltime)},
        "ec": {
            "lexeme": attributes.get("Exit_status", ""),
            "value": _integer(attributes.get("Exit_status")),
        },
        "sn": {"lexeme": "", "value": None},
        "pc": {"lexeme": "", "value": None},
        "nnumu": {"lexeme": str(expected_nodes), "value": expected_nodes},
        "mmszu": {"lexeme": memory, "bytes": _memory_bytes(memory)},
        "uctmut": {"lexeme": cpu_time, "seconds": _duration(cpu_time)},
        "sctmut": {"lexeme": "", "seconds": None},
        "node_usage": [],
    }


def _duration(value: str) -> float | None:
    match = re.fullmatch(r"([0-9]+):([0-5][0-9]):([0-5][0-9](?:[.][0-9]+)?)", value)
    return (
        int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
        if match
        else None
    )


def _memory_bytes(value: str) -> int | None:
    match = re.fullmatch(r"([0-9]+)(b|kb|mb|gb|tb)", value.lower())
    if match is None:
        return None
    return (
        int(match.group(1))
        * {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}[
            match.group(2)
        ]
    )


def _integer(value: object) -> int | None:
    token = str(value)
    return int(token) if re.fullmatch(r"-?[0-9]+", token) else None


def _launcher_path(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise ValueError("scheduler launcher is not executable")
    return resolved


def _which(name: str) -> Path:
    value = shutil.which(name)
    if value is None:
        raise FileNotFoundError(name)
    return Path(value)


def _run(argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(argv, check=False, capture_output=True)


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _member(path: Path, root: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _atomic_json(path: Path, document: object) -> None:
    _atomic_bytes(path, (canonical_json(document) + "\n").encode())


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    temporary.replace(path)
