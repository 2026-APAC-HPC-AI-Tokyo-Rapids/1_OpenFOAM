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
    ) == (17, "memory-access")


@pytest.mark.parametrize(
    "body",
    [
        '{}',
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"hotspots","rank":true}',
        '{"schema_version":"openfoam-profile-condition/v1","analysis":"unknown","rank":0}',
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
