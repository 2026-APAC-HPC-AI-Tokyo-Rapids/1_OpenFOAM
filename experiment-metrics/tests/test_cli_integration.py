from __future__ import annotations

import json
from pathlib import Path

from experiment_metrics import init_run
from experiment_metrics.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_records_saved_solver_and_imb_sources(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest_path.parents[1]
    log = run_dir / "logs/solver.log"
    log.write_text((FIXTURES / "solver-valid.log").read_text())
    imb = run_dir / "source/network/imb-mpi1/stdout.txt"
    imb.parent.mkdir(parents=True)
    imb.write_text((FIXTURES / "imb-complete.txt").read_text())

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
                "--source-member",
                "source/network/imb-mpi1/stdout.txt",
                "--version",
                "2021.3",
                "--time-limit-sec",
                "1",
                "--iteration-policy",
                "dynamic",
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


def test_cli_package_and_publish_are_lazy_runner_adapters(
    tmp_path: Path,
    registry_path: Path,
    identities: dict[str, object],
    monkeypatch: object,
) -> None:
    manifest_path = init_run(None, tmp_path, identities, registry_path=registry_path)
    run_dir = manifest_path.parents[1]
    (run_dir / "logs/solver.log").write_text("done\n")
    run_id = manifest_path.parents[1].name
    (run_dir / "metrics.jsonl").write_text(
        json.dumps({"run": run_id, "key": "collection_complete", "value": "false"})
        + "\n"
    )
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

    import experiment_metrics.publish as publication

    monkeypatch.setattr(publication, "publish_metrics", lambda *_args, **_kwargs: 1)
    assert (
        main(
            [
                "publish",
                "--manifest",
                str(manifest_path),
                "--artifact-manifest",
                str(run_dir / "artifact-manifest.json"),
                "--pyproject",
                str(Path(__file__).parents[1] / "pyproject.toml"),
            ]
        )
        == 0
    )
