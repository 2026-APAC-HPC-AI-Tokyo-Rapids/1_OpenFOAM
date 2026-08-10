from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .fact import validate_encoded_value
from .manifest import RunManifest
from .protocol import RunProtocol, default_protocol_path
from .registry import Registry


@dataclass(frozen=True, slots=True)
class FinalizeOutcome:
    metrics_path: Path
    collection_complete: bool
    missing_producers: tuple[str, ...]
    missing_keys: tuple[str, ...]
    conflicts: tuple[str, ...]
    invalid_fragments: tuple[str, ...]
    missing_stages: tuple[str, ...]
    missing_sources: tuple[str, ...]
    protocol_invalid: bool


def merge_run(
    manifest_path: Path,
    runtime_dir: Path,
    *,
    registry_path: Path,
    protocol_path: Path | None = None,
) -> FinalizeOutcome:
    """Validate producer fragments and atomically materialize the raw export.

    An incomplete merge is still useful evidence: valid non-conflicting rows
    are retained and `collection_complete=false` makes its state explicit.
    """

    manifest = RunManifest.load(manifest_path)
    if runtime_dir.resolve(strict=True) != manifest.path.parents[1]:
        raise ValueError("merge runtime directory differs from the bound manifest")
    registry = Registry.load(registry_path)
    protocol, protocol_invalid = _protocol(
        protocol_path or default_protocol_path(registry_path), manifest
    )
    fragment_dir = runtime_dir / "domain/fragments"
    files = sorted(fragment_dir.glob("*.jsonl"), key=lambda item: item.name.encode())
    rows: dict[str, set[str]] = {}
    key_sources: dict[str, set[Path]] = {}
    conflicts: set[str] = set()
    invalid: set[str] = set()
    rejected: set[Path] = set()
    accepted_producers: set[str] = set()
    for path in files:
        instance = _producer_from_path(path)
        if instance is None:
            invalid.add(path.name)
            rejected.add(path)
            continue
        producer_id, fragment_id = instance
        try:
            registry.producer(producer_id)
        except ValueError:
            invalid.add(path.name)
            rejected.add(path)
            continue
        file_rows: list[tuple[str, str]] = []
        valid = True
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                _validate_row(row, manifest.run_id, registry, producer_id)
                _validate_protocol_key(row["key"], protocol)
                _validate_producer_instance_key(
                    producer_id, fragment_id, row["key"], protocol
                )
                key = row["key"]
                value = row["value"]
            except (TypeError, ValueError, json.JSONDecodeError):
                invalid.add(path.name)
                rejected.add(path)
                valid = False
                break
            file_rows.append((key, value))
        if not valid:
            continue
        accepted_producers.add(producer_id)
        for key, value in file_rows:
            values = rows.setdefault(key, set())
            if values and value not in values:
                conflicts.add(key)
                rejected.update(key_sources[key])
                rejected.add(path)
            values.add(value)
            key_sources.setdefault(key, set()).add(path)

    missing_producers = tuple(
        sorted(registry.required_producers(manifest.purpose) - accepted_producers)
    )
    required_keys = registry.required_keys(
        manifest.purpose, expected_pstream_ranks=protocol.expected_pstream_ranks
    )
    missing_keys = tuple(sorted(required_keys - set(rows)))
    missing_stages = _missing_stages(protocol, rows)
    missing_sources = _missing_literal_sources(registry, manifest, runtime_dir)
    complete = not (
        protocol_invalid
        or missing_producers
        or missing_keys
        or conflicts
        or invalid
        or missing_stages
        or missing_sources
    )
    rows["collection_complete"] = {"true" if complete else "false"}
    metrics_path = runtime_dir / "metrics.jsonl"
    _write_rows(metrics_path, manifest.run_id, rows)
    for path in files:
        if path not in rejected:
            path.unlink()
    return FinalizeOutcome(
        metrics_path=metrics_path,
        collection_complete=complete,
        missing_producers=missing_producers,
        missing_keys=missing_keys,
        conflicts=tuple(sorted(conflicts)),
        invalid_fragments=tuple(sorted(invalid)),
        missing_stages=missing_stages,
        missing_sources=missing_sources,
        protocol_invalid=protocol_invalid,
    )


def _validate_row(
    row: object, run_id: str, registry: Registry, producer_id: str
) -> None:
    if not isinstance(row, dict) or set(row) != {"run", "key", "value"}:
        raise ValueError("fragment row must contain exactly run, key, value")
    if (
        row["run"] != run_id
        or not isinstance(row["key"], str)
        or not isinstance(row["value"], str)
    ):
        raise ValueError("fragment row has invalid scalar values")
    spec = registry.spec_for(row["key"])
    if spec.owner != producer_id:
        raise ValueError("fragment owner does not own key")
    validate_encoded_value(row["value"], spec.logical_type)


def _producer_from_path(path: Path) -> tuple[str, str] | None:
    producer_id, separator, fragment_id = path.stem.partition("--")
    if not separator or not producer_id or not fragment_id:
        return None
    return producer_id, fragment_id


def _write_rows(path: Path, run_id: str, rows: dict[str, set[str]]) -> None:
    ordered = sorted(
        ((key, value) for key, values in rows.items() for value in values),
        key=lambda item: (item[0].encode("utf-8"), item[1].encode("utf-8")),
    )
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=".metrics-", delete=False
    ) as stream:
        for key, value in ordered:
            stream.write(
                json.dumps(
                    {"run": run_id, "key": key, "value": value},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
        temporary = Path(stream.name)
    temporary.replace(path)


def _protocol(path: Path, manifest: RunManifest) -> tuple[RunProtocol, bool]:
    try:
        return RunProtocol.load(path, manifest.purpose), False
    except (FileNotFoundError, ValueError, OSError):
        # Keep merging recoverable evidence, but protocol absence/malformation
        # can never silently certify a collection.
        return RunProtocol((), 0), True


def _missing_stages(
    protocol: RunProtocol, rows: dict[str, set[str]]
) -> tuple[str, ...]:
    missing = []
    for stage in protocol.expected_stages:
        keys = {
            f"run.stage.{stage}.launch",
            f"run.stage.{stage}.termination",
            f"perf.stage.{stage}.wall_time_sec",
        }
        termination = rows.get(f"run.stage.{stage}.termination", set())
        if not keys.issubset(rows) or not _successful_termination(termination):
            missing.append(stage)
    return tuple(missing)


def _successful_termination(values: set[str]) -> bool:
    if len(values) != 1:
        return False
    try:
        value = json.loads(next(iter(values)))
    except json.JSONDecodeError:
        return False
    return value == {"kind": "exit", "code": 0}


def _missing_literal_sources(
    registry: Registry, manifest: RunManifest, runtime_dir: Path
) -> tuple[str, ...]:
    missing: list[str] = []
    for source_id, relative in registry.required_literal_sources(
        manifest.purpose, storages=frozenset({"run_bundle", "profile_raw"})
    ):
        path = runtime_dir / relative
        exists = path.is_file() or (
            path.is_dir() and any(item.is_file() for item in path.iterdir())
        )
        if not exists:
            missing.append(source_id)
    return tuple(missing)


def _validate_protocol_key(key: str, protocol: RunProtocol) -> None:
    prefix = "solver.pstream."
    if not key.startswith(prefix):
        return
    rank_token = key.rsplit(".", 1)[-1]
    if not rank_token.isdecimal() or int(rank_token) >= protocol.expected_pstream_ranks:
        raise ValueError("Pstream rank key is outside the protocol axis")


def _validate_producer_instance_key(
    producer_id: str, fragment_id: str, key: str, protocol: RunProtocol
) -> None:
    if producer_id != "stage.runner":
        return
    prefix = "stage."
    if not fragment_id.startswith(prefix) or not fragment_id[len(prefix) :]:
        raise ValueError("stage fragment must use stage.<name> instance ID")
    stage = fragment_id[len(prefix) :]
    if stage not in protocol.expected_stages:
        raise ValueError("stage fragment is outside the protocol stage set")
    expected = {
        f"run.stage.{stage}.launch",
        f"run.stage.{stage}.termination",
        f"perf.stage.{stage}.wall_time_sec",
    }
    if key not in expected:
        raise ValueError("stage fragment key does not match its instance axis")
