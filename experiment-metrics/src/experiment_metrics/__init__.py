"""Local v2 fact recording and merge primitives for OpenFOAM experiments."""

from .fact import Fact
from .imb import IMBResult, parse_imb_mpi1
from .manifest import RunManifest, init_run, manifest_facts
from .merge import FinalizeOutcome, merge_run
from .protocol import RunProtocol
from .pstream import pstream_facts
from .recording import Recorder, collect_once
from .reducers import network_config_facts, network_projection_rows, solver_log_facts
from .solver_log import (
    OfficialEvaluation,
    ParsedSolverLog,
    evaluate_official,
    parse_solver_log,
)
from .stage_runner import StageRunner, Termination, run_stage

__all__ = [
    "Fact",
    "FinalizeOutcome",
    "IMBResult",
    "OfficialEvaluation",
    "ParsedSolverLog",
    "Recorder",
    "RunManifest",
    "RunProtocol",
    "StageRunner",
    "Termination",
    "collect_once",
    "evaluate_official",
    "init_run",
    "merge_run",
    "manifest_facts",
    "network_projection_rows",
    "network_config_facts",
    "parse_imb_mpi1",
    "parse_solver_log",
    "pstream_facts",
    "run_stage",
    "solver_log_facts",
]
