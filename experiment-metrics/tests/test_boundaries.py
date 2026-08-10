from __future__ import annotations

from pathlib import Path


def test_core_has_no_cloud_or_workflow_dependency() -> None:
    source_root = Path(__file__).parents[1] / "src/experiment_metrics"
    core_modules = (
        "fact.py",
        "manifest.py",
        "registry.py",
        "recording.py",
        "stage_runner.py",
        "merge.py",
    )
    content = "\n".join((source_root / name).read_text() for name in core_modules)

    assert "google.auth" not in content
    assert "urllib.request" not in content
    assert "BigQuery" not in content
