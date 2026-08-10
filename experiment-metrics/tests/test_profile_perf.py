from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from experiment_metrics.profile_perf import (
    EVENTS,
    PerfConflictError,
    PerfProjectionRow,
    PerfValidationError,
    deduplicate_projection_rows,
    parse_perf_csv,
    perf_command,
    project_profile_perf,
)

RUN_ID = "openfoam-profile-0123456789abcdef"


def _csv() -> str:
    return (
        "\n".join(
            (
                "123,,cycles,1000000,100.00,1.25,",
                "<not counted>,,instructions,900000,90.00,2.5,",
                "3.0,counts,branches,800000,80.00,3.5,events",
                "4e2,,branch-misses,700000,70.00,4.5,",
                "5,,cache-misses,600000,60.00,5.5,",
            )
        )
        + "\n"
    )


def test_perf_parser_preserves_lexemes_and_nulls() -> None:
    record = parse_perf_csv(
        _csv(),
        run_id=RUN_ID,
        global_rank=0,
        source_member="profile/raw/perf/rank-0.csv",
        source_sha256="a" * 64,
    )
    assert tuple(item.event_name for item in record.items) == EVENTS
    assert record.items[0].raw_count_lexeme == "123"
    assert record.items[0].count == Decimal("123")
    assert record.items[1].count is None
    assert record.items[1].running_ns == Decimal("900000")
    assert record.items[3].raw_count_lexeme == "4e2"
    assert record.items[3].count == Decimal("4e2")
    assert record.items[2].metric_value_lexeme == "3.5"


def test_perf_parser_requires_fixed_event_order_and_columns() -> None:
    with pytest.raises(PerfValidationError):
        parse_perf_csv(
            _csv().replace("cycles", "instructions", 1),
            run_id=RUN_ID,
            global_rank=0,
        )
    with pytest.raises(PerfValidationError):
        parse_perf_csv(
            "1,,cycles,1,100,1\n" * 5,
            run_id=RUN_ID,
            global_rank=0,
        )


def test_perf_command_is_exact_and_shell_free() -> None:
    command = perf_command(
        Path("/opt/perf"),
        Path("/run/profile/perf/rank-0.csv"),
        Path("/opt/icoFoam"),
        ("-case", "/run/case"),
    )
    assert command == (
        "/opt/perf",
        "stat",
        "--no-big-num",
        "-x,",
        "-o",
        "/run/profile/perf/rank-0.csv",
        "-e",
        "cycles,instructions,branches,branch-misses,cache-misses",
        "--",
        "/opt/icoFoam",
        "-case",
        "/run/case",
    )


def _write_rank(runtime: Path, rank: int, *, metadata: bool = True) -> None:
    perf = runtime / "profile/raw/perf"
    perf.mkdir(parents=True, exist_ok=True)
    csv_path = perf / f"rank-{rank}.csv"
    csv_path.write_text(_csv(), encoding="utf-8")
    if metadata:
        (perf / f"rank-{rank}.json").write_text(
            "{"
            '"argv":["/opt/perf","stat"],'
            f'"cpu_affinity":[{rank}],'
            f'"environment":{{"PMI_RANK":"{rank}"}},'
            f'"global_rank":{rank},"hostname":"node-a",'
            '"local_rank":0,"local_size":2,"numa_mems":"0",'
            f'"output_member":"profile/raw/perf/rank-{rank}.csv",'
            f'"run_id":"{RUN_ID}","schema_version":"openfoam-rank-launch/v1"'
            "}\n",
            encoding="utf-8",
        )


def test_profile_projection_has_rank_completeness_and_rank_facts(
    tmp_path: Path,
) -> None:
    _write_rank(tmp_path, 0)
    _write_rank(tmp_path, 1)
    projection = project_profile_perf(tmp_path, run_id=RUN_ID, expected_ranks=3)
    assert not projection.collection_complete
    assert projection.missing_ranks == (2,)
    assert len(projection.rows) == 10
    assert len(projection.rank_facts) == 2
    assert (
        projection.rows[0].as_dict()["source_member"] == "profile/raw/perf/rank-0.csv"
    )


def test_projection_dedupes_equal_rows_and_keeps_conflicts() -> None:
    record = parse_perf_csv(
        _csv(), run_id=RUN_ID, global_rank=0, source_sha256="a" * 64
    )
    row = PerfProjectionRow(RUN_ID, 0, record.items[0], record.source_member, "a" * 64)
    duplicate = PerfProjectionRow(
        RUN_ID, 0, record.items[0], record.source_member, "a" * 64
    )
    rows, conflicts = deduplicate_projection_rows((row, duplicate))
    assert rows == (row,)
    assert conflicts == ()
    changed_item = replace(
        record.items[0], raw_count_lexeme="999", count=Decimal("999")
    )
    changed = PerfProjectionRow(
        RUN_ID,
        0,
        changed_item,
        record.source_member,
        "a" * 64,
    )
    rows, conflicts = deduplicate_projection_rows((row, changed))
    assert rows == ()
    assert len(conflicts) == 1
    with pytest.raises(PerfConflictError):
        raise PerfConflictError(conflicts)
