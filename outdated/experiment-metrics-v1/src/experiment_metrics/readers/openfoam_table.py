from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def split_tokens(line: str) -> list[str]:
    tokens: list[str] = []
    token: list[str] = []
    depth = 0
    for character in line.strip():
        if character == "(":
            depth += 1
            token.append(character)
        elif character == ")":
            depth = max(0, depth - 1)
            token.append(character)
        elif character.isspace() and depth == 0:
            if token:
                tokens.append("".join(token))
                token.clear()
        else:
            token.append(character)
    if token:
        tokens.append("".join(token))
    return tokens


@dataclass(frozen=True, slots=True)
class Table:
    header: list[str]
    rows: list[dict[str, str]]

    def last(self) -> dict[str, str]:
        return self.rows[-1] if self.rows else {}

    def tail(self, count: int) -> list[dict[str, str]]:
        return self.rows[-count:]


def read_table(path: Path) -> Table:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return Table([], [])

    header: list[str] = []
    rows: list[dict[str, str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            candidate = [token for token in split_tokens(stripped) if token != "#"]
            if candidate and candidate[0] == "Time":
                header = candidate
            continue
        if not header:
            continue
        values = split_tokens(stripped)
        if len(values) < len(header):
            continue
        rows.append(dict(zip(header, values)))
    return Table(header, rows)


def vector(value: str) -> list[str]:
    text = value.strip()
    if text.startswith("(") and text.endswith(")"):
        parts = text[1:-1].split()
        if len(parts) == 3:
            return parts
    return []
