from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/vtune-hotspots-summary.py"
FIXTURE = ROOT / "tests/fixtures/vtune-hotspots.csv"


def load_summary_module():
    spec = importlib.util.spec_from_file_location("vtune_hotspots_summary", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reads_vtune_hotspots_with_units() -> None:
    module = load_summary_module()
    hotspots = module.read_hotspots(FIXTURE)

    assert hotspots[0] == {
        "function": "PMPI_Allreduce",
        "module": "libmpi.so",
        "cpu_time_sec": 11.36,
    }
    assert module._number("120ms") == 0.12


def test_cli_writes_json_and_actions_markdown(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    markdown = tmp_path / "summary.md"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--hotspots",
            str(FIXTURE),
            "--summary",
            str(summary),
            "--markdown",
            str(markdown),
            "--limit",
            "2",
        ],
        check=True,
    )

    document = json.loads(summary.read_text(encoding="utf-8"))
    rendered = markdown.read_text(encoding="utf-8")
    assert document["schema_version"] == "openfoam-vtune-hotspots-summary/v1"
    assert document["exported_hotspots"] == 2
    assert document["collection_duration_sec"] == 60
    assert document["reported_cpu_time_sec"] == 21.58
    assert "## Intel VTune hotspots" in rendered
    assert "PMPI_Allreduce" in rendered
    assert "Attached sampling window: 60 s" in rendered
    assert "Perfetto" not in rendered
