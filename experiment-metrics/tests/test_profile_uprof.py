from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics.manifest import init_run
from experiment_metrics.profile_uprof import parse_uprof_hotspots, record_uprof_hotspots


def _report(*, collect: str | None = None, ranks: str = "2", hosts: str = "1") -> str:
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
Report Command:,"./AMDuProfCLI report --input-dir /run/profile/raw/uprof/sessions/AMDuProf-simpleFoam-Hotspots_MPI --host all --detail --cutoff 30"

PROFILE DETAILS
Profile Session Type:,"Hotspots"
Profile Duration:,"12.340 seconds"
Call Stack Sampling:,"True"

APPLICATION PERFORMANCE SNAPSHOT
Thread Count,"{ranks}"
Number Of MPI ranks,"{ranks}"
Number Of MPI hosts,"{hosts}"

MPI Ranks Per Node
node-a,{ranks}

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
    report = run_dir / "profile/raw/uprof/report.csv"
    report.parent.mkdir(parents=True)
    report.write_text(_report())
    summary = run_dir / "results/uprof-summary.json"
    markdown = run_dir / "results/uprof-summary.md"

    fragment = record_uprof_hotspots(
        manifest_path=manifest,
        runtime_dir=run_dir,
        report_path=report,
        summary_path=summary,
        markdown_path=markdown,
    )

    row = json.loads(fragment.read_text())
    assert row["key"] == "profile.uprof_hotspots"
    value = json.loads(row["value"])
    assert value["tool_version"] == "5.3.521.0"
    assert value["collection"] == {
        "analysis_type": "hotspots",
        "call_stack_sampling": True,
        "mpi": True,
        "report_cutoff": 30,
        "report_host_scope": "all",
    }
    assert value["source"]["member"] == "profile/raw/uprof/report.csv"
    assert value["ranks_per_node"] == [{"host": "node-a", "ranks": 2}]
    document = json.loads(summary.read_text())
    assert document["profile_duration_sec"] == "12.340"
    assert document["source_hotspots"] == 2
    rendered = markdown.read_text()
    assert "slow\\|function" in rendered
    assert "complete session is retained" in rendered
