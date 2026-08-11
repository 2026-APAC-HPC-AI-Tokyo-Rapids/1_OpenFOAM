from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .fact import Fact


def snapshot_bytes(environment: dict[bytes, bytes] | None = None) -> bytes:
    values = os.environb if environment is None else environment
    secret_names = {
        b"EXPERIMENT_METRICS_GOOGLE_CREDENTIALS_FILE",
        b"EXPERIMENT_METRICS_BIGQUERY_CONFIG",
        b"EXPERIMENT_METRICS_DIRECT_SEND",
    }
    names = sorted(name for name in values if name not in secret_names)
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


def environment_facts(snapshot: Path) -> tuple[Fact, ...]:
    facts: list[Fact] = []
    for name, value in parse_snapshot(snapshot.read_bytes()).items():
        try:
            decoded = value.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("environment value is not UTF-8") from error
        facts.append(Fact(f"env.{escape_name(name)}", decoded))
    return tuple(facts)


def escape_name(name: bytes) -> str:
    return "".join(
        chr(value)
        if chr(value).isalnum() and value < 128 or value == ord("_")
        else f"~{value:02X}"
        for value in name
    )


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
