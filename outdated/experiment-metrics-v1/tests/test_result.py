from pathlib import Path

from experiment_metrics.collectors.result import collect
from experiment_metrics.context import Context


def test_aero_collector_uses_available_tail_rows(tmp_path: Path) -> None:
    output = tmp_path / "postProcessing/forceCoeffs1/0"
    output.mkdir(parents=True)
    (output / "coefficient.dat").write_text(
        "# Time Cd Cl CmPitch\n1 1.0 2.0 3.0\n2 3.0 4.0 5.0\n",
        encoding="utf-8",
    )
    context = Context("run", tmp_path, None)
    values = {metric.key: metric.value for metric in collect(context)}

    assert values["result.aero.tail.window_size"] == "2"
    assert values["result.aero.cd.tail.mean"] == "2.0"
    assert values["result.aero.cd.tail.population_stddev"] == "1.0"
    assert values["result.flux.inlet.final_m3_per_sec"] == ""
