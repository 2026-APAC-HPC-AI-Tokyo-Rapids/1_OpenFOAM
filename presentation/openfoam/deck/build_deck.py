# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0", "lxml", "pillow", "xlsxwriter"]
# ///
"""Rebuild the OpenFOAM (HPC) part of the team deck from the 10/15 team deck.

usage: uv run build_deck.py INPUT.pptx OUTPUT.pptx FIGDIR

INPUT is the team deck as of 2026-10-15 (35 slides: OpenFOAM 1-24, AI track 25-31, acknowledgements and supporting slides 32-35).
FIGDIR holds caption-free renders of ../figures.py (figures_nocaption.py). build.sh runs both steps.
The output keeps every slide from the AI title slide on byte for byte, and puts the shared reproducibility slide (input 24) before it.
"""

import copy
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.chart import XL_LEGEND_POSITION

from decklib import BASE, BASIC, BONUS, FAINT, GREEN, INK, LIGHT, LINE, MUTED, NAVY, RED, TINT, WHITE, add_sldnum, add_text, arrow_line, bar_chart, block_arrow, box, bullets, circle_num, clear_slide, picture, picture_fit, remove_body_placeholders, set_notes, set_title, shape_info, shape_text, table
from notes import NOTES

SRC, OUT, FIG = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
prs = Presentation(SRC)
S = list(prs.slides)  # S[i] is input slide i + 1
X0, XW = 0.70, 11.93  # left edge and width of the content area
ORANGE_TINT = "FDF1E4"
GREY_TINT = "F1F1F1"
DECOMP_COLUMNS = {"hier": (0.0, 0.667), "scotch": (0.333, 0.334)}
PANEL_TOP, PLANE_BOTTOM, ALL_BOTTOM = 0.113, 0.346, 0.085


def check_input():
    titles = [s.shapes.title.text_frame.text if s.shapes.title is not None else "" for s in S]
    first_text = " ".join(sh.text_frame.text for sh in S[24].shapes if sh.has_text_frame)
    if len(S) != 35 or titles[1] != "OpenFOAM TASK OVERVIEW" or titles[15] != "SUPPORTING INFORMATION" or "AI Track" not in first_text:
        raise SystemExit("build_deck.py expects the 2026-10-15 team deck (35 slides, OpenFOAM 1-24, AI title slide at 25); see README.md")


check_input()
LAYOUT = S[1].slide_layout
SLDNUM = copy.deepcopy(next(el for el in S[13].shapes._spTree if shape_info(el)[1] == "sldNum"))
DECOMP = next(sh for sh in S[14].shapes if sh.name == "図 6").image.blob  # hierarchical, scotch, multiLevel x car, centre plane, cross-section


def fig(name):
    return FIG / f"{name}.png"


def new_slide():
    s = prs.slides.add_slide(LAYOUT)
    remove_body_placeholders(s)
    add_sldnum(s, SLDNUM)
    return s


def message(s, runs, size=20):
    return add_text(s, X0, 0.94, XW, 0.5, [runs], size=size, color=NAVY, bold=True, name="Message")


def caption(s, text, x=X0, y=6.55, w=XW, h=0.32, size=11, color=MUTED, align="l", italic=False):
    return add_text(s, x, y, w, h, [[(text, {"i": italic})]], size=size, color=color, align=align, name="Caption")


def lesson(s, text, x=X0, y=6.43, label="LESSON"):
    w = min(XW, 1.15 + 0.1 * len(label) + 0.122 * len(text))
    box(s, x, y, w, 0.46, fill=TINT, radius=0.5, name="Lesson")
    add_text(s, x + 0.22, y, w - 0.3, 0.46, [[(label + "   ", {"b": True, "size": 11}), (text, {"b": True, "size": 14})]], color=NAVY, anchor="m", name="LessonText")


def card(s, x, y, w, h, fill=LIGHT, line=None):
    return box(s, x, y, w, h, fill=fill, line=line, radius=0.05)


def stat(s, x, y, w, h, number, label, sub=None, color=NAVY, num_size=34, label_size=14, sub_size=12):
    card(s, x, y, w, h)
    paras = [{"runs": [number], "size": num_size, "color": color, "bold": True, "line": 0.95}, {"runs": [label], "size": label_size, "bold": True, "space_before": 2}]
    if sub:
        paras.append({"runs": [sub], "size": sub_size, "color": MUTED, "space_before": 2})
    add_text(s, x + 0.22, y, w - 0.44, h, paras, color=INK, anchor="m")


def label_value_table(s, x, y, col_w, rows, row_h=0.6, size=14):
    return table(s, x, y, col_w, rows, row_h=row_h, size=size, header=False, bolds=[[True, False]] * len(rows), colors=[[NAVY, None]] * len(rows))


def decomp_panel(s, which, x, y, w=None, h=None, bottom=PLANE_BOTTOM):
    left, right = DECOMP_COLUMNS[which]
    return picture(s, DECOMP, x, y, w, h, crop=(left, PANEL_TOP, right, bottom))


# ====================================================================== main part
def slide_title():
    set_notes(S[0], NOTES["title"])
    return S[0]


def slide_overview():
    s = S[1]
    clear_slide(s, keep=("flow-iterations", "図 5"))
    set_title(s, "OpenFOAM TASK OVERVIEW")
    message(s, "Make the same math faster: same mesh, same solver, same work")
    rows = [("Case", ["Steady flow around a car at 140 km/h", "\n", "simpleFoam (k-ω SST), OpenFOAM v2512"]), ("Mesh", ["occDrivAerStaticMesh: 65.3 M cells,", "\n", "finest near the car; the mesh is fixed"]), ("Step", ["Fixed solver iterations", "\n", "→ the same work in every step"]), ("Metric", ["Average time per step on 4 nodes (steps 2–150)", "\n", "1 / 2 / 4 nodes for scaling: 40 / 80 / 150 steps"])]
    for i, (label, value) in enumerate(rows):
        add_text(s, X0, 1.62 + i * 0.76, 1.25, 0.66, [label], size=16, color=NAVY, bold=True)
        add_text(s, 1.95, 1.62 + i * 0.76, 5.6, 0.66, [value], size=15)
    for sh in s.shapes:
        if sh.name == "flow-iterations":
            sh.left, sh.top, sh.width, sh.height = [int(v * 914400) for v in (7.85, 1.6, 4.78, 2.689)]
        if sh.name == "図 5":
            sh.left, sh.top, sh.width, sh.height = [int(v * 914400) for v in (7.85, 4.75, 4.78, 4.78 * 638 / 2764)]
    caption(s, "Flow around the car (ParaView, a separate run)", x=7.85, y=4.36, w=4.78, h=0.3)
    caption(s, "Mesh: refinement level of the 65,334,765 cells", x=7.85, y=5.95, w=4.78, h=0.3)
    card(s, X0, 4.78, 6.85, 2.02)
    add_text(s, X0 + 0.25, 4.88, 6.3, 0.34, [[("Our result on 4 nodes", {"b": True, "color": NAVY}), ("   s / step, lower is better", {"color": MUTED, "size": 12})]], size=15)
    for i, (number, name, delta, color) in enumerate([("3.65", "Baseline", "", BASE), ("2.90", "Basic", "−21 %", BASIC), ("2.60", "Bonus", "−29 %", BONUS)]):
        x = X0 + 0.25 + i * 2.2
        add_text(s, x, 5.22, 1.8, 0.62, [number], size=34, color=color, bold=True)
        add_text(s, x, 5.86, 1.85, 0.34, [[(name + "  ", {"b": True}), (delta, {"color": color, "b": True})]], size=14)
        if i < 2:
            block_arrow(s, x + 1.55, 5.38, 0.4, 0.32, color="B8C2D3")
    add_text(s, X0 + 0.25, 6.28, 6.4, 0.36, [[("1.40× faster", {"b": True, "color": NAVY}), (" with the same build, scripts and measurement", {"color": MUTED})]], size=13)
    set_notes(s, NOTES["overview"])
    return s


def node_diagram(s, x, y, w, h):
    """One ASPIRE-2A node as the job sees it: 2 sockets x 4 NUMA domains, each 16 cores with 2 memory channels."""
    box(s, x, y, w, h, fill="F7F8FA", line=LINE, radius=0.04)
    add_text(s, x + 0.15, y + 0.06, w - 0.3, 0.3, ["One node: 2 sockets × 4 NUMA domains × 16 cores"], size=11, color=NAVY, bold=True)
    socket_w, socket_h = (w - 0.45) / 2, h - 0.52
    numa_w, numa_h = (socket_w - 0.3) / 2, (socket_h - 0.42) / 2
    for k in range(2):
        sx, sy = x + 0.15 + k * (socket_w + 0.15), y + 0.42
        box(s, sx, sy, socket_w, socket_h, fill=WHITE, line="B8C2D3", radius=0.04)
        add_text(s, sx + 0.1, sy + 0.04, socket_w - 0.2, 0.26, [f"socket {k}"], size=10, bold=True)
        for r in range(2):
            for c in range(2):
                domain = 4 * k + 2 * r + c
                nx, ny = sx + 0.1 + c * (numa_w + 0.1), sy + 0.32 + r * (numa_h + 0.06)
                box(s, nx, ny, numa_w, numa_h, fill=TINT, radius=0.06)
                add_text(s, nx, ny, numa_w, numa_h, [{"runs": [f"NUMA {domain}"], "size": 10.5, "bold": True, "color": NAVY}, {"runs": ["16 cores, 2 channels"], "size": 9}], align="c", anchor="m")


def slide_aspire():
    s = S[2]
    clear_slide(s)
    set_title(s, "ASPIRE-2A")
    message(s, "8 NUMA domains per node; 16 cores already fill the bandwidth")
    rows = [["Processor", "2 × EPYC 7713 (Zen 3): 128 cores, 2.0 GHz"], ["NUMA, cache", "8 NUMA × 16 cores; 32 MB L3 per 8 cores"], ["Memory", "512 GB DDR4-3200, 16 channels, 409.6 GB/s peak"], ["Network", "HPE Slingshot-10 (100 Gb/s), dragonfly"], ["Software", "Cray PE: GCC 11.2, Cray MPICH 8.1.15, PBS Pro"]]
    label_value_table(s, X0, 1.62, [1.62, 5.08], rows, row_h=0.56, size=14)
    node_diagram(s, 7.6, 1.62, 5.03, 2.25)
    card(s, 7.6, 4.02, 5.03, 0.98, fill=TINT)
    add_text(s, 7.82, 4.02, 4.7, 0.98, [{"runs": [("≈ 290 GB/s", {"color": RED, "size": 20}), ("  STREAM triad", {"size": 13})], "bold": True, "color": NAVY}, {"runs": ["reached with only 16 of 128 cores (one per L3)"], "size": 13, "color": NAVY}], anchor="m")
    card(s, X0, 5.3, XW, 1.42)
    add_text(s, X0 + 0.25, 5.4, 5.6, 0.4, ["Why ASPIRE-2A?"], size=17, color=NAVY, bold=True)
    add_text(s, X0 + 0.25, 5.82, 5.75, 0.85, ["OpenFOAM works with very many files: a build is ≈ 36,000 files, and each decomposed case adds thousands more."], size=13)
    for i, (head, value, fill, color, mark) in enumerate([("Gadi project quota", "0.2 M files · 1 TB", GREY_TINT, MUTED, "✕"), ("ASPIRE-2A quota", "200 M files · 100 TB", WHITE, NAVY, "✓")]):
        x = 6.75 + i * 2.95
        box(s, x, 5.48, 2.75, 1.06, fill=fill, line=LINE, radius=0.08)
        add_text(s, x + 0.18, 5.52, 2.45, 1.0, [{"runs": [(mark + " ", {"color": color}), (head, {})], "size": 12, "color": MUTED, "bold": True}, {"runs": [value], "size": 16, "color": color, "bold": True, "space_before": 3}], anchor="m")
    set_notes(s, NOTES["aspire"])
    return s


def slide_baseline_settings():
    s = S[3]
    clear_slide(s, keep=("図 7",))
    set_title(s, "BASELINE SETTINGS")
    message(s, "We start from the case defaults, on our own build of v2512")
    rows = [["Build", "Official v2512 source, GCC 11.2 -O3, AMD AOCL-LibM: as fast as the site module (−0.08 %), and it records what ran"], ["MPI", "Cray MPICH 8.1.15 over UCX: with the default OFI, every 2- and 4-node run died with SIGBUS at MPI_Finalize"], ["Decomposition", "Case default hierarchical: (16 8 1) / (16 8 2) / (16 8 4) on 1 / 2 / 4 nodes"], ["Placement", "128 ranks per node, one per core, bound by the launcher (mpiexec --cpu-bind depth), as the site recommends"], ["Measurement", "Official metric (steps 2 to N); at least 3 jobs per condition; one point = one job"]]
    label_value_table(s, X0, 1.62, [2.0, 6.35], rows, row_h=0.78, size=14)
    caption(s, "Modules: PrgEnv-gnu/8.3.3 · aocl/4.0.0 · cray-mpich-ucx/8.1.15", y=5.66, w=8.3, size=12)
    h = 4.4
    w = h * (3840 * 0.333) / (2220 * (1 - PANEL_TOP - ALL_BOTTOM))
    x = 12.63 - w
    for sh in s.shapes:
        if sh.name == "図 7":
            sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom = 0.0, PANEL_TOP, 0.667, ALL_BOTTOM
            sh.left, sh.top, sh.width, sh.height = [int(v * 914400) for v in (x, 1.98, w, h)]
    add_text(s, x, 1.6, w, 0.34, ["hierarchical (16 8 4)"], size=14, color=BASE, bold=True, align="c")
    add_text(s, x, 6.48, w, 0.5, [{"runs": ["512 subdomains"], "align": "c"}, {"runs": ["car · centre plane · cross-section"], "align": "c"}], size=11, color=MUTED)
    set_notes(s, NOTES["baseline_settings"])
    return s


def slide_baseline_results():
    s = S[4]
    clear_slide(s)
    set_title(s, "BASELINE RESULTS")
    message(s, "3.65 s/step on 4 nodes: linear scaling, but slow and unsteady")
    picture(s, fig("fig23_baseline_scaling"), 0.5, 1.55, w=8.35)
    stat(s, 9.15, 1.62, 3.48, 1.3, "3.65 s/step", "on 4 nodes", "mean of 3 jobs", color=BASE, num_size=28)
    stat(s, 9.15, 3.07, 3.48, 1.3, "4.0×", "from 1 to 4 nodes", "parallel efficiency 1.00", color=NAVY, num_size=28)
    stat(s, 9.15, 4.52, 3.48, 1.3, "8 %", "spread between jobs", "of one setup: 3.53–3.82 s/step", color=RED, num_size=28)
    add_text(s, X0, 5.95, XW, 0.38, ["Slow and unsteady at the same time: a sign that something is misconfigured"], size=15, color=NAVY, bold=True)
    caption(s, "Reference only: the organisers' hierarchical run took 3.415 s/step (site build, default MPI transport, no binding). Every comparison in this talk is against our own baseline: same build, scripts and measurement.", y=6.36, h=0.5, size=11.5)
    set_notes(s, NOTES["baseline_results"])
    return s


def slide_measure():
    s = new_slide()
    set_title(s, "HOW WE MEASURE AND PROFILE")
    message(s, "Benchmark runs give the numbers; profile runs explain them")
    rows = [["Tool", "When it runs", "Question it answers"], ["Official metric", "Every benchmark run, no profiler", "How long does a step take?"], ["IMB-MPI1", "After the solver, every benchmark run", "How fast is the network between these nodes?"], ["CrayPAT", "Profile runs: 4 nodes, 40 steps", "Which MPI calls take the time, per rank?"], ["OpenFOAM profiling", "Profile runs", "Which solver stage takes the time, per rank?"], ["AMD uProf", "Profile runs", "Which functions use the CPU? Hardware counters"], ["/proc in the job", "Profile runs", "Is each rank on its own core? Where is its memory?"]]
    colors = [None, [BASE, INK, INK]] + [[NAVY, INK, INK]] * 5
    table(s, X0, 1.6, [2.45, 4.3, 5.18], rows, row_h=0.43, size=14, bolds=[None] + [[True, False, False]] * 6, colors=colors)
    cards = [("✓", "Decision rule", "Candidate and control alternate in the same period, at least 3 jobs each on 4 nodes. A change is kept only if every job with it beats every job without it."), ("≈", "Know the noise before trusting a gain", "One setup, repeated: 8 % spread in our baseline, 0.18 % after Basic. Profilers shift a step by −1 % to +6 %, so profiled times are never results.")]
    for i, (mark, head, body) in enumerate(cards):
        x = X0 + i * 6.08
        card(s, x, 4.92, 5.85, 1.62)
        circle_num(s, x + 0.22, 5.08, 0.42, mark, size=15)
        add_text(s, x + 0.78, 5.06, 4.9, 0.44, [head], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.78, 5.52, 4.85, 1.0, [body], size=13.5)
    set_notes(s, NOTES["measure"])
    return s


def slide_baseline_analysis():
    s = S[5]
    clear_slide(s)
    set_title(s, "BASELINE ANALYSIS")
    message(s, "Binding lost at MPI_Init → uneven computation → everyone waits")
    items = [("Binding lost", "/proc during the solve", "0 / 512", "ranks on their own core", "removed during MPI_Init; 9 % of a rank's memory on its own NUMA domain (random: 12.5 %)"), ("Uneven computation", "OpenFOAM profiling, 512 ranks", "1.46×", "slowest / median rank", "computation per rank: 54–115 s in 40 steps; cell counts equal within 0.002 %"), ("Everyone waits", "CrayPAT", "46 %", "of the time is MPI", "MPI_Waitall 55 % and MPI_Allreduce 35 % of it: calls that wait for other ranks")]
    w, gap = 3.55, 0.64
    for i, (head, tool, number, label, detail) in enumerate(items):
        x = X0 + i * (w + gap)
        card(s, x, 1.62, w, 3.12)
        circle_num(s, x + 0.2, 1.8, 0.38, str(i + 1), size=14)
        add_text(s, x + 0.68, 1.76, w - 0.8, 0.46, [head], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.25, 2.27, w - 0.4, 0.3, [(tool, {"i": True})], size=12, color=MUTED)
        add_text(s, x + 0.25, 2.62, w - 0.4, 0.68, [number], size=38, color=RED, bold=True)
        add_text(s, x + 0.25, 3.3, w - 0.4, 0.34, [label], size=14, bold=True)
        add_text(s, x + 0.25, 3.68, w - 0.45, 0.98, [detail], size=12.5, color=MUTED)
        if i < 2:
            block_arrow(s, x + w + 0.11, 2.95, 0.42, 0.42)
    card(s, X0, 4.95, XW, 0.9, fill=TINT)
    add_text(s, X0 + 0.25, 4.95, XW - 0.5, 0.9, [[("Why one slow rank matters:  ", {"b": True, "color": NAVY}), ("every solver iteration exchanges halo values and takes a global sum, about 14,000 messages and 1,600 global sums per rank per step. When one rank is late, the other 511 wait.", {})]], size=14, anchor="m")
    caption(s, "Hottest functions (AMD uProf): sparse-matrix sweeps, i.e. Gauss–Seidel, residual and A·x. Profiles: 4 nodes, separate 40-step runs (#62).", y=6.0, size=11.5)
    lesson(s, "Check what is already broken before hunting for gains")
    set_notes(s, NOTES["baseline_analysis"])
    return s


def slide_strategy():
    s = S[6]
    clear_slide(s)
    set_title(s, "OPTIMIZATION STRATEGY")
    message(s, "Keep memory near each core, balance the work, move fewer bytes")
    rows = [["Bottleneck", "Measured on 4 nodes", "Our strategy"], ["Memory bandwidth", "Main limit: half the bandwidth → 2.2× slower; half the cores → no change", "Move fewer bytes (Bonus)"], ["Memory placement", "0 of 512 ranks pinned; 9 % of a rank's memory local", "Pin CPU and memory (Basic)"], ["Load imbalance", "MPI 46 % of the time, mostly waiting for the slowest rank", [[("scotch (Basic), ", {}), ("multiLevel (Bonus)", {"color": BONUS})]]], ["Network", "55 % more bandwidth or 92 % fewer faces between nodes: no change", "—"], ["Arithmetic", "Compiler flags, another compiler, PGO: within 0.13 %", "—"], ["File I/O", "0.01 % of a step", "—"], ["OS noise", "0.8 % of each core's time", "— (needs root)"]]
    fills = [None] + [[TINT] * 3] * 3 + [[WHITE] * 3] * 4
    colors = [None, [NAVY, INK, BONUS], [NAVY, INK, BASIC], [NAVY, INK, BASIC]] + [[MUTED] * 3] * 4
    bolds = [None] + [[True, False, True]] * 3 + [[True, False, False]] * 4
    table(s, X0, 1.6, [2.4, 6.15, 3.38], rows, row_h=0.47, size=14, fills=fills, colors=colors, bolds=bolds, zebra=False)
    for i, (name, color, text) in enumerate([("BASIC", BASIC, "No source change: build, job script, placement, hierarchical or scotch"), ("BONUS", BONUS, "Source changes and other decomposition methods, proven to be the same math")]):
        x = X0 + i * 6.08
        shape_text(box(s, x, 5.82, 1.15, 0.42, fill=color, radius=0.5), name, size=13)
        add_text(s, x + 1.3, 5.72, 4.6, 0.64, [text], size=13, anchor="m")
    set_notes(s, NOTES["strategy"])
    return s


def slide_basic_pinning():
    s = S[7]
    clear_slide(s)
    set_title(s, "BASIC OPTIMIZATION (1/2)")
    message(s, [("Putting the lost binding back: 3.65 → 3.26 s/step ", {}), ("(−11 %)", {"color": RED})])
    steps = [("Cause", "The launcher binds each rank, but the binding is removed from outside during MPI_Init. Linux keeps a page where it was first written (first touch), so data allocated off-core stays remote."), ("Fix, in the job script only", "Each rank starts under numactl, with its memory bound to its own NUMA domain; one watcher per node re-pins each rank to its core with taskset."), ("Check", "/proc during the solve: 128 of 128 ranks pinned on every node; 58 % of pages local (was 9 %).")]
    for y, (i, (head, body)) in zip((1.65, 3.22, 4.62), enumerate(steps)):
        circle_num(s, X0, y, 0.42, str(i + 1), size=15)
        add_text(s, X0 + 0.6, y - 0.02, 5.1, 0.42, [head], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, X0 + 0.6, y + 0.42, 5.1, 1.1, [body], size=13.5)
    add_text(s, 6.75, 1.6, 5.88, 0.36, ["Both halves are needed"], size=16, color=NAVY, bold=True)
    add_text(s, 6.75, 1.95, 5.88, 0.3, ["4 nodes, scotch: s/step, lower is better (mean of 1–3 jobs)"], size=12, color=MUTED)
    bar_chart(s, 6.55, 2.25, 6.08, 3.55, ["Memory bound only\n(numactl)", "CPU re-pinned only\n(taskset keeper)", "Launcher binding only\n(lost at MPI_Init)", "Both: Basic\n(numactl + keeper)"], [("s/step", (4.3796, 3.4738, 3.3950, 2.9168))], point_colors=[RED, FAINT, FAINT, BASIC], number_format="0.00", vmin=0, vmax=5, font_size=12, label_size=14, gap=45, value_axis=False, gridlines=False)
    caption(s, "−11 %: the case-default split with and without pinning, 3 jobs each in the same period (3.670 → 3.257 s/step). LD_PRELOAD pinning is as fast but counts as Bonus work, so Basic uses numactl and taskset.", y=6.08, h=0.55, size=11.5)
    set_notes(s, NOTES["basic_pinning"])
    return s


def slide_basic_decomp():
    s = new_slide()
    set_title(s, "BASIC OPTIMIZATION (2/2)")
    message(s, [("scotch cuts compact blocks: 3.26 → 2.92 s/step ", {}), ("(−10.5 %)", {"color": RED})])
    pw = 3.3
    for i, (which, label, color, lines) in enumerate([("hier", "hierarchical (case default)", BASE, ["4.31 M faces between subdomains", "slowest / median rank 1.16"]), ("scotch", "scotch (Basic)", BASIC, ["2.93 M faces (−32 %)", "slowest / median rank 1.06"])]):
        x = X0 + i * (pw + 0.12)
        add_text(s, x, 1.58, pw, 0.34, [label], size=14, color=color, bold=True, align="c")
        decomp_panel(s, which, x, 1.95, w=pw)
        add_text(s, x, 5.14, pw, 0.62, [{"runs": [lines[0]], "align": "c"}, {"runs": [lines[1]], "align": "c"}], size=12.5, color=INK if i else MUTED, bold=bool(i))
    xr, wr = 7.72, 4.91
    add_text(s, xr, 1.58, wr, 0.36, ["scotch against hierarchical"], size=16, color=NAVY, bold=True)
    add_text(s, xr, 1.93, wr, 0.3, ["same placement, 3 jobs each, alternated"], size=12, color=MUTED)
    bar_chart(s, xr - 0.1, 2.2, wr + 0.1, 2.4, ["1 node", "2 nodes", "4 nodes"], [("change", (-1.31, -2.46, -10.53))], colors=[BASIC], horizontal=False, number_format='0.0" %";"−"0.0" %"', vmin=-13, vmax=0, font_size=12, label_size=14, gap=70, value_axis=False, gridlines=False)
    card(s, xr, 4.78, wr, 1.48, fill=TINT)
    add_text(s, xr + 0.22, 4.86, wr - 0.4, 0.36, ["Then: map the split onto the node"], size=14, color=NAVY, bold=True)
    add_text(s, xr + 0.22, 5.22, wr - 0.4, 1.0, [[("scotchCoeffs follow 2 sockets × 4 NUMA domains × 16 cores: 23 % fewer faces between nodes. ", {}), ("2.918 → 2.898 s/step (−0.7 %)", {"b": True, "color": BASIC}), ("; all 5 jobs beat all 5 controls", {})]], size=12.5)
    caption(s, "One early job at 5.03 s/step first made us reject scotch; alternated jobs reversed that. Since then we never decide from one job.", y=6.48, size=12, italic=True, color=NAVY)
    set_notes(s, NOTES["basic_decomp"])
    return s


def slide_basic_results():
    s = S[8]
    clear_slide(s)
    set_title(s, "BASIC RESULTS")
    message(s, "−21 % on 4 nodes, and the profiles show why")
    rows = [["4 nodes", "Baseline", "Basic"], ["s / step (jobs)", "3.65 (3)", "2.90 (5): −21 %"], ["Spread between jobs", "8 %", "0.18 %"], ["Ranks on their own core (/proc)", "0 of 512", "128 of 128 per node"], ["Memory on the rank's own NUMA domain (median)", "9 %", "58 %"], ["Computation, slowest / median rank *", "1.46", "1.06"], ["MPI share of the time *", "46 %", "19 %"]]
    table(s, X0, 1.6, [4.75, 1.6, 2.35], rows, row_h=0.55, size=14, colors=[None] + [[INK, BASE, BASIC]] * 6, bolds=[None, [True, True, True]] + [[False, False, True]] * 5, aligns=["l", "c", "c"])
    card(s, 9.7, 1.6, 2.93, 3.85)
    add_text(s, 9.95, 1.6, 2.5, 3.85, [{"runs": ["2.90"], "size": 50, "color": BASIC, "bold": True, "line": 0.95}, {"runs": ["s / step on 4 nodes"], "size": 15, "bold": True}, {"runs": [("−21 %", {"b": True, "color": BASIC}), (" vs our baseline", {})], "size": 13, "space_before": 10}, {"runs": ["1 node: −8 %"], "size": 12.5, "color": MUTED, "space_before": 8}, {"runs": ["2 nodes: −14 %"], "size": 12.5, "color": MUTED}], anchor="m")
    caption(s, "* Profiles of Basic before the node mapping, which changes a step by 0.7 %. The MPI time left is mostly waiting for the slowest rank.", y=5.62, size=11.5)
    add_text(s, X0, 6.05, XW, 0.4, ["Steadier too: the organisers score a re-run of exactly this configuration"], size=15, color=NAVY, bold=True)
    set_notes(s, NOTES["basic_results"])
    return s


def channel_row(s, x, y, used, size=0.22, gap=0.06):
    for k in range(16):
        box(s, x + k * (size + gap), y, size, size, fill=NAVY if k < used else "D5D9E0", radius=0.15)


def slide_bandwidth():
    s = S[11]
    clear_slide(s)
    set_title(s, "MEMORY BANDWIDTH SETS THE SPEED")
    message(s, "Half the memory channels: 2.2× slower. Half the cores: no change")
    add_text(s, X0, 1.52, XW, 0.36, ["No memory-controller counters on ASPIRE-2A, so we moved the ranks instead (4 nodes, every rank pinned, 2 jobs each)"], size=13, color=MUTED)
    experiments = [("Half the cores", "128 → 64 ranks per node, still on all 16 channels", 16, "×0.99–1.02", NAVY, "If the cores set the speed: ×2"), ("Half the memory channels", "the same 64 ranks and split, on 8 of the 16 channels", 8, "×2.11–2.20", RED, "Triad bandwidth: 279 → 125 GB/s (×2.22)")]
    for i, (head, sub, used, number, color, note) in enumerate(experiments):
        x = X0 + i * 6.08
        card(s, x, 1.98, 5.85, 3.3)
        add_text(s, x + 0.3, 2.08, 5.3, 0.42, [head], size=18, color=NAVY, bold=True)
        add_text(s, x + 0.3, 2.5, 5.3, 0.34, [sub], size=13, color=MUTED)
        channel_row(s, x + 0.3, 3.0, used)
        add_text(s, x + 0.3, 3.32, 5.3, 0.3, [f"{used} of 16 memory channels in use"], size=11, color=MUTED)
        add_text(s, x + 0.3, 3.66, 5.3, 0.75, [[(number, {}), ("  time per step", {"size": 15, "color": INK, "b": False})]], size=36, color=color, bold=True)
        add_text(s, x + 0.3, 4.52, 5.3, 0.5, [note], size=14, bold=True)
    add_text(s, X0, 5.5, XW, 0.62, [[("Arithmetic intensity agrees: ", {"b": True, "color": NAVY}), ("the sparse-matrix sweeps do ≈ 0.1 flop per byte, about 1/100 of what keeps the cores busy (4.1 TFLOP/s ÷ 290 GB/s ≈ 14 flop/byte).", {})]], size=13.5)
    lesson(s, "Move fewer bytes, not the same bytes faster")
    set_notes(s, NOTES["bandwidth"])
    return s


def slide_bonus_opt():
    s = S[9]
    clear_slide(s)
    set_title(s, "BONUS OPTIMIZATION")
    message(s, "The same arithmetic with fewer bytes moved")
    circle_num(s, X0, 1.66, 0.4, "1", fill=BONUS, size=14)
    add_text(s, X0 + 0.55, 1.62, 5.6, 0.46, ["A split that follows the machine"], size=16, color=NAVY, bold=True, anchor="m")
    add_text(s, X0 + 0.55, 2.08, 5.75, 0.92, ["multiLevel (4 2 4 16) splits nodes → sockets → NUMA → cores, with scotch at each level: 38 % fewer faces between nodes"], size=13.5)
    circle_num(s, X0, 3.08, 0.4, "2", fill=BONUS, size=14)
    add_text(s, X0 + 0.55, 3.04, 5.6, 0.46, ["Four source changes that move fewer bytes"], size=16, color=NAVY, bold=True, anchor="m")
    items = [("No copies in the linear solvers", ""), ("U components in one pass", ": the shared matrix is read once, not 3 times"), ("No unused boundary updates", ": skip values nobody reads"), ("Fused face loops", ": face values formed inside the sums")]
    add_text(s, X0 + 0.55, 3.52, 5.75, 1.9, [{"runs": [(a, {"b": True}), (b, {})], "bullet": {"color": BONUS}, "space_after": 3} for a, b in items], size=13.5)
    card(s, X0, 5.62, 6.3, 1.05, fill=TINT)
    add_text(s, X0 + 0.25, 5.62, 5.9, 1.05, [{"runs": ["Same math: every operation and its order are kept"], "bold": True, "color": NAVY, "size": 14}, {"runs": ["Only copies, extra passes and values nobody reads are removed"], "size": 12.5}], anchor="m")
    xd = 7.35
    add_text(s, xd, 1.58, 5.28, 0.36, ["Example: U components in one pass"], size=15, color=NAVY, bold=True)
    add_text(s, xd, 2.0, 5.28, 0.3, ["Before: one pass per component"], size=13, bold=True)
    for k, component in enumerate(("Ux", "Uy", "Uz")):
        y = 2.38 + k * 0.5
        shape_text(box(s, xd, y, 2.15, 0.4, fill=TINT, line="9FB0CC", radius=0.12), "matrix arrays", size=12, color=NAVY, bold=False)
        arrow_line(s, xd + 2.2, y + 0.2, xd + 2.85, y + 0.2, color=FAINT)
        shape_text(box(s, xd + 2.9, y, 2.2, 0.4, fill=ORANGE_TINT, line="E8B987", radius=0.12), f"sweep {component}", size=12, color=INK, bold=False)
    add_text(s, xd, 3.88, 5.1, 0.32, ["the matrix is read 3 times"], size=13, color=RED, bold=True, align="c")
    add_text(s, xd, 4.38, 5.28, 0.3, ["After: one pass for all three"], size=13, bold=True)
    shape_text(box(s, xd, 4.78, 2.15, 1.0, fill=TINT, line="9FB0CC", radius=0.08), "matrix arrays", size=12, color=NAVY, bold=False)
    arrow_line(s, xd + 2.2, 5.28, xd + 2.85, 5.28, color=FAINT)
    shape_text(box(s, xd + 2.9, 4.78, 2.2, 1.0, fill=ORANGE_TINT, line="E8B987", radius=0.08), ["sweep Ux", "sweep Uy", "sweep Uz"], size=12, color=INK, bold=False)
    add_text(s, xd, 5.86, 5.1, 0.32, ["the matrix is read once"], size=13, color=GREEN, bold=True, align="c")
    caption(s, "Each component still gets the same operations in the same order.", x=xd, y=6.25, w=5.28, size=11.5, align="c")
    set_notes(s, NOTES["bonus_opt"])
    return s


def slide_bonus_results():
    s = new_slide()
    set_title(s, "BONUS RESULTS")
    message(s, "Bit-identical Cd, and 10 % faster than our Basic")
    rows = [["Nodes (steps)", "Basic s / step", "Bonus s / step", "Bonus vs Basic", "coefficient.dat vs pre-change baseline"], ["1 (40)", "13.365 (3 jobs)", "11.668 (3 jobs)", "−12.7 %", "bit-identical"], ["2 (80)", "6.372 (3 jobs)", "5.641 (3 jobs)", "−11.5 %", "bit-identical"], ["4 (150)", "2.898 (5 jobs)", "2.599 (3 jobs)", "−10.3 %", "bit-identical"]]
    table(s, X0, 1.6, [1.85, 2.3, 2.3, 2.05, 3.43], rows, row_h=0.48, size=14.5, colors=[None] + [[INK, BASIC, BONUS, BONUS, GREEN]] * 3, bolds=[None] + [[True, False, True, True, True]] * 3, aligns=["l", "c", "c", "c", "c"])
    add_text(s, X0, 3.78, XW, 0.38, ["What the rules ask of Bonus work, and our answer"], size=15, color=NAVY, bold=True)
    checks = [("What changed", "Four patches and the multiLevel dictionaries, submitted as text"), ("Why the same math", "Only copies, extra passes and unread values are removed; every operation and its order is kept"), ("Evidence", "Against the same split without the patches: coefficient.dat bit-identical, all 371 / 771 / 1,475 log lines identical"), ("Speedup vs Basic", "−12.7 / −11.5 / −10.3 % on 1 / 2 / 4 nodes, on the same machine")]
    w = 2.83
    for i, (head, body) in enumerate(checks):
        x = X0 + i * (w + 0.2)
        card(s, x, 4.22, w, 1.85)
        circle_num(s, x + 0.18, 4.36, 0.36, "✓", fill=GREEN, size=13)
        add_text(s, x + 0.62, 4.32, w - 0.75, 0.44, [head], size=13.5, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.2, 4.84, w - 0.36, 1.2, [body], size=12)
    caption(s, "Pre-change baseline: the same multiLevel split and rank counts with the four source changes removed. Each change was also checked on its own.", y=6.25, size=11.5)
    set_notes(s, NOTES["bonus_results"])
    return s


def slide_bonus_analysis():
    s = S[10]
    clear_slide(s)
    set_title(s, "BONUS ANALYSIS")
    message(s, [("4 % fewer instructions, but ", {}), ("17 % fewer refills from DRAM", {"color": RED})])
    add_text(s, X0, 1.58, 6.9, 0.36, ["With the patches, against the same build without them"], size=15, color=NAVY, bold=True)
    add_text(s, X0, 1.93, 6.9, 0.3, ["1 node, AMD uProf, computation only, 2 jobs each"], size=12, color=MUTED)
    categories = ["L1 refills from DRAM", "L2 accesses incl. prefetch", "L1 data accesses", "Instructions", "Cycles", "Time per step"]
    bar_chart(s, 0.5, 2.22, 7.1, 4.15, categories, [("change", (-17.17, -9.61, -5.85, -4.07, -10.81, -12.28))], point_colors=[RED, BONUS, BONUS, FAINT, BONUS, BONUS], number_format='0.0" %";"−"0.0" %"', vmin=-25, vmax=0, font_size=12.5, label_size=14, gap=45, value_axis=False, gridlines=False)
    xr, wr = 7.95, 4.68
    card(s, xr, 1.6, wr, 2.3)
    add_text(s, xr + 0.25, 1.68, wr - 0.4, 0.4, ["Less bandwidth per core, bigger gain"], size=15, color=NAVY, bold=True)
    for k, (number, label, color) in enumerate((("−7.9 %", "all 16 channels", BONUS), ("−11.4 %", "8 of 16 channels", RED))):
        add_text(s, xr + 0.25 + k * 2.2, 2.12, 2.1, 1.0, [{"runs": [number], "size": 28, "color": color, "bold": True}, {"runs": [label], "size": 12.5, "bold": True}])
    add_text(s, xr + 0.25, 3.3, wr - 0.4, 0.5, ["4 nodes, 64 ranks per node, the same patches (placement experiment)"], size=11.5, color=MUTED)
    card(s, xr, 4.1, wr, 2.25)
    add_text(s, xr + 0.25, 4.18, wr - 0.4, 0.4, ["Computation shrinks, MPI does not"], size=15, color=NAVY, bold=True)
    add_text(s, xr + 0.25, 4.62, wr - 0.4, 1.0, [{"runs": ["104.2 → 94.9 s"], "size": 26, "color": BONUS, "bold": True}, {"runs": ["computation per rank in 40 steps; MPI stays ≈ 23.5 s"], "size": 12.5, "bold": True}])
    add_text(s, xr + 0.25, 5.8, wr - 0.4, 0.45, ["CrayPAT, 4 nodes, 512 ranks"], size=11.5, color=MUTED)
    caption(s, "Counters are L1 demand refills, not DRAM bytes: the memory-controller counters are not readable. IPC 0.36 → 0.39.", y=6.5, size=11.5)
    set_notes(s, NOTES["bonus_analysis"])
    return s


def slide_scaling():
    s = S[12]
    clear_slide(s)
    set_title(s, "SCALING ANALYSIS")
    message(s, "Faster at 1, 2 and 4 nodes; parallel efficiency 1.00 → 1.15")
    add_text(s, X0, 1.58, 6.3, 0.36, ["Time per step against our baseline"], size=15, color=NAVY, bold=True)
    bar_chart(s, 0.5, 1.95, 6.45, 4.45, ["1 node", "2 nodes", "4 nodes"], [("Basic", (-8.25, -14.21, -20.60)), ("Bonus", (-19.90, -24.06, -28.77))], colors=[BASIC, BONUS], horizontal=False, number_format='0" %";"−"0" %"', vmin=-33, vmax=0, font_size=13, label_size=14, gap=90, overlap=-20, legend=True, value_axis=False, gridlines=False)
    rows = [["s / step", "1 node", "2 nodes", "4 nodes", "E(4)"], ["Baseline", "14.57", "7.43", "3.65", "1.00"], ["Basic", "13.36", "6.37", "2.90", "1.15"], ["Bonus", "11.67", "5.64", "2.60", "1.12"]]
    table(s, 7.25, 1.6, [1.45, 1.0, 1.05, 1.05, 0.83], rows, row_h=0.45, size=14, colors=[None, [BASE, INK, INK, INK, INK], [BASIC, INK, INK, BASIC, BASIC], [BONUS, INK, INK, BONUS, BONUS]], bolds=[None, [True, False, False, False, False], [True, False, False, True, True], [True, False, False, True, True]], aligns=["l", "r", "r", "r", "r"])
    caption(s, "E(4): parallel efficiency from 1 to 4 nodes. Jobs per point: 3–6.", x=7.25, y=3.45, w=5.38, size=11)
    items = [[("Basic gains grow with the node count, ", {}), ("mostly from scotch: −1.3 / −2.5 / −10.5 %", {"b": True})], [("The source changes gain most on 1 node, ", {}), ("where each rank holds 4× more data", {"b": True}), (" (U in one pass: −6.4 % vs −2.3 %)", {})], [("Efficiency above 1 is cache: ", {"b": True}), ("on 4 nodes the cell arrays shrink to 1 MB per rank and fit in L3; DRAM refills per cell −30 % (uProf)", {})]]
    bullets(s, 7.25, 3.9, 5.38, 2.7, items, size=13)
    set_notes(s, NOTES["scaling"])
    return s


def slide_not_helped():
    s = S[13]
    clear_slide(s)
    set_title(s, "WHAT DID NOT HELP, AND WHY")
    message(s, "Proxy metrics improved; the time per step did not")
    rows = [["Idea", "Result (4 nodes)", "Why it did not help"], ["Compiler flags, AOCC, LTO, GCC PGO", "within ±0.13 %", "The loops wait on memory, not on instructions"], ["Other MPI transports: OFI, UCX over RC", "−0.16 % to +0.77 %", "MPI time is waiting for the slowest rank"], ["Reordering ranks: 92 % fewer inter-node faces", "+0.1 %", "Fewer bytes between nodes do not cut the wait"], ["GAMG coarsest level on fewer ranks", "−0.25 % to +4.95 %", "81 % of the global sums, ≈ 0.6 % of the time"], ["Weighted cells (×2, ×12), 2-constraint METIS", "+1.5 % to +6.1 %", "Uneven cells, or more faces between subdomains"], ["malloc thresholds", "−0.4 % (3 jobs)", "Too small to separate with 3 jobs; not re-tested"], ["SMT: 2 ranks per core", "5.7× slower", "Stalls of minutes; cause not isolated"]]
    table(s, X0, 1.6, [4.75, 2.25, 4.93], rows, row_h=0.45, size=13, bolds=[None] + [[True, False, False]] * 7)
    for i, (question, answer) in enumerate([("Why no gain?", "None of them moves fewer bytes, and memory bandwidth sets the speed."), ("Why not combine them?", "Gains we cannot separate from the run-to-run spread may be luck; stacking them would be overfitting.")]):
        y = 5.62 + i * 0.6
        shape_text(box(s, X0, y, 2.85, 0.44, fill=NAVY, radius=0.5), question, size=13)
        add_text(s, X0 + 3.05, y - 0.06, 8.88, 0.56, [answer], size=14, bold=True, anchor="m")
    set_notes(s, NOTES["not_helped"])
    return s


def slide_conclusion():
    s = S[14]
    clear_slide(s)
    set_title(s, "CONCLUSION")
    message(s, [("1.40× faster on 4 nodes", {"color": RED}), (", with the same math", {})])
    w = 3.82
    for i, (number, head, sub, nodes, color) in enumerate([("3.65", "Baseline", "case defaults", "14.57 / 7.43 / 3.65", BASE), ("2.90", "Basic  −21 %", "unmodified v2512", "13.36 / 6.37 / 2.90", BASIC), ("2.60", "Bonus  −29 %", "bit-identical Cd", "11.67 / 5.64 / 2.60", BONUS)]):
        x = X0 + i * (w + 0.235)
        card(s, x, 1.58, w, 1.45)
        add_text(s, x + 0.22, 1.6, 1.6, 0.85, [[(number, {}), ("\n", {}), ("s / step", {"size": 12, "color": MUTED, "b": False})]], size=32, color=color, bold=True, anchor="m")
        add_text(s, x + 1.72, 1.62, w - 1.85, 0.85, [{"runs": [head], "size": 15, "bold": True, "color": color}, {"runs": [sub], "size": 12}], anchor="m")
        add_text(s, x + 0.22, 2.52, w - 0.4, 0.42, [[("1 / 2 / 4 nodes:  ", {}), (nodes, {})]], size=11.5, color=MUTED, anchor="m")
    rows = [["What we changed", "The bottleneck it removes, and the evidence", "4 nodes, own control"], ["Pin CPU and memory (Basic)", "Lost binding: 0 of 512 ranks pinned, 9 % of memory local", "−11 %"], ["scotch, then node mapping (Basic)", "Uneven work near the car: slowest / median 1.16 → 1.06", "−10.5 %, −0.7 %"], ["Four source changes (Bonus)", "Memory bandwidth: half the channels → 2.2× slower", "−9.5 %"], ["multiLevel split (Bonus)", "Faces between nodes −38 %, sockets −34 %, NUMA −26 %", "−1.5 %"]]
    table(s, X0, 3.25, [3.85, 5.83, 2.25], rows, row_h=0.5, size=13.5, colors=[None, [BASIC, INK, BASIC], [BASIC, INK, BASIC], [BONUS, INK, BONUS], [BONUS, INK, BONUS]], bolds=[None] + [[True, False, True]] * 4, aligns=["l", "l", "c"])
    add_text(s, X0, 5.97, XW, 0.62, [[("What remains: ", {"b": True, "color": NAVY}), ("memory bandwidth still sets the speed, and ranks still differ by 6 % in computation, so MPI is 19 % of a step, mostly waiting. Each gain is against its own control; they are not added up.", {})]], size=13)
    lesson(s, "know the noise · fix what is broken · follow the bottleneck · trust time, not proxies", y=6.65, label="HOW WE WORKED")
    set_notes(s, NOTES["conclusion"])
    return s


def slide_extra():
    s = new_slide()
    set_title(s, "EXTRA: A GAIN WE DID NOT COUNT")
    message(s, [("−13 % and bit-identical, ", {"color": RED}), ("but it only helps fixed iterations", {})])
    stat(s, X0, 1.6, 4.3, 1.25, "−13.3 %", "4 nodes: 2.250 vs 2.595 s/step", "3 jobs each, alternated; ranges do not overlap", color=BONUS, num_size=26, label_size=13, sub_size=11.5)
    stat(s, X0, 3.0, 4.3, 1.25, "bit-identical", "coefficient.dat at 1, 2 and 4 nodes", "all 1,323 solver log lines identical", color=GREEN, num_size=26, label_size=13, sub_size=11.5)
    stat(s, X0, 4.4, 4.3, 1.25, "≈ 13 %", "of a Bonus step at 512 ranks", "goes to convergence checks that are never used", color=NAVY, num_size=26, label_size=13, sub_size=11.5)
    xr, wr = 5.3, 7.33
    add_text(s, xr, 1.58, wr, 0.38, ["What it does"], size=15, color=NAVY, bold=True)
    add_text(s, xr, 1.98, wr, 1.3, ["fvSolution.fixedIter sets tolerance 0 and relTol 0, so no solve can stop early. The residual norm computed after every sweep, a residual pass plus a global sum, is used only after the last one. The patch computes it once, after the last sweep."], size=13.5)
    add_text(s, xr, 3.4, wr, 0.38, ["Why it is not in our Bonus"], size=15, color=NAVY, bold=True)
    bullets(s, xr, 3.8, wr, 1.9, ["It helps only the benchmark's fixed-iteration setting: the case's own fvSolution.fixedTol runs the original code", "The rules prohibit “less work per step”, and the skipped norms could be read as work", "Our four Bonus changes, in contrast, help with any convergence setting"], size=13.5)
    lesson(s, "Speed up the computation, not the benchmark", y=6.05)
    set_notes(s, NOTES["extra"])
    return s


# ====================================================================== supporting slides
def supp(title, msg, notes_key):
    s = new_slide()
    set_title(s, title)
    message(s, msg, size=18)
    set_notes(s, NOTES[notes_key])
    return s


def s_noise():
    s = supp("MEASURING HONESTLY", "Most repeated jobs lie within ±0.4 % of their median, but single jobs can be 90 % slower", "s_noise")
    picture(s, fig("fig08_variability"), 0.5, 1.55, w=8.2)
    bullets(s, 8.95, 1.7, 3.68, 4.8, ["92 jobs in 29 repeated configurations, 21 Sep to 5 Oct", "Two September jobs were 84 % and 91 % slower", "So we never decide from one job, and alternate candidate and control", "Step-to-step variation inside a job is not the job-to-job spread: 150 steps are not 150 samples"])
    caption(s, "Deviation from the median of the same configuration (same commit, build, nodes, decomposition). Shaded: ±0.4 %. Issue #47.", y=6.5)
    return s


def s_automation():
    s = supp("EXPERIMENT AUTOMATION", "One commit = one condition; every run is started by GitHub Actions", "s_automation")
    steps = [("git push or manual run", GREY_TINT), ("select build: reuse if inputs unchanged", TINT), ("build OpenFOAM (1-node job)", TINT), ("prepare case: decomposePar, cached", TINT), ("run job: Allrun chain + simpleFoam", ORANGE_TINT), ("official parser + Cd file", "E7F3EC"), ("archive raw records + metrics DB", "E7F3EC")]
    w, gap = 1.49, 0.25
    for i, (text, fill) in enumerate(steps):
        x = X0 + i * (w + gap)
        shape_text(box(s, x, 1.85, w, 1.55, fill=fill, line="B8C2D3", radius=0.08), text, size=12, color=INK, bold=False, margin=(0.06, 0.05, 0.06, 0.05))
        if i < len(steps) - 1:
            arrow_line(s, x + w + 0.02, 2.62, x + w + gap - 0.02, 2.62, color=MUTED, width=1.25)
    bullets(s, X0, 3.95, XW, 2.8, ["Each condition is a commit (compiler flag, decomposition, patch), so every result traces back to its exact scripts", "Builds and decomposed cases are reused only when their inputs are identical; nothing is shared between clusters", "Profilers run only in separate diagnostic jobs; nothing is measured inside a benchmark's timed solver run", "Several runners submit jobs in parallel, so control and candidate run in the same period"], size=15, space_after=12)
    return s


def s_build():
    s = supp("BUILD, STORAGE AND MPI", "Builds and records on Lustre; every node solves from its own local disk", "s_build")
    columns = [(X0, 3.35, GREY_TINT, ["GitHub Actions runner", "team server"]), (4.4, 4.05, TINT, ["ASPIRE-2A login node", "/scratch: Lustre, shared"]), (8.8, 3.83, ORANGE_TINT, ["Compute nodes", "$TMPDIR: node-local"])]
    rows_y = [2.35, 3.03, 3.71, 4.39]
    items = {0: {0: "start build, case and run jobs (ssh + qsub)", 3: "after the job: pack the run, archive it, send metrics to the database"}, 1: {0: "mesh archive (3.2 GB)", 1: "build archive per build (OpenFOAM tree, flags, hashes)", 2: "decomposed case per build and decomposition", 3: "run directory per run (logs, results, records)"}, 2: {0: "unpack the OpenFOAM build", 1: "copy the decomposed case, restore0Dir", 2: "Allrun chain + simpleFoam: all case I/O stays local", 3: "write logs and coefficient.dat back"}}
    for ci, (x, w, fill, head) in enumerate(columns):
        box(s, x, 1.58, w, 3.48, fill=fill, line="B8C2D3", radius=0.04)
        add_text(s, x, 1.64, w, 0.62, [{"runs": [head[0]], "bold": True, "size": 13, "color": NAVY, "align": "c"}, {"runs": [head[1]], "size": 11.5, "color": MUTED, "align": "c"}])
        for ri, text in items[ci].items():
            shape_text(box(s, x + 0.15, rows_y[ri], w - 0.3, 0.56, fill=WHITE, line=LINE, radius=0.1), text, size=11.5, color=INK, bold=False, margin=(0.06, 0.02, 0.06, 0.02))
    def mid(ci, ri, side):
        x, w = columns[ci][0], columns[ci][1]
        return (x + 0.15 if side == "l" else x + w - 0.15), rows_y[ri] + 0.28
    for (c1, r1, s1), (c2, r2, s2) in [((0, 0, "r"), (1, 0, "l")), ((1, 1, "r"), (2, 0, "l")), ((1, 2, "r"), (2, 1, "l")), ((2, 3, "l"), (1, 3, "r")), ((1, 3, "l"), (0, 3, "r"))]:
        x1, y1 = mid(c1, r1, s1)
        x2, y2 = mid(c2, r2, s2)
        arrow_line(s, x1 + (0.02 if s1 == "r" else -0.02), y1, x2 + (-0.02 if s2 == "l" else 0.02), y2, color=MUTED, width=1.25)
    bullets(s, X0, 5.32, XW, 1.6, ["Build: official v2512, GCC 11.2 -O3, AMD math library, in a 1-node PBS job; every run records which build it used", "Storage: every node solves from its own copy in $TMPDIR (‑hostRoots, ‑ioRanks); file I/O in the timed steps ≈ 0.01 % of the run (#46)", "MPI: Cray MPICH 8.1.15 over UCX instead of the default OFI"], size=13)
    return s


def s_reference():
    s = supp("THE ORGANISERS' REFERENCE", "For context only: Basic −12 % and Bonus −21 % against the organisers' scotch runs", "s_reference")
    add_text(s, X0, 1.58, 6.2, 0.36, ["Against the organisers' scotch mean, same machine"], size=15, color=NAVY, bold=True)
    bar_chart(s, 0.5, 1.95, 6.35, 4.45, ["1 node", "2 nodes", "4 nodes"], [("Our Basic", (-7.76, -12.83, -12.09)), ("Our Bonus", (-19.47, -22.83, -21.14))], colors=[BASIC, BONUS], horizontal=False, number_format='0" %";"−"0" %"', vmin=-27, vmax=0, font_size=13, label_size=14, gap=90, overlap=-20, legend=True, value_axis=False, gridlines=False)
    rows = [["s / step", "1 node", "2 nodes", "4 nodes"], ["Organisers' hierarchical", "14.67", "7.12", "3.41"], ["Organisers' scotch, mean", "14.49", "7.31", "3.30"], ["Our Basic", "13.36", "6.37", "2.90"], ["Our Bonus", "11.67", "5.64", "2.60"]]
    table(s, 7.1, 1.6, [2.35, 1.0, 1.1, 1.08], rows, row_h=0.45, size=13.5, colors=[None, [MUTED] * 4, [MUTED] * 4, [BASIC, INK, INK, BASIC], [BONUS, INK, INK, BONUS]], bolds=[None, None, None, [True, False, False, True], [True, False, False, True]], aligns=["l", "r", "r", "r"])
    bullets(s, 7.1, 4.12, 5.53, 2.3, ["Organisers (tasks 4.3 notes): site module, mpirun with no options, default MPI settings, no binding", "Their scotch runs (3 / 2 / 5 jobs) spread by 12 % on 4 nodes: 3.19 to 3.58 s/step", "Build, MPI transport and placement all differ, so the gap has more than one cause"], size=13)
    caption(s, "Our own comparisons use our baseline, with the same build, scripts and measurement.", y=6.5)
    return s


def s_mpi_calls():
    s = supp("BASELINE MPI CALLS", "Most calls are halo exchanges; most time goes to the calls that wait", "s_mpi_calls")
    rows = [["Rank", "Most calls per rank", "Calls", "Most time in MPI per rank", "Time per rank"], ["1", "MPI_Isend", "566,107", "MPI_Waitall", "43.1 s (55 %)"], ["2", "MPI_Irecv", "566,107", "MPI_Allreduce", "27.6 s (35 %)"], ["3", "MPI_Test", "563,646", "MPI_Bcast", "2.5 s (3 %)"], ["All", "", "1,815,336", "All MPI", "78.3 s (46 % of the time)"]]
    table(s, X0, 1.62, [0.9, 2.55, 1.85, 3.35, 3.28], rows, row_h=0.5, size=14.5, bolds=[None, None, None, None, [True] * 5], colors=[None, [INK, INK, INK, RED, RED], [INK, INK, INK, RED, RED], None, None], aligns=["c", "l", "c", "l", "r"])
    bullets(s, X0, 4.4, XW, 2.1, ["CrayPAT (pat_run -g mpi), baseline, 4 nodes, 512 ranks, 40 steps; values per rank", "MPI time per rank ranges from 35 to 112 s, while cell counts are equal within 0.002 %: the time is waiting, not transfer", "After Basic the same three calls lead by count, and the time order swaps: MPI_Allreduce 48 %, MPI_Waitall 38 %"], size=14)
    return s


def s_step():
    s = supp("WHERE A STEP GOES AFTER BASIC", "The p and U solves take half a step; assembly and turbulence the rest", "s_step")
    add_text(s, X0, 1.58, 7.4, 0.36, ["Share of a step, median rank"], size=15, color=NAVY, bold=True)
    categories = ["rest of the step\n(assembly, gradients, turbulence)", "function objects", "fvOptions", "k solve", "omega solve", "U solve", "p solve (GAMG)"]
    bar_chart(s, 0.5, 1.95, 7.7, 4.5, categories, [("share", (40.46, 1.84, 0.48, 4.25, 4.66, 22.23, 26.07))], point_colors=[FAINT, BASIC, BASIC, BASIC, BASIC, BASIC, BASIC], number_format='0.0" %"', vmin=0, vmax=48, font_size=12.5, label_size=13, gap=45, value_axis=False, gridlines=False)
    bullets(s, 8.5, 1.7, 4.13, 4.8, ["OpenFOAM's built-in profiling, Basic, 4 nodes, all 512 ranks, 40 steps (#57)", "Computation per rank: median 97.95 s, max 104.17 s (max / median 1.063)", "Cell counts do not explain the spread (r = +0.06); wall faces partly (r = +0.43)", "MPI as a whole: 19 % of the step for the median rank; region times include the waiting inside them"])
    return s


def s_path():
    s = supp("THE PATH ON 4 NODES", "Each change against its own control, in the same period: 3.670 → 2.599 s/step", "s_path")
    picture_fit(s, fig("fig16_journey"), X0, 1.5, XW, 4.85)
    caption(s, "Grey: start (case-default split, binding lost; #36, the same setup as our 3.65 baseline). Blue: Basic. Orange: Bonus. Red: each change against its own control; the changes are separate experiments and are not added up. y-axis does not start at 0.", y=6.38, h=0.55, size=11)
    return s


def s_network():
    s = supp("IS THE NETWORK THE BOTTLENECK?", "No: four changes to the network side, none made a step more than 0.25 % faster", "s_network")
    rows = [["What we changed on the network side", "How much the network side changed", "Step time (4 nodes)"], ["UCX over RC instead of UD between nodes", "IMB bandwidth (1 MiB Sendrecv) 6.7 → 10.4 GB/s, +55 %", "−0.01 % Basic, −0.16 % Bonus (4 v 4)"], ["Rank reordering, hierarchical split", "92 % fewer faces between nodes", "+0.1 %"], ["OFI instead of UCX, with the organisers' two workarounds", "Another transport and provider", "+0.77 % (3 v 3), +0.50 % (1 v 1)"], ["GAMG coarsest level solved on 32 ranks instead of 512", "Fewer ranks in 81 % of the global sums", "−0.25 % (1 v 1)"]]
    table(s, X0, 1.55, [4.3, 4.3, 3.33], rows, row_h=0.6, size=13.5, bolds=[None] + [[True, False, False]] * 4)
    bullets(s, X0, 5.0, XW, 1.9, ["One 8-byte global sum over 512 ranks takes ≈ 12 µs (IMB): 1,600 per step ≈ 0.02 s, under 1 % of a step", "A rank's MPI_Waitall follows its own computation (R² 0.77); adding its neighbours raises that only to 0.80. 13 of the 16 slowest ranks have no neighbours on other nodes", "Not measured: NIC and switch counters"], size=13.5)
    return s


def s_ofi():
    s = supp("OFI AGAINST UCX", "The organisers' OFI workarounds avoid the crash; UCX stays faster", "s_ofi")
    rows = [["MPI transport (Basic, 4 nodes)", "Jobs", "s / step", "Against UCX"], ["UCX (what we use)", "3", "2.9176, 2.9168, 2.9246 (mean 2.9197)", "—"], ["OFI with FI_OFI_RXM_USE_SRX=0", "3", "2.9452, 2.9374, 2.9438 (mean 2.9421)", "+0.77 %"], ["OFI with FI_VERBS_PREFER_XRC=0", "1", "2.9338 (UCX beside it: 2.9192)", "+0.50 %"]]
    table(s, X0, 1.62, [4.0, 0.9, 4.93, 2.1], rows, row_h=0.52, size=14, bolds=[None, [True, False, False, False], [True, False, False, True], [True, False, False, True]], colors=[None, [BASIC, INK, INK, INK], [INK, INK, INK, RED], [INK, INK, INK, RED]], aligns=["l", "c", "l", "c"])
    bullets(s, X0, 3.95, XW, 2.4, ["Basic before the node mapping; only the transport changed; alternated in the same period (7 and 9 Oct, #56, #60)", "All jobs VALID, no SIGBUS, the same Cd (0.28404934573921931)", "OFI's own spread is 0.26 %, so our small spread does not come from UCX: it comes from the placement"], size=14)
    return s


def s_cores():
    s = supp("CORES OR MEMORY?", "Halving the cores changes nothing; halving the memory channels slows a step 2.2×", "s_cores")
    rows = [["s / step (4 nodes, 2 jobs each)", "full128", "spread64", "packed64", "spread64 / full128", "packed64 / spread64"], ["Basic (before the mapping)", "2.920", "2.887", "6.347", "0.99", "2.20"], ["Bonus without the patches", "2.869", "2.874", "6.321", "1.00", "2.20"], ["Bonus", "2.595", "2.649", "5.598", "1.02", "2.11"], ["Triad bandwidth per node", "274 GB/s", "279 GB/s", "125 GB/s", "—", "0.45"]]
    table(s, X0, 1.62, [3.5, 1.45, 1.5, 1.5, 1.95, 2.03], rows, row_h=0.48, size=14, bolds=[None] + [[True, False, False, False, True, True]] * 4, colors=[None] + [[INK, INK, INK, INK, NAVY, RED]] * 4, aligns=["l", "r", "r", "r", "r", "r"])
    add_text(s, X0, 4.25, 5.85, 0.36, ["The three placements"], size=15, color=NAVY, bold=True)
    bullets(s, X0, 4.65, 5.85, 1.8, ["full128: 128 ranks per node, as submitted", "spread64: 64 ranks per node, 4 per L3, on all 16 L3s and all 16 memory channels", "packed64: the same 64 ranks and split, 8 per L3, on 8 L3s and 8 channels"], size=13)
    add_text(s, 6.78, 4.25, 5.85, 0.36, ["What it shows"], size=15, color=NAVY, bold=True)
    bullets(s, 6.78, 4.65, 5.85, 1.8, ["Half the cores: ×0.99–1.02, no change", "Half the channels: ×2.11–2.20, as the triad bandwidth drops ×2.22", "Limit: packed64 also halves the L3, so DRAM bandwidth and L3 capacity are not separated"], size=13)
    caption(s, "Memory-controller counters and IBS are not readable (perf_event_paranoid=2), so we moved the ranks instead (#61). coefficient.dat is bit-identical across placements.", y=6.5)
    return s


def s_changes():
    s = supp("THE SOURCE CHANGES", "Each change removes data movement, never an operation or its order", "s_changes")
    rows = [["Change (patch)", "What it removes", "Why the result is the same"], ["No copies in the solvers (0001)", "smoothSolver built each residual in a new field and copied it; GAMG copied the source, then subtracted", "The same function computes the same residual in place; source − A·psi is the same subtraction per cell"], ["U components in one pass (0002)", "Gauss–Seidel read the shared matrix of U three times, once per component", "The components are independent; each sees the same operations in the same order"], ["No unused boundary updates (0003)", "Six callers built boundary values of a surface integral, exchanged them, and used only the cell values", "The cell values come from the same loop; only values nobody reads are skipped"], ["Fused face loops (0004)", "Interpolated face fields and product fields built before every summation", "The same face expressions, evaluated inside the summation loop in the same face order"]]
    table(s, X0, 1.55, [3.05, 4.5, 4.38], rows, row_h=0.9, size=13, bolds=[None] + [[True, False, False]] * 4, colors=[None] + [[BONUS, INK, INK]] * 4, row_heights=[0.45, 0.9, 0.9, 0.9, 0.9])
    caption(s, "Full text: bonus/README.md and bonus/patches/0001–0004 in the submission. Boundary conditions, every exchange the solution uses, and the bounding of k and omega are unchanged.", y=6.2, h=0.55, size=11.5)
    return s


def detail_slide(s, title, msg, cards, footer):
    clear_slide(s)
    add_sldnum(s, SLDNUM)  # the 10/08 slide held a static number
    set_title(s, title)
    message(s, msg, size=18)
    for i, (number, name, functions, lines, result) in enumerate(cards):
        x = X0 + i * 6.08
        card(s, x, 1.6, 5.85, 4.55)
        shape_text(box(s, x + 0.25, 1.8, 0.85, 0.36, fill=BONUS, radius=0.5), number, size=12)
        add_text(s, x + 1.25, 1.74, 4.45, 0.48, [name], size=16, color=NAVY, bold=True, anchor="m")
        add_text(s, x + 0.25, 2.32, 5.35, 0.62, [{"runs": [f]} for f in functions], size=12.5, color=MUTED)
        bullets(s, x + 0.25, 3.0, 5.35, 2.4, lines, size=13, space_after=4)
        add_text(s, x + 0.25, 5.52, 5.35, 0.5, [result], size=15, color=BONUS, bold=True, anchor="m")
    caption(s, footer, y=6.35, size=12)
    set_notes(s, NOTES["s_detail"])
    return s


def s_detail1():
    cards = [("0001", "No copies in the solvers", ["smoothSolver::scalarSolve", "GAMGSolver::solve"], ["Before: residual = matrix_.residual(...) builds a new field, then copies it", "After: matrix_.residual(residual, ...) writes into the existing buffer", "GAMG: source − A·psi in one pass instead of a copy and a subtraction"], "2.873 → 2.776 s/step (−3.39 %, 4 v 4 jobs)"), ("0002", "U components in one pass", ["fvMatrix::solveSegregated", "solveGaussSeidelComponents"], ["Before: one complete solve per component, each reading the matrix", "After: each face coefficient serves Ux, Uy and Uz in one sweep", "Shared: lower and upper coefficients and the addressing; per component: diagonal, source, norms", "Falls back to the original path when the solver or field type does not match"], "2.781 → 2.718 s/step (−2.29 %, 3 v 3 jobs)")]
    return detail_slide(S[19], "SOURCE CHANGES IN DETAIL (1/2)", "No copies, and the U matrix read once instead of three times", cards, "Face order and per-component convergence are kept. Each gain is against the configuration just before it, in the same period.")


def s_detail2():
    cards = [("0003", "No unused boundary updates", ["fvc::surfaceIntegrateInternal", "gaussConvectionScheme::fvmDiv"], ["Return the internal cell values directly; skip building and evaluating output boundaries that nobody reads", "Input boundary contributions are kept", "Build lower, upper and diagonal in one face loop", "Used at six call sites, including pEqn.H and kOmegaSST"], "2.708 → 2.672 s/step (−1.31 %, 3 v 3 jobs)"), ("0004", "Fused face loops", ["gaussGrad / addLinearFaceSums", "surfaceIntegrateInternal(a, b)"], ["Interpolate while adding the gradient's face sums", "Multiply the two fields inside the integration loop", "No temporary surface fields and no re-reads; boundaries, volume division and order kept", "Non-linear interpolation keeps the original path"], "2.675 → 2.599 s/step (−2.82 %, 3 v 3 jobs)")]
    return detail_slide(S[20], "SOURCE CHANGES IN DETAIL (2/2)", "No unused boundary values, and no temporary face fields", cards, "coefficient.dat matches the unpatched build with the same split at 1, 2 and 4 nodes.")


def s_each():
    s = supp("EFFECT OF EACH BONUS CHANGE", "Each change against the configuration just before it; separate experiments, not added up", "s_each")
    add_text(s, X0, 1.58, 6.3, 0.36, ["Change in time per step (%)"], size=15, color=NAVY, bold=True)
    categories = ["multiLevel\nvs scotch", "+ no copies\nin solvers", "+ U in\none pass", "+ no unused\nboundary updates", "+ fused face\nloops"]
    series = [("1 node", (-0.45, -2.19, -6.39, -1.40, -2.88)), ("2 nodes", (-0.38, -2.94, -4.13, -1.88, -2.29)), ("4 nodes", (-1.54, -3.39, -2.29, -1.31, -2.82))]
    bar_chart(s, 0.5, 1.95, 6.55, 4.5, categories, series, colors=["F5C99B", "E9A15B", BONUS], horizontal=False, number_format='0;"−"0', vmin=-7, vmax=0, major=1, font_size=11, gap=60, overlap=-5, legend=True, value_axis=True, gridlines=True, labelled=())
    rows = [["Change", "1 node", "2 nodes", "4 nodes"], ["multiLevel vs scotch defaults", "−0.45 %", "−0.38 %", "−1.54 %"], ["+ no copies in the solvers", "−2.19 %", "−2.94 %", "−3.39 %"], ["+ U components in one pass", "−6.39 %", "−4.13 %", "−2.29 %"], ["+ no unused boundary updates", "−1.40 %", "−1.88 %", "−1.31 %"], ["+ fused face loops", "−2.88 %", "−2.29 %", "−2.82 %"]]
    table(s, 7.3, 1.6, [2.22, 1.0, 1.0, 1.11], rows, row_h=0.5, size=12.5, bolds=[None] + [[True, False, False, True]] * 5, colors=[None] + [[INK, INK, INK, BONUS]] * 5, aligns=["l", "r", "r", "r"])
    bullets(s, 7.3, 4.85, 5.33, 1.6, ["4 nodes: 3–4 jobs each, alternated; most 1- and 2-node values are single jobs", "coefficient.dat is bit-identical for every source change"], size=12.5)
    return s


def s_profiles():
    s = supp("PROFILES BEFORE AND AFTER", "The source changes shorten the computation by 9 % and leave MPI as it was", "s_profiles")
    add_text(s, X0, 1.58, 7.4, 0.36, ["Seconds per rank in 40 steps (mean of 512 ranks)"], size=15, color=NAVY, bold=True)
    categories = ["Final Bonus\n118.5 s, MPI 19.9 %", "Bonus, first change only\n127.6 s, MPI 18.3 %", "Basic (scotch)\n137.6 s, MPI 19.4 %"]
    series = [("computation", (94.94, 104.25, 110.83)), ("MPI_Allreduce", (11.35, 11.01, 12.89)), ("MPI_Waitall", (8.45, 8.78, 10.25)), ("other MPI", (3.73, 3.60, 3.61))]
    bar_chart(s, 0.5, 1.95, 7.6, 3.9, categories, series, colors=["A9BCDD", "E8907F", "F2B36B", "F7D9B4"], stacked=True, number_format="0.0", vmin=0, vmax=140, font_size=12, label_size=12, gap=55, overlap=100, legend=XL_LEGEND_POSITION.BOTTOM, value_axis=False, gridlines=False, label_pos="ctr", labelled=(0,))
    bullets(s, 8.45, 1.7, 4.18, 4.8, ["CrayPAT diagnostic runs, 4 nodes, 512 ranks, 40 steps (#53)", "Computation per rank 104.2 → 94.9 s from the first change alone to the final Bonus; MPI stays ≈ 23.5 s", "The spread between ranks stays: max / median 1.074 → 1.067; the whole distribution moves down by about 9 %"], size=13)
    caption(s, "“Bonus, first change only”: multiLevel with no copies in the solvers, before the other three source changes.", y=6.1)
    return s


def s_efficiency():
    s = supp("WHY THE EFFICIENCY EXCEEDS 1", "On 4 nodes the cell arrays fit in L3: 30 % fewer DRAM refills per cell", "s_efficiency")
    rows = [["Per cell and step (Basic, uProf)", "1 node", "2 nodes", "4 nodes", "4 nodes / 1 node"], ["Cycles", "24,235", "22,860", "20,418", "0.843"], ["L1 demand refills from DRAM", "24.6", "20.7", "17.1", "0.697"], ["L1 demand refills from L3 (same CCX)", "5.4", "6.3", "9.4", "1.75"]]
    table(s, X0, 1.62, [4.4, 1.7, 1.7, 1.7, 2.43], rows, row_h=0.5, size=14, bolds=[None] + [[True, False, False, False, True]] * 3, colors=[None, [INK, INK, INK, INK, NAVY], [INK, INK, INK, INK, RED], [INK, INK, INK, INK, NAVY]], aligns=["l", "r", "r", "r", "r"])
    bullets(s, X0, 3.85, XW, 2.8, ["AMD uProf data_access, one rank per NUMA domain, normalised by ranks, steps and cells per rank (#66)", "The sparse-matrix kernels gather cell arrays in face order: their DRAM refills fall to 0.30 (Gauss–Seidel), 0.40 (residual) and 0.42 (A·x); a loop that streams cell fields stays at 0.95", "Cell arrays per rank: 4 MB on 1 node, 2 MB on 2, 1 MB on 4, against 4 MB of L3 per core; the face arrays (≈ 16 MB) never fit", "The same counters explain the imbalance left: a rank's cycles follow its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24)"], size=13.5)
    return s


def s_cd():
    s = supp("DRAG COEFFICIENT CHECKS", "Cd depends on the split before convergence; the Bonus is bit-identical to its own baseline", "s_cd")
    rows = [["Steps", "OHC-1 values", "Baseline (hierarchical)", "scotch defaults", "Basic (mapped scotch)", "Bonus (multiLevel)"], ["40", "0.433 – 0.436", "0.43305", "0.43599", "0.43958", "0.43828"], ["80", "0.334 – 0.345", "0.33733", "0.32714", "0.33410", "0.32286"], ["150", "0.284 – 0.292", "0.27356", "0.28405", "0.29302", "0.29139"]]
    table(s, X0, 1.62, [1.0, 2.0, 2.45, 1.95, 2.35, 2.18], rows, row_h=0.5, size=14, colors=[None] + [[INK, MUTED, BASE, INK, BASIC, BONUS]] * 3, bolds=[None] + [[True, False, False, False, True, True]] * 3, aligns=["c"] * 6)
    bullets(s, X0, 3.85, XW, 2.8, ["The organisers' notes: hierarchical and scotch differ by 0.7 / 3.0 / 3.5 % at 40 / 80 / 150 steps; the node mapping moves Cd by +0.8 / +2.1 / +3.2 %, within that", "Same split as the organisers: our 150-step Cd is 0.284049 against their 0.283983 (2.3 × 10⁻⁴). With the site module and our scripts we get their value exactly, so the difference is our build (AMD's math library), not the method", "Every job of the same configuration and node count produced a byte-identical coefficient.dat"], size=13.5)
    return s


def s_repro():
    s = supp("REPRODUCING OUR RESULTS", "The submitted scripts, run from public sources: same Cd, times within 0.4 %", "s_repro")
    rows = [["Configuration", "Nodes", "s / step", "Recorded mean", "Change", "coefficient.dat"], ["Basic (2026-10-16)", "1", "13.413150", "13.364504", "+0.36 %", "identical"], ["Basic (2026-10-16)", "2", "6.390324", "6.371748", "+0.29 %", "identical"], ["Basic (2026-10-16)", "4", "2.904620", "2.897638", "+0.24 %", "identical"], ["Bonus (2026-10-07)", "1", "11.644042", "11.668460", "−0.21 %", "identical"], ["Bonus (2026-10-07)", "2", "5.649779", "5.640683", "+0.16 %", "identical"], ["Bonus (2026-10-07)", "4", "2.600607", "2.599353", "+0.05 %", "identical"]]
    table(s, X0, 1.6, [2.85, 1.0, 2.0, 2.2, 1.6, 2.28], rows, row_h=0.45, size=14, colors=[None] + [[BASIC, INK, INK, INK, INK, GREEN]] * 3 + [[BONUS, INK, INK, INK, INK, GREEN]] * 3, bolds=[None] + [[True, False, False, False, False, True]] * 6, aligns=["l", "c", "r", "r", "r", "c"])
    bullets(s, X0, 4.95, XW, 1.6, ["build/build.pbs builds from the official public sources; run/submit.sh 1|2|4 runs the whole Allrun chain with plain qsub", "Every step ended with End and returned 0; every solve job reported bound=128/128 on every node"], size=13.5)
    return s


def s_rejected():
    s = supp("NOT ADOPTED: THE FULL LIST", "What we tried, what happened, and what we learned", "s_rejected")
    rows = [["Idea (tier)", "Result, 4 nodes", "Why it did not help"], ["-march=znver3, AOCC 5.0, -O2, LTO (Basic)", "within ±0.1 %", "The loops wait on memory, not on instructions"], ["GCC profile-guided optimisation (Basic)", "+0.13 % (+0.08 % on 1 node)", "The same; Cd bit-identical"], ["Default OFI with the organisers' workarounds (Basic)", "+0.77 % (3 v 3), +0.50 % (1 v 1)", "Not faster than UCX; same Cd, no SIGBUS"], ["UCX over RC instead of UD between nodes", "−0.01 % Basic, −0.16 % Bonus", "IMB bandwidth +55 %, but a step does not wait on transfers"], ["OpenFOAM comm switches (topoControl, nbx, pbufs)", "no gain; commsType scheduled crashed", "MPI time is waiting for the slowest rank"], ["Rank reordering (MPICH_RANK_REORDER_METHOD=3)", "+0.1 %, 92 % fewer faces between nodes", "Fewer bytes between nodes do not shorten the wait"], ["GAMG coarsest level on fewer ranks (Bonus)", "−0.25 % to +4.95 %", "81 % of the global sums, but ≈ 0.6 % of the time"], ["Weighted cells (×2, ×12), METIS two constraints (Bonus)", "+1.5 % to +6.1 %", "Uneven cells, or 18 % more faces between subdomains"], ["glibc malloc thresholds (Basic)", "−0.4 % (3 jobs)", "Too small to separate with 3 jobs; not re-tested"], ["SMT, 2 ranks per core (Basic)", "≈ 5.7× slower", "Stalls of minutes; cause not isolated"], ["Overlapping halo exchange with computation", "under 1 % available", "Led to skipping unused exchanges instead (0003)"], ["File I/O in the timed steps", "≈ 0.01 % of a step", "Not a factor"]]
    table(s, X0, 1.6, [4.85, 3.45, 3.63], rows, row_h=0.37, size=11.5, bolds=[None] + [[True, False, False]] * 12, margins=(0.08, 0.04, 0.08, 0.04))
    return s


def s_compiler():
    s = S[16]
    clear_slide(s)
    set_title(s, "COMPILER AND FLAGS")
    message(s, "Every compiler and flag variant lies inside the control's range", size=18)
    picture_fit(s, fig("fig07_compiler_options"), X0, 1.5, XW, 4.85)
    caption(s, "4 nodes, scotch, 3 jobs each in the same period (2026-10-03). Shaded: range of the control jobs; every mean lies inside it. GCC PGO: +0.13 % (#59).", y=6.45, size=11.5)
    set_notes(s, NOTES["s_compiler"])
    return s


def fill_index(s, entries):
    """Q&A index: one clickable line per supporting slide; call after the slide order is final."""
    set_title(s, "Q&A INDEX")
    message(s, "Supporting slides for questions: click a line to jump there", size=18)
    groups = [(0, "Measurement and setup", entries[0:4]), (0, "Baseline and Basic", entries[4:9]), (1, "Memory and Bonus", entries[9:16]), (1, "Results, and what we did not use", entries[16:])]
    next_y = [1.55, 1.55]
    for column, group_name, items in groups:
        x, y0 = (X0, 6.78)[column], next_y[column]
        add_text(s, x, y0, 5.85, 0.36, [group_name], size=15, color=NAVY, bold=True)
        for k, (title, target) in enumerate(items):
            line = add_text(s, x + 0.1, y0 + 0.4 + k * 0.36, 5.75, 0.33, [[(f"{prs.slides.index(target) + 1}", {"b": True, "color": NAVY}), ("   " + title, {})]], size=13, anchor="m")
            line.click_action.target_slide = target
        next_y[column] = y0 + 0.4 + len(items) * 0.36 + 0.3
    set_notes(s, NOTES["index"])


# ====================================================================== assemble
main = [slide_title(), slide_overview(), slide_aspire(), slide_baseline_settings(), slide_baseline_results(), slide_measure(), slide_baseline_analysis(), slide_strategy(), slide_basic_pinning(), slide_basic_decomp(), slide_basic_results(), slide_bandwidth(), slide_bonus_opt(), slide_bonus_results(), slide_bonus_analysis(), slide_scaling(), slide_not_helped(), slide_conclusion(), slide_extra()]
divider = S[15]
supporting = [("Measuring honestly", s_noise()), ("Experiment automation", s_automation()), ("Build, storage and MPI", s_build()), ("The organisers' reference", s_reference()), ("Baseline MPI calls", s_mpi_calls()), ("Where a step goes after Basic", s_step()), ("The path on 4 nodes", s_path()), ("Is the network the bottleneck?", s_network()), ("OFI against UCX", s_ofi()), ("Cores or memory?", s_cores()), ("The source changes", s_changes()), ("Source changes in detail (1/2)", s_detail1()), ("Source changes in detail (2/2)", s_detail2()), ("Effect of each Bonus change", s_each()), ("Profiles before and after", s_profiles()), ("Why the efficiency exceeds 1", s_efficiency()), ("Drag coefficient checks", s_cd()), ("Reproducing our results", s_repro()), ("Not adopted: the full list", s_rejected()), ("Compiler and flags", s_compiler())]
add_sldnum(S[23], SLDNUM)  # the shared reproducibility slide held a static "14"
deleted = [S[17], S[18], S[21], S[22]]  # 10/08 compact slides that repeat the main part with older numbers
index_slide = new_slide()
order = main + [divider, index_slide] + [sl for _, sl in supporting] + S[23:]

sldIdLst = prs.slides._sldIdLst
by_part = {prs.part.related_part(sldId.rId): sldId for sldId in sldIdLst}
for sl in deleted:
    sldId = by_part.pop(sl.part)
    sldIdLst.remove(sldId)
    prs.part.rels.pop(sldId.rId)
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
