from argparse import Namespace

import pytest

from experiment_metrics.cli import _profile_condition


def test_profile_condition_loads_tracked_condition(tmp_path) -> None:
    condition = tmp_path / "profile.json"
    condition.write_text(
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"memory-access","rank":17}\n',
        encoding="utf-8",
    )

    assert _profile_condition(
        Namespace(
            profile_condition=condition,
            profile_rank=0,
            profile_analysis="hotspots",
        )
    ) == (17, "memory-access", 0)


def test_profile_condition_accepts_selected_rank_memory_events(tmp_path) -> None:
    condition = tmp_path / "profile.json"
    condition.write_text(
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"memory-access-core","rank":365}\n',
        encoding="utf-8",
    )

    assert _profile_condition(
        Namespace(
            profile_condition=condition,
            profile_rank=0,
            profile_analysis="hotspots",
        )
    ) == (365, "memory-access-core", 0)


def test_profile_condition_accepts_uprof_assess(tmp_path) -> None:
    condition = tmp_path / "profile.json"
    condition.write_text('{"schema_version":"openfoam-profile-condition/v1","analysis":"assess","rank":0}\n', encoding="utf-8")

    assert _profile_condition(Namespace(profile_condition=condition, profile_rank=0, profile_analysis="hotspots")) == (0, "assess", 0)


def test_profile_condition_accepts_craypat_mpi(tmp_path) -> None:
    condition = tmp_path / "profile.json"
    condition.write_text('{"schema_version":"openfoam-profile-condition/v1","analysis":"mpi","rank":0}\n', encoding="utf-8")

    assert _profile_condition(Namespace(profile_condition=condition, profile_rank=0, profile_analysis="hotspots")) == (0, "mpi", 0)


def test_profile_condition_accepts_short_diagnostic(tmp_path) -> None:
    condition = tmp_path / "profile.json"
    condition.write_text('{"schema_version":"openfoam-profile-condition/v1","analysis":"mpi","rank":0,"diagnostic_iterations":40}\n', encoding="utf-8")

    assert _profile_condition(Namespace(profile_condition=condition, profile_rank=0, profile_analysis="hotspots")) == (0, "mpi", 40)


def test_profile_condition_accepts_mpi_timing_diagnostic(tmp_path) -> None:
    condition = tmp_path / "profile.json"
    condition.write_text('{"schema_version":"openfoam-profile-condition/v1","analysis":"mpi_timing","rank":0,"diagnostic_iterations":40}\n', encoding="utf-8")

    assert _profile_condition(Namespace(profile_condition=condition, profile_rank=0, profile_analysis="hotspots")) == (0, "mpi_timing", 40)


@pytest.mark.parametrize(
    "body",
    [
        '{}',
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"hotspots","rank":true}',
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"unknown","rank":0}',
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"mpi","rank":0,"diagnostic_iterations":true}',
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"mpi","rank":0,"diagnostic_iterations":39}',
    ],
)
def test_profile_condition_rejects_invalid_documents(tmp_path, body) -> None:
    condition = tmp_path / "profile.json"
    condition.write_text(body, encoding="utf-8")

    with pytest.raises(ValueError):
        _profile_condition(
            Namespace(
                profile_condition=condition,
                profile_rank=0,
                profile_analysis="hotspots",
            )
        )
