"""Local producer recording primitives for OpenFOAM experiments."""

from .fact import Fact
from .imb import IMBResult, parse_imb_mpi1
from .instrumentation import bundle_identity, install_bundle, load_bundle
from .manifest import RunManifest, init_run, manifest_facts
from .protocol import RunProtocol
from .recording import Recorder, collect_once
from .reducers import network_config_facts, solver_log_facts
from .solver_log import (
    OfficialEvaluation,
    ParsedSolverLog,
    evaluate_official,
    parse_solver_log,
)
from .stage_runner import StageRunner, Termination, run_stage
from .workload import WorkloadDefinition, capture_workload, load_workload_definition

__all__ = [
    "Fact",
    "IMBResult",
    "OfficialEvaluation",
    "ParsedSolverLog",
    "Recorder",
    "RunManifest",
    "RunProtocol",
    "StageRunner",
    "Termination",
    "WorkloadDefinition",
    "capture_workload",
    "load_workload_definition",
    "collect_once",
    "bundle_identity",
    "evaluate_official",
    "init_run",
    "install_bundle",
    "load_bundle",
    "manifest_facts",
    "network_config_facts",
    "parse_imb_mpi1",
    "parse_solver_log",
    "run_stage",
    "solver_log_facts",
]
