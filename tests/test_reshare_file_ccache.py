from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "reshare-file-ccache.py"
SPEC = importlib.util.spec_from_file_location("reshare_file_ccache", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def entry_bytes(*, self_contained: bool = True) -> bytes:
    return bytes.fromhex("ccac01") + bytes((0, 1, 1, int(self_contained))) + b"payload"


def local_entry(cache: Path, key: str, content: bytes) -> Path:
    path = cache / key[0] / key[1] / key[2:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_reshare_maps_local_layout_to_file_backend_layout(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    shared = tmp_path / "shared"
    primary.mkdir()
    shared.mkdir()
    key = "0123456789abcdef0123456789abcdef01234567"
    content = entry_bytes()
    local_entry(primary, key, content)
    (primary / "0" / "stats").write_text("ignored", encoding="utf-8")

    summary = MODULE.reshare(primary, shared)

    assert (shared / key[:2] / key[2:]).read_bytes() == content
    assert summary.entries == 1
    assert summary.missing == 1
    assert summary.copied == 1
    assert summary.already_shared == 0
    assert summary.ignored == 1


def test_reshare_does_not_overwrite_or_copy_non_self_contained_entries(
    tmp_path: Path,
) -> None:
    primary = tmp_path / "primary"
    shared = tmp_path / "shared"
    primary.mkdir()
    shared.mkdir()
    existing_key = "1123456789abcdef0123456789abcdef01234567"
    local_entry(primary, existing_key, entry_bytes())
    destination = shared / existing_key[:2] / existing_key[2:]
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")
    local_entry(
        primary,
        "2123456789abcdef0123456789abcdef01234567",
        entry_bytes(self_contained=False),
    )

    summary = MODULE.reshare(primary, shared)

    assert destination.read_bytes() == b"existing"
    assert summary.entries == 1
    assert summary.missing == 0
    assert summary.copied == 0
    assert summary.already_shared == 1
    assert summary.non_self_contained == 1


def test_reshare_rejects_malformed_keyed_entry(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    shared = tmp_path / "shared"
    primary.mkdir()
    shared.mkdir()
    local_entry(primary, "3123456789abcdef0123456789abcdef01234567", b"not ccache")

    with pytest.raises(ValueError, match="invalid ccache entry header"):
        MODULE.reshare(primary, shared)


def test_dry_run_reports_missing_without_copying(tmp_path: Path) -> None:
    primary = tmp_path / "primary"
    shared = tmp_path / "shared"
    primary.mkdir()
    shared.mkdir()
    key = "4123456789abcdef0123456789abcdef01234567"
    local_entry(primary, key, entry_bytes())

    summary = MODULE.reshare(primary, shared, dry_run=True)

    assert not (shared / key[:2] / key[2:]).exists()
    assert summary.missing == 1
    assert summary.copied == 0
    assert summary.copied_bytes == 0
