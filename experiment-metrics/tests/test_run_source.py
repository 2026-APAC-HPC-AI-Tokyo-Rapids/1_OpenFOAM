import shlex
from types import SimpleNamespace

from experiment_metrics.collectors import run_source
from experiment_metrics.context import Context


def test_collect_start_records_one_round_trippable_command(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/openfoam")
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.setattr(
        run_source,
        "run",
        lambda _command: SimpleNamespace(returncode=0, stdout=""),
    )
    context = Context(run="openfoam-test", case_dir=tmp_path, provision_dir=None)
    command = ["simpleFoam", "-case", "case with space"]

    values = {
        metric.key: metric.value
        for metric in run_source.collect_start(context, command)
    }

    assert shlex.split(values["run.command"]) == command
    assert not any(key.startswith("run.command.") for key in values)
