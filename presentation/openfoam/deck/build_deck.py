# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0", "lxml", "pillow", "xlsxwriter"]
# ///
"""Rebuild the OpenFOAM (HPC) part of the team deck as the 8th edition of ../slides.md, as a deck of its own.

usage: uv run build_deck.py INPUT.pptx OUTPUT.pptx FIGDIR

INPUT is the team deck whose OpenFOAM part is still the 10/29 build: the cover 1, main 2-21 with the team's HPC roofline at
14, divider 22, Q&A index 23, supporting 24-45 and the shared reproducibility slide 46, then the AI track from slide 47 on.
FIGDIR holds the deck's renders of ../figures.py (deck_figures.py), its per-job plots (deck_plots.py) and Box's pictures of
the decompositions coloured by node and NUMA domain; build.sh puts them there and runs all three steps.

The output is the HPC part alone (the user, 11/02: the team keeps the HPC and AI parts apart): the cover, the 20 main
slides of slides.md, the divider, the Q&A index and 19 supporting slides. They are rebuilt in place on input slides, so each
keeps a slide id and the team's slide-number box; the supporting slides are hidden from the slide show. The other input
slides are removed: the AI track, the team's roofline and the shared reproducibility slide, which the user did not want
(11/01). The notes of the main slides are read from slides.md (script, translation, memo), the others come from notes.py.
PowerPoint's sections follow the new slide list.

The look follows the user (11/01): pure black, bold text; emphasis in the accent blue, never by weight; a unit on every
number; each figure numbered with a one-sentence caption under it, and each table with one over it; and the content spread
over the whole slide. Time axes start at 0, with a wavy break where the jobs need a narrow range (11/02).
"""

import csv
import json
import re
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.chart import XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE

from decklib import add_text, arrow_line, bar_chart, box, bullets, clear_slide, picture, set_notes, set_title, shape_text, table
from notes import NOTES
from palette import BASE, BASIC, BONUS, BONUS_LINE, BONUS_TINT, COMPUTATION, FAINT, HALVED, INK, LIGHT, LINE, MEMORY, MPI, MUTED, NAVY, WHITE

SRC, OUT, FIG = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
HERE = Path(__file__).resolve().parent
PLAN, DATA = HERE.parent / "slides.md", HERE.parent / "data"
prs = Presentation(SRC)
S = list(prs.slides)  # S[i] is input slide i + 1
EMU = 914400
X0, XW = 0.70, 11.93  # left edge and width of the content area; the title ends at 0.80 in and the slide number at 7.14 in
# the columns (picture, left and right crops) of Box's presentation/openfoam/decomposition/ pictures coloured by node and
# NUMA domain, each column the car, the centre plane and a cross-section between a header row and the key to the colours:
# decomposition-numa.png (3840 x 2220) has the case default hierarchical, plain scotch and multiLevel, and
# decomposition-numa-scotch-domains-vs-multilevel.png (3840 x 3330, drawn on Genkai on 11/02) Basic's scotch on the node
# tree and multiLevel; the second is the first's rows at 1.5 times the scale, so both take the same top and bottom crops
DECOMP_COLUMNS = {"hier": ("decomposition-numa", 0.0, 0.667), "scotch": ("decomposition-numa", 0.333, 0.334), "basic": ("decomposition-numa-scotch-domains-vs-multilevel", 0.0, 0.5), "multi": ("decomposition-numa-scotch-domains-vs-multilevel", 0.5, 0.0)}
PANEL_TOP, ALL_BOTTOM = 0.113, 0.085
# the hue of each node in those pictures (decomposition/render.py), its 8 NUMA domains shaded from 45% darker to 45% lighter
NODE_HUES = [(0.12, 0.47, 0.71), (1.0, 0.50, 0.05), (0.17, 0.63, 0.17), (0.58, 0.40, 0.74)]
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
CODE = "Consolas"  # the font of OpenFOAM dictionaries on the slides
COUNT = {"prefix": "", "Figure": 0, "Table": 0}  # Figure 1 and Table 1 on in the main part, Figure S1 and Table S1 on in the supporting slides
# the titles of the input's OpenFOAM part, slides 1-46, in order
INPUT_TITLES = ["", "OpenFOAM TASK OVERVIEW", "ASPIRE-2A", "BASELINE SETTINGS", "BASELINE RESULTS", "HOW WE MEASURE AND PROFILE", "MPI PROFILE ON 4 NODES", "BASELINE ANALYSIS", "OPTIMIZATION STRATEGY", "BASIC OPTIMIZATION (1/2)", "BASIC OPTIMIZATION (2/2)", "BASIC RESULTS", "MEMORY BANDWIDTH SETS THE SPEED", "HPC ROOFLINE: MEMORY AND COMMUNICATION", "BONUS OPTIMIZATION", "BONUS RESULTS", "BONUS ANALYSIS", "SCALING ANALYSIS", "WHAT DID NOT HELP, AND WHY", "CONCLUSION", "EXTRA: A GAIN WE DID NOT COUNT", "SUPPORTING INFORMATION", "Q&A INDEX", "BOTTLENECKS WE MEASURED", "MEASURING HONESTLY", "EXPERIMENT AUTOMATION", "BUILD, STORAGE AND MPI", "THE ORGANISERS' REFERENCE", "WHERE A STEP GOES AFTER BASIC", "THE PATH ON 4 NODES", "IS THE NETWORK THE BOTTLENECK?", "OFI AGAINST UCX", "THE THREE SPLITS: FACES OR EVEN WORK?", "CORES OR MEMORY?", "THE SOURCE CHANGES (1/2)", "THE SOURCE CHANGES (2/2)", "SOURCE CHANGES IN DETAIL (1/2)", "SOURCE CHANGES IN DETAIL (2/2)", "EFFECT OF EACH BONUS CHANGE", "PROFILES BEFORE AND AFTER", "WHY THE EFFICIENCY EXCEEDS 1", "DRAG COEFFICIENT CHECKS", "REPRODUCING OUR RESULTS", "NOT ADOPTED: THE FULL LIST", "COMPILER AND FLAGS", "Reproducibility: Code, Build, Runtime and Results"]
AI = len(INPUT_TITLES)  # S[AI] is the AI track's title slide


def check_input():
    titles = [s.shapes.title.text_frame.text if s.shapes.title is not None else "" for s in S]
    ai_title = " ".join(sh.text_frame.text for sh in S[AI].shapes if sh.has_text_frame) if len(S) > AI else ""
    if titles[:AI] != INPUT_TITLES or "AI Track" not in ai_title:
        raise SystemExit("build_deck.py expects the team deck with the 10/29 OpenFOAM part (slides 1-46, the HPC roofline at 14, the AI title slide at 47); see README.md")


def plan_notes():
    """The notes of the 20 main slides from slides.md: the time, the English script, its translation and the memo."""
    text = PLAN.read_text(encoding="utf-8")
    body = text[text.index("\n## 本編"):text.index("\n## 入れなかったもの")]
    notes = []
    for section in body.split("\n### ")[1:]:
        head, rest = section.split("\n", 1)
        time = re.search(r"（(\d+:\d\d)）$", head).group(1)
        script = re.search(r"^原稿（[^）]*）：(.+)$", rest, re.MULTILINE).group(1)
        translation = re.search(r"^訳：(.+)$", rest, re.MULTILINE).group(1)
        memo = rest.split("\nメモ：\n", 1)[1].strip().replace("`", "") if "\nメモ：\n" in rest else ""
        notes.append(f"[{time}]\nEN: {script}\n\n訳（参考）: {translation}\n\nJP:\n{memo}")
    if len(notes) != 20:
        raise SystemExit(f"slides.md has {len(notes)} main slides instead of 20; see README.md")
    return notes


check_input()
PLAN_NOTES = plan_notes()
MESH = next(sh for sh in S[1].shapes if sh.name == "図 5").image.blob  # refinement level of the mesh, on the input's slide 2 with the video


def reuse(i, keep=()):
    """Input slide i + 1, emptied but for its title, its slide number and the shapes named in keep."""
    clear_slide(S[i], keep=keep)
    return S[i]


def fig(name):
    return FIG / f"{name}.png"


def place(s, name, x, y, w, h):
    sh = next(sh for sh in s.shapes if sh.name == name)
    sh.left, sh.top, sh.width, sh.height = (int(v * EMU) for v in (x, y, w, h))


def heading(s, x, y, w, text, size=17):
    """A short heading over a table or a column of text."""
    return add_text(s, x, y, w, 0.42, [text], size=size, color=NAVY)


def caption(s, x, y, w, text, h=0.55, size=14, align="l", kind="Figure"):
    """'Figure N. One sentence on what it shows' under a figure, or 'Table N. ...' over a table, numbered in slide order."""
    COUNT[kind] += 1
    return add_text(s, x, y, w, h, [{"runs": [f"{kind} {COUNT['prefix']}{COUNT[kind]}. {text}"], "align": align}], size=size)


def table_caption(s, x, y, w, text, h=0.42):
    """The numbered caption over a table; returns its bottom, where the table starts."""
    caption(s, x, y, w, text, h=h, kind="Table")
    return y + h


def figure(s, name, x, y, w, text, gap=0.08, h=0.55):
    """A plot from FIGDIR with its caption under it; returns the bottom of the caption."""
    pic = picture(s, fig(name), x, y, w=w)
    bottom = y + pic.height / EMU
    caption(s, x, bottom + gap, w, text, h=h)
    return bottom + gap + h


def decomp_panel(s, which, x, y, w=None, h=None):
    """One column of a decomposition picture coloured by node and NUMA domain (the user, 11/02), its three views stacked;
    build.sh copies the pictures into FIGDIR."""
    name, left, right = DECOMP_COLUMNS[which]
    return picture(s, fig(name), x, y, w, h, crop=(left, PANEL_TOP, right, ALL_BOTTOM))


def numa_shade(domain):
    """The colour of NUMA domain domain (0-31, node 1 first) in the decomposition pictures, as render.py draws it."""
    shade = domain % 8 / 7.0 * 0.9 - 0.45
    return "".join(f"{round(255 * (c * (1 + shade) if shade < 0 else c + (1 - c) * shade)):02X}" for c in NODE_HUES[domain // 8])


def numa_key(s, x, y, w):
    """The key to the colours under the decomposition pictures, as Box's picture has it (the user, 11/02): each node's name
    over its 8 shades, one per NUMA domain; returns the bottom."""
    gap = 0.2
    group = (w - 3 * gap) / 4
    cell = group / 8
    for n in range(4):
        gx = x + n * (group + gap)
        add_text(s, gx, y, group, 0.3, [f"node {n + 1}"], size=14, align="c")
        for k in range(8):
            box(s, gx + k * cell, y + 0.32, cell - 0.015, 0.17, fill=numa_shade(8 * n + k), shape=MSO_SHAPE.RECTANGLE)
    return y + 0.49


def main_slide(i):
    """Input slide i + 1 as a new main slide: emptied like reuse() and shown in the slide show (the free input slides are
    hidden supporting slides of the 10/29 build, but for the team's roofline)."""
    s = reuse(i)
    s._element.attrib.pop("show", None)
    return s


def merge_down(frame, column, first, last):
    """One cell over rows first..last of a table column, keeping the text of the first; the rows below must be empty."""
    frame.table.cell(first, column).merge(frame.table.cell(last, column))


def code(s, x, y, w, lines, size=15):
    """Lines of an OpenFOAM dictionary in a monospace font with a thin rule on their left (the user, 11/02: show the
    decompositions in OpenFOAM's own syntax); returns the bottom."""
    h = len(lines) * size * 1.25 / 72
    arrow_line(s, x + 0.02, y, x + 0.02, y + h, color=LINE, width=3, head=False)
    add_text(s, x + 0.2, y, w - 0.2, h, [{"runs": [line], "font": CODE} for line in lines], size=size)
    return y + h


# The ASPIRE-2A node as icons (the user asked for memory and CPU icons, 11/02): two CPUs, each a chip with pins holding its
# four NUMA domains of 16 cores, and under each domain its two memory channels drawn as memory modules. A core that runs a
# rank is navy and a channel in use green, so that CPU and memory differ (the user, 11/02, as in their hand edit of the
# memory-limit slide); the others are grey. In a domain the top two rows of cores share one L3, the bottom two the other.
OFF = "D5D9E0"  # a core without a rank, or a memory channel not in use


class Node:
    """The geometry of the node drawing at a scale: a core is 0.09 in at scale 1, and the node 4.86 x 1.10 in."""

    def __init__(self, x, y, scale=1.0):
        self.x, self.y = x, y
        self.cell, self.cell_gap, self.pad, self.domain_gap, self.edge, self.cpu_gap = (v * scale for v in (0.09, 0.022, 0.045, 0.035, 0.055, 0.3))
        self.side = 4 * self.cell + 3 * self.cell_gap + 2 * self.pad  # of a domain
        self.chip_w, self.chip_h = 4 * self.side + 3 * self.domain_gap + 2 * self.edge, self.side + 2 * self.edge
        self.module_w, self.module_h, self.module_top = 0.16 * scale, 0.34 * scale, 0.13 * scale
        self.pin_w, self.pin_h = 0.034 * scale, 0.05 * scale
        self.w, self.h = 2 * self.chip_w + self.cpu_gap, self.chip_h + self.module_top + self.module_h

    def chip_x(self, cpu):
        return self.x + cpu * (self.chip_w + self.cpu_gap)

    def domain_x(self, d):
        return self.chip_x(d // 4) + self.edge + d % 4 * (self.side + self.domain_gap)

    def core(self, d, k):
        """Top-left corner of core k (0-15, row by row) of NUMA domain d (0-7, CPU 0 first)."""
        r, c = divmod(k, 4)
        return self.domain_x(d) + self.pad + c * (self.cell + self.cell_gap), self.y + self.edge + self.pad + r * (self.cell + self.cell_gap)

    def module(self, d, m):
        """Top-left corner of memory channel m (0-1) of domain d."""
        gap = (self.side - 2 * self.module_w) / 3
        return self.domain_x(d) + gap + m * (self.module_w + gap), self.y + self.chip_h + self.module_top


def node(s, at, cores, channels, frame=()):
    """One node as icons in a group of shapes, laid out by the Node at: cores[d] lists the cores of NUMA domain d that run a
    rank and channels[d] how many of its two memory channels are in use; the domains in frame get a navy outline."""
    g = s.shapes.add_group_shape()
    for cpu in range(2):
        cx = at.chip_x(cpu)
        for k in range(12):  # pins on the top and bottom edges of the chip
            px = cx + at.edge + (at.chip_w - 2 * at.edge) * (k + 0.5) / 12 - at.pin_w / 2
            for py in (at.y - at.pin_h, at.y + at.chip_h):
                box(g, px, py, at.pin_w, at.pin_h, fill=FAINT, shape=MSO_SHAPE.RECTANGLE)
        box(g, cx, at.y, at.chip_w, at.chip_h, fill=WHITE, line=MUTED, line_w=1.25, radius=0.06)
    for d in range(8):
        framed = d in frame
        box(g, at.domain_x(d), at.y + at.edge, at.side, at.side, fill=LIGHT, line=NAVY if framed else LINE, line_w=2.25 if framed else 0.75, radius=0.08)
        for k in range(16):
            box(g, *at.core(d, k), at.cell, at.cell, fill=NAVY if k in cores[d] else OFF, radius=0.15)
        for m in range(2):
            mx, my = at.module(d, m)
            used = m < channels[d]
            box(g, mx, my, at.module_w, at.module_h, fill=MEMORY if used else OFF, radius=0.12)
            for k in range(3):  # the memory chips on the module
                box(g, mx + at.module_w * 0.2, my + at.module_h * (0.1 + k * 0.28), at.module_w * 0.6, at.module_h * 0.2, fill=WHITE if used else LIGHT, radius=0.1)
    return g


# The flow of the first and the last main slide: the unit, each stage with what it dealt with, and the change from one stage
# to the next.
HPC_FLOW = ("s/step", [("Our Baseline", "3.650", "case defaults"), ("Basic", "2.898", "rank balance and binding"), ("Bonus", "2.360", "less data moved per step")], ["−20.6%", "−18.6%"])


def flow(s, y, stages=HPC_FLOW, common=False, big=46, small=18):
    """From the Baseline through Basic to the Bonus, with what each stage dealt with: time per step on 4 nodes on the first
    main slide. common adds the official runs (the organisers' Common Baselines, called Official on the slides since 11/01)
    under our Baseline; big and small are the sizes of the numbers and their unit."""
    unit, stages, changes = stages
    w = 3.3
    gap = (XW - 3 * w) / 2
    for k, ((name, value, what), color) in enumerate(zip(stages, (BASE, BASIC, BONUS))):
        x = X0 + k * (w + gap)
        add_text(s, x, y, w, 0.45, [name], size=20, color=color, align="c")
        add_text(s, x, y + 0.45, w, 0.95, [[(value, {"size": big}), (f" {unit}", {"size": small, "color": INK})]], color=color, align="c", anchor="m")
        paras = [{"runs": [what], "align": "c"}]
        if common and k == 0:
            # each official run on a line of its own, named by its decomposition (the user, 11/02), the times lined up by tabs
            # as in the user's hand edit (11/02)
            paras += [{"runs": ["Official"], "align": "c", "size": 14, "space_before": 4}] + [{"runs": [f"{method}:{tabs}{value} s/step"], "align": "c", "size": 14} for method, tabs, value in (("hierarchical", "\t", "3.415"), ("scotch", "\t\t", "3.576"))]
        add_text(s, x, y + 1.45, w, 1.1, paras, size=16)
        if k:
            x1, x2 = x - gap + 0.1, x - 0.1
            arrow_line(s, x1, y + 0.92, x2, y + 0.92, color=INK, width=3)  # black and 3 pt, as the user drew them (11/02)
            add_text(s, x1 - 0.25, y + 0.42, x2 - x1 + 0.5, 0.42, [changes[k - 1]], size=17, color=color, align="c")


# ====================================================================== main part (slides.md 1-20, deck 2-21)
def m_summary():
    """The results as the flow of the last slide with the mesh under it (the user's draft of 11/01: the flow of the 6th
    edition's conclusion). The flow video went to the Basic results, which had room for it (the user, 11/01), so this slide
    is built on another input slide and the mesh picture is added again."""
    s = reuse(7)
    set_title(s, "OpenFOAM ON ASPIRE-2A")
    flow(s, 1.35, common=True)
    mw = 11.0
    mx = X0 + (XW - mw) / 2
    pic = picture(s, MESH, mx, 3.95, w=mw)
    caption(s, mx, 3.95 + pic.height / EMU + 0.08, mw, "Refinement level of the 65.3 million cells, finest near the car.", h=0.4)
    set_notes(s, PLAN_NOTES[0])
    return s


def m_criteria():
    """The test for keeping a change; the Cd band and the profile behind each gain are the organisers' rules, so the third
    item only says that a source change keeps the computation, as the rules require (the user, 11/02)."""
    s = reuse(2)
    set_title(s, "CRITERIA FOR KEEPING A CHANGE")
    rules = ["Candidate and control ran in turns in the same period with at least 3 jobs each on 4 nodes.", "We kept a change only if every candidate job was faster than every control job.", "Source changes had to keep the computation the same, as the rules require."]
    add_text(s, X0, 1.5, 6.0, 5.3, [{"runs": [rule], "bullet": {"number": True, "size_pct": 100, "indent": 0.45}, "space_after": 40} for rule in rules], size=20, line=1.1)
    figure(s, "p07_rule", 7.05, 1.3, 5.58, "Each job of a change that was kept and of one that was not, against its control on 4 nodes.")
    set_notes(s, PLAN_NOTES[1])
    return s


def m_profile_baseline():
    s = reuse(3)
    set_title(s, "PROFILING THE BASELINE")
    # 3.650 s/step: the user's hand edit (11/02); the wait for other ranks is MPI_Waitall and MPI_Allreduce, 70.72 of the
    # 169.57 s of a rank in CrayPAT 38219766511, told apart from the computing and waiting for memory outside MPI (the user,
    # 11/02: MPI alone did not look like the largest bottleneck)
    add_text(s, X0, 1.35, XW, 1.0, [{"runs": ["Our Baseline was unmodified v2512 built with GCC 11.2 and run on Cray MPICH over UCX."], "space_after": 6}, "It took 3.650 s/step on 4 nodes with an SD of 4.1% over 3 jobs."], size=20)
    rows = [["Possible bottleneck", "How we measured it", "What we found"], ["MPI", "CrayPAT and OpenFOAM profiling", "46% of each rank's time, 42% waiting for other ranks"], ["Outside MPI", "CrayPAT and AMD uProf", "The other 54%, computing and waiting for memory"], ["Network transfer", "IMB after every run", "Global sums took about 0.02 s per step"], ["File I/O and OS noise", "Timers and interrupt counts", "0.01% and 0.8% of the time"]]
    top = table_caption(s, X0, 2.62, XW, "Each possible bottleneck of our Baseline, how we measured it and what we found.")
    table(s, X0, top + 0.05, [3.0, 3.9, 5.03], rows, row_heights=[0.55, 0.8, 0.8, 0.8, 0.8], size=18, colors=[None, [INK, INK, NAVY], None, None, None])
    set_notes(s, PLAN_NOTES[2])
    return s


def m_mpi():
    """The organisers' ISC26 SCC task asks for the 3 most used MPI calls on 4 nodes, by number of calls and by total CPU time;
    the APAC task rules strongly recommend MPI profiling. Two tables, one per ranking, with the time of the most frequent
    calls too, and the sum over the ranks told apart from the time of one rank (the user, 11/02). CrayPAT 38219766511 (#62):
    the sums are its mean per rank times 512, over the whole run of 40 steps."""
    s = reuse(4)
    set_title(s, "MPI CALLS ON 4 NODES")
    xr, w = X0 + 5.97, 5.96  # the user's hand edit of 11/02: the right table moved left and widened for MPI_Allreduce
    top = table_caption(s, X0, 1.3, 5.7, "The three MPI calls made most often, summed over the 512 ranks.")
    rows = [["Call", "Calls, all ranks", "Time, all ranks"], ["MPI_Isend", "290 M calls", "839 s"], ["MPI_Irecv", "290 M calls", "167 s"], ["MPI_Test", "289 M calls", "24 s"]]
    table(s, X0, top + 0.08, [2.0, 1.9, 1.8], rows, row_heights=[0.75, 0.6, 0.6, 0.6], size=18, aligns=["l", "r", "r"])
    table_caption(s, xr, 1.3, w, "The three MPI calls that took the most time, summed over the 512 ranks and per rank.")
    rows = [["Call", "Time, all ranks", "Time per rank", "Share of MPI"], ["MPI_Waitall", "22,069 s", "43.1 s", "55%"], ["MPI_Allreduce", "14,140 s", "27.6 s", "35%"], ["MPI_Bcast", "1,289 s", "2.5 s", "3%"]]
    table(s, xr, top + 0.08, [2.175, 1.353, 1.33, 1.105], rows, row_heights=[0.75, 0.6, 0.6, 0.6], size=18, aligns=["l", "r", "r", "r"], colors=[None, [NAVY] * 4, [NAVY] * 4, None])
    bullets(s, X0, top + 2.95, XW, 6.95 - top - 2.95, ["Isend, Irecv and Test exchange halo values with neighbouring subdomains and took little time.", "Waitall and Allreduce wait for other ranks and took 90% of the MPI time.", "With equal cells the fastest rank computed for 1.34 s/step and the slowest for 2.88 s/step."], size=19, space_after=12)
    set_notes(s, PLAN_NOTES[3])
    return s


def steps(s, x, y, w, items, size=19, gap=16):
    """Short steps of a story, each a navy word over one sentence: [(word, sentence), ...]."""
    paras = []
    for k, (word, sentence) in enumerate(items):
        paras += [{"runs": [word], "color": NAVY, "size": size - 1, "space_before": gap if k else 0}, {"runs": [sentence], "line": 1.05}]
    return add_text(s, x, y, w, 6.95 - y, paras, size=size)


def m_pinning():
    """Why we pinned, what /proc showed and the fix: the user (11/02) wanted the slide to start from why pinning should help,
    with the NUMA domains, and less text. The node is drawn with one rank (a navy core) whose memory is in its own NUMA
    domain's two channels (green), and the way to the memory of a domain on the other CPU. What /proc showed is from the scotch jobs
    without pinning (Neither of the next slide, #36 A3), since scotch came first (the user, 11/02)."""
    s = reuse(5)
    set_title(s, "CPU AND MEMORY PINNING")
    at = Node(X0 + 0.05, 3.0, scale=1.3)
    cores = [[] for _ in range(8)]
    cores[1] = [5]
    node(s, at, cores, [0, 2, 0, 0, 0, 0, 0, 0], frame=(1,))
    for cpu in range(2):
        add_text(s, at.chip_x(cpu), at.y - 0.55, at.chip_w, 0.4, [f"CPU {cpu}"], size=17, align="c")
    cx, cy = at.core(1, 5)
    cx, cy = cx + at.cell / 2, cy + at.cell / 2
    bottom = at.y + at.h
    # arrows are black (the user, 11/03), but for the way to remote memory, which may stay grey
    for d, m, arrow, color, label in ((1, 0, INK, MEMORY, "local memory"), (6, 1, FAINT, INK, "remote memory")):
        mx, my = at.module(d, m)
        arrow_line(s, cx, cy, mx + at.module_w / 2, my - 0.02, color=arrow, width=2.25)
        add_text(s, at.domain_x(d) + at.side / 2 - 1.2, bottom + 0.08, 2.4, 0.4, [label], size=16, color=color, align="c")
    caption(s, X0, bottom + 0.62, at.w + 0.1, "One node of 2 CPUs with 4 NUMA domains each, a domain having 16 cores and 2 memory channels, one rank in navy and its local memory in green.", h=0.7)
    steps(s, 7.45, 1.45, 5.18, [("Expected", "A rank that stays on one core keeps its data in the memory of its own NUMA domain, the closest."), ("Found", "During the solve no rank stayed on its own core and only 7% of its memory was local."), ("Cause", "The launcher had bound each rank but MPI_Init removed the binding."), ("Fixed", "numactl binds the memory before each rank starts and a watcher re-pins the rank with taskset.")])
    set_notes(s, PLAN_NOTES[5])
    return s


def m_decomposition():
    """The decomposition first (the user, 11/02: the most common way to speed up OpenFOAM, and the Task Rules say "try this
    first"): the case default and scotch in decomposeParDict's own words, the time per step of each job in a plot with the
    faces between subdomains under each name instead of a table (the user, 11/02: a comparison of results goes in a plot),
    and the pictures coloured by node and NUMA domain over the key to their colours. The jobs ran without pinning, our
    Baseline (#62) and Neither of the pinning experiment on scotch (#36 A3), not in turns; the pinned, alternated
    comparison is on the pinning results slide. The scotch of the pictures is plain scotch, as in these jobs."""
    s = reuse(6)
    set_title(s, "DECOMPOSITION")
    w = 5.75
    heading(s, X0, 1.3, w, "The case default, as in our Baseline", size=16)
    bottom = code(s, X0, 1.72, w, ["method  hierarchical;", "hierarchicalCoeffs { n (16 8 4); }"])
    heading(s, X0, bottom + 0.15, w, "The first change we tried", size=16)
    bottom = code(s, X0, bottom + 0.57, w, ["method  scotch;"])
    figure(s, "p05_decomposition", X0, bottom + 0.2, w, "Each job without pinning on 4 nodes, with the faces between subdomains.")
    pw = 2.8
    xr = 12.63 - 2 * pw - 0.15
    for i, (which, label) in enumerate((("hier", "hierarchical (16 8 4)"), ("scotch", "scotch"))):  # (16 8 4): the user's hand edit, 11/02
        x = xr + i * (pw + 0.15)
        add_text(s, x, 1.3, pw, 0.4, [label], size=18, color=NAVY, align="c")
        panel = decomp_panel(s, which, x, 1.72, w=pw)
    bottom = numa_key(s, xr, 1.72 + panel.height / EMU + 0.1, 2 * pw + 0.15)
    caption(s, xr, bottom + 0.12, 2 * pw + 0.15, "The subdomains on the car, the centre plane and a cross-section, one hue per node and one shade per NUMA domain.", h=0.62)
    set_notes(s, PLAN_NOTES[4])
    return s


def m_pinning_results():
    """The four placements on scotch (#36 A3, data/pinning.csv), the figure the user preferred (11/02: scotch came first and
    the pinning was measured on it), with the times in a table and the alternated comparison of the two decompositions once
    both were pinned (#36, data/decomposition_basic.csv). The figure on the Baseline's own decomposition is a supporting
    slide."""
    s = main_slide(13)
    set_title(s, "PINNING RESULTS")
    w = 5.75
    top = table_caption(s, X0, 1.3, w, "Time per step on 4 nodes with scotch under four placements.", h=0.7)
    # no column of jobs beside a plot that shows them (the user, 11/02); "in alternated jobs" is said once on slide 2
    rows = [["Pinned", "s/step", "SD"], ["Neither", "3.395", "0.78%"], ["CPU only", "3.474", "2.0%"], ["Memory only", "4.380", ""], ["CPU and memory", "2.917", "0.13%"]]
    table(s, X0, top + 0.05, [2.85, 1.45, 1.45], rows, row_h=0.5, size=18, aligns=["l", "r", "r"], colors=[None, None, None, None, [NAVY] * 3])
    bullets(s, X0, top + 2.8, w, 6.95 - top - 2.8, ["Only pinning both took 14.1% off a step.", "Pinned jobs varied less, so smaller gains could be seen.", "Pinned, scotch was 10.5% faster than hierarchical."], size=18, space_after=12)
    figure(s, "p10_pinning", 6.73, 1.3, 5.9, "Each job under four placements of the ranks on 4 nodes with scotch.")
    set_notes(s, PLAN_NOTES[6])
    return s


def m_mapping():
    """Basic's last change, scotch mapped onto the node tree, in decomposeParDict's own words (the user, 11/02). The
    dictionary is the one run/prepare.pbs writes but for the strategy string, Scotch 6.1's default mapping strategy with an
    exact final balance of 1% (#38, #63). In Scotch the weights become the costs 64, 8, 4 and 1 of a link between nodes,
    sockets, NUMA domains and cores (#38). Faces against plain scotch from the decomposePar logs (REPORT §6.3); jobs of #63,
    5 v 5 alternated."""
    s = reuse(15)
    set_title(s, "SCOTCH ON THE NODE TREE")
    w = 5.75
    heading(s, X0, 1.3, w, "decomposeParDict of Basic", size=16)
    bottom = code(s, X0, 1.72, w, ["method  scotch;", "scotchCoeffs", "{", "    domains        (2 4 16);", "    domainWeights  (0.125 0.0625 0.015625);", "    strategy       \"…\";", "}"])
    top = table_caption(s, X0, bottom + 0.25, w, "The tree that domains describes, with its faces against plain scotch.", h=0.7)
    rows = [["Between two", "Cost", "Faces"], ["nodes", "64", "−22.7%"], ["sockets", "8", "−21.3%"], ["NUMA domains", "4", "−10.4%"], ["cores", "1", "+3.3%"]]
    table(s, X0, top + 0.05, [2.85, 1.2, 1.7], rows, row_h=0.44, size=17, aligns=["l", "r", "r"], colors=[None, [INK, INK, NAVY], [INK, INK, NAVY], [INK, INK, NAVY], None])
    figure(s, "p09_mapping", 6.73, 1.3, 5.9, "Each job of plain scotch and of scotch mapped onto the node, both pinned, on 4 nodes.")
    set_notes(s, PLAN_NOTES[7])
    return s


def basic_table(s, x, y, w):
    """The official runs, our Baseline and Basic on 4 nodes, with the SD of each, the jobs being in the plot beside it (the
    user, 11/02); returns the bottom."""
    top = table_caption(s, x, y, w, "Time per step on 4 nodes.")
    rows = [["Run", "s/step", "SD"], ["Official, hierarchical", "3.415", ""], ["Official, scotch", "3.576", ""], ["Our Baseline", "3.650", "4.1%"], ["Basic", "2.898", "0.07%"]]
    table(s, x, top + 0.05, [w - 2.5, 1.35, 1.15], rows, row_h=0.47, size=17, aligns=["l", "r", "r"], colors=[None, None, None, None, [BASIC, NAVY, NAVY]])
    return top + 0.05 + 5 * 0.47


def m_basic_results():
    """Basic against the official runs and our Baseline: the times in a table, the plot with the official runs and an arrow
    (the user, 11/02), and the flow video under the table (moved here from slide 1, 11/01). The slide is built on the input
    slide that holds the video, so the video keeps its autoplay, which lives in that slide's timing."""
    s = reuse(1, keep=("flow-iterations",))
    set_title(s, "BASIC RESULTS")
    bottom = basic_table(s, X0, 1.3, 5.5)
    vh = 2.0
    place(s, "flow-iterations", X0, bottom + 0.3, vh * 5.33 / 3.0, vh)  # the video's own 16:9 frame
    caption(s, X0, bottom + 0.3 + vh + 0.06, 5.5, "Flow around the car over the 150 iterations, drawn with ParaView.")
    figure(s, "p12_basic", 6.43, 1.3, 6.2, "Each job of the official runs, our Baseline and Basic on 4 nodes, with the mean and SD of each.")
    set_notes(s, PLAN_NOTES[8])
    return s


def m_basic_mpi():
    """The MPI profile of Tables 2 and 3 again after Basic, the calls by count and by time, per rank, against our Baseline
    (the user, 11/02: the calls too, and no copy of the plot of the Basic results). CrayPAT, whole runs of 40 steps:
    Baseline 38219766511 (#62), Basic before its mapping onto the node 37176272426 (#36, plain scotch, pinned); no profile of
    the mapped Basic exists, and the mapping changed a step by 0.7%. Basic's default report leaves out the calls that take
    little time, MPI_Test among them, so the third row by count is every MPI call but the six it lists (Isend, Irecv,
    Waitall, Allreduce, Bcast, Comm_dup), taken the same way for both: in the Baseline that is MPI_Test's 563,646 calls and
    2,238 rare ones (pat-report-baseline-calls.txt)."""
    s = main_slide(36)
    set_title(s, "MPI AFTER BASIC")
    xr = 6.8
    top = table_caption(s, X0, 1.3, 5.89, "The MPI calls made most often, per rank, our Baseline against Basic before its node mapping.", h=0.7)
    rows = [["Call", "Baseline", "Basic"], ["MPI_Isend", "566,107", "597,033"], ["MPI_Irecv", "566,107", "597,033"], ["MPI_Test and others", "565,883", "596,475"]]
    table(s, X0, top + 0.08, [3.05, 1.42, 1.42], rows, row_h=0.55, size=18, aligns=["l", "r", "r"])
    table_caption(s, xr, 1.3, 12.63 - xr, "The MPI calls that took the most time, per rank, in the same CrayPAT runs of 40 steps.", h=0.7)
    rows = [["Call", "Baseline", "Basic"], ["MPI_Waitall", "43.1 s", "10.2 s"], ["MPI_Allreduce", "27.6 s", "12.9 s"], ["MPI_Bcast", "2.5 s", "1.4 s"], ["All MPI calls", "78.3 s", "26.7 s"], ["Share of the time", "46%", "19%"]]
    table(s, xr, top + 0.08, [2.65, 1.59, 1.59], rows, row_h=0.55, size=18, aligns=["l", "r", "r"], colors=[None, [INK, INK, NAVY], None, None, [INK, INK, NAVY], [INK, INK, NAVY]])
    bullets(s, X0, top + 0.08 + 6 * 0.55 + 0.3, XW, 1.2, ["The most frequent calls stayed the same three, with about 5% more calls.", "The wait in Waitall fell by 76% because the ranks now finish their computation together."], size=19, space_after=12)
    set_notes(s, PLAN_NOTES[9])
    return s


def m_not_helped_basic():
    """Every Basic idea we tried and did not keep, with its result in words, not + or −, and the ones we expected to help in
    navy (the user, 11/02: show all of them before the Basic profile, and explain the striking ones).
    Data: data/compiler_options.csv (#36 D), #59 (PGO), #36 and #41 (network), #43 (SMT), REPORT §10 (git c562b50)."""
    s = main_slide(37)
    set_title(s, "WHAT DID NOT HELP IN BASIC")
    top = table_caption(s, X0, 1.3, XW, "Each Basic idea we tried and did not keep, with its time per step against its control on 4 nodes.")
    rows = [["Idea", "Time per step"], ["Compiler flags -march=znver3, -O2 and LTO", "no change, at most 0.1% slower"], ["AMD compilers AOCC 5.0 and AOCL 5.1", "no change, within 0.1%"], ["GCC profile-guided optimisation", "0.1% slower"], ["UCX over RC with 55% more network bandwidth", "no change, within 0.1%"], ["Rank reordering with 92% fewer faces between nodes", "0.1% slower"], ["Default OFI transport with the organisers' workarounds", "0.8% slower"], ["OpenFOAM's communication switches", "no gain, and one crashed"], ["glibc malloc thresholds", "0.4% faster, within the spread"], ["Two ranks per core (SMT)", "5.7 times slower"]]
    striking = {1, 2, 3, 4, 5}
    table(s, X0, top + 0.05, [7.3, 4.63], rows, row_h=0.46, size=16, colors=[None] + [[NAVY, NAVY] if i in striking else None for i in range(1, len(rows))])
    # why the compilers did not help comes with the profile of Basic on the next slides (the user, 11/02)
    bullets(s, X0, top + 0.05 + 0.46 * len(rows) + 0.2, XW, 0.6, ["Network changes cannot shorten the wait for the slowest rank."], size=18, space_after=4)
    set_notes(s, PLAN_NOTES[10])
    return s


def m_profile_basic():
    s = reuse(8)
    set_title(s, "PROFILING BASIC")
    rows = [["Possible bottleneck", "How we measured it", "What we found after Basic"], ["MPI", "CrayPAT", "Fell from 46% to 19% of the time"], ["Outside MPI", "CrayPAT and AMD uProf", "81% of the time with about 0.1 flop per byte in the hottest loops"], ["Core speed", "Core counters and five compiler settings", "0.4 to 0.7 instructions per cycle and no compiler setting helped"], ["Memory bandwidth", "Memory controller counters", "Not readable by users on ASPIRE-2A"]]
    top = table_caption(s, X0, 1.35, XW, "Each possible bottleneck after Basic, how we measured it and what we found.")
    table(s, X0, top + 0.05, [2.9, 3.9, 5.13], rows, row_heights=[0.58, 0.98, 1.25, 1.25, 0.98], size=18, colors=[None, None, None, None, [INK, INK, NAVY]])
    set_notes(s, PLAN_NOTES[11])
    return s


# The placement experiment of #61 on 4 nodes, drawn plainly (the user, 11/02: CPU and memory named, the halves easy to see):
# per node 16 CPU blocks, each the 8 cores that share an L3, filled in navy as far as their cores run ranks, and 16 memory
# channels, green where in use, 8 of each per CPU. spread64 runs 4 ranks on every L3; packed64 fills the first two NUMA domains of each
# CPU (L3s 0-3 and 8-11; TASK #61: local rank l on CPU (l / 32) × 64 + l % 32) and so uses only their 8 channels.
FIRST_HALVES = [1.0 if k % 8 < 4 else 0.0 for k in range(16)]
PLACEMENT_ROWS = [(("128 ranks", "16 channels"), [1.0] * 16, [1.0] * 16, "2.920 s/step", "STREAM 274 GB/s", None), (("64 ranks", "16 channels"), [0.5] * 16, [1.0] * 16, "2.887 s/step", "STREAM 279 GB/s", 0), (("64 ranks", "8 channels"), FIRST_HALVES, FIRST_HALVES, "6.347 s/step", "STREAM 125 GB/s", 1)]


def usage_bar(s, x, y, w, h, label, fill, color):
    """A label and a row of 16 blocks, 8 per CPU in its 4 NUMA domains of 2, with a gap between NUMA domains and a wider one
    between the CPUs (the user, 11/02); each block is color from the bottom up to fill[k] (0 to 1) and grey above it."""
    add_text(s, x, y, 1.15, h, [label], size=17, anchor="m")
    x0, gap, numa_gap, cpu_gap = x + 1.2, 0.035, 0.12, 0.28
    cell = (w - 1.2 - 8 * gap - 6 * numa_gap - cpu_gap) / 16
    for k, f in enumerate(fill):
        numa, cpu = k // 2, k // 8
        cx = x0 + k * cell + (k + 1) // 2 * gap + (numa - cpu) * numa_gap + cpu * cpu_gap
        box(s, cx, y, cell, h, fill=OFF, radius=0.12)
        if f:
            box(s, cx, y + h * (1 - f), cell, h * f, fill=color, radius=0.12)


def m_memory_limit():
    """No memory-controller counters on ASPIRE-2A, so the placement experiment of #61 stands in: Basic before the mapping,
    4 nodes, every rank pinned, STREAM triad on the same nodes after the solver. Each placement is one node as a row of CPU
    blocks over a row of memory channels, so that the halved resource can be seen (the user, 11/02: simpler than the chips
    of the 8th edition's first build); then the ranks and channels per node, the time and the bandwidth, and arrows between
    the rows. The colours are the user's hand edit (11/02): the cores in navy and the channels in green, what was halved in
    red and the step that took 2.2 times as long in navy; both arrows are black (the user, 11/03)."""
    s = reuse(9)
    set_title(s, "MEASURING THE MEMORY LIMIT")
    pitch, top, bar_w, xc, xr, xa = 1.5, 1.45, 4.95, 5.8, 7.65, 10.45
    for k, (label, cpu, memory, time, bandwidth, halved) in enumerate(PLACEMENT_ROWS):
        y = top + k * pitch
        usage_bar(s, X0, y, bar_w, 0.4, "CPU", cpu, NAVY)
        usage_bar(s, X0, y + 0.52, bar_w, 0.4, "Memory", memory, MEMORY)
        for i, (line, yy) in enumerate(zip(label, (y, y + 0.52))):
            add_text(s, xc, yy, xr - xc - 0.1, 0.4, [line], size=17, color=HALVED if i == halved else INK, anchor="m")
        add_text(s, xr, y - 0.02, xa - xr - 0.15, 0.5, [time], size=23, color=NAVY if k == 2 else INK, anchor="m")
        add_text(s, xr, y + 0.5, xa - xr - 0.15, 0.42, [bandwidth], size=16, color=NAVY if k == 2 else INK, anchor="m")
    for k, (cause, effect) in enumerate((("Half the cores", "the same time"), ("Half the channels", "2.2 times the time"))):
        y1, y2 = top + k * pitch + 0.46, top + (k + 1) * pitch + 0.46
        arrow_line(s, xa, y1, xa, y2 - 0.05, color=INK, width=2.25)
        add_text(s, xa + 0.15, (y1 + y2) / 2 - 0.4, 12.63 - xa - 0.15, 0.8, [{"runs": [cause], "color": HALVED}, {"runs": [effect], "color": NAVY if k else INK}], size=15, anchor="m")
    bottom = top + 3 * pitch - 0.35
    caption(s, X0, bottom, XW, "One node under each placement, with the cores that run ranks in navy and the channels in use in green.", h=0.4)
    add_text(s, X0, bottom + 0.6, XW, 0.8, ["A step slowed as much as the bandwidth fell, so about 97% of it follows the memory bandwidth."], size=19)
    set_notes(s, PLAN_NOTES[12])
    return s


def m_bonus_decomposition():
    """The multiLevel decomposition on a slide of its own (the user, 11/02): Basic's mapping and multiLevel side by side in
    decomposeParDict's own words (the user's second round, 11/02), what each gains against plain scotch, and the pictures of
    the two coloured by node and NUMA domain, Basic's drawn on Genkai (the user, 11/02: put it on the slide) over the key to
    their colours. multiLevel's domains are (2 4 16) on 1 node and (2 2 4 16) on 2. Faces from the decomposePar logs (#42 for
    multiLevel against plain scotch, REPORT §6.3 for the mapping); times against plain scotch in alternated runs (#42,
    4 v 4; #63, 5 v 5)."""
    s = reuse(10)
    set_title(s, "MULTILEVEL DECOMPOSITION")
    w, cw = 6.2, 3.0
    for x, title, lines in ((X0, "Basic, one scotch run", ["method  scotch;", "scotchCoeffs", "{", "    domains  (2 4 16);", "    // and its weights", "}"]), (X0 + cw + 0.2, "Bonus, scotch per level", ["method  multiLevel;", "multiLevelCoeffs", "{", "    method   scotch;", "    domains  (4 2 4 16);", "}"])):
        heading(s, x, 1.3, cw, title, size=16)
        bottom = code(s, x, 1.72, cw, lines)
    top = table_caption(s, X0, bottom + 0.3, w, "Each against plain scotch on 4 nodes.")
    rows = [["", "Basic", "multiLevel"], ["Faces between nodes", "−22.7%", "−38.3%"], ["Faces between sockets", "−21.3%", "−33.5%"], ["Faces between NUMA domains", "−10.4%", "−25.7%"], ["Time per step", "−0.7%", "−1.5%"]]
    table(s, X0, top + 0.05, [3.15, 1.3, 1.75], rows, row_heights=[0.45, 0.47, 0.47, 0.72, 0.47], size=17, aligns=["l", "r", "r"], colors=[None, None, None, None, [INK, INK, NAVY]])
    pw, xr = 2.62, 12.63 - 2 * 2.62 - 0.15
    # the domains in the heading and its wider box are the user's hand edit (11/02), with multiLevel spelt as OpenFOAM does
    for i, (which, label) in enumerate((("basic", "scotch (2 4 16)"), ("multi", "multiLevel (4 2 4 16)"))):
        x = xr + i * (pw + 0.15)
        add_text(s, x - 0.15, 1.3, pw + 0.18, 0.42, [label], size=18, color=NAVY, align="c")
        panel = decomp_panel(s, which, x, 1.72, w=pw)
    bottom = numa_key(s, xr, 1.72 + panel.height / EMU + 0.1, 2 * pw + 0.15)
    caption(s, xr, bottom + 0.12, 2 * pw + 0.15, "The subdomains on the car, the centre plane and a cross-section, one hue per node and one shade per NUMA domain.", h=0.8)
    set_notes(s, PLAN_NOTES[13])
    return s


# The 14 source changes by what they remove (the user, 11/02: the list on two slides, grouped by intent). Each is (patch,
# what it removes, its change in time per step on 4 nodes against the configuration before it); patches measured together
# share one value, written once for the rows that stand next to each other (bonus/README.md, data/changes_ab.csv).
CHANGES_BY_INTENT = [
    ("Fewer passes over the data", [("0002", "One pass over the matrix of U for all three components", "−2.3%"), ("0004", "Face values computed in the sums, no temporary fields", "−2.8%"), ("0006", "Laplacian coefficients and diagonal in one face loop", "−2.0% with 0008, 0010"), ("0009", "The viscous stress in one loop instead of three passes", None), ("0013", "The turbulence model in 13 instead of 80 cell passes", "−2.5% with 0014"), ("0015", "GAMG correction and restriction done in place", None), ("0016", "Gauss–Seidel residual taken from the last sweep", "−3.8%")]),
    ("No copies or zero fills", [("0001", "The solvers' residual written in place, not copied", "−3.4%"), ("0011", "No copy of the source in every Gauss–Seidel sweep", "−1.0%"), ("0014", "No zeroing of overwritten coefficients, no U matrix copy", "−2.5% with 0013, 0015")]),
    ("No values that nobody reads", [("0003", "Six callers skip boundary values they would throw away", "−1.3%"), ("0008", "Pressure reference decided once, not checked every step", "−2.0% with 0006, 0009"), ("0010", "Wall shear stress computed on the walls only", None)]),
    ("Fewer global sums", [("0012", "One global sum per CG iteration instead of three", "−0.3%")]),
]


def changes_table(s, y, groups, row_h=0.47):
    """The source changes of some intents as one table: a navy row naming each intent, then its patches, one line each."""
    rows, colors, fills, intents, merges = [["Patch", "What it removes", "4 nodes"]], [None], [None], [], []
    for intent, patches in groups:
        intents.append(len(rows))
        rows.append([intent, "", ""])
        colors.append([NAVY] * 3)
        fills.append([LIGHT] * 3)
        for patch, what, gain in patches:
            if gain is None:
                merges.append(len(rows) - 1)
            rows.append([patch, what, gain or ""])
            colors.append([BONUS, INK, INK])
            fills.append(None)
    frame = table(s, X0, y, [0.85, 7.98, 3.1], rows, row_h=row_h, size=16, aligns=["l", "l", "r"], colors=colors, fills=fills)
    for i in intents:
        frame.table.cell(i, 0).merge(frame.table.cell(i, 2))
    for i in merges:
        merge_down(frame, 2, i, i + 1)
    return y + row_h * len(rows)


def m_changes(part):
    """Source changes by intent, (1/2) the passes removed and (2/2) the rest."""
    s = main_slide((38, 39)[part])
    set_title(s, f"SOURCE CHANGES BY INTENT ({part + 1}/2)")
    groups = CHANGES_BY_INTENT[:1] if part == 0 else CHANGES_BY_INTENT[1:]
    text = "The changes that remove passes over the data, with their change per step on 4 nodes." if part == 0 else "The other changes by what they remove, with their change per step on 4 nodes."
    top = table_caption(s, X0, 1.3, XW, text)
    bottom = changes_table(s, top + 0.05, groups, row_h=0.5 if part == 0 else 0.44)
    if part == 0:
        add_text(s, X0, bottom + 0.3, XW, 0.5, ["No change alters the iterations, the convergence tests or the discretisation."], size=19)
    set_notes(s, PLAN_NOTES[14 + part])
    return s


def u_diagram(s, x, y, w=5.6):
    """0002: the three components of U share one matrix, so one pass over it updates all three."""
    bw = (w - 0.6) / 2
    add_text(s, x, y, w, 0.36, ["Before, one pass per component"], size=16)
    for k, component in enumerate(("Ux", "Uy", "Uz")):
        yy = y + 0.42 + k * 0.52
        shape_text(box(s, x, yy, bw, 0.42, fill=LIGHT, line=LINE, radius=0.12), "matrix of U", size=15, color=NAVY)
        arrow_line(s, x + bw + 0.06, yy + 0.21, x + bw + 0.54, yy + 0.21, color=INK)
        shape_text(box(s, x + bw + 0.6, yy, bw, 0.42, fill=BONUS_TINT, line=BONUS_LINE, radius=0.12), f"sweep {component}", size=15, color=INK)
    add_text(s, x, y + 1.98, w, 0.36, ["the matrix is read 3 times"], size=16, align="c")
    add_text(s, x, y + 2.5, w, 0.36, ["After, one pass for all three"], size=16)
    shape_text(box(s, x, y + 2.92, bw, 1.0, fill=LIGHT, line=LINE, radius=0.08), "matrix of U", size=15, color=NAVY)
    arrow_line(s, x + bw + 0.06, y + 3.42, x + bw + 0.54, y + 3.42, color=INK)
    shape_text(box(s, x + bw + 0.6, y + 2.92, bw, 1.0, fill=BONUS_TINT, line=BONUS_LINE, radius=0.08), ["sweep Ux", "sweep Uy", "sweep Uz"], size=15, color=INK)
    add_text(s, x, y + 3.98, w, 0.36, ["the matrix is read once"], size=16, color=NAVY, align="c")
    return y + 4.34


def residual_diagram(s, x, y, w=5.6):
    """0001: smoothSolver formed each residual b − Aψ in a new field and copied it; now it writes it in place."""
    bw = (w - 2 * 0.5) / 3
    add_text(s, x, y, w, 0.36, ["Before, a new field and a copy"], size=16)
    for k, (text, fill, line) in enumerate((("matrix, ψ and b", LIGHT, LINE), ("new field", BONUS_TINT, BONUS_LINE), ("residual r", BONUS_TINT, BONUS_LINE))):
        bx = x + k * (bw + 0.5)
        shape_text(box(s, bx, y + 0.5, bw, 0.9, fill=fill, line=line, radius=0.1), text, size=15, color=NAVY if k == 0 else INK)
        if k:
            arrow_line(s, bx - 0.44, y + 0.95, bx - 0.06, y + 0.95, color=INK)
            add_text(s, bx - 0.75, y + 1.45, 1.0, 0.3, [("b − Aψ", "copy")[k - 1]], size=13, align="c")
    add_text(s, x, y + 1.98, w, 0.36, ["the residual is written twice"], size=16, align="c")
    add_text(s, x, y + 2.5, w, 0.36, ["After, in place"], size=16)
    for k, (text, fill, line) in enumerate((("matrix, ψ and b", LIGHT, LINE), ("residual r", BONUS_TINT, BONUS_LINE))):
        bx = x + k * 2 * (bw + 0.5)
        shape_text(box(s, bx, y + 2.97, bw, 0.9, fill=fill, line=line, radius=0.1), text, size=15, color=NAVY if k == 0 else INK)
    arrow_line(s, x + bw + 0.06, y + 3.42, x + 2 * (bw + 0.5) - 0.06, y + 3.42, color=INK)
    add_text(s, x + bw, y + 3.47, bw + 1.0, 0.3, ["b − Aψ"], size=13, align="c")
    add_text(s, x, y + 3.98, w, 0.36, ["the residual is written once"], size=16, color=NAVY, align="c")
    return y + 4.34


def m_examples():
    """Two source changes drawn side by side (the user, 11/02: like the example of U, left and right): 0002 removes passes
    over a matrix and 0001 a copy, two of the four intents, each measured on its own. A thin black line divides the two at
    the middle of the slide, as the user drew it (11/02)."""
    s = main_slide(40)
    set_title(s, "TWO SOURCE CHANGES IN PICTURES")
    arrow_line(s, 6.667, 1.01, 6.667, 7.34, color=INK, width=0.5, head=False)
    for x, title, gain, draw, text in ((X0, "0002 U components in one pass", "−2.3% per step on 4 nodes, −6.4% on 1 node", u_diagram, "The three components of U share one matrix, so one pass over it can update all three."), (7.03, "0001 No copies in the solvers", "−3.4% per step on 4 nodes, −2.2% on 1 node", residual_diagram, "The residual is written straight into its field instead of into a new field that is then copied.")):
        heading(s, x, 1.3, 5.6, title, size=18)
        add_text(s, x, 1.7, 5.6, 0.36, [gain], size=16)
        bottom = draw(s, x, 2.15)
        caption(s, x, bottom + 0.08, 5.6, text, h=0.5)
    set_notes(s, PLAN_NOTES[16])
    return s


def m_bonus_results():
    """The Bonus against the official runs, our Baseline and Basic (the user, 11/02), and each Bonus step against its own
    control in a table instead of the counters, which went to the supporting slides."""
    s = reuse(11)
    set_title(s, "BONUS RESULTS")
    top = table_caption(s, X0, 1.3, 5.75, "Each Bonus step against its control on 4 nodes.")
    rows = [["Step", "s/step", "Change"], ["multiLevel instead of plain scotch", "2.918 → 2.873", "−1.5%"], ["First four source changes", "2.873 → 2.599", "−9.5%"], ["Ten more source changes", "2.603 → 2.360", "−9.3%"], ["Bonus against Basic", "2.898 → 2.360", "−18.6%"]]
    table(s, X0, top + 0.05, [2.35, 2.2, 1.2], rows, row_heights=[0.47, 0.72, 0.72, 0.72, 0.72], size=16, aligns=["l", "r", "r"], colors=[None, None, None, None, [BONUS, NAVY, NAVY]])
    bullets(s, X0, top + 3.6, 5.75, 6.95 - top - 3.6, ["Cd stayed within 0.0005% of the unmodified code at 1, 2 and 4 nodes."], size=18)
    figure(s, "p15_bonus", 6.63, 1.3, 6.0, "Each job of the official runs and our three tiers on 4 nodes, with the mean and SD of each.")
    set_notes(s, PLAN_NOTES[17])
    return s


TIER_COLOURS = {"Baseline": BASE, "Basic": BASIC, "Bonus": BONUS}


def m_scaling():
    """The scaling plot alone, as tall as the slide allows (the user, 11/03: the table of speedups under it made the slide
    busy), with the official runs beside our three tiers at each node count (the user, 11/01). Over it, as slide shapes the
    user can move by hand, how many times faster than on 1 node each of our tiers is at 2 and 4 nodes, over its label
    (instead of the efficiency, the user, 11/02), and why that passes 4 on 4 nodes, in the empty part over the 4-node jobs.
    deck_plots.py gives the speedups and those places in p17_scaling.json; the official runs' speedups (4.30 and 3.93 on 4
    nodes) are in the notes only."""
    s = reuse(12)
    set_title(s, "SCALING FROM 1 TO 4 NODES")
    x, y, w = X0 - 0.1, 1.25, XW + 0.1
    figure(s, "p17_scaling", x, y, w, "Each job on 1, 2 and 4 nodes on one axis from 0, with the dashes for ideal scaling and the numbers for times faster than on 1 node.", h=0.62)
    plot = json.loads((FIG / "p17_scaling.json").read_text(encoding="utf-8"))
    h = w * plot["size"][1] / plot["size"][0]

    def on_slide(fx, fy):
        """A point of the plot, given in figure fractions from its bottom left, on the slide."""
        return x + fx * w, y + (1 - fy) * h

    number_h = 0.42
    for key, mark in plot["marks"].items():
        cx, top = on_slide(mark["x"], mark["top"])
        add_text(s, cx - 0.55, top - number_h, 1.1, number_h, [f"{mark['speedup']:.2f}×"], size=17, color=TIER_COLOURS[key.split()[0]], align="c", anchor="b")
    (left, floor), (right, ceiling) = on_slide(*plot["free"][:2]), on_slide(*plot["free"][2:])
    add_text(s, left, ceiling + 0.1, right - left, floor - number_h - 0.15 - ceiling - 0.1, ["Over 4 times on 4 nodes because each rank's arrays fit in the L3 cache."], size=18, line=1.05, anchor="b")
    set_notes(s, PLAN_NOTES[18])
    return s


def m_not_helped_bonus():
    """Every Bonus idea we tried and did not keep, with its result in words and the striking ones in navy, and what limits
    a step now (the user, 11/02). Data: #33, #35, #37, #45, #49, #69, bonus/README.md."""
    s = reuse(14)
    set_title(s, "WHAT DID NOT HELP IN THE BONUS")
    top = table_caption(s, X0, 1.3, XW, "Each Bonus idea we tried and did not keep, with its time per step against its control on 4 nodes.")
    rows = [["Idea", "Time per step"], ["Cell weights to balance the faces in scotch or multiLevel", "2.2% to 6.5% slower"], ["METIS balancing both cells and faces", "1.5% slower"], ["GAMG coarsest level gathered on one rank", "5.0% slower"], ["The same on one rank per node or per NUMA domain", "1.0% slower or 0.3% faster"], ["UCX over RC between nodes", "0.2% faster, within the spread"], ["Gauss–Seidel overlapped with its halo exchange", "8.3% slower and Cd 1.2% lower"], ["bound() averaging only the bounded cells", "not run, one more global sum"]]
    striking = {1, 2, 3, 6}
    table(s, X0, top + 0.05, [7.2, 4.73], rows, row_h=0.45, size=16, colors=[None] + [[NAVY, NAVY] if i in striking else None for i in range(1, len(rows))])
    bullets(s, X0, top + 0.05 + 0.45 * len(rows) + 0.15, XW, 1.3, ["Balancing the faces unbalanced the cells, and fewer ranks in the global sums did not shorten the wait.", [("Now a step is limited by memory traffic and by the ranks that read the most from DRAM.", {"color": NAVY})]], size=18, space_after=6)
    set_notes(s, PLAN_NOTES[19])
    return s


# ====================================================================== supporting slides
def supp(i, title, notes_key):
    """Supporting slide on input slide i + 1, hidden from the slide show like the rest of the supporting part (five of them
    sit on slides that were shown in the input)."""
    s = reuse(i)
    s._element.set("show", "0")
    set_title(s, title)
    set_notes(s, NOTES[notes_key])
    return s


def label_value_table(s, x, y, col_w, rows, row_h=0.6, size=16):
    return table(s, x, y, col_w, rows, row_h=row_h, size=size, header=False, colors=[[NAVY, None]] * len(rows))


def s_aspire():
    s = supp(16, "ASPIRE-2A AND WHY WE CHOSE IT", "s_aspire")
    table_caption(s, X0, 1.35, 6.95, "The hardware and software of one ASPIRE-2A node.")
    rows = [["Processor", "2 × AMD EPYC 7713 (Zen 3) with 128 cores at 2.0 GHz"], ["NUMA and cache", "8 NUMA domains of 16 cores and 32 MB of L3 per 8 cores"], ["Memory", "512 GB DDR4-3200 on 16 channels and about 290 GB/s by STREAM"], ["Network", "HPE Slingshot-10 at 100 Gb/s in a dragonfly"], ["Software", "Cray PE with GCC 11.2, Cray MPICH 8.1.15 and PBS Pro"]]
    label_value_table(s, X0, 1.85, [1.95, 5.0], rows, row_h=1.06, size=17)
    xr = 8.0
    heading(s, xr, 1.35, 4.63, "Why ASPIRE-2A")
    bullets(s, xr, 1.9, 4.63, 5.0, ["Last year we competed on Gadi, so this year we wanted to learn the other machine.", "OpenFOAM uses very many files, and one build alone is about 36,000 files.", "Our Gadi project allowed 0.2 M files and 1 TB, and ASPIRE-2A allows 200 M files and 100 TB."], size=18, space_after=22)
    return s


def s_settings():
    s = supp(17, "BUILD, MPI AND RUN SETTINGS", "s_settings")
    rows = [["Build", "Official v2512 source with GCC 11.2 -O3 and AMD AOCL-LibM, as fast as the site module (−0.08%)"], ["MPI", "Cray MPICH 8.1.15 over UCX, because the default OFI crashed at MPI_Finalize on 2 and 4 nodes"], ["OFI with workarounds", "No crash and the same Cd, but 0.77% slower than UCX in 3 alternated jobs each"], ["Decomposition", "Baseline hierarchical (16 8 4), Basic scotch mapped onto the node, Bonus multiLevel (4 2 4 16)"], ["Placement", "128 ranks per node, numactl for the memory and a watcher that re-pins each rank with taskset"], ["Storage", "Each node solves from its own copy of the case in $TMPDIR, and file I/O is about 0.01% of a step"], ["Measurement", "The official metric over steps 2 to N, at least 3 jobs per condition, profilers only in separate runs"]]
    top = table_caption(s, X0, 1.35, XW, "How we built, ran and measured OpenFOAM on ASPIRE-2A.")
    label_value_table(s, X0, top + 0.08, [2.9, 9.03], rows, row_h=0.72, size=16)
    return s


def s_noise():
    s = supp(18, "RUN-TO-RUN VARIATION OVER 92 JOBS", "s_noise")
    figure(s, "fig08_variability", 0.45, 1.35, 8.85, "Each of the 92 jobs against the median of its configuration, 21 September to 5 October.")
    bullets(s, 9.55, 1.5, 3.08, 5.4, ["92 jobs in 29 repeated configurations.", "Most jobs lie within 0.4% of their configuration's median.", "Two September jobs were 84% and 91% slower.", "So we never decide from one job, and we alternate candidate and control."], size=17, space_after=18, anchor="m")
    return s


def s_reference():
    s = supp(19, "THE ORGANISERS' REFERENCE", "s_reference")
    bottom = figure(s, "ps_reference", X0, 1.3, XW, "Each job of the organisers' runs and of ours on the same machine, with the mean and SD of each group.", h=0.4)
    bullets(s, X0, bottom + 0.1, XW, 6.95 - bottom - 0.1, ["The percentages compare our means with the mean of the organisers' scotch jobs.", "The organisers used the site module and default MPI settings without binding, and their scotch jobs spread by 12% on 4 nodes.", "Build, MPI transport and placement all differ, so the gap has more than one cause."], size=15, space_after=6)
    return s


def s_repro():
    s = supp(20, "REPRODUCING OUR RESULTS", "s_repro")
    table_caption(s, X0, 1.35, XW, "Re-runs with the submitted scripts against our recorded means.")
    rows = [["Configuration", "Nodes", "Re-run, s/step", "Recorded, s/step", "Change", "coefficient.dat"],["Basic", "1", "13.413150", "13.364504", "+0.36%", "identical"], ["Basic", "2", "6.390324", "6.371748", "+0.29%", "identical"], ["Basic", "4", "2.904620", "2.897638", "+0.24%", "identical"], ["Bonus", "1", "10.201813", "10.233606", "−0.31%", "identical"], ["Bonus", "2", "4.980185", "4.992196", "−0.24%", "identical"], ["Bonus", "4", "2.365118", "2.359976", "+0.22%", "identical"]]
    table(s, X0, 1.85, [2.75, 0.95, 2.2, 2.25, 1.5, 2.28], rows, row_h=0.6, size=15, colors=[None] + [[BASIC, INK, INK, INK, INK, INK]] * 3 + [[BONUS, INK, INK, INK, INK, INK]] * 3, aligns=["l", "c", "r", "r", "r", "c"])
    bullets(s, X0, 6.15, XW, 0.85, ["build/build.pbs builds from the official public sources and run/submit.sh 1|2|4 runs the whole Allrun chain with plain qsub.", "Every step ended with End and returned 0, and every solve job reported bound=128/128 on every node."], size=14, space_after=4)
    return s


def s_network():
    s = supp(23, "IS THE NETWORK THE BOTTLENECK?", "s_network")
    table_caption(s, X0, 1.35, XW, "Four changes to the network side on 4 nodes and what each did to a step.")
    rows = [["What we changed on the network side", "How much the network side changed", "Step time (4 nodes)"], ["UCX over RC instead of UD between nodes", "IMB bandwidth (1 MiB Sendrecv) 6.7 → 10.4 GB/s, +55%", "−0.01% Basic, −0.16% Bonus of four changes (4 v 4)"], ["Rank reordering, hierarchical decomposition", "92% fewer faces between nodes", "+0.1%"], ["OFI instead of UCX, with the organisers' two workarounds", "Another transport and provider", "+0.77% (3 v 3), +0.50% (1 v 1)"], ["GAMG coarsest level solved on 32 ranks instead of 512", "Fewer ranks in 81% of the global sums", "−0.25% (1 v 1)"]]
    table(s, X0, 1.85, [4.3, 4.3, 3.33], rows, row_h=0.75, size=15)
    bullets(s, X0, 5.75, XW, 1.2, ["One 8-byte global sum over 512 ranks takes about 12 µs (IMB), so 1,600 per step take about 0.02 s.", "A rank's MPI_Waitall follows its own computation (R² 0.77), and 13 of the 16 slowest ranks have no neighbours on other nodes.", "We did not read NIC or switch counters."], size=14, space_after=4)
    return s


def s_pinning_case_default():
    """Pinning on the Baseline's own decomposition, alternated with the same setting unpinned (#36), next to our Baseline's
    jobs (#62): the main pinning slide of the 8th edition's first build, which the user asked for (11/02) before preferring
    the four placements on scotch in the main part."""
    s = supp(41, "PINNING WITH HIERARCHICAL", "s_pinning_case_default")
    top = table_caption(s, X0, 1.3, 5.75, "Time per step on 4 nodes with the case-default hierarchical decomposition.", h=0.7)
    rows = [["Run", "s/step", "SD"], ["Our Baseline", "3.650", "4.1%"], ["Not pinned", "3.670", "2.0%"], ["Pinned", "3.257", "1.1%"]]
    table(s, X0, top + 0.05, [2.95, 1.45, 1.35], rows, row_h=0.55, size=18, aligns=["l", "r", "r"], colors=[None, [BASE, INK, INK], None, [NAVY] * 3])
    bullets(s, X0, top + 2.5, 5.75, 6.95 - top - 2.5, ["Not pinned and pinned ran in turns in the same period.", "Pinning took 11.2% off a step and its SD fell from 2.0% to 1.1%.", "Our Baseline ran the unpinned setting later."], size=18, space_after=14)
    figure(s, "ps_pinning", 6.73, 1.3, 5.9, "Each job of our Baseline and of its setting without and with pinning on 4 nodes.")
    return s


def s_decompositions():
    """Every decomposition we measured on 4 nodes, each against its own control (the user asked whether we tried other
    methods, 11/02). Sources in the notes."""
    s = supp(42, "DECOMPOSITIONS WE TRIED", "s_decompositions")
    rows = [["Decomposition (tier)", "Against", "Time per step on 4 nodes"], ["hierarchical (4 8 16) in the order zyx (Basic)", "the case default", "0.4% slower (1 job)"], ["hierarchical with rank reordering (Basic)", "without reordering", "0.1% slower (3 v 3)"], ["scotch (Basic, kept)", "hierarchical", "10.5% faster (3 v 3)"], ["scotch mapped onto the node (Basic, kept)", "plain scotch", "0.7% faster (5 v 5)"], ["scotch with a quality strategy (Basic)", "the mapped scotch", "no gain (1 job)"], ["multiLevel (4 128) (Bonus)", "plain scotch", "1.1% faster (2 v 2)"], ["multiLevel (4 2 4 16) (Bonus, kept)", "plain scotch", "1.5% faster (4 v 4)"], ["multiLevel (4 2 8 8) (Bonus)", "multiLevel (4 2 4 16)", "0.7% slower (1 v 1, 40 steps)"], ["multiLevel with weights by point share, × 2 and × 12 (Bonus)", "the same with 0001", "2.2% and 6.1% slower (1 v 4)"], ["multiLevel with weight 3 on wheel and underbody cells (Bonus)", "multiLevel", "11% and 64% slower, Cd −2.6%"], ["scotch with weight 2 on boundary cells (Bonus)", "plain scotch", "6.5% slower (3 v 6)"], ["METIS with two constraints, cells and faces (Bonus)", "multiLevel with 0001", "1.5% slower (2 v 3)"], ["kahip, METIS and ptscotch alone", "", "not run, the build had stub libraries"]]
    top = table_caption(s, X0, 1.25, XW, "Every decomposition we measured, each against its own control on 4 nodes.")
    table(s, X0, top + 0.04, [5.6, 2.55, 3.78], rows, row_h=0.36, size=12.5, colors=[None, None, None, [BASIC, INK, INK], [BASIC, INK, INK], None, None, [BONUS, INK, INK], None, None, None, None, None, None], margins=(0.08, 0.02, 0.08, 0.02))
    return s


def s_scotch():
    s = supp(24, "HIERARCHICAL AGAINST SCOTCH", "s_scotch")
    bottom = figure(s, "p11_scotch", X0, 1.3, XW, "Each job of hierarchical and scotch on 1, 2 and 4 nodes with the same placement, with the mean and SD of each.", h=0.4)
    bullets(s, X0, bottom + 0.2, XW, 0.9, ["scotch was faster at every node count and gained more on more nodes, which we have not explained."], size=18)
    return s


def s_cores():
    s = supp(25, "THE PLACEMENT EXPERIMENT IN FULL", "s_cores")
    table_caption(s, X0, 1.35, XW, "Time per step under three placements on 4 nodes, with 2 jobs each.")
    rows = [["s/step (4 nodes, 2 jobs each)", "full128", "spread64", "packed64", "spread64 / full128", "packed64 / spread64"], ["Basic (before the mapping)", "2.920", "2.887", "6.347", "0.99", "2.20"], ["Bonus without the patches", "2.869", "2.874", "6.321", "1.00", "2.20"], ["Bonus, first four changes", "2.595", "2.649", "5.598", "1.02", "2.11"], ["Triad bandwidth per node", "274 GB/s", "279 GB/s", "125 GB/s", "—", "0.45"]]
    table(s, X0, 1.85, [3.5, 1.45, 1.5, 1.5, 1.95, 2.03], rows, row_h=0.62, size=15, colors=[None] + [[INK, INK, INK, INK, INK, NAVY]] * 4, aligns=["l", "r", "r", "r", "r", "r"])
    heading(s, X0, 5.0, 5.85, "The three placements", size=15)
    bullets(s, X0, 5.4, 5.85, 1.55, ["full128 has 128 ranks per node, as submitted.", "spread64 has 64 ranks per node, 4 per L3, on all 16 L3s and all 16 memory channels.", "packed64 has the same 64 ranks and decomposition, 8 per L3, on 8 L3s and 8 channels."], size=14, space_after=4)
    heading(s, 6.78, 5.0, 5.85, "What it shows", size=15)
    bullets(s, 6.78, 5.4, 5.85, 1.55, ["Half the cores changed a step by 0.99 to 1.02 times.", "Half the channels made a step 2.11 to 2.20 times slower as the triad bandwidth fell 2.22 times.", "packed64 also halves the L3, so DRAM bandwidth and L3 capacity are not separated."], size=14, space_after=4)
    return s


def s_callstack():
    """The CrayPAT stack samples of the Bonus with the first four changes (#53), by phase of the step, each split into
    computation and MPI; data/callstack_phases_fa4f5b0.csv from research/profile-reaggregation-fa4f5b0/summary.md."""
    s = supp(26, "WHERE A BONUS STEP GOES", "s_callstack")
    with open(DATA / "callstack_phases_fa4f5b0.csv", encoding="utf-8") as f:
        rows = [(row["phase"], int(row["samples"]), int(row["mpi_samples"])) for row in csv.DictReader(f)]
    total = sum(samples for _, samples, _ in rows)
    phases = [row for row in rows if row[1] / total >= 0.03]
    rest = [row for row in rows if row[1] / total < 0.03]
    phases.append(("other", sum(r[1] for r in rest), sum(r[2] for r in rest)))
    phases.reverse()  # a bar chart draws its first category at the bottom
    bar_chart(s, 0.5, 1.3, 7.9, 4.9, [name for name, _, _ in phases], [("computation", [round((n - m) / total * 100, 1) for _, n, m in phases]), ("MPI", [round(m / total * 100, 1) for _, _, m in phases])], colors=[COMPUTATION, MPI], stacked=True, number_format='0.0"%"', label_format='[<2]"";0.0"%"', vmin=0, vmax=35, font_size=15, label_size=14, gap=45, overlap=100, legend=XL_LEGEND_POSITION.BOTTOM, value_axis=False, gridlines=False, label_pos="ctr")
    caption(s, 0.7, 6.3, 7.7, "Share of the 2,396 call-stack samples by phase of a step, split into computation and MPI.")
    bullets(s, 8.7, 1.5, 3.93, 5.4, ["The samples came from 48 of the 512 ranks on 4 nodes, with the first four changes.", "The k-ω SST correction, the Gauss–Seidel sweeps and the global sums of the coarsest CG led us to the ten later changes.", "Stack samples count MPI about 1.8 times higher than CrayPAT's timers."], size=17, space_after=20, anchor="m")
    return s


def s_flame():
    """The same 2,396 samples as a flame graph (deck_plots.flame) from data/callstack_folded_fa4f5b0.txt, which
    research/profile-reaggregation-fa4f5b0/analyse.py writes from the raw samples (Actions 37529785072, profile-raw.tar.zst)."""
    s = supp(35, "CALL STACKS OF A BONUS STEP", "s_flame")
    bottom = figure(s, "ps_flame", X0, 1.3, XW, "The 2,396 samples as a flame graph, each box a function as wide as its share of them.", h=0.4)
    bullets(s, X0, bottom + 0.1, XW, 6.95 - bottom - 0.1, ["A box's callees sit on top of it, and each MPI call (purple) holds the MPI library's own functions.", "The widest towers are GAMG for p (31.4%), the k-ω SST correction (26.9%) and Gauss–Seidel for U (19.0%).", "GAMG's coarsest level took 6.6% of the samples and nearly all of it was in MPI."], size=14, space_after=6)
    return s


def s_changes():
    s = supp(27, "SOURCE CHANGES IN DETAIL (1/2)", "s_changes")
    table_caption(s, X0, 1.35, XW, "The first four patches, which are in full in bonus/patches/ of the submission.")
    rows = [["Change (patch)", "What it removes", "Why the result is the same"], ["No copies in the solvers (0001)", "smoothSolver built each residual in a new field and copied it; GAMG copied the source, then subtracted", "The same function computes the same residual in place; source − A·psi is the same subtraction per cell"], ["U components in one pass (0002)", "Gauss–Seidel read the shared matrix of U three times, once per component", "The components are independent; each sees the same operations in the same order"], ["No unused boundary updates (0003)", "Six callers built boundary values of a surface integral, exchanged them, and used only the cell values", "The cell values come from the same loop; only values nobody reads are skipped"], ["Fused face loops (0004)", "Interpolated face fields and product fields built before every summation", "The same face expressions, evaluated inside the summation loop in the same face order"]]
    table(s, X0, 1.85, [3.05, 4.5, 4.38], rows, size=14, colors=[None] + [[BONUS, INK, INK]] * 4, row_heights=[0.5, 1.2, 1.2, 1.2, 1.2])
    return s


def s_changes2():
    s = supp(28, "SOURCE CHANGES IN DETAIL (2/2)", "s_changes2")
    table_caption(s, X0, 1.35, XW, "The ten later patches (0006, 0008–0016), where F3 means rounding can change so Cd is checked.")
    f3 = ("F3: ", {"color": NAVY})
    rows = [["Change (patch)", "What it removes", "Why the result is the same"], ["Laplacian coefficients with the diagonal (0006)", "A temporary product field, its copy and a re-read of upper", "The same operations per face in the same order"], ["Pressure reference decided once (0008)", "Patch loops and a global sum per step that did nothing here", "The same cells get the same change whenever one is needed"], ["Viscous stress in one pass (0009)", "Three whole-field passes for nuEff · dev2(T(grad U))", "The same operations on the same operands in the same order"], ["Wall shear stress on the walls only (0010)", "A full-volume field of which only the wall values were read", "The same expression on the walls, as the forces object uses"], ["Gauss–Seidel without the source copy (0011)", "A copy of the source into a work array in every sweep", [[f3, ("the same terms, but the source is added last", {})]]], ["One global sum per CG iteration (0012)", "Two of three global sums per iteration on the coarsest level", [[f3, ("the same iterates in exact arithmetic", {})]]], ["Turbulence model in single cell loops (0013)", "67 of the 80 passes over the cells per k-ω SST update", "The same operations in the same association, no new FMAs"], ["No zero fill of overwritten coefficients (0014)", "Zero fills of face coefficients, a copy of the U matrix", "No arithmetic changes"], ["GAMG correction and restriction in place (0015)", "Two passes over the finest level per V-cycle", "The same operations and summation order"], ["Gauss–Seidel residual from the sweep (0016)", "A matrix pass and a halo exchange per component and iteration", [[f3, ("still formed and tested every iteration", {})]]]]
    table(s, X0, 1.85, [3.95, 4.15, 3.83], rows, size=11.5, row_heights=[0.42] + [0.48] * 10, colors=[None] + [[BONUS, INK, INK]] * 10, margins=(0.08, 0.03, 0.08, 0.03))
    return s


def s_each():
    s = supp(29, "EFFECT OF EACH BONUS CHANGE", "s_each")
    figure(s, "ps_each", X0 - 0.05, 1.3, 6.4, "Each job of each Bonus change against the mean of its control on 4 nodes, with the change and SD.", h=0.5)
    table_caption(s, 7.25, 1.3, 5.38, "Change per step on 1, 2 and 4 nodes.")
    rows = [["Change", "1 node", "2 nodes", "4 nodes"], ["multiLevel vs scotch", "−0.45%", "−0.38%", "−1.54%"], ["0001 no copies", "−2.19%", "−2.94%", "−3.39%"], ["0002 U in one pass", "−6.39%", "−4.13%", "−2.29%"], ["0003 no unused values", "−1.40%", "−1.88%", "−1.31%"], ["0004 fused face loops", "−2.88%", "−2.29%", "−2.82%"], ["0006, 0008–0010", "", "", "−1.99%"], ["0011 GS without copy", "", "", "−1.04%"], ["0012 one sum per CG", "", "", "−0.30%"], ["0013–0015 *", "", "", "−2.48%"], ["0016 sweep residual *", "", "", "−3.80%"], ["0006–0016, alternated", "−12.16%", "−11.44%", "−9.34%"]]
    table(s, 7.25, 1.75, [2.26, 1.04, 1.04, 1.04], rows, row_h=0.35, size=11.5, colors=[None] + [[INK, INK, INK, BONUS]] * 10 + [[BONUS] * 4], aligns=["l", "r", "r", "r"], margins=(0.08, 0.02, 0.08, 0.02))
    bullets(s, 7.25, 6.1, 5.38, 0.85, ["4 nodes have 3 to 4 jobs each and * ran a few days after its control. Most 1- and 2-node values are single jobs.", "coefficient.dat is bit-identical for every change but 0011 and 0012, which move Cd by under 0.001% (F3)."], size=11, space_after=2)
    return s


def s_counters():
    s = supp(30, "HARDWARE COUNTERS", "s_counters")
    table_caption(s, X0, 1.35, 6.3, "Counters of the first four changes on 1 node.")
    rows = [["Counter", "Change"], ["Time per step", "−12.3%"], ["Cycles", "−10.8%"], ["Instructions", "−4.1%"], ["L1 data accesses", "−5.8%"], ["L2 accesses including prefetch", "−9.6%"], ["L1 refills from DRAM", "−17.2%"], ["Instructions per cycle", "0.360 → 0.388"]]
    table(s, X0, 1.85, [3.9, 2.4], rows, row_h=0.64, size=17, aligns=["l", "r"], colors=[None, None, None, None, None, None, [INK, NAVY], None])
    xr = 7.5
    table_caption(s, xr, 1.35, 5.13, "Gains by channels and nodes.")
    rows2 = [["Test", "Gain"], ["First four on all 16 channels", "−7.9%"], ["First four on 8 of the 16 channels", "−11.4%"], ["Ten later changes on 4 nodes", "−9.3%"], ["Ten later changes on 2 nodes", "−11.4%"], ["Ten later changes on 1 node", "−12.2%"]]
    table(s, xr, 1.85, [3.75, 1.38], rows2, row_h=0.64, size=17, aligns=["l", "r"])
    bullets(s, xr, 5.95, 5.13, 1.0, ["These are demand refills of L1, not DRAM bytes, because users cannot read the memory controller counters."], size=15)
    return s


def s_cd_iterations():
    s = supp(31, "DRAG COEFFICIENT OVER THE ITERATIONS", "s_cd_iterations")
    bottom = figure(s, "ps_cd_iterations", X0, 1.3, XW, "Cd at every iteration of the 4-node runs, where every job of a configuration gives the same Cd.", h=0.4)
    bullets(s, X0, bottom + 0.1, XW, 6.95 - bottom - 0.1, ["The Bonus and the same decomposition without its source changes lie on top of each other and end 0.0004% apart.", "Different decompositions end up to 7% apart after 150 iterations, as the organisers' notes also show."], size=15, space_after=8)
    return s


def s_cd():
    s = supp(32, "DRAG COEFFICIENT CHECKS", "s_cd")
    table_caption(s, X0, 1.35, XW, "Cd at the last step on 1, 2 and 4 nodes.")
    rows = [["Steps", "OHC-1 values", ["Baseline", "(hierarchical)"], ["scotch", "defaults"], ["Basic", "(mapped scotch)"], ["Bonus", "(multiLevel)"]], ["40", "0.433 – 0.436", "0.43305", "0.43599", "0.43958", "0.43828"], ["80", "0.334 – 0.345", "0.33733", "0.32714", "0.33410", "0.32286"], ["150", "0.284 – 0.292", "0.27356", "0.28405", "0.29302", "0.29139"]]
    table(s, X0, 1.85, [1.0, 2.0, 2.45, 1.95, 2.35, 2.18], rows, row_h=0.7, size=16, row_heights=[0.8, 0.65, 0.65, 0.65], colors=[None] + [[INK, INK, BASE, INK, BASIC, BONUS]] * 3, aligns=["c"] * 6)
    bullets(s, X0, 4.85, XW, 2.1, ["The Bonus against the same decomposition with unchanged source differs by +1.2 × 10⁻¹² (relative), −0.00002% and −0.00041% on 1 / 2 / 4 nodes, over 1,000 times inside F3's ±0.5%.", "The organisers' notes show hierarchical and scotch 0.7 / 3.0 / 3.5% apart at 40 / 80 / 150 steps, and the node mapping moves Cd by +0.8 / +2.1 / +3.2%, within that.", "With the organisers' decomposition our 150-step Cd is 0.284049 against their 0.283983, and the site module with our scripts gives their value exactly, so the difference is our build (AMD's math library).", "Every job of the same configuration and node count produced a byte-identical coefficient.dat."], size=14, space_after=6)
    return s


def s_efficiency():
    s = supp(33, "WHY THE SPEEDUP EXCEEDS 4", "s_efficiency")
    table_caption(s, X0, 1.35, XW, "Counters per cell and step of Basic before the node mapping, from AMD uProf.")
    rows = [["Per cell and step (Basic, uProf)", "1 node", "2 nodes", "4 nodes", "4 nodes / 1 node"], ["Cycles", "24,235", "22,860", "20,418", "0.843"], ["L1 demand refills from DRAM", "24.6", "20.7", "17.1", "0.697"], ["L1 demand refills from L3 (same CCX)", "5.4", "6.3", "9.4", "1.75"]]
    table(s, X0, 1.85, [4.7, 1.6, 1.6, 1.6, 2.43], rows, row_h=0.74, size=16, colors=[None] + [[INK, INK, INK, INK, NAVY]] * 3, aligns=["l", "r", "r", "r", "r"])
    bullets(s, X0, 5.0, XW, 2.0, ["AMD uProf data_access on one rank per NUMA domain, normalised by ranks, steps and cells per rank.", "The sparse-matrix kernels gather cell arrays in face order, and their DRAM refills fall to 0.30 (Gauss–Seidel), 0.40 (residual) and 0.42 (A·x), while a loop that streams cell fields stays at 0.95.", "Cell arrays per rank are 4 MB on 1 node, 2 MB on 2 and 1 MB on 4, against 4 MB of L3 per core, while the face arrays of about 16 MB never fit.", "A rank's cycles follow its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24)."], size=14.5, space_after=8)
    return s


def fill_index(s, groups):
    """Q&A index: one clickable line per supporting slide in two columns; call after the slide order is final."""
    set_title(s, "Q&A INDEX")
    for column, pair in enumerate((groups[:2], groups[2:])):
        x, y = (X0, 6.78)[column], 1.4
        for name, items in pair:
            add_text(s, x, y, 5.85, 0.42, [name], size=18, color=NAVY)
            y += 0.5
            for title, target in items:
                line = add_text(s, x + 0.1, y, 5.75, 0.4, [[(f"{prs.slides.index(target) + 1}", {"color": NAVY}), ("   " + title, {})]], size=16, anchor="m")
                line.click_action.target_slide = target
                y += 0.42
            y += 0.32
    set_notes(s, NOTES["index"])


def fix_sections():
    """Keep PowerPoint's sections in step with the slide list: drop the ids of removed slides and put each section's slides in
    the new order (the team deck has one section with every slide and an empty ai-archive)."""
    ids = [sldId.get("id") for sldId in prs.slides._sldIdLst]
    position = {value: i for i, value in enumerate(ids)}
    seen = set()
    for lst in prs.part._element.iter(f"{{{P14}}}sldIdLst"):
        members = [el.get("id") for el in lst if el.get("id") in position]
        for el in list(lst):
            lst.remove(el)
        for value in sorted(members, key=position.get):
            etree.SubElement(lst, f"{{{P14}}}sldId").set("id", value)
            seen.add(value)
    if seen and seen != set(ids):
        raise SystemExit("some slides are in no section; see README.md")


# ====================================================================== assemble
cover = S[0]
set_notes(cover, NOTES["cover"])
main = [m_summary(), m_criteria(), m_profile_baseline(), m_mpi(), m_decomposition(), m_pinning(), m_pinning_results(), m_mapping(), m_basic_results(), m_basic_mpi(), m_not_helped_basic(), m_profile_basic(), m_memory_limit(), m_bonus_decomposition(), m_changes(0), m_changes(1), m_examples(), m_bonus_results(), m_scaling(), m_not_helped_bonus()]
COUNT.update(prefix="S", Figure=0, Table=0)
divider = S[21]
index_slide = reuse(22)
groups = [("Setup and measurement", [("ASPIRE-2A and why we chose it", s_aspire()), ("Build, MPI and run settings", s_settings()), ("Run-to-run variation over 92 jobs", s_noise()), ("The organisers' reference", s_reference()), ("Reproducing our results", s_repro())]), ("Basic", [("Is the network the bottleneck?", s_network()), ("Pinning with hierarchical", s_pinning_case_default()),("hierarchical and scotch on 1, 2 and 4 nodes", s_scotch()), ("The placement experiment in full", s_cores())]), ("Bonus", [("Decompositions we tried", s_decompositions()), ("Where a Bonus step goes, by phase", s_callstack()), ("Call stacks of a Bonus step: flame graph", s_flame()), ("Source changes in detail (1/2)", s_changes()), ("Source changes in detail (2/2)", s_changes2()), ("Effect of each Bonus change", s_each()), ("Hardware counters of the first four changes", s_counters())]), ("Results", [("Drag coefficient over the iterations", s_cd_iterations()), ("Drag coefficient checks", s_cd()), ("Why the speedup exceeds 4 on 4 nodes", s_efficiency())])]
order = [cover] + main + [divider, index_slide] + [sl for _, items in groups for _, sl in items]

sldIdLst = prs.slides._sldIdLst
by_part = {prs.part.related_part(sldId.rId): sldId for sldId in sldIdLst}
kept = {sl.part for sl in order}
assert len(order) == len(kept), "a slide is used twice"
for part, sldId in by_part.items():
    if part not in kept:
        prs.part.rels.pop(sldId.rId)
for sldId in list(sldIdLst):
    sldIdLst.remove(sldId)
for sl in order:
    sldIdLst.append(by_part[sl.part])
fix_sections()
fill_index(index_slide, groups)

# the co-authoring change log lists the old slide ids
for rId, rel in list(prs.part.rels.items()):
    if "changesInfo" in rel.reltype:
        prs.part.rels.pop(rId)

prs.save(OUT)
print("saved", OUT, "with", len(prs.slides), "slides")
for i, sl in enumerate(prs.slides, 1):
    print(f"{i:3d} {sl.shapes.title.text_frame.text[:60] if sl.shapes.title is not None else ''}")
