from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiment_metrics import bundle_identity, init_run, load_bundle
from experiment_metrics.cli import main
from experiment_metrics.instrumentation import validate_runtime_bindings

BUNDLES = Path(__file__).parents[1] / "bundles"


@pytest.mark.parametrize(
    ("name", "purpose", "track"),
    [
        ("openfoam-score-v1.json", "bench", "score"),
        ("openfoam-profile-vtune-hotspots-v1.json", "profile", "profile"),
        ("openfoam-profile-craypat-apa-v1.json", "profile", "profile"),
    ],
)
def test_git_managed_bundle_is_closed_and_purpose_bound(
    name: str, purpose: str, track: str
) -> None:
    path = BUNDLES / name
    assert load_bundle(path, purpose=purpose)["bundle_track"] == track
    assert len(bundle_identity(path, purpose=purpose)) == 64


def test_init_installs_canonical_bundle_and_checks_identity(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    bundle = BUNDLES / "openfoam-score-v1.json"
    registry_path = Path(__file__).parents[1] / "registry/openfoam-v2.toml"
    expected = bundle_identity(bundle, purpose="bench")
    bound = {**identities, "instrumentation_bundle_sha256": expected}
    manifest = init_run(
        None,
        tmp_path,
        bound,
        registry_path=registry_path,
        instrumentation_bundle_path=bundle,
    )
    installed = manifest.with_name("instrumentation-bundle.json")
    assert bundle_identity(installed, purpose="bench") == expected
    rendered = validate_runtime_bindings(
        manifest,
        installed,
        registry_path,
        environment={},
    )
    assert rendered == {}
    wrong = {**identities, "instrumentation_bundle_sha256": "0" * 64}
    with pytest.raises(ValueError, match="identity does not match"):
        init_run(
            None,
            tmp_path / "wrong",
            wrong,
            registry_path=registry_path,
            instrumentation_bundle_path=bundle,
        )


def test_bundle_rejects_open_schema_and_wrong_track(tmp_path: Path) -> None:
    document = json.loads((BUNDLES / "openfoam-score-v1.json").read_text())
    document["unexpected"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="closed"):
        load_bundle(path, purpose="bench")
    with pytest.raises(ValueError, match="track"):
        load_bundle(BUNDLES / "openfoam-score-v1.json", purpose="profile")


def test_bundle_identity_cli(capsys: object) -> None:
    bundle = BUNDLES / "openfoam-score-v1.json"
    assert main(["bundle-identity", "--bundle", str(bundle), "--purpose", "bench"]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert captured.out.strip() == bundle_identity(bundle, purpose="bench")


def test_profile_bundle_declares_vtune_executable(
    tmp_path: Path, identities: dict[str, object]
) -> None:
    bundle = BUNDLES / "openfoam-profile-vtune-hotspots-v1.json"
    document = load_bundle(bundle, purpose="profile")
    activation = document["components"][0]["activation"]

    assert activation["kind"] == "executable"
    assert activation["artifact_relative_path"] == "scripts/exec-profiler.sh"
    profile_identities = {
        **identities,
        "source_track": {
            **identities["source_track"],
            "base_role": "profile_base",
        },
        "instrumentation_bundle_sha256": bundle_identity(bundle, purpose="profile"),
    }
    registry = Path(__file__).parents[1] / "registry/openfoam-v2.toml"
    manifest = init_run(
        None,
        tmp_path / "runs",
        profile_identities,
        purpose="profile",
        registry_path=registry,
        instrumentation_bundle_path=bundle,
    )
    rendered = validate_runtime_bindings(
        manifest,
        manifest.with_name("instrumentation-bundle.json"),
        registry,
        environment={},
    )
    assert rendered == {}
