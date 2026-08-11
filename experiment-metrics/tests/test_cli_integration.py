from __future__ import annotations

import json
from pathlib import Path

from experiment_metrics import init_run
from experiment_metrics.cli import main
from experiment_metrics.fact import canonical_json

FIXTURES = Path(__file__).parent / "fixtures"


def _complete_imb() -> str:
    lines = ["IMB-MPI1 2021.3"]
    for benchmark in ("PingPong", "Sendrecv", "Allreduce"):
        lines.extend((f"# Benchmarking {benchmark}", "# #processes = 2"))
        if benchmark == "Allreduce":
            lines.append("#bytes #repetitions t_min[usec] t_max[usec] t_avg[usec]")
            row = "{size} 1000 0.1 0.3 0.2"
        else:
            lines.append("#bytes #repetitions t[usec] Mbytes/sec")
            row = "{size} 1000 0.1 1.0"
        exponents = range(2, 23) if benchmark == "Allreduce" else range(23)
        for size in (0, *(1 << exponent for exponent in exponents)):
            lines.append(row.format(size=size))
    return "\n".join(lines) + "\n"


def test_cli_records_saved_solver_and_imb_sources(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest_path.parents[1]
    log = run_dir / "logs/solver.log"
    log.write_text((FIXTURES / "solver-valid.log").read_text())
    imb = run_dir / "source/network/imb-mpi1/stdout.txt"
    imb.parent.mkdir(parents=True)
    imb.write_text(_complete_imb())
    stderr = imb.parent / "stderr.txt"
    stderr.write_bytes(b"")
    imb_argv = [
        "/bin/true",
        "-np",
        "2",
        "-ppn",
        "2",
        "/bin/true",
        "-npmin",
        "2",
        "-msglog",
        "0:22",
        "-iter",
        "1000",
        "-time",
        "1",
        "-iter_policy",
        "dynamic",
        "PingPong",
        "Sendrecv",
        "Allreduce",
    ]
    argv_json = imb.parent / "argv.json"
    argv_json.write_text(
        canonical_json({"schema_version": "argv/v1", "argv": imb_argv}) + "\n"
    )
    digest = "a" * 64
    protocol = tmp_path / "protocol.toml"
    protocol.write_text(
        f"""
[protocol]
schema_version = "openfoam-v2-run-protocol/v1"
[variant.bench]
expected_stages = ["solver"]
nodes = 1
ranks = 2
resource_group = "test"
transport_policy = "shm"
workload_id = "test"
expected_workload_identity = "{digest}"
[variant.profile]
expected_stages = ["solver"]
nodes = 1
ranks = 2
resource_group = "test"
transport_policy = "shm"
workload_id = "test"
expected_workload_identity = "{digest}"
""".strip()
        + "\n"
    )

    assert (
        main(
            [
                "record-solver-log",
                "--manifest",
                str(manifest_path),
                "--runtime-dir",
                str(run_dir),
                "--registry",
                str(registry_path),
                "--log",
                str(log),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "record-imb-mpi1",
                "--manifest",
                str(manifest_path),
                "--runtime-dir",
                str(run_dir),
                "--registry",
                str(registry_path),
                "--stdout",
                str(imb),
                "--stderr",
                str(stderr),
                "--argv-json",
                str(argv_json),
                "--protocol",
                str(protocol),
                "--source-member",
                "source/network/imb-mpi1/stdout.txt",
            ]
        )
        == 0
    )
    rows = [
        json.loads(line)
        for line in (run_dir / "domain/network-imb-mpi1-results.jsonl")
        .read_text()
        .splitlines()
    ]
    assert rows[0]["source_member"] == "source/network/imb-mpi1/stdout.txt"


def test_cli_package_excludes_merged_metrics(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest_path.parents[1]
    (run_dir / "logs/solver.log").write_text("done\n")
    assert (
        main(
            [
                "package",
                "--manifest",
                str(manifest_path),
                "--member",
                "logs/solver.log:solver_log",
            ]
        )
        == 0
    )

    assert not (run_dir / "metrics.jsonl").exists()
