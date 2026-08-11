from experiment_metrics.collectors import case
from experiment_metrics.context import Context


def test_freestream_velocity_is_one_list_string_metric(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        case,
        "read_entry",
        lambda _case_dir, _path, entry: "(1 2 3)" if entry == "flowVelocity" else "",
    )
    monkeypatch.setattr(case, "manifest_sha256", lambda _root, _paths: "digest")
    monkeypatch.setattr(case, "sha256_file", lambda _path: "digest")
    monkeypatch.setattr(case, "tree_files", lambda _root, _directories: [])

    values = {
        metric.key: metric.value
        for metric in case.collect(Context("run", tmp_path, None))
    }

    assert values["case.freestream_velocity_m_per_sec"] == "['1', '2', '3']"
    assert not any(key.startswith("case.freestream_velocity_m_per_sec.") for key in values)
