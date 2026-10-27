# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0", "lxml", "pillow", "xlsxwriter"]
# ///
"""Rebuild the OpenFOAM (HPC) part of the team deck from the 10/26 team deck.

usage: uv run build_deck.py INPUT.pptx OUTPUT.pptx FIGDIR ASSETDIR

INPUT is the team deck as of 2026-10-26: our 10/21 build of the OpenFOAM part (main 1-21 with the team's HPC roofline at 14,
divider 22, Q&A index 23, supporting 24-44, the shared reproducibility slide 45), then the AI track from slide 46 on.
FIGDIR holds the deck's renders of ../figures.py (deck_figures.py) and its per-job plots (deck_plots.py). ASSETDIR holds
pictures that are neither in INPUT nor drawn here: the decomposition renders from the Box folder
presentation/openfoam/decomposition/. build.sh runs all three steps.

Every OpenFOAM slide is rebuilt in place, so it keeps its slide id and the team's slide-number box. The roofline slide and
the shared reproducibility slide are the team's: only their Bonus numbers are brought up to date. Every slide from the AI
title slide on stays byte for byte.
"""

import copy
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.chart import XL_LEGEND_POSITION
from pptx.oxml.ns import qn

from decklib import NBSP, add_sldnum, add_text, arrow_line, bar_chart, block_arrow, box, bullets, circle_num, clear_slide, picture, picture_fit, remove_body_placeholders, set_notes, set_title, shape_info, shape_text, table
from notes import NOTES
from palette import BAD, BASE, BASIC, BONUS, BONUS_LIGHT, BONUS_LINE, BONUS_TINT, FAINT, GRID, INK, LIGHT, LINE, MUTED, NAVY, TINT, WHITE

SRC, OUT, FIG, ASSETS = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
prs = Presentation(SRC)
S = list(prs.slides)  # S[i] is input slide i + 1
X0, XW = 0.70, 11.93  # left edge and width of the content area
GREY_TINT = "F1F1F1"
DECOMP_COLUMNS = {"hier": (0.0, 0.667), "scotch": (0.333, 0.334)}
PANEL_TOP, PLANE_BOTTOM, ALL_BOTTOM = 0.113, 0.346, 0.085
CAR_CROP = (0.06, 0.12, 0.17, 0.0)  # a 1920 x 1080 car render from decomposition/panels/, cropped to the car
COUNT = {"Figure": 0, "Table": 0}
SERIES = [""]  # "" in the main part, "S" in the supporting slides
# the titles of the input's OpenFOAM part, slides 1-45, in order; S[i] is rebuilt as the slide that had title INPUT_TITLES[i]
INPUT_TITLES = ["", "OpenFOAM TASK OVERVIEW", "ASPIRE-2A", "BASELINE SETTINGS", "BASELINE RESULTS", "HOW WE MEASURE AND PROFILE", "MPI PROFILE ON 4 NODES", "BASELINE ANALYSIS", "OPTIMIZATION STRATEGY", "BASIC OPTIMIZATION (1/2)", "BASIC OPTIMIZATION (2/2)", "BASIC RESULTS", "MEMORY BANDWIDTH SETS THE SPEED", "HPC ROOFLINE: MEMORY AND COMMUNICATION", "BONUS OPTIMIZATION", "BONUS RESULTS", "BONUS ANALYSIS", "SCALING ANALYSIS", "WHAT DID NOT HELP, AND WHY", "CONCLUSION", "EXTRA: A GAIN WE DID NOT COUNT", "SUPPORTING INFORMATION", "Q&A INDEX", "BOTTLENECKS WE MEASURED", "MEASURING HONESTLY", "EXPERIMENT AUTOMATION", "BUILD, STORAGE AND MPI", "THE ORGANISERS' REFERENCE", "WHERE A STEP GOES AFTER BASIC", "THE PATH ON 4 NODES", "IS THE NETWORK THE BOTTLENECK?", "OFI AGAINST UCX", "THE THREE SPLITS: FACES OR EVEN WORK?", "CORES OR MEMORY?", "THE SOURCE CHANGES", "SOURCE CHANGES IN DETAIL (1/2)", "SOURCE CHANGES IN DETAIL (2/2)", "EFFECT OF EACH BONUS CHANGE", "PROFILES BEFORE AND AFTER", "WHY THE EFFICIENCY EXCEEDS 1", "DRAG COEFFICIENT CHECKS", "REPRODUCING OUR RESULTS", "NOT ADOPTED: THE FULL LIST", "COMPILER AND FLAGS", "Reproducibility: Code, Build, Runtime and Results"]
AI = len(INPUT_TITLES)  # S[AI] is the AI track's title slide


def check_input():
    titles = [s.shapes.title.text_frame.text if s.shapes.title is not None else "" for s in S]
    ai_title = " ".join(sh.text_frame.text for sh in S[AI].shapes if sh.has_text_frame) if len(S) > AI else ""
    if titles[:AI] != INPUT_TITLES or "AI Track" not in ai_title:
        raise SystemExit("build_deck.py expects the 2026-10-26 team deck (OpenFOAM 1-45 with the HPC roofline at 14, AI title slide at 46); see README.md")


check_input()
LAYOUT = S[1].slide_layout
SLDNUM = copy.deepcopy(next(el for el in S[9].shapes._spTree if shape_info(el)[1] == "sldNum"))  # the box the team widened for two digits
DECOMP = next(sh for sh in S[3].shapes if sh.name == "図 7").image.blob  # hierarchical, scotch, multiLevel x car, centre plane, cross-section


def reuse(i, keep=()):
    """Input slide i + 1, emptied but for its title, its slide number and the shapes named in keep."""
    clear_slide(S[i], keep=keep)
    return S[i]


def fig(name):
    return FIG / f"{name}.png"


def new_slide():
    s = prs.slides.add_slide(LAYOUT)
    remove_body_placeholders(s)
    add_sldnum(s, SLDNUM)
    return s


def message(s, runs, size=20):
    return add_text(s, X0, 0.94, XW, 0.5, [runs], size=size, color=NAVY, bold=True, name="Message")


def number(kind):
    """The next figure or table number in slide order: Figure 1, Table 1 in the main part, Figure S1, Table S1 after it."""
    COUNT[kind] += 1
    return f"{kind} {SERIES[0]}{COUNT[kind]}"


def heading(s, x, y, w, kind, text, sub=None, size=15):
    """A numbered heading over a figure or table, with an optional short line under it."""
    add_text(s, x, y, w, 0.36, [[(number(kind) + ". ", {}), (text, {})]], size=size, color=NAVY, bold=True)
    if sub:
        add_text(s, x, y + 0.36, w, 0.3, [sub], size=12, color=MUTED)


def figure_caption(s, text, x, y, w, h=0.3, size=11, align="l"):
    """A numbered caption under a picture."""
    return add_text(s, x, y, w, h, [{"runs": [(number("Figure") + ". ", {"b": True}), (text, {})], "align": align}], size=size, color=MUTED)


def lesson(s, text, x=X0, y=6.52, label="TAKEAWAY"):
    w = min(XW, 1.15 + 0.1 * len(label) + 0.122 * len(text))
    box(s, x, y, w, 0.46, fill=TINT, radius=0.5, name="Lesson")
    add_text(s, x + 0.22, y, w - 0.3, 0.46, [[(label + "   ", {"b": True, "size": 11}), (text, {"b": True, "size": 14})]], color=NAVY, anchor="m", name="LessonText")


def card(s, x, y, w, h, fill=LIGHT, line=None):
    return box(s, x, y, w, h, fill=fill, line=line, radius=0.05)


def stat(s, x, y, w, h, number_text, label, sub=None, color=NAVY, num_size=34, label_size=14, sub_size=12):
    card(s, x, y, w, h)
    paras = [{"runs": [number_text], "size": num_size, "color": color, "bold": True, "line": 0.95}, {"runs": [label], "size": label_size, "bold": True, "space_before": 2}]
    if sub:
        paras.append({"runs": [sub], "size": sub_size, "color": MUTED, "space_before": 2})
    add_text(s, x + 0.22, y, w - 0.44, h, paras, color=INK, anchor="m")


def label_value_table(s, x, y, col_w, rows, row_h=0.6, size=14):
    return table(s, x, y, col_w, rows, row_h=row_h, size=size, header=False, bolds=[[True, False]] * len(rows), colors=[[NAVY, None]] * len(rows))


def decomp_panel(s, which, x, y, w=None, h=None, bottom=PLANE_BOTTOM):
    left, right = DECOMP_COLUMNS[which]
    return picture(s, DECOMP, x, y, w, h, crop=(left, PANEL_TOP, right, bottom))


def answer_rows(s, y0, pairs, step=0.48, size=13.5):
    """Question pills on the left, one-line answers on the right."""
    for i, (question, answer) in enumerate(pairs):
        y = y0 + i * step
        shape_text(box(s, X0, y, 2.85, 0.42, fill=NAVY, radius=0.5), question, size=13)
        add_text(s, X0 + 3.05, y - 0.04, 8.88, 0.5, [answer], size=size, bold=True, anchor="m")


# ====================================================================== main part
def slide_title():
    set_notes(S[0], NOTES["title"])
    return S[0]


def slide_overview():
    s = reuse(1, keep=("flow-iterations", "図 5"))
    set_title(s, "OpenFOAM TASK OVERVIEW")
    message(s, "Make the same math faster: same mesh, same solver, same work")
    rows = [("Case", ["Steady flow around a car at 140 km/h", "\n", "simpleFoam (k-ω SST), OpenFOAM v2512"]), ("Mesh", ["occDrivAerStaticMesh: 65.3 M cells,", "\n", "finest near the car; the mesh is fixed"]), ("Step", ["Fixed solver iterations", "\n", "→ the same work in every step"]), ("Metric", ["Average time per step on 4 nodes (steps 2–150)", "\n", "1 / 2 / 4 nodes for scaling: 40 / 80 / 150 steps"])]
    for i, (label, value) in enumerate(rows):
        add_text(s, X0, 1.62 + i * 0.82, 1.25, 0.66, [label], size=16, color=NAVY, bold=True)
        add_text(s, 1.95, 1.62 + i * 0.82, 5.15, 0.66, [value], size=15)
    xr, wr = 7.3, 5.33
    flow_h, mesh_h = wr * 2.689 / 4.78, wr * 638 / 2764
    for sh in s.shapes:
        if sh.name == "flow-iterations":
            sh.left, sh.top, sh.width, sh.height = [int(v * 914400) for v in (xr, 1.6, wr, flow_h)]
        if sh.name == "図 5":  # its caption ends on the bottom line, with the result card
            sh.left, sh.top, sh.width, sh.height = [int(v * 914400) for v in (xr, 6.7 - mesh_h, wr, mesh_h)]
    figure_caption(s, "Flow around the car (ParaView, a separate run)", xr, 1.66 + flow_h, wr)
    figure_caption(s, "Mesh: refinement level of the 65,334,765 cells", xr, 6.76, wr, h=0.26)
    card(s, X0, 4.98, 6.35, 2.02)
    add_text(s, X0 + 0.25, 5.08, 5.9, 0.34, [[("Our result on 4 nodes", {"b": True, "color": NAVY}), ("   s/step, lower is better", {"color": MUTED, "size": 12})]], size=15)
    for i, (number_text, name, delta, color) in enumerate([("3.65", "Baseline", "", BASE), ("2.90", "Basic", "−21%", BASIC), ("2.36", "Bonus", "−35%", BONUS)]):
        x = X0 + 0.25 + i * 2.05
        add_text(s, x, 5.38, 1.5, 0.62, [number_text], size=34, color=color, bold=True)
        add_text(s, x, 6.02, 1.85, 0.34, [[(name + "  ", {"b": True}), (delta, {"color": color, "b": True})]], size=14)
        if i < 2:
            block_arrow(s, x + 1.45, 5.54, 0.4, 0.32, color="B8C2D3")
    add_text(s, X0 + 0.25, 6.38, 5.9, 0.3, [[("1.55× faster", {"b": True, "color": NAVY}), (" with the same build, scripts and measurement", {"color": MUTED})]], size=13)
    # "5. Common Baselines" (official repository, 2026-10-20) asks every team to show this next to its own result
    add_text(s, X0 + 0.25, 6.68, 5.9, 0.26, [[("Organisers' common baseline:", {"b": True}), (" hierarchical 3.415, scotch 3.576 s/step", {})]], size=11, color=MUTED)
    set_notes(s, NOTES["overview"])
    return s


def node_diagram(s, x, y, w, h):
    """One ASPIRE-2A node as the job sees it: 2 sockets x 4 NUMA domains, each 16 cores with 2 memory channels."""
    box(s, x, y, w, h, fill="F7F8FA", line=LINE, radius=0.04)
    add_text(s, x + 0.15, y + 0.06, w - 0.3, 0.3, [f"{number('Figure')}. One node: 2 sockets × 4 NUMA × 16 cores"], size=12, color=NAVY, bold=True)
    socket_w, socket_h = (w - 0.45) / 2, h - 0.52
    numa_w, numa_h = (socket_w - 0.3) / 2, (socket_h - 0.46) / 2
    for k in range(2):
        sx, sy = x + 0.15 + k * (socket_w + 0.15), y + 0.42
        box(s, sx, sy, socket_w, socket_h, fill=WHITE, line="B8C2D3", radius=0.04)
        add_text(s, sx + 0.1, sy + 0.04, socket_w - 0.2, 0.28, [f"socket {k}"], size=11, bold=True)
        for r in range(2):
            for c in range(2):
                domain = 4 * k + 2 * r + c
                nx, ny = sx + 0.1 + c * (numa_w + 0.1), sy + 0.36 + r * (numa_h + 0.06)
                box(s, nx, ny, numa_w, numa_h, fill=TINT, radius=0.06)
                add_text(s, nx, ny, numa_w, numa_h, [{"runs": [f"NUMA {domain}"], "size": 11.5, "bold": True, "color": NAVY}, {"runs": ["16 cores, 2 channels"], "size": 10}], align="c", anchor="m")


def slide_aspire():
    s = reuse(2)
    set_title(s, "ASPIRE-2A")
    message(s, "8 NUMA domains per node; 16 cores already fill the bandwidth")
    heading(s, X0, 1.58, 6.7, "Table", "One ASPIRE-2A node")
    rows = [["Processor", "2 × EPYC 7713 (Zen 3): 128 cores, 2.0 GHz"], ["NUMA, cache", "8 NUMA × 16 cores; 32 MB L3 per 8 cores"], ["Memory", "512 GB DDR4-3200, 16 channels, 409.6 GB/s peak"], ["Network", "HPE Slingshot-10 (100 Gb/s), dragonfly"], ["Software", "Cray PE: GCC 11.2, Cray MPICH 8.1.15, PBS Pro"]]
    label_value_table(s, X0, 1.98, [1.62, 5.08], rows, row_h=0.66, size=14)
    node_diagram(s, 7.6, 1.62, 5.03, 2.5)
    card(s, 7.6, 4.3, 5.03, 1.0, fill=TINT)
    add_text(s, 7.82, 4.3, 4.7, 1.0, [{"runs": [("≈ 290 GB/s", {"size": 20}), ("  STREAM triad", {"size": 13})], "bold": True, "color": NAVY}, {"runs": ["reached with only 16 of 128 cores (one per L3)"], "size": 13, "color": NAVY}], anchor="m")
    card(s, X0, 5.55, XW, 1.45)
    add_text(s, X0 + 0.25, 5.8, 5.6, 0.4, ["Why ASPIRE-2A?"], size=17, color=NAVY, bold=True)
    add_text(s, X0 + 0.25, 6.22, 5.75, 0.7, ["OpenFOAM works with very many files: a build is ≈ 36,000 files, and each decomposed case adds thousands more."], size=13)
    for i, (head, value, fill, color, mark) in enumerate([("Gadi project quota", "0.2 M files · 1 TB", GREY_TINT, BAD, "✕"), ("ASPIRE-2A quota", "200 M files · 100 TB", WHITE, NAVY, "✓")]):
        x = 6.75 + i * 2.95
        box(s, x, 5.75, 2.75, 1.06, fill=fill, line=LINE, radius=0.08)
        add_text(s, x + 0.18, 5.78, 2.45, 1.0, [{"runs": [(mark + " ", {"color": color}), (head, {})], "size": 12, "color": MUTED, "bold": True}, {"runs": [value], "size": 16, "color": color, "bold": True, "space_before": 3}], anchor="m")
    set_notes(s, NOTES["aspire"])
    return s


def slide_baseline_settings():
    s = reuse(3, keep=("図 7",))
    set_title(s, "BASELINE SETTINGS")
    message(s, "We start from the case defaults, on our own build of v2512")
    heading(s, X0, 1.58, 8.35, "Table", "Baseline settings")
    rows = [["Build", "Official v2512 source, GCC 11.2 -O3, AMD AOCL-LibM: as fast as the site module (−0.08%), and it records what ran"], ["MPI", "Cray MPICH 8.1.15 over UCX: with the default OFI, every 2-node and 4-node run died with SIGBUS at MPI_Finalize"], ["Decomposition", "Case default hierarchical: (16 8 1) / (16 8 2) / (16 8 4) on 1 / 2 / 4 nodes"], ["Placement", "128 ranks per node, one per core, bound by the launcher (mpiexec --cpu-bind depth), as the site recommends"], ["Measurement", "Official metric (steps 2 to N); at least 3 jobs per condition; one point = one job"], ["Modules", "PrgEnv-gnu/8.3.3, aocl/4.0.0, cray-mpich-ucx/8.1.15"]]
    label_value_table(s, X0, 1.98, [2.0, 6.35], rows, row_h=0.82, size=15)
    h = 4.45
    w = h * (3840 * 0.333) / (2220 * (1 - PANEL_TOP - ALL_BOTTOM))
    x = 12.63 - w
    for sh in s.shapes:
        if sh.name == "図 7":
            sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom = 0.0, PANEL_TOP, 0.667, ALL_BOTTOM
            sh.left, sh.top, sh.width, sh.height = [int(v * 914400) for v in (x, 1.98, w, h)]
    add_text(s, x, 1.6, w, 0.34, ["hierarchical (16 8 4)"], size=14, color=BASE, bold=True, align="c")
    add_text(s, x, 6.5, w, 0.45, [{"runs": [(number("Figure") + ". ", {"b": True}), ("512 subdomains", {})], "align": "c"}, {"runs": ["car · centre plane · cross-section"], "align": "c"}], size=11, color=MUTED)
    set_notes(s, NOTES["baseline_settings"])
    return s


def slide_baseline_results():
    s = reuse(4)
    set_title(s, "BASELINE RESULTS")
    message(s, "3.65 s/step on 4 nodes: linear scaling, but slow and unsteady")
    heading(s, X0, 1.58, 8.3, "Figure", "Time per step on 1, 2 and 4 nodes, each job")
    picture(s, fig("p05_baseline_scaling"), 0.55, 1.98, w=8.4)
    stat(s, 9.2, 1.62, 3.43, 1.38, "3.65 s/step", "on 4 nodes", "mean of 3 jobs", color=BASE, num_size=30)
    stat(s, 9.2, 3.15, 3.43, 1.38, "4.0×", "from 1 to 4 nodes", "parallel efficiency 1.00", color=NAVY, num_size=30)
    stat(s, 9.2, 4.68, 3.43, 1.38, "8%", "spread between jobs", "of one setup: 3.53–3.82 s/step", color=BAD, num_size=30)
    add_text(s, X0, 6.56, XW, 0.4, ["Slow and unsteady at the same time: a sign that something is misconfigured"], size=15, color=NAVY, bold=True)
    set_notes(s, NOTES["baseline_results"])
    return s


def slide_measure():
    s = reuse(5)
    set_title(s, "HOW WE MEASURE AND PROFILE")
    message(s, "Benchmark runs give the numbers; profile runs explain them")
    heading(s, X0, 1.58, XW, "Table", "One question per tool")
    rows = [["Tool", "When it runs", "Question it answers"], ["Official metric", "Every benchmark run, no profiler", "How long does a step take?"], ["IMB-MPI1", "After the solver, every benchmark run", "How fast is the network between these nodes?"], ["CrayPAT", "Profile runs: 4 nodes, 40 steps", "Which MPI calls take the time, per rank?"], ["OpenFOAM profiling", "Profile runs", "Which solver stage takes the time, per rank?"], ["AMD uProf", "Profile runs", "Which functions use the CPU? Hardware counters"], ["/proc in the job", "Profile runs", "Is each rank on its own core? Where is its memory?"]]
    colors = [None] + [[NAVY, INK, INK]] * 6
    table(s, X0, 1.98, [2.45, 4.3, 5.18], rows, row_h=0.46, size=14, bolds=[None] + [[True, False, False]] * 6, colors=colors)
    cards = [("✓", "Decision rule", "Candidate and control alternate in the same period, at least 3 jobs each on 4 nodes. A change is kept only if every job with it beats every job without it."), ("≈", "Know the noise before trusting a gain", "One setup, repeated: 8% spread in our baseline, 0.18% after Basic. Profilers shift a step by −1% to +6%, so profiled times are never results.")]
    for i, (mark, head, body) in enumerate(cards):
        x = X0 + i * 6.08
        card(s, x, 5.35, 5.85, 1.65)
        circle_num(s, x + 0.22, 5.51, 0.42, mark, size=15)
        add_text(s, x + 0.78, 5.49, 4.9, 0.44, [head], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.78, 5.95, 4.85, 1.0, [body], size=14)
    set_notes(s, NOTES["measure"])
    return s


def slide_mpi_profile():
    """The organisers' ISC26 SCC task asks for the 3 most used MPI calls on 4 nodes, by number of calls and by total CPU time."""
    s = reuse(6)
    set_title(s, "MPI PROFILE ON 4 NODES")
    message(s, "Most calls are halo exchanges; most time goes to the calls that wait")
    add_text(s, X0, 1.52, XW, 0.36, [[(number("Figure") + ". CrayPAT on our baseline", {"b": True, "color": NAVY}), (": 4 nodes, all 512 ranks, 40 steps; values per rank are the mean of the 512 ranks", {})]], size=13.5, color=MUTED)
    cards = [("Top 3 by number of calls", "calls per rank in 40 steps, of 1.82 M MPI calls per rank", [("MPI_Isend", 566107.3, "566,107", ""), ("MPI_Irecv", 566107.3, "566,107", ""), ("MPI_Test", 563645.5, "563,646", "")], [NAVY] * 3, [("93% of all calls: ", {"b": True, "color": NAVY}), ("the non-blocking halo exchange with the neighbouring subdomains", {})]), ("Top 3 by total time", "seconds per rank, and share of the 78.3 s of MPI per rank", [("MPI_Waitall", 43.103, "43.1 s", "   55%"), ("MPI_Allreduce", 27.617, "27.6 s", "   35%"), ("MPI_Bcast", 2.518, "2.5 s", "   3%")], [BAD, BAD, FAINT], [("90% of the MPI time waits for other ranks, ", {"b": True, "color": BAD}), ("and MPI is 46% of a rank's time", {})])]
    for i, (head, sub, rows, colors, footer) in enumerate(cards):
        x = X0 + i * 6.08
        card(s, x, 1.98, 5.85, 4.12)
        add_text(s, x + 0.3, 2.1, 5.3, 0.42, [head], size=18, color=NAVY, bold=True)
        add_text(s, x + 0.3, 2.53, 5.3, 0.32, [sub], size=12.5, color=MUTED)
        vmax = max(value for _, value, _, _ in rows)
        for k, ((name, value, label, share), color) in enumerate(zip(rows, colors)):
            y = 3.05 + k * 0.78
            circle_num(s, x + 0.3, y, 0.38, str(k + 1), fill=color, size=13)
            add_text(s, x + 0.82, y - 0.04, 2.6, 0.46, [name], size=16, bold=True, anchor="m")
            add_text(s, x + 3.0, y - 0.04, 2.55, 0.46, [[(label, {"b": True}), (share, {"color": MUTED, "size": 13})]], size=16, align="r", anchor="m")
            box(s, x + 0.82, y + 0.47, 4.73, 0.12, fill=GRID, radius=0.5)
            box(s, x + 0.82, y + 0.47, 4.73 * value / vmax, 0.12, fill=color, radius=0.5)
        add_text(s, x + 0.3, 5.4, 5.3, 0.62, [footer], size=13.5)
    add_text(s, X0, 6.4, XW, 0.4, [[("Waiting, not transfer: ", {"b": True, "color": NAVY}), ("MPI time per rank ranges from 35 to 112 s, with equal cell counts", {})]], size=15)
    set_notes(s, NOTES["mpi_profile"])
    return s


def slide_baseline_analysis():
    s = reuse(7)
    set_title(s, "BASELINE ANALYSIS")
    message(s, "Binding lost at MPI_Init → uneven computation → everyone waits")
    items = [("Binding lost", "/proc during the solve", "0 / 512", "ranks on their own core", "removed during MPI_Init; 9% of a rank's memory on its own NUMA domain (random: 12.5%)"), ("Uneven computation", "OpenFOAM profiling, 512 ranks", "1.46×", "slowest / median rank", "computation per rank: 54–115 s in 40 steps; cell counts equal within 0.002%"), ("Everyone waits", "CrayPAT", "46%", "of the time is MPI", "MPI_Waitall 55% and MPI_Allreduce 35% of it: calls that wait for other ranks")]
    w, gap = 3.55, 0.64
    for i, (head, tool, number_text, label, detail) in enumerate(items):
        x = X0 + i * (w + gap)
        card(s, x, 1.62, w, 3.28)
        circle_num(s, x + 0.2, 1.8, 0.38, str(i + 1), size=14)
        add_text(s, x + 0.68, 1.76, w - 0.8, 0.46, [head], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.25, 2.3, w - 0.4, 0.3, [(tool, {"i": True})], size=12, color=MUTED)
        add_text(s, x + 0.25, 2.68, w - 0.4, 0.68, [number_text], size=38, color=BAD, bold=True)
        add_text(s, x + 0.25, 3.38, w - 0.4, 0.34, [label], size=14, bold=True)
        add_text(s, x + 0.25, 3.78, w - 0.45, 1.05, [detail], size=13, color=MUTED)
        if i < 2:
            block_arrow(s, x + w + 0.11, 3.05, 0.42, 0.42)
    boxes = [("Why one slow rank matters", "Every solver iteration exchanges halo values and takes a global sum: about 14,000 messages and 1,600 global sums per rank per step. When one rank is late, the other 511 wait.", TINT), ("Where the computation goes (AMD uProf)", "Sparse-matrix sweeps lead: Gauss–Seidel smoothing, residuals and A·x are about a quarter of the computation. Each sweep streams the whole matrix with little arithmetic per byte.", LIGHT)]
    for i, (head, body, fill) in enumerate(boxes):
        x = X0 + i * 6.08
        card(s, x, 5.1, 5.85, 1.88, fill=fill)
        add_text(s, x + 0.25, 5.2, 5.4, 0.4, [head], size=15, color=NAVY, bold=True)
        add_text(s, x + 0.25, 5.62, 5.4, 1.3, [body], size=14.5)
    set_notes(s, NOTES["baseline_analysis"])
    return s


def slide_strategy():
    """The plan of the work: the loop we ran, and the rounds it took on 4 nodes."""
    s = reuse(8)
    set_title(s, "OPTIMIZATION STRATEGY")
    message(s, "Fix what is broken first, then follow the measured bottleneck")
    steps = [("Baseline", "Case defaults on our own build, 3 or more jobs per node count: know the spread"), ("Profile", "Separate profile runs: /proc, OpenFOAM profiling, CrayPAT, uProf, IMB"), ("Bottleneck", "What is broken? Why do the ranks wait? What limits one rank?"), ("Change one thing", "One commit per condition: job script and split (Basic), source (Bonus)"), ("Check", "Alternate with a control; keep it only if every job is faster. Bonus: Cd within F3")]
    w, gap = 2.146, 0.3
    for i, (head, body) in enumerate(steps):
        x = X0 + i * (w + gap)
        box(s, x, 1.6, w, 1.56, fill=TINT, line="B8C2D3", radius=0.08)
        circle_num(s, x + w / 2 - 0.17, 1.66, 0.34, str(i + 1), size=12)
        add_text(s, x + 0.08, 2.01, w - 0.16, 0.34, [head], size=14.5, color=NAVY, bold=True, align="c")
        add_text(s, x + 0.1, 2.35, w - 0.2, 0.8, [body], size=11.5, align="c")
        if i < len(steps) - 1:
            arrow_line(s, x + w + 0.03, 2.38, x + w + gap - 0.03, 2.38, color=MUTED, width=1.5)
    x_profile, x_check = X0 + (w + gap) + w / 2, X0 + 4 * (w + gap) + w / 2
    arrow_line(s, x_check, 3.17, x_check, 3.36, color=MUTED, width=1.5, head=False)
    arrow_line(s, x_check, 3.36, x_profile, 3.36, color=MUTED, width=1.5, head=False)
    arrow_line(s, x_profile, 3.36, x_profile, 3.18, color=MUTED, width=1.5)
    add_text(s, x_profile + 0.3, 3.38, x_check - x_profile - 0.6, 0.28, [("next round: profile the new baseline", {"i": True})], size=12, color=MUTED, align="c")
    heading(s, X0, 3.6, XW, "Table", "Our rounds on 4 nodes")
    rows = [["Round, from", "Bottleneck found, and how", "What we changed", "4 nodes"], ["1  baseline", "Binding lost at MPI_Init, uneven work, MPI 46% waiting (/proc, OpenFOAM profiling, CrayPAT)", "Pin CPU and memory, scotch, map the split onto the node (Basic)", "3.65 → 2.90 s/step"], ["2  Basic", "Memory bandwidth: half the channels 2.2× slower, half the cores no change (placement runs)", "Move fewer bytes: multiLevel split, four source changes (Bonus)", "2.90 → 2.60 s/step"], ["3  Bonus", "Passes, copies and global sums left in the turbulence model, Gauss–Seidel and coarsest CG (call stacks, uProf)", "Ten more source changes: fewer passes, copies and global sums (Bonus)", "2.60 → 2.36 s/step"], ["4  final Bonus", "Memory traffic, and the imbalance between ranks, which follows their DRAM reads (counters)", "Not done: fuse the assembly of U, k and ω; renumber cells for locality", "next steps"]]
    table(s, X0, 3.97, [1.35, 4.85, 3.7, 2.03], rows, row_h=0.52, size=12, row_heights=[0.38, 0.54, 0.54, 0.54, 0.54], colors=[None, [BASE, INK, INK, BASIC], [BASIC, INK, INK, BONUS], [BONUS, INK, INK, BONUS], [BONUS, INK, MUTED, MUTED]], bolds=[None, [True, False, False, True], [True, False, False, True], [True, False, False, True], [True, False, False, False]], aligns=["l", "l", "l", "c"], margins=(0.09, 0.04, 0.09, 0.04))
    for i, (name, color, text) in enumerate([("BASIC", BASIC, "Unmodified source; hierarchical or scotch split"), ("BONUS", BONUS, "Source changes or other splits; proven the same math")]):
        x = X0 + i * 6.08
        shape_text(box(s, x, 6.62, 0.98, 0.34, fill=color, radius=0.5), name, size=11)
        add_text(s, x + 1.1, 6.57, 4.75, 0.44, [text], size=12.5, anchor="m")
    set_notes(s, NOTES["strategy"])
    return s


def slide_basic_pinning():
    s = reuse(9)
    set_title(s, "BASIC OPTIMIZATION (1/2)")
    message(s, [("Putting the lost binding back: 3.65 → 3.26 s/step ", {}), ("(−11%)", {"color": BASIC})])
    steps = [("Cause", "The launcher binds each rank, but the binding is removed from outside during MPI_Init. Linux keeps a page where it was first written (first touch), so data allocated off-core stays remote."), ("Fix, in the job script only", "Each rank starts under numactl, with its memory bound to its own NUMA domain; one watcher per node re-pins each rank to its core with taskset."), ("Check", "During the solve, every rank is on its own core (512 of 512) and 58% of its pages are local (was 9%). Case-default split: 3.67 → 3.26 s/step, 3 v 3 jobs.")]
    for y, (i, (head, body)) in zip((1.65, 3.62, 5.38), enumerate(steps)):
        circle_num(s, X0, y, 0.42, str(i + 1), size=15)
        add_text(s, X0 + 0.6, y - 0.02, 5.1, 0.42, [head], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, X0 + 0.6, y + 0.44, 5.1, 1.4, [body], size=14.5)
    heading(s, 6.75, 1.58, 5.88, "Figure", "Each half alone is not enough", sub="4 nodes, scotch split, each job")
    picture(s, fig("p10_pinning"), 6.73, 2.32, w=5.9)
    set_notes(s, NOTES["basic_pinning"])
    return s


def slide_basic_decomp():
    s = reuse(10)
    set_title(s, "BASIC OPTIMIZATION (2/2)")
    message(s, [("scotch cuts compact blocks: 3.26 → 2.92 s/step ", {}), ("(−10.5%)", {"color": BASIC})])
    pw = 2.95
    heading(s, X0, 1.58, 2 * pw + 0.12, "Figure", "One colour per subdomain, 4 nodes")
    for i, (which, label, lines) in enumerate([("hier", "hierarchical (case default)", ["4.31 M faces between subdomains", "slowest / median rank 1.16"]), ("scotch", "scotch (Basic)", ["2.93 M faces (−32%)", "slowest / median rank 1.06"])]):
        x = X0 + i * (pw + 0.12)
        add_text(s, x, 1.95, pw, 0.32, [label], size=13.5, color=NAVY, bold=True, align="c")
        decomp_panel(s, which, x, 2.3, w=pw, bottom=ALL_BOTTOM)
        add_text(s, x, 6.47, pw, 0.5, [{"runs": [lines[0]], "align": "c"}, {"runs": [lines[1]], "align": "c"}], size=12, color=INK if i else MUTED, bold=bool(i))
    xr, wr = 7.15, 5.48
    heading(s, xr, 1.58, wr, "Figure", "scotch against hierarchical", sub="same placement, 3 jobs each, alternated")
    picture(s, fig("p11_scotch"), xr, 2.28, w=wr)
    card(s, xr, 5.4, wr, 1.58, fill=TINT)
    add_text(s, xr + 0.22, 5.5, wr - 0.4, 0.36, ["Then: map the split onto the node"], size=14.5, color=NAVY, bold=True)
    add_text(s, xr + 0.22, 5.88, wr - 0.4, 1.05, [[("scotchCoeffs follow 2 sockets × 4 NUMA domains × 16 cores: 23% fewer faces between nodes. ", {}), ("2.918 → 2.898 s/step (−0.7%)", {"b": True, "color": BASIC}), ("; all 5 jobs beat all 5 controls", {})]], size=13)
    set_notes(s, NOTES["basic_decomp"])
    return s


def slide_basic_results():
    s = reuse(11)
    set_title(s, "BASIC RESULTS")
    message(s, "−21% on 4 nodes, and the profiles show why")
    heading(s, X0, 1.58, 8.1, "Table", "Baseline against Basic on 4 nodes")
    rows = [["4 nodes", "Baseline", "Basic"], ["s/step (jobs)", "3.65 (3)", "2.90 (5): −21%"], ["Spread between jobs", "8%", "0.18%"], ["Ranks on their own core", "0 of 512", "512 of 512"], ["Memory on the rank's own NUMA domain (median)", "9%", "58%"], ["Computation, slowest / median rank (profile run)", "1.46", "1.06"], ["MPI share of the time (profile run)", "46%", "19%"]]
    table(s, X0, 1.98, [4.3, 1.55, 2.25], rows, row_h=0.6, size=14.5, colors=[None] + [[INK, BASE, BASIC]] * 6, bolds=[None, [True, True, True]] + [[False, False, True]] * 5, aligns=["l", "c", "c"])
    heading(s, 8.95, 1.58, 3.68, "Figure", "Each job on 4 nodes")
    picture(s, fig("p12_basic"), 8.93, 1.98, w=3.7)
    add_text(s, X0, 6.5, XW, 0.42, ["Steadier too: the organisers score a re-run of exactly this configuration"], size=15, color=NAVY, bold=True)
    set_notes(s, NOTES["basic_results"])
    return s


def channel_row(s, x, y, used, size=0.22, gap=0.06):
    for k in range(16):
        box(s, x + k * (size + gap), y, size, size, fill=NAVY if k < used else "D5D9E0", radius=0.15)


def slide_bandwidth():
    s = reuse(12)
    set_title(s, "MEMORY BANDWIDTH SETS THE SPEED")
    message(s, "Half the memory channels: 2.2× slower. Half the cores: no change")
    add_text(s, X0, 1.52, XW, 0.36, ["No memory-controller counters on ASPIRE-2A, so we moved the ranks instead (4 nodes, every rank pinned, 2 jobs each)"], size=13, color=MUTED)
    experiments = [("Half the cores", "128 → 64 ranks per node, still on all 16 channels", 16, "×0.99–1.02", NAVY, "If the cores set the speed: ×2"), ("Half the memory channels", "the same 64 ranks and split, on 8 of the 16 channels", 8, "×2.11–2.20", BAD, "Triad bandwidth: 279 → 125 GB/s (×2.22)")]
    for i, (head, sub, used, number_text, color, note) in enumerate(experiments):
        x = X0 + i * 6.08
        card(s, x, 1.98, 5.85, 3.47)
        add_text(s, x + 0.3, 2.1, 5.3, 0.42, [head], size=18, color=NAVY, bold=True)
        add_text(s, x + 0.3, 2.55, 5.3, 0.34, [sub], size=13, color=MUTED)
        channel_row(s, x + 0.3, 3.1, used)
        add_text(s, x + 0.3, 3.42, 5.3, 0.3, [f"{used} of 16 memory channels in use"], size=11, color=MUTED)
        add_text(s, x + 0.3, 3.8, 5.3, 0.75, [[(number_text, {}), ("  time per step", {"size": 15, "color": INK, "b": False})]], size=36, color=color, bold=True)
        add_text(s, x + 0.3, 4.72, 5.3, 0.5, [note], size=14, bold=True)
    add_text(s, X0, 5.68, XW, 0.62, [[("Arithmetic intensity agrees: ", {"b": True, "color": NAVY}), ("the sparse-matrix sweeps do ≈ 0.1 flop per byte, about 1/100 of what keeps the cores busy (4.1 TFLOP/s ÷ 290 GB/s ≈ 14 flop/byte).", {})]], size=14)
    lesson(s, "Move fewer bytes, not the same bytes faster")
    set_notes(s, NOTES["bandwidth"])
    return s


def replace_run_text(s, shape_name, old, new):
    """Replace text inside one run of a shape that the team made, keeping the run's formatting."""
    for paragraph in next(sh for sh in s.shapes if sh.name == shape_name).text_frame.paragraphs:
        for run in paragraph.runs:
            if old in run.text:
                run.text = run.text.replace(old, new)
                return
    raise SystemExit(f"{shape_name}: '{old}' not found; see README.md")


def prepend_notes(s, text):
    """Put our script above the notes the team wrote, leaving their paragraphs as they are."""
    tf = s.notes_slide.notes_text_frame
    if tf.text.startswith("[0:"):
        return
    anchor = tf.paragraphs[0]._p
    for line in text.strip("\n").split("\n") + [""]:
        p = etree.Element(qn("a:p"))
        if line:
            etree.SubElement(etree.SubElement(p, qn("a:r")), qn("a:t")).text = line
        anchor.addprevious(p)


def slide_roofline():
    """The team's HPC roofline (2026-10-26), as it is but for the measured time of the final Bonus in its label 5."""
    s = S[13]
    replace_run_text(s, "HPC_change_5", "2.599 s/step", "2.360 s/step")
    prepend_notes(s, NOTES["roofline"])
    return s


def slide_bonus_opt():
    s = reuse(14)
    set_title(s, "BONUS OPTIMIZATION")
    message(s, "The same computation with fewer bytes moved")
    circle_num(s, X0, 1.66, 0.4, "1", fill=BONUS, size=14)
    add_text(s, X0 + 0.55, 1.62, 5.75, 0.46, ["A split that follows the machine"], size=16, color=NAVY, bold=True, anchor="m")
    add_text(s, X0 + 0.55, 2.1, 5.75, 0.6, ["multiLevel (4 2 4 16): nodes → sockets → NUMA → cores, scotch at each level; 38% fewer faces between nodes"], size=13.5)
    # the car surface from the decomposition renders of #39: one colour per subdomain, then colour = node, shade = NUMA domain
    left = picture(s, ASSETS / "multiLevel-car-subdomains.png", X0 + 0.55, 2.74, h=1.48, crop=CAR_CROP)
    picture(s, ASSETS / "multiLevel-car-numa.png", X0 + 0.55 + left.width / 914400 + 0.12, 2.74, h=1.48, crop=CAR_CROP)
    figure_caption(s, "multiLevel by subdomain (left), by node and NUMA domain (right)", X0 + 0.55, 4.25, 5.75, h=0.28, size=10.5)
    circle_num(s, X0, 4.68, 0.4, "2", fill=BONUS, size=14)
    add_text(s, X0 + 0.55, 4.64, 5.75, 0.46, ["Fourteen source changes that move fewer bytes"], size=16, color=NAVY, bold=True, anchor="m")
    items = [("No copies or zero fills", ": solvers, Gauss–Seidel, matrices"), ("Fewer passes", ": U components together, fused loops"), ("No unused values", ": boundaries, wall stress, p reference"), ("Fewer global sums", ": one per coarse-level CG iteration")]
    add_text(s, X0 + 0.55, 5.12, 5.75, 1.2, [{"runs": [(a, {"b": True}), (b, {})], "bullet": {"color": BONUS}, "space_after": 2} for a, b in items], size=13)
    card(s, X0, 6.4, 6.3, 0.58, fill=TINT)
    add_text(s, X0 + 0.25, 6.4, 5.9, 0.58, [[("Same computation: ", {"b": True, "color": NAVY}), ("same iterations, tests and discretisation", {})]], size=13.5, anchor="m")
    xd = 7.35
    heading(s, xd, 1.58, 5.28, "Figure", "Example: U components in one pass")
    add_text(s, xd, 2.02, 5.28, 0.3, ["Before: one pass per component"], size=13, bold=True)
    for k, component in enumerate(("Ux", "Uy", "Uz")):
        y = 2.42 + k * 0.56
        shape_text(box(s, xd, y, 2.15, 0.44, fill=TINT, line="9FB0CC", radius=0.12), "matrix arrays", size=12.5, color=NAVY, bold=False)
        arrow_line(s, xd + 2.2, y + 0.22, xd + 2.85, y + 0.22, color=FAINT)
        shape_text(box(s, xd + 2.9, y, 2.2, 0.44, fill=BONUS_TINT, line=BONUS_LINE, radius=0.12), f"sweep {component}", size=12.5, color=INK, bold=False)
    add_text(s, xd, 4.06, 5.1, 0.32, ["the matrix is read 3 times"], size=13.5, color=BAD, bold=True, align="c")
    add_text(s, xd, 4.6, 5.28, 0.3, ["After: one pass for all three"], size=13, bold=True)
    shape_text(box(s, xd, 5.0, 2.15, 1.1, fill=TINT, line="9FB0CC", radius=0.08), "matrix arrays", size=12.5, color=NAVY, bold=False)
    arrow_line(s, xd + 2.2, 5.55, xd + 2.85, 5.55, color=FAINT)
    shape_text(box(s, xd + 2.9, 5.0, 2.2, 1.1, fill=BONUS_TINT, line=BONUS_LINE, radius=0.08), ["sweep Ux", "sweep Uy", "sweep Uz"], size=12.5, color=INK, bold=False)
    add_text(s, xd, 6.18, 5.1, 0.32, ["the matrix is read once"], size=13.5, color=BONUS, bold=True, align="c")
    add_text(s, xd, 6.58, 5.28, 0.36, ["Each component gets the same operations in the same order"], size=12, align="c")
    set_notes(s, NOTES["bonus_opt"])
    return s


def slide_bonus_results():
    s = reuse(15)
    set_title(s, "BONUS RESULTS")
    message(s, "19% faster than our Basic, with Cd within 0.0005%")
    heading(s, X0, 1.58, XW, "Figure", "Each job: Basic, the multiLevel split alone, the first four changes, and the Bonus")
    picture(s, fig("p15_bonus"), X0, 1.96, w=XW)
    add_text(s, X0, 5.0, XW, 0.38, ["What the rules ask of Bonus work, and our answer"], size=15, color=NAVY, bold=True)
    checks = [("What changed", "Fourteen patches and the multiLevel dictionaries, submitted as text"), ("Why the same math", "Only copies, extra passes, unread values and extra global sums go; iterations and tests unchanged"), ("Evidence", "First four: bit-identical, every log line too. All fourteen: Cd within 0.0005% (F3 allows ±0.5%)"), ("Speedup vs Basic", "−23.4 / −21.7 / −18.6% on 1 / 2 / 4 nodes, on the same machine")]
    w = 2.83
    for i, (head, body) in enumerate(checks):
        x = X0 + i * (w + 0.2)
        card(s, x, 5.42, w, 1.56)
        circle_num(s, x + 0.18, 5.53, 0.34, "✓", fill=NAVY, size=12)
        add_text(s, x + 0.6, 5.49, w - 0.72, 0.42, [head], size=13.5, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.2, 5.95, w - 0.36, 1.0, [body], size=12)
    set_notes(s, NOTES["bonus_results"])
    return s


def slide_bonus_analysis():
    s = reuse(16)
    set_title(s, "BONUS ANALYSIS")
    message(s, [("4% fewer instructions, but ", {}), ("17% fewer refills from DRAM", {"color": BONUS})])
    heading(s, X0, 1.58, 6.9, "Figure", "The first four changes against none", sub="the same build, 1 node, AMD uProf, computation only, 2 jobs each")
    categories = ["L1 refills from DRAM", "L2 accesses incl. prefetch", "L1 data accesses", "Instructions", "Cycles", "Time per step"]
    bar_chart(s, 0.5, 2.25, 7.1, 4.7, categories, [("change", (-17.17, -9.61, -5.85, -4.07, -10.81, -12.28))], point_colors=[BONUS, BONUS_LIGHT, BONUS_LIGHT, FAINT, BONUS_LIGHT, BONUS_LIGHT], number_format='0.0"%";"−"0.0"%"', vmin=-25, vmax=0, font_size=13, label_size=14.5, gap=45, value_axis=False, gridlines=False)
    xr, wr = 7.95, 4.68
    cards = [(1.6, 2.5, "Less bandwidth per core, bigger gain", (("−7.9%", "all 16 channels"), ("−11.4%", "8 of 16 channels")), "the first four changes, 4 nodes, 64 ranks per node (placement experiment)"), (4.3, 2.68, "More data per rank, bigger gain", (("−12.2%", "1 node"), ("−9.3%", "4 nodes")), "the ten later changes against the first four, 3 jobs each, alternated; a rank holds 4× more data on 1 node")]
    for y, h, head, numbers, note in cards:
        card(s, xr, y, wr, h)
        add_text(s, xr + 0.25, y + 0.12, wr - 0.4, 0.4, [head], size=15, color=NAVY, bold=True)
        for k, (number_text, label) in enumerate(numbers):
            add_text(s, xr + 0.25 + k * 2.2, y + 0.6, 2.1, 1.0, [{"runs": [number_text], "size": 28, "color": BONUS, "bold": True}, {"runs": [label], "size": 13, "bold": True}])
        add_text(s, xr + 0.25, y + 1.85, wr - 0.4, h - 1.95, [note], size=12, color=MUTED)
    set_notes(s, NOTES["bonus_analysis"])
    return s


def slide_scaling():
    s = reuse(17)
    set_title(s, "SCALING ANALYSIS")
    message(s, "Faster at 1, 2 and 4 nodes; parallel efficiency 1.00 → 1.15")
    heading(s, X0, 1.58, 6.4, "Figure", "Time per step on 1, 2 and 4 nodes, each job")
    picture(s, fig("p17_scaling"), 0.6, 1.98, w=6.45)
    heading(s, 7.25, 1.58, 5.38, "Table", "Mean time per step")
    rows = [["s/step", "1 node", "2 nodes", "4 nodes", "Efficiency"], ["Baseline", "14.57", "7.43", "3.65", "1.00"], ["Basic", "13.36", "6.37", "2.90", "1.15"], ["Bonus", "10.23", "4.99", "2.36", "1.08"]]
    table(s, 7.25, 1.98, [1.1, 0.9, 1.0, 1.0, 1.38], rows, row_h=0.52, size=13.5, colors=[None, [BASE, INK, INK, INK, INK], [BASIC, INK, INK, BASIC, BASIC], [BONUS, INK, INK, BONUS, BONUS]], bolds=[None, [True, False, False, False, False], [True, False, False, True, True], [True, False, False, True, True]], aligns=["l", "r", "r", "r", "r"])
    items = [[("Basic gains grow with the node count, ", {}), ("mostly from scotch: −1.3 / −2.5 / −10.5%", {"b": True})], [("The source changes gain most on 1 node, ", {}), ("where each rank holds 4× more data", {"b": True}), (": Bonus vs Basic −23% on 1 node, −19% on 4, so its efficiency is 1.08", {})], [("Efficiency above 1 is cache: ", {"b": True}), ("on 4 nodes the cell arrays shrink to 1 MB per rank and fit in L3; DRAM refills per cell −30% (uProf)", {})]]
    bullets(s, 7.25, 4.3, 5.38, 2.68, items, size=14, space_after=12)
    set_notes(s, NOTES["scaling"])
    return s


def slide_not_helped():
    s = reuse(18)
    set_title(s, "WHAT DID NOT HELP, AND WHY")
    message(s, "Proxy metrics improved; the time per step did not")
    heading(s, X0, 1.58, XW, "Table", "Ideas that did not make a step faster")
    rows = [["Idea", "Result (4 nodes)", "Why it did not help"], ["Compiler flags, AOCC, LTO, GCC PGO", "within ±0.13%", "The loops wait on memory, not on instructions"], ["Other MPI transports: OFI, UCX over RC", "−0.16% to +0.77%", "MPI time is waiting for the slowest rank"], ["Reordering ranks: 92% fewer inter-node faces", "+0.1%", "Fewer bytes between nodes do not cut the wait"], ["SMT: 2 ranks per core", "5.7× slower", "Stalls of minutes; cause not isolated"], ["GAMG coarsest level on fewer ranks", "−0.25% to +4.95%", "81% of the global sums, ≈ 0.6% of the time"], ["Weighted cells (×2, ×12), 2-constraint METIS", "+1.5% to +6.1%", "Uneven cells, or more faces between subdomains"], ["Gauss–Seidel overlapped with halo exchange", "+8.3%, Cd −1.2%", "New update order: fails F3, and slower"]]
    table(s, X0, 1.96, [4.75, 2.25, 4.93], rows, row_h=0.44, size=13, bolds=[None] + [[True, False, False]] * 7)
    answer_rows(s, 5.6, [("Why no gain?", "None of them moves fewer bytes, and memory bandwidth sets the speed."), ("Fewer faces?", "Only with even work: scotch −10.5%; 92% fewer faces between nodes alone, +0.1%."), ("Why not combine them?", "Gains we cannot separate from the spread may be luck; stacking them is overfitting.")], step=0.47)
    set_notes(s, NOTES["not_helped"])
    return s


def slide_conclusion():
    s = reuse(19)
    set_title(s, "CONCLUSION")
    message(s, [("1.55× faster on 4 nodes", {"color": BONUS}), (", with the same math", {})])
    w = 3.82
    for i, (number_text, head, sub, nodes, color) in enumerate([("3.65", "Baseline", "case defaults", "14.57 / 7.43 / 3.65", BASE), ("2.90", "Basic  −21%", "unmodified v2512", "13.36 / 6.37 / 2.90", BASIC), ("2.36", "Bonus  −35%", "Cd within 0.0005%", "10.23 / 4.99 / 2.36", BONUS)]):
        x = X0 + i * (w + 0.235)
        card(s, x, 1.58, w, 1.36)
        add_text(s, x + 0.22, 1.58, 1.6, 0.85, [[(number_text, {}), ("\n", {}), ("s/step", {"size": 12, "color": MUTED, "b": False})]], size=32, color=color, bold=True, anchor="m")
        add_text(s, x + 1.72, 1.6, w - 1.85, 0.85, [{"runs": [head], "size": 15, "bold": True, "color": color}, {"runs": [sub], "size": 12}], anchor="m")
        add_text(s, x + 0.22, 2.47, w - 0.4, 0.4, [[("1 / 2 / 4 nodes:  ", {}), (nodes, {})]], size=11.5, color=MUTED, anchor="m")
    heading(s, X0, 3.02, XW, "Table", "What we changed, the bottleneck it removed, and the gain on 4 nodes")
    rows = [["What we changed", "The bottleneck it removes, and the evidence", "vs own control"], ["Pin CPU and memory (Basic)", "Lost binding: 0 of 512 ranks pinned, 9% of memory local", "−11%"], ["scotch, then node mapping (Basic)", "Uneven work near the car: slowest / median 1.16 → 1.06", "−10.5%, −0.7%"], ["multiLevel split (Bonus)", "Faces between nodes −38%, sockets −34%, NUMA −26%", "−1.5%"], ["Four source changes (Bonus)", "Memory bandwidth: half the channels → 2.2× slower", "−9.5%"], ["Ten more source changes (Bonus)", "Passes, copies and global sums left in the Bonus profile", "−9.3%"]]
    table(s, X0, 3.38, [3.85, 5.83, 2.25], rows, row_h=0.38, size=13.5, colors=[None, [BASIC, INK, BASIC], [BASIC, INK, BASIC], [BONUS, INK, BONUS], [BONUS, INK, BONUS], [BONUS, INK, BONUS]], bolds=[None] + [[True, False, True]] * 5, aligns=["l", "l", "c"])
    card(s, X0, 5.82, 6.55, 1.16, fill=TINT)
    add_text(s, X0 + 0.22, 5.86, 6.15, 0.36, ["What remains after the Bonus"], size=14.5, color=NAVY, bold=True)
    bullets(s, X0 + 0.22, 6.22, 6.2, 0.76, ["Memory traffic: fuse U, k and ω assembly for fewer passes", "Imbalance: slow ranks read most from DRAM, so reorder cells"], size=12.5, space_after=2)
    xr = X0 + 6.75
    card(s, xr, 5.82, XW - 6.75, 1.16)
    add_text(s, xr + 0.22, 5.86, XW - 7.2, 0.36, ["How we worked"], size=14.5, color=NAVY, bold=True)
    add_text(s, xr + 0.22, 6.22, XW - 7.2, 0.75, ["Know the noise · fix what is broken first · follow the measured bottleneck · judge by the time per step, not by proxy metrics such as faces or counters"], size=12.5)
    set_notes(s, NOTES["conclusion"])
    return s


def slide_extra():
    s = reuse(20)
    set_title(s, "EXTRA: A GAIN WE DID NOT COUNT")
    message(s, "2.360 → 2.166 s/step and byte-identical, but only with fixed iterations")
    stat(s, X0, 1.6, 4.3, 1.7, "2.360 → 2.166", "s/step on 4 nodes: Bonus → Bonus + this patch", "3 jobs each; the Bonus from its final runs", color=NAVY, num_size=28, label_size=14, sub_size=11.5)
    stat(s, X0, 3.43, 4.3, 1.7, "byte-identical", "coefficient.dat, against the Bonus", "and on the first four changes: 1 / 2 / 4 nodes, all 1,323 log lines", color=NAVY, num_size=28, label_size=14, sub_size=11.5)
    stat(s, X0, 5.26, 4.3, 1.7, "≈ 0.19 s", "of every 2.36 s Bonus step on 4 nodes", "goes to convergence checks that are never used", color=NAVY, num_size=28, label_size=14, sub_size=11.5)
    xr, wr = 5.3, 7.33
    for y, h, head, body in [(1.6, 1.6, "How we found it", "In the call stacks of the Bonus, every sweep of the U, k and ω solvers ends with a residual and a global sum (MPI_Allreduce) for the convergence check. With tolerance 0 the check can never stop a solve, so every result but the last is thrown away."), (3.33, 1.25, "What it does", "The patch computes the residual once, after the last sweep. The residuals and iteration counts in the log stay the same.")]:
        card(s, xr, y, wr, h)
        add_text(s, xr + 0.25, y + 0.08, wr - 0.5, 0.38, [head], size=16, color=NAVY, bold=True)
        add_text(s, xr + 0.25, y + 0.48, wr - 0.5, h - 0.52, [body], size=13.5)
    card(s, xr, 4.71, wr, 2.25)
    add_text(s, xr + 0.25, 4.79, wr - 0.5, 0.38, ["Why it is not in our Bonus"], size=16, color=NAVY, bold=True)
    bullets(s, xr + 0.25, 5.22, wr - 0.5, 1.7, ["It helps only the benchmark's fixed-iteration setting: the case's own fvSolution.fixedTol runs the original code", "The rules prohibit “less work per step”, and the skipped norms could be read as work", "Our fourteen Bonus changes keep every check and help with any convergence setting"], size=13.5, space_after=6)
    set_notes(s, NOTES["extra"])
    return s


# ====================================================================== supporting slides
def supp(i, title, msg, notes_key):
    """Supporting slide on input slide i + 1, or on a new slide when i is None."""
    s = new_slide() if i is None else reuse(i)
    set_title(s, title)
    message(s, msg, size=18)
    set_notes(s, NOTES[notes_key])
    return s


def s_bottlenecks():
    s = supp(23, "BOTTLENECKS WE MEASURED", "What limits a step: placement, balance and memory bandwidth", "s_bottlenecks")
    heading(s, X0, 1.58, XW, "Table", "Each candidate bottleneck, what we measured on 4 nodes, and what we did")
    rows = [["Bottleneck", "Measured on 4 nodes", "Our strategy"], ["Memory placement", "0 of 512 ranks pinned; 9% of a rank's memory local", "Pin CPU and memory (Basic)"], ["Load imbalance", "MPI 46% of the time, mostly waiting for the slowest rank", [[("scotch (Basic), ", {}), ("multiLevel (Bonus)", {"color": BONUS})]]], ["Memory bandwidth", "Half the bandwidth → 2.2× slower; half the cores → no change", "Move fewer bytes (Bonus)"], ["Network", "55% more bandwidth or 92% fewer faces between nodes: no change", "—"], ["Arithmetic", "Compiler flags, another compiler, PGO: within 0.13%", "—"], ["File I/O", "0.01% of a step", "—"], ["OS noise", "0.8% of each core's time", "— (needs root)"]]
    fills = [None] + [[TINT] * 3] * 3 + [[WHITE] * 3] * 4
    colors = [None, [NAVY, INK, BASIC], [NAVY, INK, BASIC], [NAVY, INK, BONUS]] + [[MUTED] * 3] * 4
    bolds = [None] + [[True, False, True]] * 3 + [[True, False, False]] * 4
    table(s, X0, 1.98, [2.4, 6.15, 3.38], rows, row_h=0.6, size=14, fills=fills, colors=colors, bolds=bolds, zebra=False)
    return s


def s_noise():
    s = supp(24, "MEASURING HONESTLY", "Most repeated jobs lie within ±0.4% of their median, but single jobs can be 90% slower", "s_noise")
    heading(s, X0, 1.58, 8.7, "Figure", "Each job against the median of its configuration", sub="same commit, build, nodes and split; shaded: ±0.4%")
    picture(s, fig("fig08_variability"), 0.45, 2.3, w=8.85)
    bullets(s, 9.55, 1.6, 3.08, 5.35, [f"92 jobs in 29 repeated configurations, 21{NBSP}Sep to 5{NBSP}Oct", "Two September jobs were 84% and 91% slower", "So we never decide from one job, and alternate candidate and control", "Step-to-step variation inside a job is not the job-to-job spread: 150 steps are not 150 samples"], size=14.5, space_after=14, anchor="m")
    return s


def s_automation():
    s = supp(25, "EXPERIMENT AUTOMATION", "One commit = one condition; every run is started by GitHub Actions", "s_automation")
    heading(s, X0, 1.58, XW, "Figure", "One condition, from a push to the archived run")
    steps = [("git push or manual run", GREY_TINT), ("select build: reuse if inputs unchanged", TINT), ("build OpenFOAM (1-node job)", TINT), ("prepare case: decomposePar, cached", TINT), ("run job: Allrun chain + simpleFoam", TINT), ("official parser + Cd file", TINT), ("archive raw records + metrics DB", TINT)]
    w, gap = 1.533, 0.2
    for i, (text, fill) in enumerate(steps):
        x = X0 + i * (w + gap)
        box(s, x, 2.02, w, 2.0, fill=fill, line="B8C2D3", radius=0.08)
        circle_num(s, x + w / 2 - 0.2, 2.19, 0.4, str(i + 1), size=13)
        add_text(s, x + 0.06, 2.69, w - 0.12, 1.2, [text], size=13, align="c", anchor="m")
        if i < len(steps) - 1:
            arrow_line(s, x + w + 0.02, 3.02, x + w + gap - 0.02, 3.02, color=MUTED, width=1.25)
    bullets(s, X0, 4.4, XW, 2.58, ["Each condition is a commit (compiler flag, decomposition, patch), so every result traces back to its exact scripts", "Builds and decomposed cases are reused only when their inputs are identical; nothing is shared between clusters", "Profilers run only in separate diagnostic jobs; nothing is measured inside a benchmark's timed solver run", "Several runners submit jobs in parallel, so control and candidate run in the same period"], size=15.5, space_after=18)
    return s


def s_build():
    s = supp(26, "BUILD, STORAGE AND MPI", "Builds and records on Lustre; every node solves from its own local disk", "s_build")
    heading(s, X0, 1.58, XW, "Figure", "Where builds, cases and runs live")
    columns = [(X0, 3.35, GREY_TINT, ["GitHub Actions runner", "team server"]), (4.4, 4.05, TINT, ["ASPIRE-2A login node", "/scratch: Lustre, shared"]), (8.8, 3.83, LIGHT, ["Compute nodes", "$TMPDIR: node-local"])]
    rows_y = [2.72, 3.37, 4.02, 4.67]
    items = {0: {0: f"start build, case and run jobs (ssh{NBSP}+{NBSP}qsub)", 3: "after the job: pack the run, archive it, send metrics to the database"}, 1: {0: "mesh archive (3.2 GB)", 1: "build archive per build (OpenFOAM tree, flags, hashes)", 2: "decomposed case per build and decomposition", 3: f"run directory per run (logs,{NBSP}results,{NBSP}records)"}, 2: {0: "unpack the OpenFOAM build", 1: "copy the decomposed case, restore0Dir", 2: "Allrun chain + simpleFoam: all case I/O stays local", 3: "write logs and coefficient.dat back"}}
    for ci, (x, w, fill, head) in enumerate(columns):
        box(s, x, 1.98, w, 3.42, fill=fill, line="B8C2D3", radius=0.04)
        add_text(s, x, 2.04, w, 0.62, [{"runs": [head[0]], "bold": True, "size": 13.5, "color": NAVY, "align": "c"}, {"runs": [head[1]], "size": 12, "color": MUTED, "align": "c"}])
        for ri, text in items[ci].items():
            shape_text(box(s, x + 0.15, rows_y[ri], w - 0.3, 0.56, fill=WHITE, line=LINE, radius=0.1), text, size=12, color=INK, bold=False, margin=(0.06, 0.02, 0.06, 0.02))

    def mid(ci, ri, side):
        x, w = columns[ci][0], columns[ci][1]
        return (x + 0.15 if side == "l" else x + w - 0.15), rows_y[ri] + 0.28

    for (c1, r1, s1), (c2, r2, s2) in [((0, 0, "r"), (1, 0, "l")), ((1, 1, "r"), (2, 0, "l")), ((1, 2, "r"), (2, 1, "l")), ((2, 3, "l"), (1, 3, "r")), ((1, 3, "l"), (0, 3, "r"))]:
        x1, y1 = mid(c1, r1, s1)
        x2, y2 = mid(c2, r2, s2)
        arrow_line(s, x1 + (0.02 if s1 == "r" else -0.02), y1, x2 + (-0.02 if s2 == "l" else 0.02), y2, color=MUTED, width=1.25)
    bullets(s, X0, 5.58, XW, 1.4, ["Build: official v2512, GCC 11.2 -O3, AMD math library, in a 1-node PBS job; every run records which build it used", "Storage: every node solves from its own copy in $TMPDIR (‑hostRoots, ‑ioRanks); file I/O in the timed steps ≈ 0.01% of the run", "MPI: Cray MPICH 8.1.15 over UCX instead of the default OFI"], size=14)
    return s


def s_reference():
    s = supp(27, "THE ORGANISERS' REFERENCE", "For context only: Basic −12% and Bonus −28% against the organisers' scotch runs", "s_reference")
    heading(s, X0, 1.58, XW, "Figure", "Each job: the organisers' runs and ours, on the same machine", sub="% under our jobs: our mean against the organisers' scotch mean")
    picture(s, fig("ps_reference"), X0, 2.3, w=XW)
    bullets(s, X0, 5.85, XW, 1.12, ["Organisers (tasks 4.3 notes): site module, mpirun with no options, default MPI settings, no binding; their scotch jobs spread by 12% on 4 nodes", "Build, MPI transport and placement all differ, so the gap has more than one cause"], size=14, space_after=6)
    return s


def s_step():
    s = supp(28, "WHERE A STEP GOES AFTER BASIC", "The p and U solves take half a step; assembly and turbulence the rest", "s_step")
    heading(s, X0, 1.58, 7.4, "Figure", "Share of a step, median rank")
    categories = ["rest of the step\n(assembly, gradients, turbulence)", "function objects", "fvOptions", "k solve", "omega solve", "U solve", "p solve (GAMG)"]
    bar_chart(s, 0.5, 1.95, 7.7, 5.0, categories, [("share", (40.46, 1.84, 0.48, 4.25, 4.66, 22.23, 26.07))], point_colors=[FAINT, BASIC, BASIC, BASIC, BASIC, BASIC, BASIC], number_format='0.0"%"', vmin=0, vmax=48, font_size=13, label_size=14, gap=45, value_axis=False, gridlines=False)
    bullets(s, 8.5, 1.6, 4.13, 5.35, ["OpenFOAM's built-in profiling, Basic, 4 nodes, all 512 ranks, 40 steps", "Computation per rank: median 97.95 s, max 104.17 s (max / median 1.063)", "Cell counts do not explain the spread (r = +0.06); wall faces partly (r = +0.43)", "MPI as a whole: 19% of the step for the median rank; region times include the waiting inside them"], size=14, space_after=14, anchor="m")
    return s


def s_path():
    s = supp(29, "THE PATH ON 4 NODES", "Each change against its own control: 3.670 → 2.360 s/step", "s_path")
    heading(s, X0, 1.58, XW, "Figure", "Every step of the path, each job", sub="the start is the case-default split with the binding lost; each % is against the configuration before it (* a few days later), not added up")
    picture_fit(s, fig("ps_path"), X0, 2.3, XW, 4.68)
    return s


def s_network():
    s = supp(30, "IS THE NETWORK THE BOTTLENECK?", "No: four changes to the network side, none made a step more than 0.25% faster", "s_network")
    heading(s, X0, 1.55, XW, "Table", "Four changes to the network side, 4 nodes")
    rows = [["What we changed on the network side", "How much the network side changed", "Step time (4 nodes)"], ["UCX over RC instead of UD between nodes", "IMB bandwidth (1 MiB Sendrecv) 6.7 → 10.4 GB/s, +55%", "−0.01% Basic, −0.16% Bonus of four changes (4 v 4)"], ["Rank reordering, hierarchical split", "92% fewer faces between nodes", "+0.1%"], ["OFI instead of UCX, with the organisers' two workarounds", "Another transport and provider", "+0.77% (3 v 3), +0.50% (1 v 1)"], ["GAMG coarsest level solved on 32 ranks instead of 512", "Fewer ranks in 81% of the global sums", "−0.25% (1 v 1)"]]
    table(s, X0, 1.93, [4.3, 4.3, 3.33], rows, row_h=0.72, size=14.5, bolds=[None] + [[True, False, False]] * 4)
    bullets(s, X0, 5.68, XW, 1.3, ["One 8-byte global sum over 512 ranks takes ≈ 12 µs (IMB): 1,600 per step ≈ 0.02 s, under 1% of a step", "A rank's MPI_Waitall follows its own computation (R² 0.77); adding its neighbours raises that only to 0.80. 13 of the 16 slowest ranks have no neighbours on other nodes", "Not measured: NIC and switch counters"], size=14)
    return s


def s_ofi():
    s = supp(31, "OFI AGAINST UCX", "The organisers' OFI workarounds avoid the crash; UCX stays faster", "s_ofi")
    heading(s, X0, 1.58, XW, "Table", "MPI transport, Basic before the node mapping, 4 nodes")
    rows = [["MPI transport (Basic, 4 nodes)", "Jobs", "s/step", "Against UCX"], ["UCX (what we use)", "3", "2.9176, 2.9168, 2.9246 (mean 2.9197)", "—"], ["OFI with FI_OFI_RXM_USE_SRX=0", "3", "2.9452, 2.9374, 2.9438 (mean 2.9421)", "+0.77%"], ["OFI with FI_VERBS_PREFER_XRC=0", "1", "2.9338 (UCX beside it: 2.9192)", "+0.50%"]]
    table(s, X0, 1.98, [4.3, 0.9, 4.73, 2.0], rows, row_h=0.8, size=15, bolds=[None, [True, False, False, False], [True, False, False, True], [True, False, False, True]], colors=[None, [BASIC, INK, INK, INK], [INK, INK, INK, BAD], [INK, INK, INK, BAD]], aligns=["l", "c", "l", "c"])
    bullets(s, X0, 5.4, XW, 1.58, ["Only the transport changed; alternated in the same period (7 and 9 Oct)", "All jobs VALID, no SIGBUS, the same Cd (0.28404934573921931)", "OFI's own spread is 0.26%, so our small spread does not come from UCX: it comes from the placement"], size=16, space_after=14)
    return s


def s_splits():
    s = supp(32, "THE THREE SPLITS: FACES OR EVEN WORK?", "Fewer faces between nodes alone did not help; evening out the work did", "s_splits")
    heading(s, X0, 1.55, XW, "Figure", "The three splits on 4 nodes: colour = node, shade = NUMA domain")
    for i, (name, faces) in enumerate([("hierarchical (case default)", "4.31 M faces"), ("scotch (Basic)", "2.93 M faces"), ("multiLevel (Bonus)", "2.81 M faces")]):
        add_text(s, X0 + i * XW / 3, 1.93, XW / 3, 0.3, [{"runs": [(name, {"b": True, "color": NAVY}), ("   " + faces, {"color": MUTED, "size": 11.5})], "align": "c"}], size=13)
    picture(s, ASSETS / "decomposition-numa.png", X0, 2.27, w=XW, crop=(0.0, 0.118, 0.0, 0.57))
    heading(s, X0, 4.56, XW, "Table", "Faces and time per step, each change against its own control on 4 nodes")
    rows = [["What changed", "Faces between subdomains", "Faces between nodes", "Work per rank", "Time per step"], ["scotch instead of hierarchical (Basic)", "−32%", "—", "evened (1.16 → 1.06)", "−10.5%"], ["Reordering ranks, hierarchical split", "unchanged", "−92%", "unchanged", "+0.1%"], ["scotch mapped onto the node (Basic)", "+3.3%", "−23%", "—", "−0.7%"], ["multiLevel instead of scotch (Bonus)", "−3.9%", "−38%", "—", "−1.5%"], ["METIS with two constraints (Bonus)", "+18%", "—", "—", "+1.5%"]]
    table(s, X0, 4.94, [3.75, 1.85, 1.75, 3.08, 1.5], rows, row_h=0.31, size=12, row_heights=[0.46] + [0.31] * 5, bolds=[None] + [[True, False, False, False, True]] * 5, aligns=["l", "c", "c", "c", "c"], margins=(0.08, 0.03, 0.08, 0.03))
    return s


def s_cores():
    s = supp(33, "CORES OR MEMORY?", "Halving the cores changes nothing; halving the memory channels slows a step 2.2×", "s_cores")
    heading(s, X0, 1.58, XW, "Table", "Time per step under three placements, 4 nodes, 2 jobs each")
    rows = [["s/step (4 nodes, 2 jobs each)", "full128", "spread64", "packed64", "spread64 / full128", "packed64 / spread64"], ["Basic (before the mapping)", "2.920", "2.887", "6.347", "0.99", "2.20"], ["Bonus without the patches", "2.869", "2.874", "6.321", "1.00", "2.20"], ["Bonus, first four changes", "2.595", "2.649", "5.598", "1.02", "2.11"], ["Triad bandwidth per node", "274 GB/s", "279 GB/s", "125 GB/s", "—", "0.45"]]
    table(s, X0, 1.98, [3.5, 1.45, 1.5, 1.5, 1.95, 2.03], rows, row_h=0.58, size=14.5, bolds=[None] + [[True, False, False, False, True, True]] * 4, colors=[None] + [[INK, INK, INK, INK, NAVY, BAD]] * 4, aligns=["l", "r", "r", "r", "r", "r"])
    add_text(s, X0, 5.0, 5.85, 0.36, ["The three placements"], size=15, color=NAVY, bold=True)
    bullets(s, X0, 5.4, 5.85, 1.58, ["full128: 128 ranks per node, as submitted", "spread64: 64 ranks per node, 4 per L3, on all 16 L3s and all 16 memory channels", "packed64: the same 64 ranks and split, 8 per L3, on 8 L3s and 8 channels"], size=14)
    add_text(s, 6.78, 5.0, 5.85, 0.36, ["What it shows"], size=15, color=NAVY, bold=True)
    bullets(s, 6.78, 5.4, 5.85, 1.58, ["Half the cores: ×0.99–1.02, no change", "Half the channels: ×2.11–2.20, as the triad bandwidth drops ×2.22", "Limit: packed64 also halves the L3, so DRAM bandwidth and L3 capacity are not separated"], size=14)
    return s


def s_changes():
    s = supp(34, "THE SOURCE CHANGES (1/2)", "The first four remove data movement, never an operation or its order", "s_changes")
    heading(s, X0, 1.55, XW, "Table", "The first four patches (full text: bonus/patches/0001–0004 in the submission)")
    rows = [["Change (patch)", "What it removes", "Why the result is the same"], ["No copies in the solvers (0001)", "smoothSolver built each residual in a new field and copied it; GAMG copied the source, then subtracted", "The same function computes the same residual in place; source − A·psi is the same subtraction per cell"], ["U components in one pass (0002)", "Gauss–Seidel read the shared matrix of U three times, once per component", "The components are independent; each sees the same operations in the same order"], ["No unused boundary updates (0003)", "Six callers built boundary values of a surface integral, exchanged them, and used only the cell values", "The cell values come from the same loop; only values nobody reads are skipped"], ["Fused face loops (0004)", "Interpolated face fields and product fields built before every summation", "The same face expressions, evaluated inside the summation loop in the same face order"]]
    table(s, X0, 1.93, [3.05, 4.5, 4.38], rows, row_h=0.94, size=13.5, bolds=[None] + [[True, False, False]] * 4, colors=[None] + [[BONUS, INK, INK]] * 4, row_heights=[0.5, 1.1, 1.1, 1.1, 1.1])
    return s


def s_changes2():
    s = supp(None, "THE SOURCE CHANGES (2/2)", "Ten more: none changes the iterations, the convergence tests or the discretisation", "s_changes2")
    heading(s, X0, 1.55, XW, "Table", "The ten later patches (0006, 0008–0016); F3: rounding can change, so Cd is checked")
    f3 = ("F3: ", {"b": True, "color": NAVY})
    rows = [["Change (patch)", "What it removes", "Why the result is the same"], ["Laplacian coefficients with the diagonal (0006)", "A temporary product field, its copy and a re-read of upper", "The same operations per face in the same order"], ["Pressure reference decided once (0008)", "Patch loops and a global sum per step that did nothing here", "The same cells get the same change whenever one is needed"], ["Viscous stress in one pass (0009)", "Three whole-field passes for nuEff · dev2(T(grad U))", "The same operations on the same operands in the same order"], ["Wall shear stress on the walls only (0010)", "A full-volume field of which only the wall values were read", "The same expression on the walls, as the forces object uses"], ["Gauss–Seidel without the source copy (0011)", "A copy of the source into a work array in every sweep", [[f3, ("the same terms, but the source is added last", {})]]], ["One global sum per CG iteration (0012)", "Two of three global sums per iteration on the coarsest level", [[f3, ("the same iterates in exact arithmetic", {})]]], ["Turbulence model in single cell loops (0013)", "67 of the 80 passes over the cells per k-ω SST update", "The same operations in the same association, no new FMAs"], ["No zero fill of overwritten coefficients (0014)", "Zero fills of face coefficients, a copy of the U matrix", "No arithmetic changes"], ["GAMG correction and restriction in place (0015)", "Two passes over the finest level per V-cycle", "The same operations and summation order"], ["Gauss–Seidel residual from the sweep (0016)", "A matrix pass and a halo exchange per component and iteration", [[f3, ("still formed and tested every iteration", {})]]]]
    table(s, X0, 1.93, [3.95, 4.15, 3.83], rows, row_h=0.46, size=11.5, row_heights=[0.4] + [0.46] * 10, bolds=[None] + [[True, False, False]] * 10, colors=[None] + [[BONUS, INK, INK]] * 10, margins=(0.08, 0.03, 0.08, 0.03))
    return s


def detail_slide(s, title, msg, cards):
    clear_slide(s)
    set_title(s, title)
    message(s, msg, size=18)
    for i, (number_text, name, functions, lines, result) in enumerate(cards):
        x = X0 + i * 6.08
        card(s, x, 1.6, 5.85, 5.38)
        shape_text(box(s, x + 0.25, 1.8, 0.85, 0.36, fill=BONUS, radius=0.5), number_text, size=12)
        add_text(s, x + 1.25, 1.74, 4.45, 0.48, [name], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.25, 2.34, 5.35, 0.62, [{"runs": [f]} for f in functions], size=13, color=MUTED)
        bullets(s, x + 0.25, 3.12, 5.35, 2.95, lines, size=14.5, space_after=10)
        box(s, x + 0.18, 6.2, 5.49, 0.58, fill=BONUS_TINT, radius=0.5)
        add_text(s, x + 0.4, 6.2, 5.1, 0.58, [result], size=15.5, color=BONUS, bold=True, anchor="m")
    set_notes(s, NOTES["s_detail"])
    return s


def s_detail1():
    cards = [("0001", "No copies in the solvers", ["smoothSolver::scalarSolve", "GAMGSolver::solve"], ["Before: residual = matrix_.residual(...) builds a new field, then copies it", "After: matrix_.residual(residual, ...) writes into the existing buffer", "GAMG: source − A·psi in one pass instead of a copy and a subtraction"], "2.873 → 2.776 s/step (−3.39%, 4 v 4 jobs)"), ("0002", "U components in one pass", ["fvMatrix::solveSegregated", "solveGaussSeidelComponents"], ["Before: one complete solve per component, each reading the matrix", "After: each face coefficient serves Ux, Uy and Uz in one sweep", "Shared: lower and upper coefficients and the addressing; per component: diagonal, source, norms", "Falls back to the original path when the solver or field type does not match"], "2.781 → 2.718 s/step (−2.29%, 3 v 3 jobs)")]
    return detail_slide(S[35], "SOURCE CHANGES IN DETAIL (1/2)", "No copies, and the U matrix read once instead of three times", cards)


def s_detail2():
    cards = [("0003", "No unused boundary updates", ["fvc::surfaceIntegrateInternal", "gaussConvectionScheme::fvmDiv"], ["Return the internal cell values directly; skip building and evaluating output boundaries that nobody reads", "Input boundary contributions are kept", "Build lower, upper and diagonal in one face loop", "Used at six call sites, including pEqn.H and kOmegaSST"], "2.708 → 2.672 s/step (−1.31%, 3 v 3 jobs)"), ("0004", "Fused face loops", ["gaussGrad / addLinearFaceSums", "surfaceIntegrateInternal(a, b)"], ["Interpolate while adding the gradient's face sums", "Multiply the two fields inside the integration loop", "No temporary surface fields and no re-reads; boundaries, volume division and order kept", "Non-linear interpolation keeps the original path"], "2.675 → 2.599 s/step (−2.82%, 3 v 3 jobs)")]
    return detail_slide(S[36], "SOURCE CHANGES IN DETAIL (2/2)", "No unused boundary values, and no temporary face fields", cards)


def s_each():
    s = supp(37, "EFFECT OF EACH BONUS CHANGE", "Each change against the configuration just before it; separate experiments, not added up", "s_each")
    heading(s, X0, 1.58, 6.4, "Figure", "Each change against the one before, 4 nodes")
    picture(s, fig("ps_each"), X0 - 0.05, 1.98, w=6.4)
    heading(s, 7.25, 1.58, 5.38, "Table", "Change per step, 1 / 2 / 4 nodes")
    rows = [["Change", "1 node", "2 nodes", "4 nodes"], ["multiLevel vs scotch", "−0.45%", "−0.38%", "−1.54%"], ["0001 no copies", "−2.19%", "−2.94%", "−3.39%"], ["0002 U in one pass", "−6.39%", "−4.13%", "−2.29%"], ["0003 no unused values", "−1.40%", "−1.88%", "−1.31%"], ["0004 fused face loops", "−2.88%", "−2.29%", "−2.82%"], ["0006, 0008–0010", "", "", "−1.99%"], ["0011 GS without copy", "", "", "−1.04%"], ["0012 one sum per CG", "", "", "−0.30%"], ["0013–0015 *", "", "", "−2.48%"], ["0016 sweep residual *", "", "", "−3.80%"], ["0006–0016, alternated", "−12.16%", "−11.44%", "−9.34%"]]
    table(s, 7.25, 1.98, [2.25, 1.05, 1.04, 1.04], rows, row_h=0.34, size=12, bolds=[None] + [[True, False, False, True]] * 10 + [[True, True, True, True]], colors=[None] + [[INK, INK, INK, BONUS]] * 10 + [[BONUS] * 4], aligns=["l", "r", "r", "r"], margins=(0.08, 0.02, 0.08, 0.02))
    bullets(s, 7.25, 6.12, 5.38, 0.86, ["4 nodes: 3–4 jobs each; * measured a few days after its control. Most 1- and 2-node values are single jobs", "coefficient.dat is bit-identical for every change but 0011 and 0012, which move Cd by under 0.001% (F3)"], size=11.5, space_after=3)
    return s


def s_profiles():
    s = supp(38, "PROFILES BEFORE AND AFTER", "The first four changes shorten the computation by 9% and leave MPI as it was", "s_profiles")
    heading(s, X0, 1.58, 7.4, "Figure", "Seconds per rank in 40 steps (mean of 512 ranks)")
    categories = ["Bonus, first four changes\n118.5 s, MPI 19.9%", "multiLevel + no copies only\n127.6 s, MPI 18.3%", "Basic (scotch)\n137.6 s, MPI 19.4%"]
    series = [("computation", (94.94, 104.25, 110.83)), ("MPI_Allreduce", (11.35, 11.01, 12.89)), ("MPI_Waitall", (8.45, 8.78, 10.25)), ("other MPI", (3.73, 3.60, 3.61))]
    bar_chart(s, 0.5, 1.95, 7.6, 5.0, categories, series, colors=["A9BCDD", "A26C97", "C7A3C2", "E5D3E2"], stacked=True, number_format="0.0", vmin=0, vmax=140, font_size=12.5, label_size=13, gap=55, overlap=100, legend=XL_LEGEND_POSITION.BOTTOM, value_axis=False, gridlines=False, label_pos="ctr", labelled=(0,))
    bullets(s, 8.45, 1.6, 4.18, 5.35, ["CrayPAT diagnostic runs, 4 nodes, 512 ranks, 40 steps", "Computation per rank 104.2 → 94.9 s from the first change alone to the first four; MPI stays ≈ 23.5 s", "The spread between ranks stays: max / median 1.074 → 1.067; the whole distribution moves down by about 9%", "Not profiled with CrayPAT: the final Bonus, whose 0012 and 0016 also cut global sums and halo exchanges"], size=14, space_after=12, anchor="m")
    return s


def s_efficiency():
    s = supp(39, "WHY THE EFFICIENCY EXCEEDS 1", "On 4 nodes the cell arrays fit in L3: 30% fewer DRAM refills per cell", "s_efficiency")
    heading(s, X0, 1.58, XW, "Table", "Per cell and step, Basic before the node mapping, AMD uProf")
    rows = [["Per cell and step (Basic, uProf)", "1 node", "2 nodes", "4 nodes", "4 nodes / 1 node"], ["Cycles", "24,235", "22,860", "20,418", "0.843"], ["L1 demand refills from DRAM", "24.6", "20.7", "17.1", "0.697"], ["L1 demand refills from L3 (same CCX)", "5.4", "6.3", "9.4", "1.75"]]
    table(s, X0, 1.98, [4.7, 1.6, 1.6, 1.6, 2.43], rows, row_h=0.62, size=15.5, bolds=[None] + [[True, False, False, False, True]] * 3, colors=[None, [INK, INK, INK, INK, NAVY], [INK, INK, INK, INK, NAVY], [INK, INK, INK, INK, NAVY]], aligns=["l", "r", "r", "r", "r"])
    bullets(s, X0, 4.7, XW, 2.28, ["AMD uProf data_access, one rank per NUMA domain, normalised by ranks, steps and cells per rank", f"The sparse-matrix kernels gather cell arrays in face order: their DRAM refills fall to 0.30{NBSP}(Gauss–Seidel), 0.40{NBSP}(residual) and 0.42{NBSP}(A·x); a loop that streams cell fields stays at 0.95", "Cell arrays per rank: 4 MB on 1 node, 2 MB on 2, 1 MB on 4, against 4 MB of L3 per core; the face arrays (≈ 16 MB) never fit", "The same counters explain the imbalance left: a rank's cycles follow its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24)"], size=14.5, space_after=10)
    return s


def s_cd():
    s = supp(40, "DRAG COEFFICIENT CHECKS", "Cd depends on the split; the Bonus is within 0.0005% of its own baseline", "s_cd")
    heading(s, X0, 1.58, XW, "Table", "Cd at the last step, 1 / 2 / 4 nodes")
    rows = [["Steps", "OHC-1 values", ["Baseline", "(hierarchical)"], ["scotch", "defaults"], ["Basic", "(mapped scotch)"], ["Bonus", "(multiLevel)"]], ["40", "0.433 – 0.436", "0.43305", "0.43599", "0.43958", "0.43828"], ["80", "0.334 – 0.345", "0.33733", "0.32714", "0.33410", "0.32286"], ["150", "0.284 – 0.292", "0.27356", "0.28405", "0.29302", "0.29139"]]
    table(s, X0, 1.98, [1.0, 2.0, 2.45, 1.95, 2.35, 2.18], rows, row_h=0.7, size=16, row_heights=[0.8, 0.62, 0.62, 0.62], colors=[None] + [[INK, MUTED, BASE, INK, BASIC, BONUS]] * 3, bolds=[None] + [[True, False, False, False, True, True]] * 3, aligns=["c"] * 6)
    bullets(s, X0, 4.82, XW, 2.16, ["The Bonus against the same split with unchanged source: +1.2 × 10⁻¹² (relative), −0.00002% and −0.00041% on 1 / 2 / 4 nodes, more than 1,000 times inside F3's ±0.5%", "The organisers' notes: hierarchical and scotch differ by 0.7 / 3.0 / 3.5% at 40 / 80 / 150 steps; the node mapping moves Cd by +0.8 / +2.1 / +3.2%, within that", "Same split as the organisers: our 150-step Cd is 0.284049 against their 0.283983 (2.3 × 10⁻⁴). With the site module and our scripts we get their value exactly, so the difference is our build (AMD's math library), not the method", "Every job of the same configuration and node count produced a byte-identical coefficient.dat"], size=14, space_after=6)
    return s


def s_repro():
    s = supp(41, "REPRODUCING OUR RESULTS", "The submitted scripts, run from public sources: same Cd, times within 0.4%", "s_repro")
    heading(s, X0, 1.58, XW, "Table", "Re-runs with the submitted scripts against our recorded means")
    rows = [["Configuration", "Nodes", "s/step", "Recorded mean", "Change", "coefficient.dat"], ["Basic (2026-10-16)", "1", "13.413150", "13.364504", "+0.36%", "identical"], ["Basic (2026-10-16)", "2", "6.390324", "6.371748", "+0.29%", "identical"], ["Basic (2026-10-16)", "4", "2.904620", "2.897638", "+0.24%", "identical"], ["Bonus (2026-10-26)", "1", "10.201813", "10.233606", "−0.31%", "identical"], ["Bonus (2026-10-26)", "2", "4.980185", "4.992196", "−0.24%", "identical"], ["Bonus (2026-10-26)", "4", "2.365118", "2.359976", "+0.22%", "identical"]]
    table(s, X0, 1.98, [2.85, 1.0, 2.0, 2.2, 1.6, 2.28], rows, row_h=0.58, size=15, colors=[None] + [[BASIC, INK, INK, INK, INK, INK]] * 3 + [[BONUS, INK, INK, INK, INK, INK]] * 3, bolds=[None] + [[True, False, False, False, False, True]] * 6, aligns=["l", "c", "r", "r", "r", "c"])
    bullets(s, X0, 6.2, XW, 0.78, ["build/build.pbs builds from the official public sources (the Bonus with bonus/patches); run/submit.sh 1|2|4 runs the whole Allrun chain with plain qsub", "Every step ended with End and returned 0; every solve job reported bound=128/128 on every node"], size=13.5)
    return s


def s_rejected():
    s = supp(42, "NOT ADOPTED: THE FULL LIST", "What we tried, what happened, and what we learned", "s_rejected")
    heading(s, X0, 1.55, XW, "Table", "Every idea we did not adopt: Basic, then Bonus, then other ideas")
    rows = [["Idea (tier)", "Result, 4 nodes", "Why it did not help"], ["-march=znver3, AOCC 5.0, -O2, LTO (Basic)", "within ±0.1%", "The loops wait on memory, not on instructions"], ["GCC profile-guided optimisation (Basic)", "+0.13% (+0.08% on 1 node)", "The same; Cd bit-identical"], ["Default OFI with the organisers' workarounds (Basic)", "+0.77% (3 v 3), +0.50% (1 v 1)", "Not faster than UCX; same Cd, no SIGBUS"], ["UCX over RC instead of UD between nodes", "−0.01% Basic, −0.16% early Bonus", "IMB bandwidth +55%; steps do not wait on transfers"], ["OpenFOAM comm switches (topoControl, nbx, pbufs)", "no gain; commsType scheduled crashed", "MPI time is waiting for the slowest rank"], ["Rank reordering (MPICH_RANK_REORDER_METHOD=3)", "+0.1%, 92% fewer faces between nodes", "Fewer bytes between nodes do not shorten the wait"], ["glibc malloc thresholds (Basic)", "−0.4% (3 jobs)", "Too small to separate with 3 jobs; not re-tested"], ["SMT, 2 ranks per core (Basic)", "≈ 5.7× slower", "Stalls of minutes; cause not isolated"], ["GAMG coarsest level on fewer ranks (Bonus)", "−0.25% to +4.95%", "81% of the global sums, but ≈ 0.6% of the time"], ["Weighted cells (×2, ×12), METIS two constraints (Bonus)", "+1.5% to +6.1%", "Uneven cells, or 18% more processor faces"], ["Gauss–Seidel overlapped with its halo exchange (Bonus)", "+8.32% (3 v 3), Cd −1.20%", "Fails F3: Cd moves far beyond rounding"], ["bound() averaging only the bounded cells (Bonus)", "not run", "An extra global sum per call costs more than it saves"], ["Overlapping halo exchange with computation", "under 1% available", "Led to skipping unused exchanges instead (0003)"], ["File I/O in the timed steps", "≈ 0.01% of a step", "Not a factor"]]
    table(s, X0, 1.9, [4.7, 3.25, 3.98], rows, row_h=0.33, size=10.5, row_heights=[0.36] + [0.33] * 14, bolds=[None] + [[True, False, False]] * 14, margins=(0.08, 0.02, 0.08, 0.02))
    return s


def s_compiler():
    s = reuse(43)
    set_title(s, "COMPILER AND FLAGS")
    message(s, "Every compiler and flag variant lies inside the control's range", size=18)
    heading(s, X0, 1.58, XW, "Figure", "Each compiler and flag variant against the control, 4 nodes, each job", sub="scotch, 3 jobs each in the same period (2026-10-03); shaded: the range of the control jobs. GCC PGO, run separately: +0.13%")
    picture_fit(s, fig("fig07_compiler_options"), X0, 2.3, XW, 4.68)
    set_notes(s, NOTES["s_compiler"])
    return s


def fill_index(s, entries):
    """Q&A index: one clickable line per supporting slide; call after the slide order is final."""
    set_title(s, "Q&A INDEX")
    message(s, "Supporting slides for questions: click a line to jump there", size=18)
    groups = [(0, "Method and setup", entries[0:5]), (0, "Basic, and what limits it", entries[5:11]), (1, "Bonus", entries[11:17]), (1, "Results, and what we did not use", entries[17:])]
    next_y = [1.6, 1.6]
    for column, group_name, items in groups:
        x, y0 = (X0, 6.78)[column], next_y[column]
        add_text(s, x, y0, 5.85, 0.38, [group_name], size=16, color=NAVY, bold=True)
        for k, (title, target) in enumerate(items):
            line = add_text(s, x + 0.1, y0 + 0.44 + k * 0.38, 5.75, 0.35, [[(f"{prs.slides.index(target) + 1}", {"b": True, "color": NAVY}), ("   " + title, {})]], size=14, anchor="m")
            line.click_action.target_slide = target
        next_y[column] = y0 + 0.44 + len(items) * 0.38 + 0.3
    set_notes(s, NOTES["index"])


def slide_reproducibility():
    """The shared reproducibility slide (the team's), with our patch list brought up to the final Bonus."""
    s = S[44]
    replace_run_text(s, "Compact_OFBuildBody", "Apply 0001 / 0002 / 0003 / 0004 in order", "Apply 0001–0004, 0006, 0008–0016 in order")
    return s


# ====================================================================== assemble
main = [slide_title(), slide_overview(), slide_aspire(), slide_baseline_settings(), slide_baseline_results(), slide_measure(), slide_mpi_profile(), slide_baseline_analysis(), slide_strategy(), slide_basic_pinning(), slide_basic_decomp(), slide_basic_results(), slide_bandwidth(), slide_roofline(), slide_bonus_opt(), slide_bonus_results(), slide_bonus_analysis(), slide_scaling(), slide_not_helped(), slide_conclusion(), slide_extra()]
divider = S[21]
COUNT.update(Figure=0, Table=0)
SERIES[0] = "S"
supporting = [("Bottlenecks we measured", s_bottlenecks()), ("Measuring honestly", s_noise()), ("Experiment automation", s_automation()), ("Build, storage and MPI", s_build()), ("The organisers' reference", s_reference()), ("Where a step goes after Basic", s_step()), ("The path on 4 nodes", s_path()), ("Is the network the bottleneck?", s_network()), ("OFI against UCX", s_ofi()), ("The three splits: faces or even work?", s_splits()), ("Cores or memory?", s_cores()), ("The source changes (1/2): the first four", s_changes()), ("The source changes (2/2): ten more", s_changes2()), ("Source changes in detail (1/2)", s_detail1()), ("Source changes in detail (2/2)", s_detail2()), ("Effect of each Bonus change", s_each()), ("Profiles before and after", s_profiles()), ("Why the efficiency exceeds 1", s_efficiency()), ("Drag coefficient checks", s_cd()), ("Reproducing our results", s_repro()), ("Not adopted: the full list", s_rejected()), ("Compiler and flags", s_compiler())]
index_slide = reuse(22)
order = main + [divider, index_slide] + [sl for _, sl in supporting] + [slide_reproducibility()] + S[AI:]

sldIdLst = prs.slides._sldIdLst
by_part = {prs.part.related_part(sldId.rId): sldId for sldId in sldIdLst}
assert len(order) == len(by_part) == len({sl.part for sl in order}), (len(order), len(by_part))
for sldId in list(sldIdLst):
    sldIdLst.remove(sldId)
for sl in order:
    sldIdLst.append(by_part[sl.part])
fill_index(index_slide, supporting)

# the co-authoring change log lists the old slide ids
for rId, rel in list(prs.part.rels.items()):
    if "changesInfo" in rel.reltype:
        prs.part.rels.pop(rId)

prs.save(OUT)
print("saved", OUT, "with", len(prs.slides), "slides")
for i, sl in enumerate(prs.slides, 1):
    print(f"{i:2d} {sl.shapes.title.text_frame.text[:60] if sl.shapes.title is not None else ''}")
