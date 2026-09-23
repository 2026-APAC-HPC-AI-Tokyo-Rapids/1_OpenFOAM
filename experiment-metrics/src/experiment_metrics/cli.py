from __future__ import annotations

import argparse
import json
from pathlib import Path

from .fact import Fact
from .manifest import init_run
from .recording import collect_once
from .stage_runner import run_stage


def _profile_condition(arguments: argparse.Namespace) -> tuple[int, str, int]:
    path = arguments.profile_condition
    if path is None:
        return arguments.profile_rank, arguments.profile_analysis, 0
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not {"schema_version", "analysis", "rank"} <= set(document) or set(document) - {
        "schema_version",
        "analysis",
        "rank",
        "diagnostic_iterations",
    }:
        raise ValueError("profile condition must be a closed v1 object")
    if document["schema_version"] != "openfoam-profile-condition/v1":
        raise ValueError("unsupported profile condition schema")
    rank = document["rank"]
    analysis = document["analysis"]
    if not isinstance(rank, int) or isinstance(rank, bool) or rank < 0:
        raise ValueError("profile condition rank must be a non-negative integer")
    if analysis not in {
        "assess",
        "data_access",
        "hotspots",
        "hpc-performance",
        "memory-access",
        "memory-access-core",
        "mpi",
    }:
        raise ValueError("unsupported profile analysis")
    diagnostic_iterations = document.get("diagnostic_iterations", 0)
    if not isinstance(diagnostic_iterations, int) or isinstance(diagnostic_iterations, bool) or diagnostic_iterations not in {0, 40}:
        raise ValueError("diagnostic profile requires exactly 40 iterations")
    return rank, analysis, diagnostic_iterations


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
    init.add_argument("--instrumentation-bundle", type=Path)

    bundle = commands.add_parser("bundle-identity")
    bundle.add_argument("--bundle", type=Path, required=True)
    bundle.add_argument("--purpose", choices=["bench", "profile"], required=True)

    runtime_bundle = commands.add_parser("validate-bundle-runtime")
    runtime_bundle.add_argument("--manifest", type=Path, required=True)
    runtime_bundle.add_argument("--bundle", type=Path, required=True)
    runtime_bundle.add_argument("--registry", type=Path, required=True)

    build_state = commands.add_parser("capture-build-state")
    build_state.add_argument("--output", type=Path, required=True)
    build_state.add_argument("--build-tree", type=Path, required=True)
    build_state.add_argument("--build-definition-repo", type=Path, required=True)
    build_state.add_argument("--openfoam-oid", required=True)
    build_state.add_argument(
        "--openfoam-algorithm", choices=["sha1", "sha256"], required=True
    )
    build_state.add_argument("--thirdparty-oid", required=True)
    build_state.add_argument(
        "--thirdparty-algorithm", choices=["sha1", "sha256"], required=True
    )
    build_state.add_argument("--executable", action="append", default=[])
    build_state.add_argument("--compile-flag", action="append", default=[])
    build_state.add_argument("--compiler-c", type=Path, required=True)
    build_state.add_argument("--compiler-cxx", type=Path, required=True)
    build_state.add_argument("--mpi-launcher", type=Path, required=True)
    build_state.add_argument("--precision", choices=["SP", "DP"], required=True)
    build_state.add_argument("--label-bits", choices=[32, 64], type=int, required=True)

    build_finalize = commands.add_parser("finalize-build-sidecar")
    build_finalize.add_argument("--state", type=Path, required=True)
    build_finalize.add_argument("--archive", type=Path, required=True)
    build_finalize.add_argument("--output", type=Path, required=True)

    build_verify = commands.add_parser("verify-build-pair")
    build_verify.add_argument("--sidecar", type=Path, required=True)
    build_verify.add_argument("--archive", type=Path, required=True)

    provision = commands.add_parser("validate-provision")
    provision.add_argument("--manifest", type=Path, required=True)
    provision.add_argument("--build-sidecar", type=Path, required=True)
    provision.add_argument("--provision-root", type=Path, required=True)
    provision.add_argument("--output", type=Path, required=True)
    provision.add_argument("--executable", action="append", default=[])

    source_track = commands.add_parser("source-track-identities")
    source_track.add_argument("--repository", type=Path, required=True)
    source_track.add_argument("--purpose", choices=["bench", "profile"], required=True)
    source_track.add_argument("--base-commit", required=True)
    source_track.add_argument("--control-plane-file", action="append", default=[])
    source_track.add_argument("--instrumentation-bundle-sha256", required=True)

    submit = commands.add_parser("submit-run")
    _runtime_common(submit)
    submit.add_argument("--protocol", type=Path, required=True)
    submit.add_argument("--pjm-script-repository-path", required=True)
    submit.add_argument("--execution-script", type=Path, required=True)
    submit.add_argument("--provision-dir", type=Path, required=True)
    submit.add_argument("--profile-condition", type=Path)
    submit.add_argument("--profile-rank", type=int, default=0)
    submit.add_argument(
        "--profile-analysis",
        choices=["hotspots", "hpc-performance", "memory-access", "memory-access-core"],
        default="hotspots",
    )

    submit_pbs = commands.add_parser("submit-pbs-run")
    _runtime_common(submit_pbs)
    submit_pbs.add_argument("--protocol", type=Path, required=True)
    submit_pbs.add_argument("--pbs-script-repository-path", required=True)
    submit_pbs.add_argument("--execution-script", type=Path, required=True)
    submit_pbs.add_argument("--provision-dir", type=Path, required=True)
    submit_pbs.add_argument("--profile-tool", choices=["craypat", "uprof", "vtune"], default="vtune")
    submit_pbs.add_argument("--profile-condition", type=Path)
    submit_pbs.add_argument("--profile-rank", type=int, default=0)
    submit_pbs.add_argument(
        "--profile-analysis",
        choices=["assess", "data_access", "hotspots", "hpc-performance", "memory-access", "memory-access-core", "mpi"],
        default="hotspots",
    )

    supervisor_start = commands.add_parser("supervisor-start")
    supervisor_start.add_argument("--manifest", type=Path, required=True)
    supervisor_start.add_argument("--state", type=Path, required=True)
    supervisor_start.add_argument("--job-id", required=True)

    supervisor_mark = commands.add_parser("supervisor-mark-pipeline")
    supervisor_mark.add_argument("--state", type=Path, required=True)
    supervisor_mark.add_argument("--mark", choices=["start", "finish"], required=True)

    supervisor_finish = commands.add_parser("supervisor-finish")
    supervisor_finish.add_argument("--manifest", type=Path, required=True)
    supervisor_finish.add_argument("--state", type=Path, required=True)
    supervisor_finish.add_argument("--exit-code", type=int, required=True)

    host_exec = commands.add_parser("capture-host-exec")
    host_exec.add_argument("--manifest", type=Path, required=True)
    host_exec.add_argument("--output", type=Path, required=True)

    capture_argv = commands.add_parser("capture-argv")
    capture_argv.add_argument("--manifest", type=Path, required=True)
    capture_argv.add_argument("--output", type=Path, required=True)
    capture_argv.add_argument("argv", nargs=argparse.REMAINDER)

    terminal = commands.add_parser("record-scheduler-terminal")
    _runtime_common(terminal)
    terminal.add_argument("--job-id", required=True)

    pbs_terminal = commands.add_parser("record-pbs-terminal")
    _runtime_common(pbs_terminal)
    pbs_terminal.add_argument("--job-id", required=True)
    pbs_terminal.add_argument("--protocol", type=Path, required=True)

    execution_context = commands.add_parser("record-execution-context")
    _runtime_common(execution_context)
    execution_context.add_argument("--protocol", type=Path, required=True)
    execution_context.add_argument("--host-snapshot", type=Path, required=True)
    execution_context.add_argument("--placement-root", type=Path, required=True)
    execution_context.add_argument("--scheduler-request", type=Path, required=True)
    execution_context.add_argument("--scheduler-accounting", type=Path, required=True)
    execution_context.add_argument("--decompose-dict", type=Path, required=True)
    execution_context.add_argument("--solver-log", type=Path, required=True)

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
    stage.add_argument("--stderr-path", type=Path)
    stage.add_argument("--timeout-sec", type=int)
    stage.add_argument("--fragment-id")
    stage.add_argument("argv", nargs=argparse.REMAINDER)

    solver_log = commands.add_parser("record-solver-log")
    _runtime_common(solver_log)
    solver_log.add_argument("--log", type=Path, required=True)
    solver_log.add_argument("--protocol", type=Path, required=True)
    solver_log.add_argument("--fragment-id", default="solver-log")
    solver_log.add_argument("--coefficient", type=Path)

    coefficient = commands.add_parser("parse-coefficient")
    coefficient.add_argument("--path", type=Path, required=True)
    coefficient.add_argument("--iterations", type=int, required=True)
    collect_coefficient = commands.add_parser("collect-coefficient")
    collect_coefficient.add_argument("--case-root", type=Path, required=True)
    collect_coefficient.add_argument("--output-root", type=Path, required=True)
    collect_coefficient.add_argument("--iterations", type=int, required=True)

    imb = commands.add_parser("record-imb-mpi1")
    _runtime_common(imb)
    imb.add_argument("--stdout", type=Path, required=True)
    imb.add_argument("--stderr", type=Path, required=True)
    imb.add_argument("--argv-json", type=Path, required=True)
    imb.add_argument("--protocol", type=Path, required=True)
    imb.add_argument("--source-member", required=True)
    imb.add_argument("--fragment-id", default="imb-mpi1")

    build_provision = commands.add_parser("record-build-provision")
    _runtime_common(build_provision)
    build_provision.add_argument("--build-provision", type=Path, required=True)

    hardware = commands.add_parser("record-minimal-hardware")
    _runtime_common(hardware)
    hardware.add_argument("--hardware-root", type=Path, required=True)
    hardware.add_argument("--protocol", type=Path, required=True)

    mesh = commands.add_parser("record-mesh")
    _runtime_common(mesh)
    mesh.add_argument("--decompose-dict", type=Path, required=True)
    mesh.add_argument("--check-mesh-log", type=Path, required=True)
    mesh.add_argument("--decompose-log", type=Path, required=True)

    profile_hardware = commands.add_parser("record-profile-hardware")
    _runtime_common(profile_hardware)
    profile_hardware.add_argument("--profile-hardware-root", type=Path, required=True)
    profile_hardware.add_argument("--protocol", type=Path, required=True)

    profile_vtune = commands.add_parser("record-profile-vtune")
    _runtime_common(profile_vtune)
    profile_vtune.add_argument("--report", type=Path, required=True)
    profile_vtune.add_argument("--status", type=Path, required=True)
    profile_vtune.add_argument("--summary", type=Path, required=True)
    profile_vtune.add_argument("--markdown", type=Path, required=True)
    profile_vtune.add_argument("--profiled-rank", type=int, required=True)
    profile_vtune.add_argument(
        "--analysis-type",
        choices=["hotspots", "hpc-performance", "memory-access"],
        required=True,
    )
    profile_vtune.add_argument("--collection-duration-sec", type=int, required=True)

    profile_uprof = commands.add_parser("record-profile-uprof")
    _runtime_common(profile_uprof)
    profile_uprof.add_argument("--report-root", type=Path, required=True)
    profile_uprof.add_argument("--expected-hosts", type=int, required=True)
    profile_uprof.add_argument("--expected-ranks", type=int, required=True)
    profile_uprof.add_argument("--uprof-rank-stride", type=int, default=1)
    profile_uprof.add_argument("--analysis-type", choices=["assess", "data_access", "hotspots"], default="hotspots")
    profile_uprof.add_argument("--summary", type=Path, required=True)
    profile_uprof.add_argument("--markdown", type=Path, required=True)

    workload = commands.add_parser("capture-workload")
    workload.add_argument("--manifest", type=Path, required=True)
    workload.add_argument("--case-root", type=Path, required=True)
    workload.add_argument("--output-root", type=Path, required=True)
    workload.add_argument("--definition", type=Path, required=True)

    package = commands.add_parser("package")
    package.add_argument("--manifest", type=Path, required=True)
    package.add_argument("--member", action="append", default=[])
    package.add_argument("--profile-member", action="append", default=[])

    artifact_index = commands.add_parser("record-artifact-index")
    _runtime_common(artifact_index)
    artifact_index.add_argument("--build-sidecar", type=Path, required=True)

    smoke = commands.add_parser("smoke-send")
    smoke.add_argument("--run", required=True)
    smoke.add_argument("--source", choices=["runner", "compute"], required=True)

    fragments = commands.add_parser("send-fragments")
    fragments.add_argument("--manifest", type=Path, required=True)
    fragments.add_argument("--runtime-dir", type=Path, required=True)
    return root


def _common(command: argparse.ArgumentParser) -> None:
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--runtime-dir", type=Path, required=True)
    command.add_argument("--producer", required=True)


def _runtime_common(command: argparse.ArgumentParser) -> None:
    command.add_argument("--manifest", type=Path, required=True)
    command.add_argument("--runtime-dir", type=Path, required=True)


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
                instrumentation_bundle_path=arguments.instrumentation_bundle,
            )
        )
        return 0
    if arguments.command == "bundle-identity":
        from .instrumentation import bundle_identity

        print(bundle_identity(arguments.bundle, purpose=arguments.purpose))
        return 0
    if arguments.command == "validate-bundle-runtime":
        from .instrumentation import validate_runtime_bindings

        print(
            json.dumps(
                validate_runtime_bindings(
                    arguments.manifest,
                    arguments.bundle,
                    arguments.registry,
                ),
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    if arguments.command == "capture-build-state":
        from .build_provenance import capture_build_state

        print(
            capture_build_state(
                output=arguments.output,
                build_tree=arguments.build_tree,
                build_definition_repo=arguments.build_definition_repo,
                openfoam_oid=arguments.openfoam_oid,
                openfoam_algorithm=arguments.openfoam_algorithm,
                thirdparty_oid=arguments.thirdparty_oid,
                thirdparty_algorithm=arguments.thirdparty_algorithm,
                executable_paths=_role_paths(arguments.executable),
                compile_flags=arguments.compile_flag,
                compiler_c=arguments.compiler_c,
                compiler_cxx=arguments.compiler_cxx,
                mpi_launcher=arguments.mpi_launcher,
                precision=arguments.precision,
                label_bits=arguments.label_bits,
            )
        )
        return 0
    if arguments.command == "finalize-build-sidecar":
        from .build_provenance import finalize_build_sidecar

        print(
            finalize_build_sidecar(arguments.state, arguments.archive, arguments.output)
        )
        return 0
    if arguments.command == "verify-build-pair":
        from .build_provenance import verify_build_pair

        verify_build_pair(arguments.sidecar, arguments.archive)
        print(arguments.sidecar)
        return 0
    if arguments.command == "validate-provision":
        from .provision import validate_provision

        print(
            validate_provision(
                manifest_path=arguments.manifest,
                build_sidecar_path=arguments.build_sidecar,
                provision_root=arguments.provision_root,
                output=arguments.output,
                executable_paths=_role_paths(arguments.executable),
            )
        )
        return 0
    if arguments.command == "source-track-identities":
        from .fact import canonical_json
        from .source_track import source_track_identities

        print(
            canonical_json(
                source_track_identities(
                    repository=arguments.repository,
                    purpose=arguments.purpose,
                    base_commit=arguments.base_commit,
                    control_plane_files=arguments.control_plane_file,
                    instrumentation_bundle_sha256=(
                        arguments.instrumentation_bundle_sha256
                    ),
                )
            )
        )
        return 0
    if arguments.command == "submit-run":
        from .scheduler import submit_run

        profile_rank, profile_analysis, diagnostic_iterations = _profile_condition(arguments)
        if diagnostic_iterations:
            raise ValueError("short diagnostic profiles are supported only on ASPIRE-2A")

        outcome = submit_run(
            manifest_path=arguments.manifest,
            runtime_dir=arguments.runtime_dir,
            protocol_path=arguments.protocol,
            pjm_script_repository_path=arguments.pjm_script_repository_path,
            execution_script=arguments.execution_script,
            provision_dir=arguments.provision_dir,
            profile_rank=profile_rank,
            profile_analysis=profile_analysis,
        )
        if outcome.job_id is not None:
            print(outcome.job_id)
        return 0 if outcome.job_id is not None else 1
    if arguments.command == "submit-pbs-run":
        from .pbs_scheduler import submit_pbs_run

        profile_rank, profile_analysis, diagnostic_iterations = _profile_condition(arguments)

        outcome = submit_pbs_run(
            manifest_path=arguments.manifest,
            runtime_dir=arguments.runtime_dir,
            protocol_path=arguments.protocol,
            pbs_script_repository_path=arguments.pbs_script_repository_path,
            execution_script=arguments.execution_script,
            provision_dir=arguments.provision_dir,
            profile_tool=arguments.profile_tool,
            profile_rank=profile_rank,
            profile_analysis=profile_analysis,
            diagnostic_iterations=diagnostic_iterations,
        )
        if outcome.job_id is not None:
            print(outcome.job_id)
        return 0 if outcome.job_id is not None else 1
    if arguments.command == "supervisor-start":
        from .supervisor import start_supervisor

        print(
            start_supervisor(
                arguments.manifest, arguments.state, job_id=arguments.job_id
            )
        )
        return 0
    if arguments.command == "supervisor-mark-pipeline":
        from .supervisor import mark_pipeline

        print(mark_pipeline(arguments.state, arguments.mark))
        return 0
    if arguments.command == "supervisor-finish":
        from .supervisor import finish_supervisor

        print(
            finish_supervisor(
                arguments.manifest,
                arguments.state,
                exit_code=arguments.exit_code,
            )
        )
        return 0
    if arguments.command == "capture-host-exec":
        from .environment import capture_snapshot
        from .manifest import RunManifest

        manifest = RunManifest.load(arguments.manifest)
        expected = manifest.path.parents[1] / "source/env/host-exec.snapshot"
        if arguments.output.resolve() != expected.resolve():
            raise ValueError("host execution snapshot is outside the bound run")
        print(capture_snapshot(arguments.output))
        return 0
    if arguments.command == "capture-argv":
        from .fact import canonical_json
        from .manifest import RunManifest

        manifest = RunManifest.load(arguments.manifest)
        expected = manifest.path.parents[1] / "source/network/imb-mpi1/argv.json"
        if arguments.output.resolve() != expected.resolve():
            raise ValueError("argv capture is outside its fixed run path")
        command = arguments.argv[1:] if arguments.argv[:1] == ["--"] else arguments.argv
        if not command or any(not item for item in command):
            raise ValueError("captured argv must be a nonempty string array")
        if arguments.output.exists():
            raise FileExistsError(arguments.output)
        arguments.output.write_text(
            canonical_json({"schema_version": "argv/v1", "argv": command}) + "\n",
            encoding="utf-8",
        )
        print(arguments.output)
        return 0
    if arguments.command == "record-scheduler-terminal":
        from .scheduler import capture_scheduler_terminal

        print(
            capture_scheduler_terminal(
                manifest_path=arguments.manifest,
                runtime_dir=arguments.runtime_dir,
                job_id=arguments.job_id,
            )
        )
        return 0
    if arguments.command == "record-pbs-terminal":
        from .pbs_scheduler import capture_pbs_terminal

        print(
            capture_pbs_terminal(
                manifest_path=arguments.manifest,
                runtime_dir=arguments.runtime_dir,
                protocol_path=arguments.protocol,
                job_id=arguments.job_id,
            )
        )
        return 0
    if arguments.command == "record-execution-context":
        from .execution_context import record_execution_context

        print(
            record_execution_context(
                manifest_path=arguments.manifest,
                runtime_dir=arguments.runtime_dir,
                protocol_path=arguments.protocol,
                host_snapshot=arguments.host_snapshot,
                placement_root=arguments.placement_root,
                scheduler_request=arguments.scheduler_request,
                scheduler_accounting=arguments.scheduler_accounting,
                decompose_dictionary=arguments.decompose_dict,
                solver_log=arguments.solver_log,
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
            )
        )
        return 0
    if arguments.command == "run-stage":
        from .recording import Recorder

        command = arguments.argv[1:] if arguments.argv[:1] == ["--"] else arguments.argv
        with Recorder.open(
            arguments.manifest,
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
                stderr_path=arguments.stderr_path,
                timeout_sec=arguments.timeout_sec,
            )
        if termination.kind == "exit":
            return termination.code or 0
        if termination.kind == "signal":
            return 128 + (termination.signal or 0)
        return 127
    if arguments.command == "parse-coefficient":
        from .coefficient import parse_coefficient

        observation = parse_coefficient(arguments.path, arguments.iterations)
        print(f"CD_SANITY: cd={observation['cd']} step={observation['step']} source_member=results/coefficient.dat reference={observation['reference']} (reference only; no pass/fail threshold)")
        return 0
    if arguments.command == "collect-coefficient":
        from .coefficient import collect_coefficient

        print(collect_coefficient(arguments.case_root, arguments.output_root, arguments.iterations))
        return 0
    if arguments.command == "record-solver-log":
        from .manifest import RunManifest
        from .protocol import RunProtocol
        from .reducers import solver_log_facts
        from .solver_log import parse_solver_log

        manifest = RunManifest.load(arguments.manifest)
        facts = solver_log_facts(parse_solver_log(arguments.log.read_text(encoding="utf-8", errors="replace")), RunProtocol.load(arguments.protocol, manifest.purpose))
        if arguments.coefficient is not None:
            from .coefficient import coefficient_fact

            facts += (coefficient_fact(arguments.coefficient, RunProtocol.load(arguments.protocol, manifest.purpose).iteration_target),)
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "runner.log_parser",
                lambda: facts,
                fragment_id=arguments.fragment_id,
            )
        )
        return 0
    if arguments.command == "record-imb-mpi1":
        from .imb import validate_imb_capture
        from .manifest import RunManifest
        from .protocol import RunProtocol
        from .reducers import network_config_facts

        manifest = RunManifest.load(arguments.manifest)
        run_dir = manifest.path.parents[1]
        expected_sources = {
            "stdout": run_dir / "source/network/imb-mpi1/stdout.txt",
            "stderr": run_dir / "source/network/imb-mpi1/stderr.txt",
            "argv": run_dir / "source/network/imb-mpi1/argv.json",
        }
        if (
            arguments.stdout.resolve(strict=True)
            != expected_sources["stdout"].resolve(strict=True)
            or arguments.stderr.resolve(strict=True)
            != expected_sources["stderr"].resolve(strict=True)
            or arguments.argv_json.resolve(strict=True)
            != expected_sources["argv"].resolve(strict=True)
            or arguments.source_member != "source/network/imb-mpi1/stdout.txt"
        ):
            raise ValueError("IMB sources are outside their fixed run paths")
        capture = validate_imb_capture(
            stdout_path=arguments.stdout,
            stderr_path=arguments.stderr,
            argv_path=arguments.argv_json,
            protocol=RunProtocol.load(arguments.protocol, manifest.purpose),
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "network.parser",
                lambda: network_config_facts(
                    capture.results,
                    capture.version,
                    process_count=capture.process_count,
                    time_limit_sec=capture.time_limit_sec,
                    iteration_policy=capture.iteration_policy,
                ),
                fragment_id=arguments.fragment_id,
            )
        )
        return 0
    if arguments.command == "record-build-provision":
        from .manifest import RunManifest
        from .postrun import build_provision_fact

        manifest = RunManifest.load(arguments.manifest)
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "compute.build_provision_parser",
                lambda: (
                    build_provision_fact(
                        arguments.build_provision, purpose=manifest.purpose
                    ),
                ),
                fragment_id="build-provision",
            )
        )
        return 0
    if arguments.command == "record-minimal-hardware":
        from .manifest import RunManifest
        from .postrun import minimal_hardware_fact
        from .protocol import RunProtocol

        manifest = RunManifest.load(arguments.manifest)
        protocol = RunProtocol.load(arguments.protocol, manifest.purpose)
        facts = tuple(
            minimal_hardware_fact(
                arguments.hardware_root / f"node-{ordinal}.json",
                run_id=manifest.run_id,
                source_member=f"source/hardware/node-{ordinal}.json",
            )
            for ordinal in range(protocol.nodes)
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "compute.minimal_hardware_parser",
                lambda: facts,
                fragment_id="minimal-hardware",
            )
        )
        return 0
    if arguments.command == "record-mesh":
        from .postrun import mesh_facts_from_logs

        facts = mesh_facts_from_logs(
            arguments.check_mesh_log,
            arguments.decompose_log,
            arguments.decompose_dict,
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "compute.mesh_parser",
                lambda: facts,
                fragment_id="mesh",
            )
        )
        return 0
    if arguments.command == "record-profile-hardware":
        from .manifest import RunManifest
        from .postrun import profile_hardware_facts
        from .protocol import RunProtocol

        manifest = RunManifest.load(arguments.manifest)
        protocol = RunProtocol.load(arguments.protocol, manifest.purpose)
        facts = profile_hardware_facts(
            arguments.profile_hardware_root,
            run_id=manifest.run_id,
            expected_nodes=protocol.nodes,
        )
        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "compute.profile_hardware_parser",
                lambda: facts,
                fragment_id="profile-hardware",
            )
        )
        return 0
    if arguments.command == "record-profile-vtune":
        from .profile_vtune import record_vtune_hotspots

        print(
            record_vtune_hotspots(
                manifest_path=arguments.manifest,
                runtime_dir=arguments.runtime_dir,
                report_root=arguments.report_root,
                expected_hosts=arguments.expected_hosts,
                expected_ranks=arguments.expected_ranks,
                status_path=arguments.status,
                summary_path=arguments.summary,
                markdown_path=arguments.markdown,
                profiled_rank=arguments.profiled_rank,
                analysis_type=arguments.analysis_type,
                collection_duration_sec=arguments.collection_duration_sec,
            )
        )
        return 0
    if arguments.command == "record-profile-uprof":
        from .profile_uprof import record_uprof

        print(
            record_uprof(
                manifest_path=arguments.manifest,
                runtime_dir=arguments.runtime_dir,
                report_root=arguments.report_root,
                expected_hosts=arguments.expected_hosts,
                expected_ranks=arguments.expected_ranks,
                profile_rank_stride=arguments.uprof_rank_stride,
                analysis_type=arguments.analysis_type,
                summary_path=arguments.summary,
                markdown_path=arguments.markdown,
            )
        )
        return 0
    if arguments.command == "capture-workload":
        from .workload import capture_workload

        print(
            capture_workload(
                arguments.manifest,
                arguments.case_root,
                arguments.output_root,
                arguments.definition,
            )
        )
        return 0
    if arguments.command == "record-artifact-index":
        from .build_provenance import build_artifact_facts

        print(
            collect_once(
                arguments.manifest,
                arguments.runtime_dir,
                "runner.artifact_index",
                lambda: build_artifact_facts(
                    arguments.manifest, arguments.build_sidecar
                ),
                fragment_id="artifact-index",
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
    if arguments.command == "smoke-send":
        from .publish import send_raw

        return (
            0
            if send_raw(
                arguments.run,
                [
                    {
                        "run": arguments.run,
                        "key": f"smoke.{arguments.source}",
                        "value": "true",
                    }
                ],
            )
            else 1
        )
    if arguments.command == "send-fragments":
        from .publish import send_fragments

        return 0 if send_fragments(arguments.manifest, arguments.runtime_dir) else 1
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


def _role_paths(values: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        role, separator, path = value.partition("=")
        if not separator or not role or not path or role in result:
            raise ValueError("--executable must be unique ROLE=PATH values")
        result[role] = Path(path)
    return result


def _run_id(manifest_path: Path) -> str:
    from .manifest import RunManifest

    return RunManifest.load(manifest_path).run_id
