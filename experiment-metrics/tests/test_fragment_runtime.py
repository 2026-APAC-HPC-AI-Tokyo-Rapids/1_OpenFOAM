from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_runtime_has_no_merge_or_metrics_sidecar_implementation() -> None:
    package = ROOT / "experiment-metrics/src/experiment_metrics"
    assert not (package / "merge.py").exists()
    assert not (package / "projections.py").exists()
    workflow = (ROOT / ".github/workflows/genkai.yml").read_text(encoding="utf-8")
    assert "metrics.jsonl" not in workflow
    assert " merge --manifest" not in workflow
    assert " publish --manifest" not in workflow
