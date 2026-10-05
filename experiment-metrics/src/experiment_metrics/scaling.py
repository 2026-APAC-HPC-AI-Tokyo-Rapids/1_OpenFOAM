"""Render an evidence-linked 1/2/4-node series from persisted run artifacts."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import subprocess
import tarfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path, PurePosixPath

from .coefficient import parse_coefficient_text
from .solver_log import evaluate_official, parse_solver_log

ITERATIONS = {1: 40, 2: 80, 4: 150}
# ASPIRE-2A's NUMA-aware multiLevel splits node -> socket (2) -> NUMA (4) -> core (16); one node has no node level.
# These declared per-node-count domains are the only input a series may vary across node counts.
MULTI_LEVEL_DOMAINS = {("aspire2a", 1): (2, 4, 16), ("aspire2a", 2): (2, 2, 4, 16), ("aspire2a", 4): (4, 2, 4, 16)}
MULTI_LEVEL_DOMAINS_ENTRY = r"(?ms)^(multiLevelCoeffs\s*\{[^{}]*?^\s*domains\s+)\(([0-9 ]+)\);"


def read_bundle(directory: Path) -> dict[str, bytes]:
    """Read a fixed artifact set without extracting paths from the archive."""
    document = json.loads((directory / "artifact-manifest.json").read_bytes())
    files = document["files"]
    if len(files) != 1 or files[0]["role"] != "run_bundle":
        raise ValueError("scaling requires bench artifacts without a profile archive")
    archive = directory / "run-artifacts.tar.zst"
    raw = archive.read_bytes()
    if len(raw) != files[0]["size_bytes"] or hashlib.sha256(raw).hexdigest() != files[0]["sha256"]:
        raise ValueError(f"artifact identity mismatch: {archive}")
    uncompressed = subprocess.run(["zstd", "-dc", str(archive)], check=True, capture_output=True).stdout
    members: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(uncompressed)) as bundle:
        for member in bundle:
            if not member.isfile() or member.name in members:
                raise ValueError("run bundle must contain unique regular files")
            stream = bundle.extractfile(member)
            assert stream is not None
            members[member.name] = stream.read()
    index = json.loads(members.pop("bundle.manifest.json"))
    if index["run_id"] != document["logical_artifact_name"]:
        raise ValueError("artifact and bundle run IDs differ")
    if len(index["members"]) != len(members) or {row["path"] for row in index["members"]} != set(members):
        raise ValueError("bundle member index differs from archive")
    for row in index["members"]:
        content = members[row["path"]]
        if len(content) != row["size_bytes"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
            raise ValueError(f"bundle member identity mismatch: {row['path']}")
    if json.loads(members["control/run-manifest.json"])["run_id"] != index["run_id"]:
        raise ValueError("run manifest and bundle run IDs differ")
    return members


@dataclass(frozen=True)
class ScalingRun:
    actions: str
    artifact: str
    run_id: str
    commit: str
    cluster: str
    nodes: int
    ranks: int
    decomposition: str
    transport: str
    iterations: int
    mean: Decimal
    stddev: Decimal
    cd: str
    condition: dict[str, object]


def load_run(actions: str, directory: Path) -> ScalingRun:
    return parse_run(actions, str(directory.resolve() / "run-artifacts.tar.zst"), read_bundle(directory))


def parse_run(actions: str, artifact: str, members: dict[str, bytes]) -> ScalingRun:
    if not re.fullmatch(r"https://github.com/[^/]+/[^/]+/actions/runs/[0-9]+(?:/attempts/[0-9]+)?", actions):
        raise ValueError("each run requires its GitHub Actions run URL")
    def document(path: str) -> dict:
        return json.loads(members[path])

    manifest = document("control/run-manifest.json")
    if not re.fullmatch(r"r-[0-9a-f]{32}", manifest["run_id"]):
        raise ValueError("invalid run ID")
    if manifest["run_purpose"] != "bench":
        raise ValueError("profile runs cannot enter a scaling series")
    request = document("control/scheduler-request.json")
    nodes, ranks = request["nodes"], request["ranks"]
    if nodes not in ITERATIONS or request["iterations"] != ITERATIONS[nodes]:
        raise ValueError("scaling requires official 1/2/4-node iteration counts (40/80/150)")
    script = request.get("pjm_script", request.get("pbs_script"))
    cluster = script["repository_path"].split("/")[1]
    cache = document("source/mesh/case-cache-manifest.json")
    if cache["number_of_subdomains"] != ranks:
        raise ValueError("decomposition and requested ranks differ")
    result = members["results/result.txt"].decode()
    if result.splitlines().count("STATUS: VALID") != 1:
        raise ValueError("official result parser did not mark this run VALID")
    result_lines = [line for line in result.splitlines() if line.startswith("RESULT:")]
    if len(result_lines) != 1:
        raise ValueError("official result must contain exactly one RESULT line")
    result_values = dict(item.split("=", 1) for item in result_lines[0].split()[1:])
    if result_values["cells"] != "65334765":
        raise ValueError("scaling requires the official 65M mesh")
    for name in ("nodes", "ranks", "workload_id", "distribution", "release", "solver"):
        if result_values[name] != str(request[name]):
            raise ValueError(f"official result differs from scheduler request: {name}")
    iterations = request["iterations"]
    if result_values["configured_iterations"] != str(iterations) or result_values["measured_iterations"] != str(iterations - 1):
        raise ValueError("official result iteration counts differ from request")
    parsed = parse_solver_log(members["logs/solver.log"].decode())
    evaluated = evaluate_official(parsed, iterations=iterations, expected_cells=int(result_values["cells"]), ranks=ranks, release=request["release"], solver=request["solver"])
    if not evaluated.valid:
        raise ValueError("archived solver log fails official result checks")
    mean = Decimal(result_values["average_wall_clock_seconds_per_iteration"])
    stddev = Decimal(result_values["standard_deviation"])
    if mean != evaluated.average_wall_clock_sec or stddev != evaluated.standard_deviation_sec or mean <= 0 or stddev < 0:
        raise ValueError("official timing result differs from archived solver log")
    cd = parse_coefficient_text(members["results/coefficient.dat"].decode(), iterations)
    provision = document("control/build-provision-validation.json")
    condition = {
        "commit": manifest["source_track"]["head_commit"],
        "cluster": cluster,
        "instrumentation": manifest["instrumentation_bundle_sha256"],
        "build": provision["build_sidecar_sha256"],
        "mpi": provision["resolved_libmpi"]["sha256"],
        "workload": document("source/workload-manifest.json")["workload_identity"],
        "mesh": cache["mesh_sha256"],
        "preparation": cache["prepare_script_sha256"],
        "preparation_toolchain": cache["prepare_toolchain_identity"],
        "decomposition": cache["method"],
        "file_handler": cache["file_handler"],
        "cells": result_values["cells"],
        **{name: request[name] for name in ("distribution", "release", "solver", "workload_id", "resource_group")},
    }
    for name, field, expected in (("controlDict", "endTime", iterations), ("caseDefinition", "nCores", ranks), ("decomposeParDict", "numberOfSubdomains", ranks)):
        text = members[f"source/mesh/{name}"].decode()
        expression = rf"(?m)^({field}\s+)([0-9]+);"
        values = re.findall(expression, text)
        if len(values) != 1 or int(values[0][1]) != expected:
            raise ValueError(f"actual input differs from request: {name}/{field}")
        condition[f"input/{name}"] = re.sub(expression, rf"\g<1><{field}>;", text)
    decomposition = cache["method"]
    if decomposition == "multiLevel":
        declared = MULTI_LEVEL_DOMAINS.get((cluster, nodes))
        entries = re.findall(MULTI_LEVEL_DOMAINS_ENTRY, condition["input/decomposeParDict"])
        if declared is None or math.prod(declared) != ranks or len(entries) != 1 or tuple(map(int, entries[0][1].split())) != declared or tuple(cache.get("domains", ())) != declared:
            raise ValueError("multiLevel domains differ from the declared node/socket/NUMA/core split")
        condition["input/decomposeParDict"] = re.sub(MULTI_LEVEL_DOMAINS_ENTRY, r"\g<1><domains>;", condition["input/decomposeParDict"])
        decomposition = f"multiLevel ({' '.join(map(str, declared))})"
    return ScalingRun(actions, artifact, manifest["run_id"], condition["commit"], cluster, nodes, ranks, decomposition, request["transport_policy"], iterations, mean, stddev, str(cd["cd"]), condition)


def render_scaling(runs: list[ScalingRun]) -> str:
    if {run.nodes for run in runs} != {1, 2, 4}:
        raise ValueError("a scaling series must include 1, 2, and 4 nodes")
    if len({run.run_id for run in runs}) != len(runs):
        raise ValueError("duplicate run in scaling series")
    for run in runs:
        differences = [key for key in run.condition if run.condition[key] != runs[0].condition[key]]
        if differences:
            raise ValueError("incompatible scaling conditions: " + ", ".join(differences))
    # Both cluster presets use shared memory alone on one node and OFI across nodes.
    transports = {run.transport for run in runs}
    if len(transports) > 1 and not all(run.cluster in {"genkai", "gadi"} and run.transport == ("shm" if run.nodes == 1 else "shm:ofi") for run in runs):
        raise ValueError("incompatible transport policies")
    columns = ["nodes", "purpose", "ranks", "decomposition", "transport", "steps", "mean_step_s", "stddev_s", "Cd", "run"]
    ordered = sorted(runs, key=lambda run: (run.nodes, run.run_id))
    rows = [[str(run.nodes), "scaling" if run.nodes < 4 else "scored" if run.cluster in {"gadi", "aspire2a"} else "reference", str(run.ranks), run.decomposition, run.transport, str(run.iterations), str(run.mean), str(run.stddev), run.cd, run.run_id] for run in ordered]
    widths = [max(len(row[index]) for row in [columns, *rows]) for index in range(len(columns))]
    def line(row: list[str]) -> str:
        return "| " + " | ".join(value.ljust(width) for value, width in zip(row, widths, strict=True)) + " |"
    separator = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    output = [f"Cluster: {runs[0].cluster}", f"Commit: {runs[0].commit}", f"Build sidecar: {runs[0].condition['build']}", "Timing stddev is across measured solver steps, not across repeated runs.", separator, line(columns), separator, *map(line, rows), separator]
    for run in ordered:
        output.extend([f"Run: {run.run_id}", f"Actions: {run.actions}", f"Artifact: {run.artifact}", "Members: logs/solver.log; results/result.txt; results/coefficient.dat; source/mesh/decomposeParDict"])
    return "\n".join(output) + "\n"


def export_text(output: Path, runs: list[ScalingRun], bundles: list[dict[str, bytes]]) -> None:
    """Export a reviewed series's text evidence into a new directory only."""
    table = render_scaling(runs)
    if len(bundles) != len(runs):
        raise ValueError("each scaling run requires its artifact bundle")
    selected: dict[Path, str] = {}
    fixed = {
        "results/result.txt", "results/coefficient.dat", "results/coefficient-source.json",
        "control/run-manifest.json", "control/scheduler-request.json",
        "control/build-sidecar.json", "control/build-provision-validation.json",
        "source/workload-manifest.json", "source/mesh/case-cache-manifest.json",
        "source/mesh/controlDict", "source/mesh/caseDefinition", "source/mesh/decomposeParDict",
    }
    for run, members in zip(runs, bundles, strict=True):
        if json.loads(members["control/run-manifest.json"])["run_id"] != run.run_id:
            raise ValueError("export bundle belongs to a different run")
        missing = fixed - members.keys()
        if missing:
            raise ValueError("missing submission evidence: " + ", ".join(sorted(missing)))
        for name, content in members.items():
            if name not in fixed and not name.startswith(("logs/", "source/workload/")):
                continue
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"invalid export member path: {name}")
            try:
                text = content.decode("utf-8")
                if "\x00" in text:
                    raise ValueError("NUL byte")
            except (UnicodeDecodeError, ValueError) as error:
                if name in fixed or name.startswith("source/workload/"):
                    raise ValueError(f"required submission member is not text: {name}") from error
                continue
            selected[Path(f"{run.nodes}node") / run.run_id / name] = text
    # Validate every member before creating any output; mkdir rejects reuse.
    output.mkdir(parents=True, exist_ok=False)
    (output / "scaling.txt").write_text(table, encoding="utf-8")
    for relative, text in selected.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", nargs=2, action="append", required=True, metavar=("ACTIONS_URL", "ARTIFACT_DIRECTORY"))
    parser.add_argument("--output-dir", type=Path, help="export text evidence and scaling.txt into a new directory")
    args = parser.parse_args()
    try:
        bundles = [read_bundle(Path(directory)) for _, directory in args.run]
        runs = [parse_run(actions, str(Path(directory).resolve() / "run-artifacts.tar.zst"), members) for (actions, directory), members in zip(args.run, bundles, strict=True)]
        if args.output_dir is not None:
            export_text(args.output_dir, runs, bundles)
        print(render_scaling(runs), end="")
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"scaling: {error}\n")


if __name__ == "__main__":
    main()
