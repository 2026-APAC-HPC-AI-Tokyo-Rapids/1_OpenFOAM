from pathlib import Path

from experiment_metrics.prepare import prepare_case


def test_prepare_case_adds_metrics_include(tmp_path: Path) -> None:
    system = tmp_path / "system"
    system.mkdir()
    control_dict = system / "controlDict"
    control_dict.write_text("functions\n{\n}\n", encoding="utf-8")
    (system / "forceCoeffs").write_text("forceCoeffs1\n{\n}\n", encoding="utf-8")
    (system / "solverInfo").write_text("solverInfo1\n{\n}\n", encoding="utf-8")

    prepare_case(tmp_path)
    updated = control_dict.read_text(encoding="utf-8")

    assert '#include "forceCoeffs"' in updated
    assert '#include "solverInfo"' in updated
    assert '#include "metricsFunctions"' in updated
    assert (system / "metricsFunctions").is_file()
    assert "coefficients    (Cd Cl CmPitch);" in (system / "forceCoeffs").read_text()
    assert "executeControl  timeStep;" in (system / "solverInfo").read_text()


def test_prepare_case_is_idempotent(tmp_path: Path) -> None:
    system = tmp_path / "system"
    system.mkdir()
    control_dict = system / "controlDict"
    control_dict.write_text("functions\n{\n}\n", encoding="utf-8")
    (system / "forceCoeffs").write_text("forceCoeffs1\n{\n}\n", encoding="utf-8")
    (system / "solverInfo").write_text("solverInfo1\n{\n}\n", encoding="utf-8")

    prepare_case(tmp_path)
    prepare_case(tmp_path)

    assert control_dict.read_text().count('#include "metricsFunctions"') == 1


def test_prepare_case_creates_missing_functions_block(tmp_path: Path) -> None:
    system = tmp_path / "system"
    system.mkdir()
    control_dict = system / "controlDict"
    control_dict.write_text("application simpleFoam;\n", encoding="utf-8")
    (system / "forceCoeffs").write_text("forceCoeffs1\n{\n}\n", encoding="utf-8")
    (system / "solverInfo").write_text("solverInfo1\n{\n}\n", encoding="utf-8")

    prepare_case(tmp_path)
    updated = control_dict.read_text(encoding="utf-8")

    assert "functions\n{" in updated
    assert '#include "forceCoeffs"' in updated
    assert '#include "solverInfo"' in updated
    assert '#include "metricsFunctions"' in updated
