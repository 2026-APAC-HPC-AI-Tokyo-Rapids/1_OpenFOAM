from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from experiment_metrics.artifact_store import Member
from experiment_metrics.coefficient import (
    coefficient_fact,
    collect_coefficient,
    parse_coefficient_text,
)


@pytest.mark.parametrize(("iterations", "cd"), [(40, "0.435"), (80, "0.337"), (150, "0.287")])
def test_coefficient_column_order_and_final_step(iterations: int, cd: str) -> None:
    text = f"# Force coefficients\n# Time Cl Cd CmPitch\n0 1 0.5 2\n{iterations} 1 {cd} 2\n"
    assert parse_coefficient_text(text, iterations)["cd"] == cd
    assert parse_coefficient_text(text, iterations)["step"] == iterations


@pytest.mark.parametrize("text", [
    "", "40 0.435\n", "# Time Cl\n40 0.435\n", "# Time Cd Cd\n40 0.435 0.435\n",
    "# Time Cd\n# Time Cd\n40 0.435\n", "# Time Cd\n40 NaN\n", "# Time Cd\n40 inf\n",
    "# Time Cd\n40 bad\n", "# Time Cd\n39 0.435\n", "# Time Cd\n40 0.435 extra\n",
    "# Time Cd\n40 0.435\n40 0.435\n", "# Time Cd\n41 0.435\n40 0.435\n",
])
def test_malformed_coefficient_is_an_error(text: str) -> None:
    with pytest.raises(ValueError):
        parse_coefficient_text(text, 40)


def test_node_local_coefficients_survive_case_removal(tmp_path: Path) -> None:
    case = tmp_path / "jobfs/case"
    source = case / "postProcessing/forceCoeffsAll/0/coefficient.dat"
    source.parent.mkdir(parents=True)
    raw = b"# Time Cd Cl\n40 0.435 0.02\n"
    source.write_bytes(raw)
    run = tmp_path / "shared/run"
    target = collect_coefficient(case, run / "results", 40)
    shutil.rmtree(case)
    assert target.read_bytes() == raw
    metadata = json.loads((run / "results/coefficient-source.json").read_text())
    assert metadata == {"source_path": str(source), "case_member": "postProcessing/forceCoeffsAll/0/coefficient.dat", "source_member": "results/coefficient.dat", "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    member = Member.from_file(run, "results/coefficient.dat", "force_coefficients")
    assert member.sha256 == metadata["sha256"]
    assert coefficient_fact(target, 40).logical_value["cd"] == "0.435"


def test_missing_or_ambiguous_output_fails_collection(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="found 0"):
        collect_coefficient(tmp_path, tmp_path / "results", 40)
    for time in ["0", "1"]:
        source = tmp_path / f"postProcessing/forceCoeffsAll/{time}/coefficient.dat"
        source.parent.mkdir(parents=True)
        source.write_text("# Time Cd\n40 0.435\n")
    with pytest.raises(ValueError, match="found 2"):
        collect_coefficient(tmp_path, tmp_path / "results", 40)


def test_malformed_raw_output_is_retained(tmp_path: Path) -> None:
    source = tmp_path / "case/postProcessing/forceCoeffsAll/0/coefficient.dat"
    source.parent.mkdir(parents=True)
    source.write_text("# Time Cd\n40 NaN\n")
    with pytest.raises(ValueError, match="non-finite"):
        collect_coefficient(tmp_path / "case", tmp_path / "results", 40)
    assert (tmp_path / "results/coefficient.dat").read_text() == source.read_text()


def test_shell_and_metric_share_cd_without_a_threshold(tmp_path: Path) -> None:
    source = tmp_path / "coefficient.dat"
    source.write_text("# Time Cd\n40 9.5\n")
    metrics = Path(__file__).parents[1] / ".venv/bin/experiment-metrics"
    output = subprocess.run([metrics, "parse-coefficient", "--path", source, "--iterations", "40"], check=True, capture_output=True, text=True).stdout
    value = coefficient_fact(source, 40).logical_value
    assert f"cd={value['cd']} step={value['step']}" in output
    assert "no pass/fail threshold" in output


def test_profile_warmup_preserves_raw_without_renaming_solver_coefficients(tmp_path: Path) -> None:
    repository = Path(__file__).parents[2]
    script = (repository / "scripts/run-openfoam.sh").read_text()
    warmup = script[script.index('  stage profile_warmup '):]
    warmup = warmup[:warmup.index('\nfi')]
    case = tmp_path / "jobfs/case"
    case.mkdir(parents=True)
    run = tmp_path / "shared/run"
    # The stub emits the post-processing file written by official v2512 at time 0.
    harness = '''set -euo pipefail
solver_launch=()
openfoam_args=()
stage() {
  mkdir -p "${CASE_DIR}/postProcessing/forceCoeffsAll/0"
  printf '# Time Cd\\n0 0.5\\n' > "${CASE_DIR}/postProcessing/forceCoeffsAll/0/coefficient.dat"
}
'''
    subprocess.run(["bash", "-c", harness + warmup], env={**os.environ, "CASE_DIR": str(case), "RUN_DIR": str(run), "LOG_DIR": str(run / "logs"), "ENV": "/usr/bin/env", "SIMPLE_FOAM": "/simpleFoam", "vtune_root": str(run / "large-output/vtune")}, check=True)
    saved = run / "profile/raw/warmup-postProcessing/forceCoeffsAll/0/coefficient.dat"
    assert saved.read_text() == "# Time Cd\n0 0.5\n"
    assert not (case / "postProcessing").exists()
    # Reproduce writeFile::newFileAtTime: an existing file gets a _0 suffix.
    official = case / "postProcessing/forceCoeffsAll/0/coefficient.dat"
    official.parent.mkdir(parents=True)
    selected = official.with_name("coefficient_0.dat") if official.exists() else official
    selected.write_text("# Time Cd\n40 0.435\n")
    target = collect_coefficient(case, run / "results", 40)
    assert target.read_text() == "# Time Cd\n40 0.435\n"
    assert saved.read_text() == "# Time Cd\n0 0.5\n"
