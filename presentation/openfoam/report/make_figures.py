# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10", "matplotlib>=3.8"]
# ///
"""Collects the technical report's figures in submission/openfoam/figures/: the deck's plots (report_plots.py), two of the
team's figures (figures.py), three diagrams cut from slides that PowerPoint exported, and three decomposition pictures
put together from the ParaView panels of presentation/openfoam/decomposition/panels in Box.

usage: make_figures.py <scratchpad> <output dir>
"""
import shutil
import sys
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

work = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
plots, team, slides, panels = work / "figs_plots", work / "figs_team", work / "slides", work / "panels"
font = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans-Bold.ttf"), 46)
PICTURE = (0x00, 0x38, 0x94)  # the blue of the deck's headings over the decomposition pictures

copies = {
    "fig01_run_to_run_variation.png": team / "fig08_variability.png",
    "fig02_criteria_example.png": plots / "p07_rule.png",
    "fig03_baseline_and_official.png": plots / "p_baseline.png",
    "fig05_decomposition_results.png": plots / "p_decomposition.png",
    "fig07_pinning_results.png": plots / "p10_pinning.png",
    "fig08_hierarchical_scotch_1_2_4_nodes.png": plots / "p11_scotch.png",
    "fig10_node_tree_results.png": plots / "p_node_tree.png",
    "fig11_basic_results.png": plots / "p_basic.png",
    "fig13_cores_or_memory.png": team / "fig19_cores_or_memory.png",
    "fig15_multilevel_results.png": plots / "p_multilevel.png",
    "fig16_call_stacks_flame_graph.png": plots / "ps_flame.png",
    "fig18_bonus_results.png": plots / "p_bonus.png",
    "fig19_effect_of_each_change.png": plots / "ps_each.png",
    "fig20_scaling.png": plots / "p17_scaling.png",
    "fig21_cd_iterations.png": plots / "ps_cd_iterations.png",
}
for name, source in copies.items():
    shutil.copyfile(source, out / name)

# Diagrams drawn as slide shapes, cut from the 2400 x 1350 exports of our 8th-edition build (slides 9, 17 and 22), without
# their titles and captions, which the report gives under the figure.
cuts = {
    "fig06_node_and_pinning.png": ("slide-09.png", (114, 420, 1290, 870)),
    "fig12_memory_limit_placements.png": ("slide-17.png", (114, 246, 2280, 978)),
    "fig17_two_source_changes.png": ("slide-22.png", (114, 222, 2280, 1152)),
}
for name, (source, box) in cuts.items():
    Image.open(slides / source).convert("RGB").crop(box).save(out / name, optimize=True)


NODE_HUES = [(0.12, 0.47, 0.71), (1.0, 0.50, 0.05), (0.17, 0.63, 0.17), (0.58, 0.40, 0.74)]  # as build_deck.py and render.py
small = ImageFont.truetype(str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans-Bold.ttf"), 34)
LABEL_BAND = 44  # the panels' own labels sit in their top 44 px (some still say "Basic: scotch"); the deck cuts them off too


def numa_shade(domain):
    """The colour of NUMA domain domain (0-31) in the pictures, as build_deck.numa_shade() and render.py draw it."""
    shade = domain % 8 / 7.0 * 0.9 - 0.45
    return tuple(round(255 * (c * (1 + shade) if shade < 0 else c + (1 - c) * shade)) for c in NODE_HUES[domain // 8])


def pair(name, left, right):
    """Two decompositions side by side, each as the car, the centre plane and a cross-section (rows) without the panels'
    labels, coloured by node (hue) and NUMA domain (shade), with its decomposeParDict name over its column and, under both,
    the key that the deck has (each node's 8 shades)."""
    width, gap, head, key = 1150, 40, 80, 120
    columns = []
    for method, title in (left, right):
        images = [Image.open(panels / f"{method}-{view}-numa.png").convert("RGB") for view in ("car", "side", "cross")]
        images = [image.crop((0, LABEL_BAND, image.width, image.height)) for image in images]
        images = [image.resize((width, round(image.height * width / image.width)), Image.LANCZOS) for image in images]
        columns.append((title, images))
    total = 2 * width + gap
    height = head + sum(image.height for image in columns[0][1]) + 2 * 12 + key
    sheet = Image.new("RGB", (total, height), "white")
    draw = ImageDraw.Draw(sheet)
    for k, (title, images) in enumerate(columns):
        x = k * (width + gap)
        draw.text((x + width / 2, head / 2), title, fill=PICTURE, font=font, anchor="mm")
        y = head
        for image in images:
            sheet.paste(image, (x, y))
            y += image.height + 12
    top, group_gap = height - key + 14, 60
    group = (total - 3 * group_gap) / 4
    for n in range(4):
        gx = n * (group + group_gap)
        draw.text((gx + group / 2, top + 18), f"node {n + 1}", fill=(0, 0, 0), font=small, anchor="mm")
        cell = group / 8
        for k in range(8):
            draw.rectangle((gx + k * cell, top + 44, gx + (k + 1) * cell - 4, top + 92), fill=numa_shade(8 * n + k))
    sheet.save(out / name, quality=90, optimize=True)


pair("fig04_decomposition_hierarchical_scotch.jpg", ("hierarchical", "hierarchical (16 8 4)"), ("scotch", "scotch"))
pair("fig09_decomposition_scotch_node_tree.jpg", ("scotch", "scotch"), ("scotchDomains", "scotch (2 4 16)"))
pair("fig14_decomposition_node_tree_multilevel.jpg", ("scotchDomains", "scotch (2 4 16)"), ("multiLevel", "multiLevel (4 2 4 16)"))
for path in sorted(out.iterdir()):
    print(f"{path.name:48s} {path.stat().st_size / 1024:7.0f} KB")
