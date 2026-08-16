#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///

"""Copy missing ccache primary entries to a file-based shared cache."""

from __future__ import annotations

import argparse
import errno
import os
import secrets
import shutil
from dataclasses import dataclass
from pathlib import Path

CCACHE_MAGIC_AND_FORMAT = bytes.fromhex("ccac01")
HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass
class Summary:
    entries: int = 0
    missing: int = 0
    copied: int = 0
    already_shared: int = 0
    non_self_contained: int = 0
    ignored: int = 0
    copied_bytes: int = 0


def cache_key(primary: Path, entry: Path) -> str | None:
    key = "".join(entry.relative_to(primary).parts)
    return key if len(key) == 40 and set(key) <= HEX_DIGITS else None


def is_self_contained(entry: Path) -> bool:
    with entry.open("rb") as stream:
        header = stream.read(7)
    if (
        len(header) != 7
        or header[:3] != CCACHE_MAGIC_AND_FORMAT
        or header[3] not in (0, 1)
        or header[4] not in (0, 1)
    ):
        raise ValueError(f"invalid ccache entry header: {entry}")
    return header[6] == 1


def copy_without_overwrite(source: Path, destination: Path) -> bool:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = (
        destination.parent
        / f".{destination.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    )
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_:
            shutil.copyfileobj(input_, output)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError:
            return False
        except OSError as error:
            if error.errno == errno.EXDEV:
                raise RuntimeError(
                    f"temporary file and destination are on different filesystems: {temporary} -> {destination}"
                ) from error
            raise
        return True
    finally:
        temporary.unlink(missing_ok=True)


def reshare(primary: Path, shared: Path, dry_run: bool = False) -> Summary:
    primary = primary.resolve(strict=True)
    shared = shared.resolve(strict=True)
    if not primary.is_dir() or not shared.is_dir():
        raise NotADirectoryError("primary and shared cache paths must be directories")

    summary = Summary()
    for entry in primary.rglob("*"):
        if not entry.is_file():
            continue
        key = cache_key(primary, entry)
        if key is None:
            summary.ignored += 1
            continue
        if not is_self_contained(entry):
            summary.non_self_contained += 1
            continue

        summary.entries += 1
        destination = shared / key[:2] / key[2:]
        if destination.exists():
            summary.already_shared += 1
            continue
        summary.missing += 1
        if dry_run:
            continue
        if copy_without_overwrite(entry, destination):
            summary.copied += 1
            summary.copied_bytes += entry.stat().st_size
        else:
            summary.already_shared += 1
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("primary", type=Path, help="node-local ccache directory")
    parser.add_argument("shared", type=Path, help="file backend directory")
    parser.add_argument(
        "--dry-run", action="store_true", help="count missing entries without copying"
    )
    arguments = parser.parse_args()

    summary = reshare(arguments.primary, arguments.shared, arguments.dry_run)
    print(
        f"entries={summary.entries} missing={summary.missing} copied={summary.copied} already_shared={summary.already_shared} "
        f"non_self_contained={summary.non_self_contained} ignored={summary.ignored} copied_bytes={summary.copied_bytes}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
