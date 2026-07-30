from experiment_metrics.collectors.scheduler import (
    _milliseconds,
    _parenthetical,
    _timestamp,
)


def test_scheduler_unit_conversions() -> None:
    assert _parenthetical("00 00:00:03 (3)") == "3"
    assert _parenthetical("1.5 GiB (1610612736)") == "1610612736"
    assert _milliseconds("2500") == "2.5"


def test_scheduler_timestamp_uses_genkai_timezone() -> None:
    assert _timestamp("2026/07/30 12:34:56") == "2026-07-30T12:34:56+09:00"
