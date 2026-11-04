"""Checks the technical report: every Markdown table has the same number of cells in each row, the table and section numbers
run in order, and none of the characters the team's style avoids (em dash, middle dot) slipped in."""
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
lines = text.split("\n")
problems = []
in_code = False
table = []
start = 0


def cells(line):
    inner = line.strip()[1:-1]
    # A '|' inside backticks would split a cell; the report has none, so a plain split is enough.
    return len(inner.split("|"))


def flush():
    if table:
        n = cells(table[0])
        for k, row in enumerate(table):
            if cells(row) != n:
                problems.append(f"table at line {start + 1}: row {k + 1} has {cells(row)} cells, header {n}")
        if len(table) > 1 and not re.fullmatch(r"\|(\s*:?-+:?\s*\|)+", table[1].strip()):
            problems.append(f"table at line {start + 1}: second row is not a separator")


for i, line in enumerate(lines):
    if line.startswith("```"):
        in_code = not in_code
        continue
    if in_code:
        continue
    if line.startswith("|"):
        if not table:
            start = i
        table.append(line)
    else:
        flush()
        table = []
    for ch, name in (("—", "em dash"), ("·", "middle dot")):
        if ch in line:
            problems.append(f"line {i + 1}: {name}: {line.strip()[:80]}")
flush()

numbers = [int(m) for m in re.findall(r"^Table (\d+)\.", text, flags=re.M)]
if numbers != list(range(1, len(numbers) + 1)):
    problems.append(f"table numbers out of order: {numbers}")
sections = re.findall(r"^## (\d+)\.", text, flags=re.M)
if [int(s) for s in sections] != list(range(1, len(sections) + 1)):
    problems.append(f"section numbers out of order: {sections}")
refs = sorted({int(m) for m in re.findall(r"[Tt]able (\d+)\b", text)})
missing = [r for r in refs if r not in numbers]
if missing:
    problems.append(f"tables referred to but not defined: {missing}")
for m in re.finditer(r"section (\d+(?:\.\d+)?)", text):
    target = m.group(1)
    if "." in target:
        if not re.search(rf"^### {re.escape(target)} ", text, flags=re.M):
            problems.append(f"reference to missing section {target}")
    elif not re.search(rf"^## {target}\. ", text, flags=re.M):
        problems.append(f"reference to missing section {target}")
for m in re.finditer(r"Appendix A\.(\d)", text):
    if not re.search(rf"^### A\.{m.group(1)} ", text, flags=re.M):
        problems.append(f"reference to missing Appendix A.{m.group(1)}")
figures = [int(m) for m in re.findall(r"^Figure (\d+)\.", text, flags=re.M)]
if figures != list(range(1, len(figures) + 1)):
    problems.append(f"figure numbers out of order: {figures}")
images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
if len(images) != len(figures):
    problems.append(f"{len(images)} images but {len(figures)} figure captions")
for k, image in enumerate(images, 1):
    if not (Path(sys.argv[1]).parent / image).is_file():
        problems.append(f"missing image {image}")
    elif not Path(image).name.startswith(f"fig{k:02d}_"):
        problems.append(f"image {k} is {image}")
for m in re.finditer(r"Figures? (\d+)(?:, (\d+))*", text):
    for n in re.findall(r"\d+", m.group(0)):
        if int(n) not in figures:
            problems.append(f"reference to missing Figure {n}")
print(f"{len(numbers)} tables, {len(figures)} figures, {len(sections)} sections, {len(lines)} lines")
print("\n".join(problems) if problems else "no problems")
