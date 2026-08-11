from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    path = tmp_path / "registry.toml"
    path.write_text(
        """
[registry]
schema_version = "test/v1"

[[producers]]
id = "runner.manifest"
required_for = ["bench", "profile"]

[[producers]]
id = "stage.runner"
required_for = ["bench", "profile"]

[[producers]]
id = "runner.finalizer"
required_for = []

[[producers]]
id = "runner.log_parser"
required_for = []

[[producers]]
id = "network.parser"
required_for = []

[[keys]]
pattern = "run.identity.run_id"
owner = "runner.manifest"
logical_type = "string"
required_for = ["bench", "profile"]

[[keys]]
pattern = "run.identity.run_purpose"
owner = "runner.manifest"
logical_type = "string"
required_for = ["bench", "profile"]

[[keys]]
pattern = "run.identity.repository_id"
owner = "runner.manifest"
logical_type = "string"
required_for = ["bench", "profile"]

[[keys]]
pattern = "run.instrumentation_bundle_sha256"
owner = "runner.manifest"
logical_type = "string"
required_for = ["bench", "profile"]

[[keys]]
pattern = "run.stage.*.launch"
owner = "stage.runner"
logical_type = "json"
required_for = []

[[keys]]
pattern = "run.stage.*.termination"
owner = "stage.runner"
logical_type = "json"
required_for = []

[[keys]]
pattern = "perf.stage.*.wall_time_sec"
owner = "stage.runner"
logical_type = "decimal"
required_for = []

[[keys]]
pattern = "solver.runtime_header"
owner = "runner.log_parser"
logical_type = "json"
required_for = []

[[keys]]
pattern = "solver.step_timings"
owner = "runner.log_parser"
logical_type = "json"
required_for = []

[[keys]]
pattern = "solver.pressure_solves"
owner = "runner.log_parser"
logical_type = "json"
required_for = []

[[keys]]
pattern = "solver.log_markers"
owner = "runner.log_parser"
logical_type = "json"
required_for = []

[[keys]]
pattern = "network.imb_mpi1.process_count"
owner = "network.parser"
logical_type = "integer"
required_for = []

[[keys]]
pattern = "network.imb_mpi1.message_size.min_bytes"
owner = "network.parser"
logical_type = "integer"
required_for = []

[[keys]]
pattern = "network.imb_mpi1.message_size.max_bytes"
owner = "network.parser"
logical_type = "integer"
required_for = []

[[keys]]
pattern = "network.imb_mpi1.iteration.max_per_sample"
owner = "network.parser"
logical_type = "integer"
required_for = []

[[keys]]
pattern = "network.imb_mpi1.iteration.time_limit_sec"
owner = "network.parser"
logical_type = "integer"
required_for = []

[[keys]]
pattern = "network.imb_mpi1.iteration.policy"
owner = "network.parser"
logical_type = "string"
required_for = []

[[keys]]
pattern = "software.imb_mpi1.version"
owner = "network.parser"
logical_type = "string"
required_for = []
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def identities() -> dict[str, object]:
    return {
        "source_track": {
            "object_hash_algorithm": "sha1",
            "base_role": "score_reference",
            "base_commit": "a" * 40,
            "head_commit": "b" * 40,
        },
        "observed_control_plane_sha256": "c" * 64,
        "instrumentation_bundle_sha256": "d" * 64,
    }
