from __future__ import annotations

import base64
import hashlib
import os
import tempfile
from pathlib import Path

from .fact import Fact, canonical_json


def snapshot_bytes(environment: dict[bytes, bytes] | None = None) -> bytes:
    values = os.environb if environment is None else environment
    names = sorted(values)
    if any(not name or b"=" in name or b"\0" in name for name in names):
        raise ValueError("environment contains an invalid name")
    if any(b"\0" in values[name] for name in names):
        raise ValueError("environment contains an invalid value")
    return b"".join(name + b"\0" + values[name] + b"\0" for name in names)


def capture_snapshot(
    output: Path, environment: dict[bytes, bytes] | None = None
) -> Path:
    _atomic_bytes(output, snapshot_bytes(environment))
    return output


def parse_snapshot(raw: bytes) -> dict[bytes, bytes]:
    if not raw or not raw.endswith(b"\0"):
        raise ValueError("environment snapshot must be nonempty and NUL-terminated")
    fields = raw.split(b"\0")
    if fields[-1] != b"" or len(fields) % 2 != 1:
        raise ValueError("environment snapshot has an invalid field count")
    pairs = list(zip(fields[0:-1:2], fields[1:-1:2], strict=True))
    names = [name for name, _ in pairs]
    if any(not name or b"=" in name for name in names) or names != sorted(set(names)):
        raise ValueError("environment snapshot names are not canonical")
    return dict(pairs)


def capture_rank_delta(
    common_snapshot: Path,
    output: Path,
    *,
    rank: int,
    environment: dict[bytes, bytes] | None = None,
) -> Path:
    if rank < 0:
        raise ValueError("rank must be nonnegative")
    common_raw = common_snapshot.read_bytes()
    common = parse_snapshot(common_raw)
    current = os.environb if environment is None else environment
    current_raw = snapshot_bytes(current)
    current = parse_snapshot(current_raw)
    changed = [
        {
            "name_b64": _b64(name),
            "value_b64": _b64(current[name]),
        }
        for name in sorted(current)
        if common.get(name) != current[name]
    ]
    removed = [_b64(name) for name in sorted(set(common) - set(current))]
    document = {
        "schema_version": "rank-env-delta/v1",
        "common_snapshot_sha256": hashlib.sha256(common_raw).hexdigest(),
        "rank": rank,
        "added_or_changed": changed,
        "removed_names_b64": removed,
    }
    _atomic_text(output, canonical_json(document) + "\n")
    return output


def environment_facts(
    job_entry_snapshot: Path,
    host_snapshot: Path,
    rank_delta_root: Path,
    *,
    expected_ranks: int,
) -> tuple[Fact, ...]:
    if expected_ranks <= 0:
        raise ValueError("expected ranks must be positive")
    return (
        *job_entry_facts(job_entry_snapshot),
        *host_execution_facts(
            host_snapshot, rank_delta_root, expected_ranks=expected_ranks
        ),
    )


def job_entry_facts(snapshot: Path) -> tuple[Fact, ...]:
    return tuple(
        Fact(f"env.job_entry.{escape_name(name)}", value)
        for name, value in parse_snapshot(snapshot.read_bytes()).items()
    )


def host_execution_facts(
    host_snapshot: Path, rank_delta_root: Path, *, expected_ranks: int
) -> tuple[Fact, ...]:
    if expected_ranks <= 0:
        raise ValueError("expected ranks must be positive")
    facts: list[Fact] = []
    common_raw = host_snapshot.read_bytes()
    common = parse_snapshot(common_raw)
    for name, value in common.items():
        facts.append(Fact(f"env.host_exec.common.{escape_name(name)}", value))
    for rank in range(expected_ranks):
        path = rank_delta_root / f"rank-{rank}.delta.json"
        delta = _load_delta(path, common_raw, rank)
        changed_names: set[bytes] = set()
        for item in delta["added_or_changed"]:
            name = _decode_b64(item["name_b64"])
            value = _decode_b64(item["value_b64"])
            changed_names.add(name)
            facts.append(
                Fact(
                    f"env.host_exec.rank.{rank}.delta.{escape_name(name)}",
                    value,
                )
            )
        removed = [_decode_b64(value) for value in delta["removed_names_b64"]]
        if changed_names & set(removed):
            raise ValueError("rank environment changed and removed names overlap")
        facts.append(
            Fact(
                f"env.host_exec.rank.{rank}.removed_names",
                [_b64(name) for name in removed],
            )
        )
    return tuple(facts)


def reconstruct_rank_environments(
    host_snapshot: Path, rank_delta_root: Path, *, expected_ranks: int
) -> tuple[dict[bytes, bytes], ...]:
    common_raw = host_snapshot.read_bytes()
    common = parse_snapshot(common_raw)
    output: list[dict[bytes, bytes]] = []
    for rank in range(expected_ranks):
        delta = _load_delta(
            rank_delta_root / f"rank-{rank}.delta.json", common_raw, rank
        )
        current = dict(common)
        for name in delta["removed_names_b64"]:
            current.pop(_decode_b64(name), None)
        for item in delta["added_or_changed"]:
            current[_decode_b64(item["name_b64"])] = _decode_b64(item["value_b64"])
        output.append(current)
    return tuple(output)


def escape_name(name: bytes) -> str:
    return "".join(
        chr(value)
        if chr(value).isalnum() and value < 128 or value == ord("_")
        else f"~{value:02X}"
        for value in name
    )


def _load_delta(path: Path, common_raw: bytes, expected_rank: int) -> dict[str, object]:
    import json

    document = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "common_snapshot_sha256",
        "rank",
        "added_or_changed",
        "removed_names_b64",
    }
    if (
        not isinstance(document, dict)
        or set(document) != required
        or document["schema_version"] != "rank-env-delta/v1"
        or document["common_snapshot_sha256"] != hashlib.sha256(common_raw).hexdigest()
        or document["rank"] != expected_rank
        or not isinstance(document["added_or_changed"], list)
        or not isinstance(document["removed_names_b64"], list)
    ):
        raise ValueError("rank environment delta has an invalid schema")
    changed: list[bytes] = []
    for item in document["added_or_changed"]:
        if not isinstance(item, dict) or set(item) != {"name_b64", "value_b64"}:
            raise ValueError("rank environment delta entry is invalid")
        changed.append(_decode_b64(item["name_b64"]))
        _decode_b64(item["value_b64"])
    removed = [_decode_b64(item) for item in document["removed_names_b64"]]
    if changed != sorted(set(changed)) or removed != sorted(set(removed)):
        raise ValueError("rank environment delta names are not canonical")
    return document


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode_b64(value: object) -> bytes:
    if not isinstance(value, str):
        raise ValueError("environment Base64 value must be a string")
    try:
        decoded = base64.b64decode(value, validate=True)
    except ValueError as error:
        raise ValueError("environment Base64 value is invalid") from error
    if _b64(decoded) != value:
        raise ValueError("environment Base64 value is not canonical")
    return decoded


def _atomic_bytes(path: Path, content: bytes) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def _atomic_text(path: Path, content: str) -> None:
    _atomic_bytes(path, content.encode("utf-8"))
