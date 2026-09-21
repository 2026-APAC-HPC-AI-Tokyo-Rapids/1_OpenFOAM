import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/source-tree-identity.sh"


def identity(path: Path) -> str:
    return subprocess.run(
        [SCRIPT, path], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_source_tree_identity_is_independent_of_root_path(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root in (first, second):
        (root / "nested").mkdir(parents=True)
        (root / "plain.txt").write_text("same\n", encoding="utf-8")
        (root / "nested/name with spaces.txt").write_bytes(b"content\x00bytes")

    assert identity(first) == identity(second)


def test_source_tree_identity_changes_with_path_or_content(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    member = source / "member.txt"
    member.write_text("before\n", encoding="utf-8")
    before = identity(source)

    member.write_text("after\n", encoding="utf-8")
    assert identity(source) != before

    after_content = identity(source)
    member.rename(source / "renamed.txt")
    assert identity(source) != after_content
