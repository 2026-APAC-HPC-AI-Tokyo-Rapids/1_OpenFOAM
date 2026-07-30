from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Context:
    run: str
    case_dir: Path
    provision_dir: Path | None


def make_run(job_id: str | None = None) -> str:
    explicit = os.environ.get("EXPERIMENT_METRICS_RUN")
    if explicit:
        return explicit

    job = job_id or os.environ.get("PJM_JOBID") or os.environ.get("PJM_JOB_ID")
    github_run = os.environ.get("GITHUB_RUN_ID")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    if github_run and attempt and job:
        return f"openfoam-{github_run}-{attempt}-{job}"
    if job:
        return f"openfoam-manual-{job}"
    return f"openfoam-local-{os.getpid()}"


def make_context(case_dir: str, job_id: str | None = None) -> Context:
    provision = os.environ.get("PROVISION_DIR")
    return Context(
        run=make_run(job_id),
        case_dir=Path(case_dir).resolve(),
        provision_dir=Path(provision).resolve() if provision else None,
    )
