from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from .fact import Fact
from .manifest import init_run
from .merge import merge_run
from .recording import collect_once
from .stage_runner import run_stage


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="experiment-metrics")
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init-run")
    init.add_argument("--runtime-root", type=Path, required=True)
    init.add_argument("--purpose", choices=["bench", "profile"], required=True)
    init.add_argument("--identities-json", required=True)
    init.add_argument("--repository-id", default="apac2026-openfoam")
    init.add_argument("--settings-path", type=Path)
    init.add_argument("--registry", type=Path)

    record = commands.add_parser("record-json")
    _common(record)
    record.add_argument("--facts", type=Path, required=True)

    stage = commands.add_parser("run-stage")
    _common(stage)
    stage.add_argument("--stage", required=True)
    stage.add_argument("--cwd", type=Path, required=True)
    stage.add_argument(
        "--stderr-mode", choices=["stdout", "separate"], default="separate"
    )
    stage.add_argument("--stdout-path", type=Path)
    stage.add_argument("--fragment-id")
    stage.add_argument("argv", nargs=argparse.REMAINDER)

    merge = commands.add_parser("merge")
    merge.add_argument("--manifest", type=Path, required=True)
    merge.add_argument("--runtime-dir", type=Path, required=True)
    merge.add_argument("--registry", type=Path, required=True)
    merge.add_argument("--protocol", type=Path)

    solver_log = commands.add_parser("record-solver-log")
    _runtime_common(solver_log)
    solver_log.add_argument("--log", type=Path, required=True)
    solver_log.add_argument("--fragment-id", default="solver-log")

    imb = commands.add_parser("record-imb-mpi1")
    _runtime_common(imb)
    imb.add_argument("--stdout", type=Path, required=True)
    imb.add_argument("--source-member", required=True)
    imb.add_argument("--version")
    imb.add_argument("--time-limit-sec", type=int, required=True)
    imb.add_argument("--iteration-policy", choices=["dynamic"], required=True)
    imb.add_argument("--fragment-id", default="imb-mpi1")

    pstream = commands.add_parser("record-pstream")
    _runtime_common(pstream)
    pstream.add_argument("--source-dir", type=Path, required=True)
    pstream.add_argument("--protocol", type=Path, required=True)
    pstream.add_argument("--fragment-id", default="pstream")

    postrun = commands.add_parser("record-postrun")
    _runtime_common(postrun)
    postrun.add_argument("--hardware", type=Path, required=True)
    postrun.add_argument("--hardware-source-member", required=True)
    postrun.add_argument("--topology", type=Path, required=True)
    postrun.add_argument("--decompose-dict", type=Path, required=True)
    postrun.add_argument("--partition-observed", type=Path, required=True)
    postrun.add_argument("--fragment-id", default="postrun")

    package = commands.add_parser("package")
    package.add_argument("--manifest", type=Path, required=True)
    package.add_argument("--member", action="append", default=[])
    package.add_argument("--profile-member", action="append", default=[])

    publish = commands.add_parser("publish")
    publish.add_argument("--manifest", type=Path, required=True)
    publish.add_argument("--artifact-manifest", type=Path, required=True)
    publish.add_argument("--pyproject", type=Path, required=True)
    return root


def _common(command: argparse.ArgumentParser) -> None:
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--runtime-dir", type=Path, required=True)
    command.add_argument("--registry", type=Path, required=True)
    command.add_argument("--producer", required=True)


def _runtime_common(command: argparse.ArgumentParser) -> None:
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--runtime-dir", type=Path, required=True)
    command.add_argument("--registry", type=Path, required=True)


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.command == "init-run":
        identities = json.loads(arguments.identities_json)
        if not isinstance(identities, dict):
            raise ValueError("identities JSON must be an object")
        print(
            init_run(
                arguments.settings_path,
                arguments.runtime_root,
                identities,
                purpose=arguments.purpose,
                repository_id=arguments.repository_id,
                registry_path=arguments.registry,
            )
        )
        return 0
    if arguments.command == "record-json":
        facts = _facts(arguments.facts)
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                arguments.producer,
                lambda: facts,
                registry_path=arguments.registry,
            )
        )
        return 0
    if arguments.command == "run-stage":
        from .recording import Recorder

        command = arguments.argv[1:] if arguments.argv[:1] == ["--"] else arguments.argv
        with Recorder.open(
            arguments.manifest,
            arguments.registry,
            arguments.producer,
            arguments.runtime_dir,
            fragment_id=arguments.fragment_id or f"stage.{arguments.stage}",
        ) as recorder:
            termination = run_stage(
                arguments.stage,
                command,
                cwd=arguments.cwd,
                stderr_mode=arguments.stderr_mode,
                recorder=recorder,
                stdout_path=arguments.stdout_path,
            )
        if termination.kind == "exit":
            return termination.code or 0
        if termination.kind == "signal":
            return 128 + (termination.signal or 0)
        return 127
    if arguments.command == "merge":
        outcome = merge_run(
            arguments.manifest,
            arguments.runtime_dir,
            registry_path=arguments.registry,
            protocol_path=arguments.protocol,
        )
        print(outcome.metrics_path)
        return 0 if outcome.collection_complete else 1
    if arguments.command == "record-solver-log":
        from .reducers import solver_log_facts
        from .solver_log import parse_solver_log

        facts = solver_log_facts(
            parse_solver_log(
                arguments.log.read_text(encoding="utf-8", errors="replace")
            )
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "runner.log_parser",
                lambda: facts,
                registry_path=arguments.registry,
                fragment_id=arguments.fragment_id,
            )
        )
        return 0
    if arguments.command == "record-imb-mpi1":
        from .imb import parse_imb_mpi1
        from .reducers import network_config_facts, network_projection_rows

        results = parse_imb_mpi1(
            arguments.stdout.read_text(encoding="utf-8", errors="replace")
        )
        _write_network_rows(
            arguments.runtime_dir / "domain/network-imb-mpi1-results.jsonl",
            network_projection_rows(
                _run_id(arguments.manifest), results, arguments.source_member
            ),
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "network.parser",
                lambda: network_config_facts(
                    results,
                    arguments.version,
                    time_limit_sec=arguments.time_limit_sec,
                    iteration_policy=arguments.iteration_policy,
                ),
                registry_path=arguments.registry,
                fragment_id=arguments.fragment_id,
            )
        )
        return 0
    if arguments.command == "record-pstream":
        from .manifest import RunManifest
        from .protocol import RunProtocol
        from .pstream import pstream_facts

        manifest = RunManifest.load(arguments.manifest)
        protocol = RunProtocol.load(arguments.protocol, manifest.purpose)
        facts = pstream_facts(
            arguments.source_dir,
            run_id=manifest.run_id,
            expected_ranks=tuple(range(protocol.expected_pstream_ranks)),
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "runner.pstream_parser",
                lambda: facts,
                registry_path=arguments.registry,
                fragment_id=arguments.fragment_id,
            )
        )
        return 0
    if arguments.command == "record-postrun":
        from .postrun import mesh_topology_fact, minimal_hardware_fact, partition_facts

        topology = mesh_topology_fact(arguments.topology)
        partition = partition_facts(
            arguments.decompose_dict,
            arguments.partition_observed,
            topology=topology.logical_value,  # type: ignore[arg-type]
        )
        facts = (
            minimal_hardware_fact(
                arguments.hardware,
                run_id=_run_id(arguments.manifest),
                source_member=arguments.hardware_source_member,
            ),
            topology,
            *partition,
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "runner.postrun_parser",
                lambda: facts,
                registry_path=arguments.registry,
                fragment_id=arguments.fragment_id,
            )
        )
        return 0
    if arguments.command == "package":
        # Runner-only adapter: importing it here keeps compute-only commands
        # independent of tar/archive implementation details.
        from .artifact_store import RunPackager

        result = RunPackager().package(
            arguments.manifest,
            run_members=tuple(_member(item) for item in arguments.member),
            profile_members=tuple(arguments.profile_member),
        )
        print(result.manifest_path)
        return 0
    if arguments.command == "publish":
        # This is the sole CLI branch allowed to load credential-aware code.
        from .publish import BigQueryConfig, publish_metrics

        print(
            publish_metrics(
                arguments.manifest,
                arguments.artifact_manifest,
                BigQueryConfig.load(arguments.pyproject),
            )
        )
        return 0
    raise AssertionError(f"unhandled command: {arguments.command}")


def _facts(path: Path) -> list[Fact]:
    facts: list[Fact] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if not isinstance(item, dict) or set(item) != {"key", "logical_value"}:
            raise ValueError("facts rows need key and logical_value")
        facts.append(Fact(item["key"], item["logical_value"]))
    return facts


def _member(value: str) -> tuple[str, str]:
    relative, separator, role = value.partition(":")
    if not separator or not relative or not role:
        raise ValueError("package --member must be RELATIVE_PATH:ROLE")
    return relative, role


def _run_id(manifest_path: Path) -> str:
    from .manifest import RunManifest

    return RunManifest.load(manifest_path).run_id


def _write_network_rows(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    if path.exists():
        raise FileExistsError(path)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".network-", delete=False
    ) as stream:
        for row in rows:
            stream.write(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
        temporary = Path(stream.name)
    temporary.replace(path)
