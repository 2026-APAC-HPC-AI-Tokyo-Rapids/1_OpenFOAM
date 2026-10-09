# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10", "matplotlib>=3.8"]
# ///
"""Puts the panels of render.py side by side (Issue #39).

    uv run presentation/openfoam/decomposition/compose.py OUT_DIR

OUT_DIR is the output directory of render.py (panels/ and stats.json). For each colouring (subdomains, numa) it writes one
sheet with the case default hierarchical, Basic's scotch and the final Bonus' multiLevel (decomposition-<colouring>.png) and
one with scotch and multiLevel only (decomposition-<colouring>-basic-vs-bonus.png). Each column has the car surface, the
centre plane and the cross-section, with the numbers of its decomposePar log under its name and a key to the colours.
"""
import json
import sys
from pathlib import Path

from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(sys.argv[1])
PANELS = OUT_DIR / "panels"
STATS = json.loads((OUT_DIR / "stats.json").read_text())
TITLES = {"hierarchical": "Case default: hierarchical (16 8 4)", "scotch": "Basic: scotch", "multiLevel": "Bonus (final): multiLevel (4 2 4 16)"}
VIEWS = ["car", "side", "cross"]
NODE_COLOURS = [(0.12, 0.47, 0.71), (1.0, 0.50, 0.05), (0.17, 0.63, 0.17), (0.58, 0.40, 0.74)]
BACKGROUND = (18, 20, 25)
WHITE = (242, 242, 242)
GREY = (160, 164, 172)
REGULAR = font_manager.findfont("DejaVu Sans")
BOLD = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold"))


def numa_colour(domain):
    base = NODE_COLOURS[domain // 8]
    shade = (domain % 8) / 7.0 * 0.9 - 0.45
    return tuple(round(255 * (c * (1 + shade) if shade < 0 else c + (1 - c) * shade)) for c in base)


def compose(methods, colouring, name, column_width):
    unit = column_width / 1280
    rows = []
    for view in VIEWS:
        images = [Image.open(PANELS / f"{method}-{view}-{colouring}.png").convert("RGB") for method in methods]
        height = round(images[0].height * column_width / images[0].width)
        rows.append([image.resize((column_width, height), Image.LANCZOS) for image in images])
    header, key = round(230 * unit), round(150 * unit)
    sheet = Image.new("RGB", (column_width * len(methods), header + sum(row[0].height for row in rows) + key), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(BOLD, round(54 * unit))
    text_font = ImageFont.truetype(REGULAR, round(38 * unit))
    small_font = ImageFont.truetype(REGULAR, round(32 * unit))
    for column, method in enumerate(methods):
        numbers = STATS[method]
        x = column * column_width + round(30 * unit)
        draw.text((x, round(30 * unit)), TITLES[method], font=title_font, fill=WHITE)
        draw.text((x, round(110 * unit)), f"Faces between subdomains: {numbers['processor_faces'] / 1e6:.2f} M", font=text_font, fill=GREY)
        draw.text((x, round(160 * unit)), f"Largest subdomain: {numbers['max_cells']:,} cells, {numbers['max_cells_above_average_percent']:.2f} % above the average", font=text_font, fill=GREY)
    y = header
    for row in rows:
        for column, image in enumerate(row):
            sheet.paste(image, (column * column_width, y))
        y += row[0].height
    x, y = round(30 * unit), y + round(25 * unit)
    if colouring == "subdomains":
        draw.text((x, y), "One colour per subdomain: 512 subdomains = 4 nodes x 128 ranks, 65.3 M cells (127,607 per subdomain on average).", font=small_font, fill=GREY)
        sheet.save(OUT_DIR / name)
        return
    draw.text((x, y), "Colour = node, shade = NUMA domain (8 per node, 16 ranks each), as the runs place rank r on node r // 128:", font=small_font, fill=GREY)
    swatch = round(34 * unit)
    left, top = x, y + round(55 * unit)
    for node in range(4):
        for numa in range(8):
            draw.rectangle([left, top, left + swatch - 3, top + swatch - 3], fill=numa_colour(node * 8 + numa))
            left += swatch
        draw.text((left + round(10 * unit), top), f"node {node + 1}", font=small_font, fill=GREY)
        left += round(10 * unit) + round(draw.textlength(f"node {node + 1}", font=small_font)) + 2 * swatch
    sheet.save(OUT_DIR / name)


for colouring in ("subdomains", "numa"):
    compose(["hierarchical", "scotch", "multiLevel"], colouring, f"decomposition-{colouring}.png", 1280)
    compose(["scotch", "multiLevel"], colouring, f"decomposition-{colouring}-basic-vs-bonus.png", 1920)
