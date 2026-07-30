from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path


def sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def manifest_sha256(root: Path, relative_files: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    found = False
    try:
        for relative in sorted(
            relative_files, key=lambda item: item.as_posix().encode()
        ):
            path = root / relative
            if not path.is_file() or path.is_symlink():
                continue
            file_hash = sha256_file(path)
            if not file_hash:
                continue
            digest.update(relative.as_posix().encode())
            digest.update(b"\0")
            digest.update(file_hash.encode())
            digest.update(b"\n")
            found = True
    except OSError:
        return ""
    return digest.hexdigest() if found else ""


def tree_files(root: Path, directories: Iterable[str]) -> list[Path]:
    result: list[Path] = []
    for directory in directories:
        base = root / directory
        if not base.is_dir():
            continue
        result.extend(
            path.relative_to(root) for path in base.rglob("*") if path.is_file()
        )
    return result
