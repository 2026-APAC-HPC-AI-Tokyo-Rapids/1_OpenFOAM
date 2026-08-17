from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath

from .fact import canonical_json

_TRACK_PURPOSE = {"score": "bench", "profile": "profile"}
_ROOT_FIELDS = {
    "schema_version",
    "bundle_track",
    "source_paths",
    "components",
    "environment_capture_scopes",
    "sink_bindings",
    "environment_bindings",
}
_HOOK_ACTIVATION_FIELDS = {
    "kind",
    "source_commit_role",
    "source_path",
    "symbol",
    "event_schema_id",
}
_EXECUTABLE_ACTIVATION_FIELDS = {
    "kind",
    "artifact_relative_path",
    "argv_template",
}


def load_bundle(
    path: Path,
    *,
    purpose: str | None = None,
    registry_path: Path | None = None,
) -> dict[str, object]:
    document = _load_json(path)
    if set(document) != _ROOT_FIELDS:
        raise ValueError("instrumentation bundle must be a closed v1 object")
    track = document["bundle_track"]
    if document["schema_version"] != "instrumentation-bundle/v1" or track not in {
        "reference",
        "score",
        "profile",
    }:
        raise ValueError("unsupported instrumentation bundle identity")
    if purpose is not None and _TRACK_PURPOSE.get(str(track)) != purpose:
        raise ValueError("instrumentation bundle track does not match run purpose")

    sources = _sorted_strings(document["source_paths"], "source_paths")
    scopes = _sorted_strings(
        document["environment_capture_scopes"], "environment_capture_scopes"
    )
    if not set(scopes).issubset({"job_entry", "host_exec_rank"}):
        raise ValueError("instrumentation bundle has an unknown environment scope")
    for source in sources:
        _relative_path(source)

    components = document["components"]
    sinks = document["sink_bindings"]
    bindings = document["environment_bindings"]
    if not all(isinstance(value, list) for value in (components, sinks, bindings)):
        raise ValueError("instrumentation bundle arrays are required")
    if track in {"reference", "score"}:
        if sources or components or scopes or sinks or bindings:
            raise ValueError(f"{track} instrumentation bundle must be empty")
        return document
    if not sources or not components:
        raise ValueError("profile instrumentation bundle must be nonempty")

    sink_ids: list[str] = []
    sink_sources: list[str] = []
    for item in sinks:
        if not isinstance(item, dict) or set(item) != {
            "sink_id",
            "source_id",
            "buffering_mode",
        }:
            raise ValueError("instrumentation sink binding is not closed")
        if item["buffering_mode"] not in {"line_buffered", "stage_buffered"}:
            raise ValueError("instrumentation sink buffering mode is invalid")
        sink_ids.append(_nonempty(item["sink_id"], "sink_id"))
        sink_sources.append(_nonempty(item["source_id"], "source_id"))
    _sorted_unique(sink_ids, "sink IDs")
    if len(set(sink_sources)) != len(sink_sources):
        raise ValueError("instrumentation source IDs must be unique")

    component_ids: list[str] = []
    used_sinks: list[str] = []
    for item in components:
        if not isinstance(item, dict) or set(item) != {
            "component_id",
            "sink_ids",
            "activation",
        }:
            raise ValueError("instrumentation component is not closed")
        component_ids.append(_nonempty(item["component_id"], "component_id"))
        component_sinks = _sorted_strings(item["sink_ids"], "component sink IDs")
        used_sinks.extend(component_sinks)
        activation = item["activation"]
        if not isinstance(activation, dict):
            raise ValueError("instrumentation activation is not closed")
        if activation.get("kind") == "in_process_hook":
            if set(activation) != _HOOK_ACTIVATION_FIELDS:
                raise ValueError("instrumentation hook activation is not closed")
            if activation["source_commit_role"] != "openfoam_source":
                raise ValueError("unsupported instrumentation hook source")
            _relative_path(_nonempty(activation["source_path"], "source_path"))
            if activation["source_path"] not in sources:
                raise ValueError(
                    "component activation source is absent from source_paths"
                )
            _nonempty(activation["symbol"], "symbol")
            _nonempty(activation["event_schema_id"], "event_schema_id")
        elif activation.get("kind") == "executable":
            if set(activation) != _EXECUTABLE_ACTIVATION_FIELDS:
                raise ValueError("instrumentation executable activation is not closed")
            artifact = _nonempty(
                activation["artifact_relative_path"], "artifact_relative_path"
            )
            _relative_path(artifact)
            if artifact not in sources:
                raise ValueError("component executable is absent from source_paths")
            _argv_template(activation["argv_template"], set(component_sinks))
        else:
            raise ValueError("unsupported instrumentation activation")
    _sorted_unique(component_ids, "component IDs")
    if sorted(set(used_sinks), key=str.encode) != sink_ids:
        raise ValueError("component and bundle sink sets differ")

    names: list[str] = []
    for item in bindings:
        if not isinstance(item, dict) or set(item) != {
            "name",
            "scope",
            "value_template",
        }:
            raise ValueError("instrumentation environment binding is not closed")
        name = _nonempty(item["name"], "environment name")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise ValueError("instrumentation environment name is not POSIX-safe")
        names.append(name)
        if item["scope"] != "solver_process_tree":
            raise ValueError("instrumentation environment scope is invalid")
        _value_template(item["value_template"], set(sink_ids))
    _sorted_unique(names, "environment names")
    _validate_registry_links(
        component_ids,
        components,
        sinks,
        registry_path=registry_path,
    )
    return document


def bundle_identity(
    path: Path, *, purpose: str | None = None, registry_path: Path | None = None
) -> str:
    document = load_bundle(path, purpose=purpose, registry_path=registry_path)
    return hashlib.sha256(canonical_json(document).encode()).hexdigest()


def install_bundle(
    path: Path,
    target: Path,
    *,
    purpose: str,
    registry_path: Path | None = None,
) -> str:
    document = load_bundle(path, purpose=purpose, registry_path=registry_path)
    canonical = canonical_json(document)
    identity = hashlib.sha256(canonical.encode()).hexdigest()
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=target.parent, prefix=".bundle-", delete=False
    ) as stream:
        stream.write(canonical + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, target)
    return identity


def validate_runtime_bindings(
    manifest_path: Path,
    bundle_path: Path,
    registry_path: Path,
    *,
    environment: dict[str, str] | None = None,
) -> dict[str, str]:
    """Bind the immutable bundle to the environment used by the solver tree."""

    from .manifest import RunManifest
    from .registry import Registry

    manifest = RunManifest.load(manifest_path)
    run_dir = manifest.path.parents[1]
    expected_bundle = run_dir / "control/instrumentation-bundle.json"
    if bundle_path.resolve(strict=True) != expected_bundle.resolve(strict=True):
        raise ValueError("runtime instrumentation bundle is outside the bound run")
    document = load_bundle(
        bundle_path,
        purpose=manifest.purpose,
        registry_path=registry_path,
    )
    if (
        hashlib.sha256(canonical_json(document).encode()).hexdigest()
        != manifest.instrumentation_bundle_sha256
    ):
        raise ValueError("runtime instrumentation bundle differs from the manifest")
    registry = Registry.load(registry_path)
    source_by_id = {source.identifier: source for source in registry.sources}
    sink_sources = {
        sink["sink_id"]: source_by_id[sink["source_id"]]  # type: ignore[index]
        for sink in document["sink_bindings"]  # type: ignore[union-attr]
    }
    rendered: dict[str, str] = {}
    for binding in document["environment_bindings"]:  # type: ignore[union-attr]
        parts: list[str] = []
        for segment in binding["value_template"]:  # type: ignore[index]
            if "literal" in segment:
                parts.append(segment["literal"])
            elif segment["token"] == "subject_run_id":
                parts.append(manifest.run_id)
            else:
                source = sink_sources[segment["sink_id"]]
                if source.path_tokens:
                    raise ValueError(
                        "absolute sink binding requires a singleton source path"
                    )
                relative = "".join(value for _, value in source.path_template)
                _relative_path(relative)
                absolute = (run_dir / relative).resolve(strict=True)
                if not absolute.is_relative_to(run_dir.resolve(strict=True)):
                    raise ValueError("instrumentation sink escapes the runtime root")
                parts.append(str(absolute))
        rendered[binding["name"]] = "".join(parts)  # type: ignore[index]
    actual = os.environ if environment is None else environment
    for name, expected in rendered.items():
        if actual.get(name) != expected:
            raise ValueError(f"runtime instrumentation binding mismatch: {name}")
    return rendered


def _load_json(path: Path) -> dict[str, object]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate instrumentation bundle key: {key}")
            value[key] = item
        return value

    try:
        document = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=unique
        )
    except json.JSONDecodeError as error:
        raise ValueError("invalid instrumentation bundle JSON") from error
    if not isinstance(document, dict):
        raise ValueError("instrumentation bundle must be an object")
    return document


def _relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "" in path.parts:
        raise ValueError("instrumentation source path must be relative-safe")


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _sorted_strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a string array")
    _sorted_unique(value, label)
    return value


def _sorted_unique(value: list[str], label: str) -> None:
    if value != sorted(set(value), key=str.encode):
        raise ValueError(f"{label} must be byte-sorted and unique")


def _value_template(value: object, sink_ids: set[str]) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("environment value template must be nonempty")
    for segment in value:
        if not isinstance(segment, dict):
            raise ValueError("environment value template segment is invalid")
        if set(segment) == {"token"} and segment["token"] == "subject_run_id":
            continue
        if (
            set(segment) == {"token", "sink_id"}
            and segment["token"] == "absolute_sink_path"
        ):
            if segment["sink_id"] in sink_ids:
                continue
        if (
            set(segment) == {"literal"}
            and isinstance(segment["literal"], str)
            and segment["literal"]
        ):
            continue
        raise ValueError("environment value template segment is invalid")


def _argv_template(value: object, sink_ids: set[str]) -> None:
    if not isinstance(value, list) or not value:
        raise ValueError("component argv template must be nonempty")
    component_tokens = 0
    for argument in value:
        if not isinstance(argument, list) or not argument:
            raise ValueError("component argv argument must be nonempty")
        for segment in argument:
            if not isinstance(segment, dict):
                raise ValueError("component argv segment is invalid")
            if (
                set(segment) == {"literal"}
                and isinstance(segment["literal"], str)
                and segment["literal"]
            ):
                if "@@GLOBAL_RANK@@" in segment["literal"]:
                    raise ValueError("rank marker cannot be a literal")
                continue
            if set(segment) == {"token"} and segment["token"] in {
                "component_executable",
                "subject_run_id",
                "expected_global_ranks",
            }:
                component_tokens += segment["token"] == "component_executable"
                continue
            if (
                set(segment) == {"token", "role"}
                and segment["token"] in {"provisioned_executable", "stage_executable"}
                and segment["role"] in {"vtune", "simpleFoam"}
            ):
                continue
            if (
                set(segment) == {"token", "sink_id"}
                and segment["token"] == "rank_sink_template"
                and segment["sink_id"] in sink_ids
            ):
                continue
            raise ValueError("component argv segment is invalid")
    if value[0] != [{"token": "component_executable"}] or component_tokens != 1:
        raise ValueError("component executable must be argv zero exactly once")


def _validate_registry_links(
    component_ids: list[str],
    components: list[object],
    sinks: list[object],
    *,
    registry_path: Path | None,
) -> None:
    from .registry import Registry

    selected = registry_path or (
        Path(__file__).resolve().parents[2] / "registry/openfoam-v2.toml"
    )
    registry = Registry.load(selected)
    source_by_id = {source.identifier: source for source in registry.sources}
    producer_by_id = {
        producer.identifier: producer for producer in registry.producer_contracts
    }
    component_sinks = {
        component_id: set(component["sink_ids"])  # type: ignore[index]
        for component_id, component in zip(component_ids, components, strict=True)
    }
    for sink in sinks:
        source_id = sink["source_id"]  # type: ignore[index]
        source = source_by_id.get(source_id)
        if source is None:
            raise ValueError(
                f"bundle sink references unknown registry source: {source_id}"
            )
        producer = producer_by_id[source.producer_id]
        component_id = producer.activation_reference
        if (
            producer.activation_kind != "bundle_component"
            or component_id not in component_sinks
            or sink["sink_id"] not in component_sinks[component_id]  # type: ignore[index]
        ):
            raise ValueError("bundle sink does not match registry producer activation")
