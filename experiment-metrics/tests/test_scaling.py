from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
from dataclasses import replace

import pytest

from experiment_metrics.scaling import (
    ITERATIONS,
    export_text,
    parse_run,
    read_bundle,
    render_scaling,
)

URL = "https://github.com/team/openfoam/actions/runs/123"


def members_for(nodes):
    ranks, steps = nodes * 120, ITERATIONS[nodes]
    documents = {
        "control/run-manifest.json": {"run_purpose": "bench", "run_id": f"r-{nodes:032x}", "source_track": {"head_commit": "a" * 40}, "instrumentation_bundle_sha256": "b" * 64},
        "control/scheduler-request.json": {"nodes": nodes, "ranks": ranks, "iterations": steps, "pjm_script": {"repository_path": "platforms/genkai/run-openfoam.pjm"}, "workload_id": "65M", "distribution": "OpenFOAM.com", "release": "v2512", "solver": "simpleFoam", "resource_group": "a-batch", "transport_policy": "shm" if nodes == 1 else "shm:ofi"},
        "source/mesh/case-cache-manifest.json": {"number_of_subdomains": ranks, "method": "scotch", "file_handler": "uncollated", "mesh_sha256": "c" * 64, "prepare_script_sha256": "d" * 64, "prepare_toolchain_identity": "e" * 64},
        "source/workload-manifest.json": {"workload_identity": "f" * 64},
        "control/build-provision-validation.json": {"build_sidecar_sha256": "1" * 64, "resolved_libmpi": {"sha256": "2" * 64}},
    }
    members = {name: json.dumps(value).encode() for name, value in documents.items()}
    members["results/result.txt"] = f"STATUS: VALID\nRESULT: average_wall_clock_seconds_per_iteration=1.25 standard_deviation=0.5 measured_iterations={steps - 1} configured_iterations={steps} cells=65334765 ranks={ranks} nodes={nodes} workload_id=65M distribution=OpenFOAM.com release=v2512 solver=simpleFoam\n".encode()
    log = ["Build : OPENFOAM=2512", 'Arch : "LSB;label=32;scalar=64"', "Exec : simpleFoam -parallel", "I/O : uncollated", f"nProcs : {ranks}"]
    for step in range(1, steps + 1):
        log.extend([f"Time = {step}", f"ExecutionTime = {step} s  ClockTime = {step} s"])
    log.extend([f"Number of measured time steps = {steps - 1}", "Average wall-clock time per time step = 1.25", "Standard deviation of wall-clock time per time step = 0.5", "End"])
    members["logs/solver.log"] = "\n".join(log).encode()
    members["results/coefficient.dat"] = f"# Time Cd\n{steps} 0.43\n".encode()
    members["source/mesh/controlDict"] = f"endTime {steps};\nwriteInterval 3000;\n".encode()
    members["source/mesh/caseDefinition"] = f"nCores {ranks};\ndecompositionMethod scotch;\n".encode()
    members["source/mesh/decomposeParDict"] = f"numberOfSubdomains {ranks};\nmethod scotch;\n".encode()
    return members


def runs():
    return [parse_run(URL, f"/archives/{node}/run-artifacts.tar.zst", members_for(node)) for node in (1, 2, 4)]


def test_official_node_dependent_iterations_and_transport_are_comparable():
    output = render_scaling(runs())
    for evidence in ("Commit: " + "a" * 40, URL, "results/coefficient.dat", "logs/solver.log", "results/result.txt", "scotch", "shm:ofi", "0.43", "150", "stddev_s"):
        assert evidence in output


@pytest.mark.parametrize("key", ["commit", "cluster", "build", "mpi", "workload", "mesh", "preparation", "instrumentation", "input/controlDict"])
def test_rejects_mixed_conditions(key):
    series = runs()
    series[1] = replace(series[1], condition={**series[1].condition, key: "different"})
    with pytest.raises(ValueError, match="incompatible scaling conditions"):
        render_scaling(series)


def test_rejects_missing_nodes_duplicate_run_and_unexpected_transport():
    series = runs()
    with pytest.raises(ValueError, match="include 1, 2, and 4"):
        render_scaling(series[:2])
    with pytest.raises(ValueError, match="duplicate"):
        render_scaling([*series, series[0]])
    series[1] = replace(series[1], transport="tcp")
    with pytest.raises(ValueError, match="transport"):
        render_scaling(series)


@pytest.mark.parametrize(("member", "before", "after", "error"), [
    ("control/run-manifest.json", b'"bench"', b'"profile"', "profile"),
    ("results/result.txt", b"STATUS: VALID", b"STATUS: INVALID", "VALID"),
    ("results/result.txt", b"iteration=1.25", b"iteration=2.5", "timing"),
    ("logs/solver.log", b"Time = 40", b"Time = 41", "solver log"),
    ("results/coefficient.dat", b"40 0.43", b"39 0.43", "final step"),
    ("source/mesh/controlDict", b"endTime 40", b"endTime 80", "actual input"),
])
def test_rejects_invalid_run(member, before, after, error):
    members = members_for(1)
    assert before in members[member]
    members[member] = members[member].replace(before, after)
    with pytest.raises(ValueError, match=error):
        parse_run(URL, "/archive/run-artifacts.tar.zst", members)


def test_fixed_archive_roundtrip_and_identity_failure(tmp_path):
    members = members_for(1)
    index = {"run_id": "r-" + f"{1:032x}", "members": [{"path": name, "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(), "role": "source"} for name, content in members.items()]}
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, content in {**members, "bundle.manifest.json": json.dumps(index).encode()}.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    compressed = subprocess.run(["zstd", "-c"], input=buffer.getvalue(), capture_output=True, check=True).stdout
    path = tmp_path / "run-artifacts.tar.zst"
    path.write_bytes(compressed)
    manifest = {"logical_artifact_name": index["run_id"], "files": [{"role": "run_bundle", "size_bytes": len(compressed), "sha256": hashlib.sha256(compressed).hexdigest()}]}
    (tmp_path / "artifact-manifest.json").write_text(json.dumps(manifest))
    assert read_bundle(tmp_path) == members
    path.write_bytes(compressed + b"changed")
    with pytest.raises(ValueError, match="artifact identity"):
        read_bundle(tmp_path)


def export_bundles():
    bundles = [members_for(node) for node in (1, 2, 4)]
    for bundle in bundles:
        bundle["results/coefficient-source.json"] = b'{"source_member":"results/coefficient.dat"}'
        bundle["control/build-sidecar.json"] = b"{}"
        bundle["logs/scheduler.log"] = b"job completed\n"
        bundle["logs/binary.dat"] = b"\xff\x00"
        bundle["source/workload/system/fvSolution"] = b"solvers {}\n"
    return bundles


def test_export_text_and_refuse_overwrite(tmp_path):
    series = runs()
    output = tmp_path / "submission"
    export_text(output, series, export_bundles())
    assert "reference" in (output / "scaling.txt").read_text()
    root = output / "1node" / series[0].run_id
    assert (root / "logs/scheduler.log").read_text() == "job completed\n"
    assert (root / "source/workload/system/fvSolution").is_file()
    assert not (root / "logs/binary.dat").exists()
    assert not list(output.rglob("*.zst"))
    with pytest.raises(FileExistsError):
        export_text(output, series, export_bundles())


def test_export_rejects_missing_or_binary_input_before_creating_directory(tmp_path):
    bundles = export_bundles()
    bundles[0]["source/mesh/controlDict"] = b"\xff"
    output = tmp_path / "submission"
    with pytest.raises(ValueError, match="not text"):
        export_text(output, runs(), bundles)
    assert not output.exists()
    del bundles[0]["source/mesh/controlDict"]
    with pytest.raises(ValueError, match="missing submission evidence"):
        export_text(output, runs(), bundles)
    assert not output.exists()


def test_gadi_four_nodes_are_marked_scored():
    series = [replace(run, cluster="gadi", transport="ucx", condition={**run.condition, "cluster": "gadi"}) for run in runs()]
    table = render_scaling(series)
    assert "scored" in table
    assert "reference" not in table
