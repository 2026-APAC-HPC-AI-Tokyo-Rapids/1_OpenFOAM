from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from experiment_metrics.manifest import init_run
from experiment_metrics.profile_uprof import parse_uprof_hotspots, record_uprof_hotspots

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
            *arguments,
        ],
        check=True,
        capture_output=True,
    )

    host = subprocess.check_output(["hostname"], text=True).strip()
    expected = [
        "collect",
        "--config",
        "hotspots",
        "-g",
        "--mpi",
        "--output-dir",
        str(session_root / host),
        *arguments,
    ]
    assert completed.stdout.split(b"\0")[:-1] == [item.encode() for item in expected]


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
    report_root.mkdir(parents=True)
    report = report_root / "node-a.csv"
    report.write_text(_report(report_scope="node-a", cutoff="0"))
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
        "aggregation": "sum function/module CPU times across complete host reports",
        "call_stack_sampling": True,
        "mpi": True,
        "report_cutoff": 0,
        "report_host_scope": "per-host",
    }
    assert value["source"]["reports"][0]["member"] == "profile/raw/uprof/reports/node-a.csv"
    assert value["ranks_per_node"] == [{"host": "node-a", "ranks": 2}]
    document = json.loads(summary.read_text())
    assert document["profile_duration_sec"] == "12.340"
    assert document["source_hotspots"] == 2
    rendered = markdown.read_text()
    assert "slow\\|function" in rendered
    assert "complete reports from every host" in rendered


def test_recording_aggregates_complete_host_reports(
    tmp_path: Path, registry_path: Path, identities: dict[str, object]
) -> None:
    manifest = _profile_run(tmp_path, registry_path, identities)
    run_dir = manifest.parents[1]
    report_root = run_dir / "profile/raw/uprof/reports"
    report_root.mkdir(parents=True)
    for host in ("node-a", "node-b"):
        (report_root / f"{host}.csv").write_text(
            _report(host=host, report_scope=host, cutoff="0")
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
    assert value["hotspots"][0]["cpu_time_sec"] == "3.0000"
    assert len(value["source"]["reports"]) == 2
