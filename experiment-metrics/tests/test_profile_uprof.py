from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from experiment_metrics.cli import main
from experiment_metrics.manifest import init_run
from experiment_metrics.profile_uprof import (
    parse_uprof_counters,
    parse_uprof_hotspots,
    record_uprof,
    record_uprof_hotspots,
)

ROOT = Path(__file__).parents[2]


def _report(
    *,
    collect: str | None = None,
    ranks: str = "2",
    hosts: str = "1",
    host: str = "node-a",
    report_scope: str = "all",
    cutoff: str = "30",
) -> str:
    collect = (
        collect
        or "./AMDuProfCLI collect --config hotspots -g --mpi --output-dir /run/profile/raw/uprof/sessions /opt/OpenFOAM/bin/simpleFoam -parallel"
    )
    return f'''\
"AMD uProf (Version:5.3.521.0)"
PERFORMANCE ANALYSIS REPORT

EXECUTION
Target Path:,"/opt/OpenFOAM/bin/simpleFoam"
Collect Command:,"{collect}"
Report Command:,"./AMDuProfCLI report --input-dir /run/profile/raw/uprof/sessions/AMDuProf-simpleFoam-Hotspots_MPI --host {report_scope} --detail --cutoff {cutoff}"

PROFILE DETAILS
Profile Session Type:,"Hotspots"
Profile Duration:,"12.340 seconds"
Call Stack Sampling:,"True"

APPLICATION PERFORMANCE SNAPSHOT
Thread Count,"{ranks}"
Number Of MPI ranks,"{ranks}"
Number Of MPI hosts,"{hosts}"

MPI Ranks Per Node
{host},{ranks}

"30 HOTTEST FUNCTIONS (Sort Event - CPU_TIME)"
FUNCTION,"CPU_TIME" (seconds),"TOTAL_CPU_TIME (s)",Module
"slow|function",0.2500,0.7500,"libsolver.so"
"fast",1.5000,2.0000,"simpleFoam"

"30 HOTTEST PROCESSES (Sort Event - CPU_TIME)"
PROCESS,"CPU_TIME" (seconds),MPI RANK ID
'''


def _profile_run(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> Path:
    profile_identities = json.loads(json.dumps(identities))
    profile_identities["source_track"]["base_role"] = "profile_base"
    return init_run(
        None,
        tmp_path,
        profile_identities,
        purpose="profile",
        registry_path=registry_path,
    )


def _rank_report(*, host: str, rank: int) -> str:
    report = _report(ranks="1", host=host, report_scope=host, cutoff="30")
    report = report.replace(" -g --mpi --output-dir", " -g --output-dir")
    report = report.replace(
        f'Number Of MPI ranks,"1"\nNumber Of MPI hosts,"1"\n\nMPI Ranks Per Node\n{host},1\n\n',
        "",
    )
    return report.replace(
        "/run/profile/raw/uprof/sessions/AMDuProf-simpleFoam-Hotspots_MPI",
        f"/run/profile/raw/uprof/sessions/{host}/rank-{rank}/AMDuProf-simpleFoam-Hotspots",
    )


def _assess_report(*, host: str = "node-a", scale: int = 1) -> str:
    events = ("CYCLES_NOT_IN_HALT.USER", "RETIRED_INST.USER", "RETIRED_BR_INST.USER", "RETIRED_BR_INST_MISP.USER", "MISALIGNED_LOADS.USER", "L1_DC_ACCESSES_ALL.USER", "L1_DEMAND_DC_REFILLS_LOCAL.USER", "L1_DEMAND_DC_REFILLS_REMOTE.USER", "L2_CACHE_ACCESS_FROM_L1_DC_MISS.USER")
    monitored = "\n".join(f',"{event} (PMCx001)",100000,0x00,0x00,False,True,False,"fixture"' for event in events)
    header = ",".join(("PROCESS", *events))
    function_header = ",".join(("FUNCTION", *events, "Module"))
    values = [1000, 2000, 200, 10, 2, 500, 80, 20, 100]
    row = ",".join(("simpleFoam (PID:1)", *(str(value * scale) for value in values)))
    function_row = ",".join(("Foam::solve", *(str(value * scale) for value in values), "libfiniteVolume.so"))
    return f'''\
"AMD uProf (Version:5.3.521.0)"
PERFORMANCE ANALYSIS REPORT

EXECUTION
Target Path:,"/opt/OpenFOAM/bin/simpleFoam"
Collect Command:,"./AMDuProfCLI collect --config assess --output-dir /run/session /opt/OpenFOAM/bin/simpleFoam -parallel"
Report Command:,"./AMDuProfCLI report --input-dir /run/session --host {host} --detail --cutoff 30 --show-event-count"

PROFILE DETAILS
Profile Session Type:,"Assess Performance"
Profile Duration:,"12.000 seconds"
Call Stack Sampling:,"False"

MONITORED EVENTS
PMC Events:,Name,Interval,Unitmask,Countmask,Invert Countmask,User,OS,Description
{monitored}

"30 HOTTEST FUNCTIONS (Sort Event - CYCLES_NOT_IN_HALT.USER)"
{function_header}
{function_row}

"ALL PROCESSES (Sort Event - CYCLES_NOT_IN_HALT.USER)"
{header}
{row}

'''


def test_counter_parser_validates_assess_events() -> None:
    report = parse_uprof_counters(_assess_report(), analysis_type="assess", expected_host_scope="node-a")
    assert dict(report.counts)["RETIRED_INST.USER"] == 2000
    assert report.functions[0][0] == "Foam::solve"


def test_counter_recorder_aggregates_sampled_ranks(tmp_path: Path, registry_path: Path, identities: dict[str, object]) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    report_root = run_dir / "profile/raw/uprof/reports/node-a"
    report_root.mkdir(parents=True)
    (report_root / "rank-0.csv").write_text(_assess_report(scale=1))
    (report_root / "rank-16.csv").write_text(_assess_report(scale=2))

    result = record_uprof(manifest_path=manifest, runtime_dir=run_dir, report_root=report_root.parent, expected_hosts=1, expected_ranks=32, profile_rank_stride=16, analysis_type="assess", summary_path=run_dir / "results/uprof-summary.json", markdown_path=run_dir / "results/uprof-summary.md")

    summary = json.loads(result.read_text())
    assert summary["aggregate_event_counts"]["CYCLES_NOT_IN_HALT.USER"] == "3000"
    assert summary["derived_metrics"]["ipc"] == "2"
    assert summary["derived_metrics"]["remote_refill_share"] == "0.2"


def test_launcher_preserves_distributed_openfoam_arguments(tmp_path: Path) -> None:
    cli = tmp_path / "AMDuProfCLI-bin"
    cli.write_text("#!/usr/bin/env bash\nprintf '%s\\0' \"$@\"\n", encoding="utf-8")
    cli.chmod(0o755)
    arguments = [
        "/opt/OpenFOAM/bin/simpleFoam",
        "-hostRoots",
        '((".*" "/var/tmp/openfoam case"))',
        "-ioRanks",
        "(0 128 256 384)",
    ]
    session_root = tmp_path / "sessions"

    completed = subprocess.run(
        [
            "bash",
            str(ROOT / "platforms/aspire2a/exec-uprof.sh"),
            str(cli),
            str(session_root),
            "hotspots",
            *arguments,
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "PMI_RANK": "17", "PMI_LOCAL_RANK": "0"},
    )

    host = subprocess.check_output(["hostname"], text=True).strip()
    expected = [
        "collect",
        "--config",
        "hotspots",
        "-g",
        "--output-dir",
        str(session_root / host / "rank-17"),
        *arguments,
    ]
    assert completed.stdout.split(b"\0")[:-1] == [item.encode() for item in expected]


def test_launcher_profiles_only_numa_representative_ranks(tmp_path: Path) -> None:
    cli = tmp_path / "AMDuProfCLI-bin"
    cli.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
    cli.chmod(0o755)
    target = tmp_path / "target"
    target.write_text("#!/usr/bin/env bash\nprintf '%s\\0' \"$@\"\n", encoding="utf-8")
    target.chmod(0o755)

    completed = subprocess.run(
        [
            "bash",
            str(ROOT / "platforms/aspire2a/exec-uprof.sh"),
            str(cli),
            str(tmp_path / "sessions"),
            "hotspots",
            str(target),
            "argument",
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "PMI_RANK": "18", "PMI_LOCAL_RANK": "2"},
    )

    assert completed.stdout == b"argument\0"
    assert not (tmp_path / "sessions").exists()


def test_exporter_reports_every_sampled_rank(tmp_path: Path) -> None:
    cli = tmp_path / "AMDuProfCLI-bin"
    cli.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "while [[ $# -gt 0 ]]; do\n"
        "  if [[ $1 == --input-dir ]]; then input_dir=$2; shift 2; else shift; fi\n"
        "done\n"
        "printf 'rank report\\n' > \"${input_dir}/report.csv\"\n",
        encoding="utf-8",
    )
    cli.chmod(0o755)
    output_root = tmp_path / "uprof"
    for rank, host in ((0, "node-a"), (16, "node-a"), (32, "node-b"), (48, "node-b")):
        (output_root / "sessions" / host / f"rank-{rank}" / "AMDuProf-test").mkdir(
            parents=True
        )

    subprocess.run(
        [
            "bash",
            str(ROOT / "platforms/aspire2a/export-uprof.sh"),
            str(cli),
            str(output_root),
            "hotspots",
        ],
        check=True,
        env={**os.environ, "OPENFOAM_NODES": "2", "OPENFOAM_MPI_PROCS": "64"},
    )

    assert sorted(
        path.relative_to(output_root / "reports").as_posix()
        for path in (output_root / "reports").glob("*/rank-*.csv")
    ) == [
        "node-a/rank-0.csv",
        "node-a/rank-16.csv",
        "node-b/rank-32.csv",
        "node-b/rank-48.csv",
    ]
    assert len((output_root / "session.txt").read_text().splitlines()) == 4


def test_target_launcher_restores_nul_delimited_openfoam_arguments(
    tmp_path: Path,
) -> None:
    target = tmp_path / "simpleFoam"
    target.write_text("#!/usr/bin/env bash\nprintf '%s\\0' \"$@\"\n", encoding="utf-8")
    target.chmod(0o755)
    arguments = [
        str(target),
        "-parallel",
        "-fileHandler",
        "uncollated",
        "-hostRoots",
        '((".*" "/var/tmp/openfoam case"))',
        "-ioRanks",
        "(0 128 256 384)",
    ]
    argv_file = tmp_path / "uprof-target.argv"
    argv_file.write_bytes(b"\0".join(item.encode() for item in arguments) + b"\0")
    launcher = tmp_path / "exec-uprof-target"
    subprocess.run(
        [
            "cc",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-std=c11",
            "-o",
            str(launcher),
            str(ROOT / "platforms/aspire2a/exec-uprof-target.c"),
        ],
        check=True,
    )

    completed = subprocess.run(
        [str(launcher), str(argv_file)],
        check=True,
        capture_output=True,
    )

    assert completed.stdout.split(b"\0")[:-1] == [
        item.encode() for item in arguments[1:]
    ]


def test_parser_validates_mpi_protocol_and_preserves_lexemes() -> None:
    report = parse_uprof_hotspots(_report())

    assert report.mpi_ranks == 2
    assert report.mpi_hosts == 1
    assert report.ranks_per_node == (("node-a", 2),)
    assert [item.function for item in report.hotspots] == ["fast", "slow|function"]
    assert report.hotspots[1].cpu_time_lexeme == "0.2500"
    assert report.duration_lexeme == "12.340 seconds"


@pytest.mark.parametrize(
    "source",
    [
        _report(
            collect="./AMDuProfCLI collect --config hotspots -g --output-dir /tmp /bin/true"
        ),
        _report().replace("--host all", "--host node-a"),
        _report().replace(
            'Call Stack Sampling:,"True"', 'Call Stack Sampling:,"False"'
        ),
        _report(hosts="2"),
        _report().replace("0.2500", "not-a-number", 1),
        _report().replace("fast", "", 1),
    ],
)
def test_parser_rejects_incomplete_or_ambiguous_reports(source: str) -> None:
    with pytest.raises(ValueError):
        parse_uprof_hotspots(source)


def test_recording_writes_structured_fact_and_bounded_summary(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    report_root = run_dir / "profile/raw/uprof/reports"
    (report_root / "node-a").mkdir(parents=True)
    for rank in range(2):
        (report_root / "node-a" / f"rank-{rank}.csv").write_text(
            _rank_report(host="node-a", rank=rank)
        )
    summary = run_dir / "results/uprof-summary.json"
    markdown = run_dir / "results/uprof-summary.md"

    fragment = record_uprof_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        report_root=report_root,
        expected_hosts=1,
        expected_ranks=2,
        summary_path=summary,
        markdown_path=markdown,
    )

    row = json.loads(fragment.read_text())
    assert row["key"] == "profile.uprof_hotspots"
    value = json.loads(row["value"])
    assert value["tool_version"] == "5.3.521.0"
    assert value["collection"] == {
        "analysis_type": "hotspots",
        "aggregation": "sum function/module CPU times across profiled ranks without extrapolation",
        "application_mpi": True,
        "call_stack_sampling": True,
        "profile_rank_stride": 1,
        "rank_selection": "local rank modulo profile rank stride equals zero",
        "report_cutoff": 30,
        "report_scope": "local-rank-stride sample",
        "uprof_mpi_session": False,
    }
    assert value["source"]["reports"][0]["member"] == (
        "profile/raw/uprof/reports/node-a/rank-0.csv"
    )
    assert value["ranks_per_node"] == [{"host": "node-a", "ranks": 2}]
    document = json.loads(summary.read_text())
    assert document["profile_duration_sec"] == "12.340"
    assert document["source_hotspots"] == 2
    rendered = markdown.read_text()
    assert "slow\\|function" in rendered
    assert "sampled-rank reports without extrapolation" in rendered


def test_recording_aggregates_complete_rank_reports(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    report_root = run_dir / "profile/raw/uprof/reports"
    report_root.mkdir(parents=True)
    for rank, host in enumerate(("node-a", "node-a", "node-b", "node-b")):
        (report_root / host).mkdir(exist_ok=True)
        (report_root / host / f"rank-{rank}.csv").write_text(
            _rank_report(host=host, rank=rank)
        )

    fragment = record_uprof_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        report_root=report_root,
        expected_hosts=2,
        expected_ranks=4,
        summary_path=run_dir / "results/uprof-summary.json",
        markdown_path=run_dir / "results/uprof-summary.md",
    )

    value = json.loads(json.loads(fragment.read_text())["value"])
    assert value["mpi_ranks"] == 4
    assert value["mpi_hosts"] == 2
    assert value["ranks_per_node"] == [
        {"host": "node-a", "ranks": 2},
        {"host": "node-b", "ranks": 2},
    ]
    assert value["hotspots"][0]["function"] == "fast"
    assert value["hotspots"][0]["cpu_time_sec"] == "6.0000"
    assert len(value["source"]["reports"]) == 4


def test_recording_preserves_application_topology_for_sampled_ranks(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    report_root = run_dir / "profile/raw/uprof/reports/node-a"
    report_root.mkdir(parents=True)
    for rank in (0, 16):
        (report_root / f"rank-{rank}.csv").write_text(
            _rank_report(host="node-a", rank=rank)
        )

    fragment = record_uprof_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        report_root=report_root.parent,
        expected_hosts=1,
        expected_ranks=32,
        profile_rank_stride=16,
        summary_path=run_dir / "results/uprof-summary.json",
        markdown_path=run_dir / "results/uprof-summary.md",
    )

    value = json.loads(json.loads(fragment.read_text())["value"])
    assert value["mpi_ranks"] == 32
    assert value["ranks_per_node"] == [{"host": "node-a", "ranks": 32}]
    assert value["profiled_mpi_ranks"] == 2
    assert value["profiled_ranks_per_node"] == [{"host": "node-a", "ranks": 2}]
    assert value["collection"]["profile_rank_stride"] == 16


def test_cli_records_per_rank_reports(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    report_root = run_dir / "profile/raw/uprof/reports"
    (report_root / "node-a").mkdir(parents=True)
    (report_root / "node-a/rank-0.csv").write_text(
        _rank_report(host="node-a", rank=0)
    )

    assert main(
        [
            "record-profile-uprof",
            "--manifest",
            str(manifest),
            "--runtime-dir",
            str(run_dir),
            "--report-root",
            str(report_root),
            "--expected-hosts",
            "1",
            "--expected-ranks",
            "16",
            "--uprof-rank-stride",
            "16",
            "--summary",
            str(run_dir / "results/uprof-summary.json"),
            "--markdown",
            str(run_dir / "results/uprof-summary.md"),
        ]
    ) == 0
