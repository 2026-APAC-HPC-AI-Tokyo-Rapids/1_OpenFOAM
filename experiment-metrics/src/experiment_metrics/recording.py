from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .fact import Fact, encode_logical_value
from .manifest import RunManifest


@dataclass(slots=True)
class Recorder:
    manifest: RunManifest
    producer_id: str
    fragment_path: Path
    _temporary_path: Path
    _stream: object
    _keys: set[str] = field(default_factory=set)
    _rows: list[dict[str, str]] = field(default_factory=list)
    _closed: bool = False

    @classmethod
    def open(
        cls,
        manifest_path: Path,
        registry_path: Path,
        producer_id: str,
        runtime_dir: Path | None = None,
        *,
        fragment_id: str = "default",
    ) -> Recorder:
        manifest = RunManifest.load(manifest_path)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", fragment_id):
            raise ValueError("fragment_id must be a safe path component")
        root = (
            runtime_dir.resolve()
            if runtime_dir is not None
            else manifest.path.parents[1]
        )
        fragments = root / "domain/fragments"
        fragments.mkdir(parents=True, exist_ok=True)
        name = f"{producer_id}--{fragment_id}.jsonl"
        fragment_path = fragments / name
        temporary_path = fragments / f".{name}.tmp"
        if fragment_path.exists() or temporary_path.exists():
            raise FileExistsError(f"fragment already exists for {producer_id}")
        stream = temporary_path.open("x", encoding="utf-8", buffering=64 * 1024)
        return cls(manifest, producer_id, fragment_path, temporary_path, stream)

    def record(self, fact: Fact) -> None:
        if self._closed:
            raise RuntimeError("recorder is closed")
        if fact.key in self._keys:
            raise ValueError(f"producer emitted duplicate key: {fact.key}")
        value = encode_logical_value(fact.logical_value)
        row = {"run": self.manifest.run_id, "key": fact.key, "value": value}
        self._stream.write(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        self._rows.append(row)
        self._keys.add(fact.key)

    def close(self) -> Path:
        if self._closed:
            return self.fragment_path
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._stream.close()
        self._temporary_path.replace(self.fragment_path)
        self._closed = True
        if os.environ.get("EXPERIMENT_METRICS_DIRECT_SEND") == "1":
            from .publish import send_raw

            send_raw(self.manifest.run_id, self._rows)
        return self.fragment_path

    def abort(self) -> None:
        if self._closed:
            return
        self._stream.close()
        self._temporary_path.unlink(missing_ok=True)
        self._closed = True

    def __enter__(self) -> Recorder:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        if exc_type is None:
            self.close()
        else:
            self.abort()
        return False


def collect_once(
    manifest_path: Path,
    runtime_dir: Path,
    producer_id: str,
    probe: Callable[[], Iterable[Fact]],
    *,
    registry_path: Path,
    fragment_id: str = "default",
) -> Path:
    with Recorder.open(
        manifest_path,
        registry_path,
        producer_id,
        runtime_dir,
        fragment_id=fragment_id,
    ) as recorder:
        for fact in probe():
            recorder.record(fact)
        return recorder.fragment_path
