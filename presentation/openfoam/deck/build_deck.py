# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0", "lxml", "pillow", "xlsxwriter"]
# ///
"""Rebuild the OpenFOAM (HPC) part of the team deck as the 7th edition of ../slides.md.

usage: uv run build_deck.py INPUT.pptx OUTPUT.pptx FIGDIR

INPUT is the team deck whose OpenFOAM part is still the 10/29 build: the cover 1, main 2-21 with the team's HPC roofline at
14, divider 22, Q&A index 23, supporting 24-45 and the shared reproducibility slide 46, then the AI track from slide 47 on.
FIGDIR holds the deck's renders of ../figures.py (deck_figures.py) and its per-job plots (deck_plots.py); build.sh runs all
three steps.

The output keeps the cover, then the 14 main slides of slides.md, the divider, the Q&A index, 17 supporting slides and the
shared reproducibility slide. They are rebuilt in place on input slides, so each keeps a slide id and the team's slide-number
box; the 11 input slides left over (the roofline among them) are removed. The notes of the main slides are read from
slides.md (script, translation, memo), the others come from notes.py. Every slide from the AI title slide on stays byte for
byte, and PowerPoint's sections follow the new slide list.
"""

import csv
import re
import sys
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.chart import XL_LEGEND_POSITION

from decklib import add_text, arrow_line, bar_chart, box, bullets, clear_slide, picture, set_notes, set_title, shape_text, table
from notes import NOTES
from palette import BAD, BASE, BASIC, BONUS, BONUS_LIGHT, BONUS_LINE, BONUS_TINT, FAINT, INK, LIGHT, LINE, MUTED, NAVY

SRC, OUT, FIG = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
HERE = Path(__file__).resolve().parent
PLAN, DATA = HERE.parent / "slides.md", HERE.parent / "data"
prs = Presentation(SRC)
S = list(prs.slides)  # S[i] is input slide i + 1
EMU = 914400
X0, XW = 0.70, 11.93  # left edge and width of the content area; the title ends at 0.80 in and the slide number at 7.14 in
DECOMP_COLUMNS = {"hier": (0.0, 0.667), "scotch": (0.333, 0.334)}
PANEL_TOP, ALL_BOTTOM = 0.113, 0.085
P14 = "http://schemas.microsoft.com/office/powerpoint/2010/main"
# the titles of the input's OpenFOAM part, slides 1-46, in order
INPUT_TITLES = ["", "OpenFOAM TASK OVERVIEW", "ASPIRE-2A", "BASELINE SETTINGS", "BASELINE RESULTS", "HOW WE MEASURE AND PROFILE", "MPI PROFILE ON 4 NODES", "BASELINE ANALYSIS", "OPTIMIZATION STRATEGY", "BASIC OPTIMIZATION (1/2)", "BASIC OPTIMIZATION (2/2)", "BASIC RESULTS", "MEMORY BANDWIDTH SETS THE SPEED", "HPC ROOFLINE: MEMORY AND COMMUNICATION", "BONUS OPTIMIZATION", "BONUS RESULTS", "BONUS ANALYSIS", "SCALING ANALYSIS", "WHAT DID NOT HELP, AND WHY", "CONCLUSION", "EXTRA: A GAIN WE DID NOT COUNT", "SUPPORTING INFORMATION", "Q&A INDEX", "BOTTLENECKS WE MEASURED", "MEASURING HONESTLY", "EXPERIMENT AUTOMATION", "BUILD, STORAGE AND MPI", "THE ORGANISERS' REFERENCE", "WHERE A STEP GOES AFTER BASIC", "THE PATH ON 4 NODES", "IS THE NETWORK THE BOTTLENECK?", "OFI AGAINST UCX", "THE THREE SPLITS: FACES OR EVEN WORK?", "CORES OR MEMORY?", "THE SOURCE CHANGES (1/2)", "THE SOURCE CHANGES (2/2)", "SOURCE CHANGES IN DETAIL (1/2)", "SOURCE CHANGES IN DETAIL (2/2)", "EFFECT OF EACH BONUS CHANGE", "PROFILES BEFORE AND AFTER", "WHY THE EFFICIENCY EXCEEDS 1", "DRAG COEFFICIENT CHECKS", "REPRODUCING OUR RESULTS", "NOT ADOPTED: THE FULL LIST", "COMPILER AND FLAGS", "Reproducibility: Code, Build, Runtime and Results"]
AI = len(INPUT_TITLES)  # S[AI] is the AI track's title slide


def check_input():
    titles = [s.shapes.title.text_frame.text if s.shapes.title is not None else "" for s in S]
    ai_title = " ".join(sh.text_frame.text for sh in S[AI].shapes if sh.has_text_frame) if len(S) > AI else ""
    if titles[:AI] != INPUT_TITLES or "AI Track" not in ai_title:
        raise SystemExit("build_deck.py expects the team deck with the 10/29 OpenFOAM part (slides 1-46, the HPC roofline at 14, the AI title slide at 47); see README.md")


def plan_notes():
    """The notes of the 14 main slides from slides.md: the time, the English script, its translation and the memo."""
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
    if len(notes) != 14:
        raise SystemExit(f"slides.md has {len(notes)} main slides instead of 14; see README.md")
    return notes


check_input()
PLAN_NOTES = plan_notes()
DECOMP = next(sh for sh in S[3].shapes if sh.name == "図 7").image.blob  # hierarchical, scotch, multiLevel x car, centre plane, cross-section


def reuse(i, keep=()):
    """Input slide i + 1, emptied but for its title, its slide number and the shapes named in keep."""
    clear_slide(S[i], keep=keep)
    return S[i]


def fig(name):
    return FIG / f"{name}.png"


def place(s, name, x, y, w, h):
    sh = next(sh for sh in s.shapes if sh.name == name)
    sh.left, sh.top, sh.width, sh.height = (int(v * EMU) for v in (x, y, w, h))


def heading(s, x, y, w, text, size=16):
    """A short heading over a figure or table: no number, no claim."""
    return add_text(s, x, y, w, 0.38, [text], size=size, color=NAVY, bold=True)


def decomp_panel(s, which, x, y, w=None, h=None, bottom=ALL_BOTTOM):
    left, right = DECOMP_COLUMNS[which]
    return picture(s, DECOMP, x, y, w, h, crop=(left, PANEL_TOP, right, bottom))


def channel_row(s, x, y, used, size=0.22, gap=0.06):
    for k in range(16):
        box(s, x + k * (size + gap), y, size, size, fill=NAVY if k < used else "D5D9E0", radius=0.15)


def replace_run_text(s, shape_name, old, new):
    """Replace text inside one run of a shape that the team made, keeping the run's formatting; done if new is there."""
    for paragraph in next(sh for sh in s.shapes if sh.name == shape_name).text_frame.paragraphs:
        for run in paragraph.runs:
            if new in run.text:
                return
            if old in run.text:
                run.text = run.text.replace(old, new)
                return
    raise SystemExit(f"{shape_name}: neither '{old}' nor '{new}' found; see README.md")


# ====================================================================== main part (slides.md 1-14, deck 2-15)
def m_summary():
    s = reuse(1, keep=("flow-iterations",))
    set_title(s, "OpenFOAM ON ASPIRE-2A")
    w = 6.3
    h = w * 3.0 / 5.33  # the video's own 16:9 frame
    place(s, "flow-iterations", X0, 1.35 + (5.5 - h) / 2, w, h)
    xr = 7.35
    add_text(s, xr, 1.35, 12.63 - xr, 0.42, ["Time per step on 4 nodes"], size=18, color=NAVY, bold=True)
    small = {"size": 13, "color": MUTED, "bold": False}

    def big(text):
        return [{"runs": [text], "size": 26}]

    rows = [[[{"runs": ["Common baseline"]}, {"runs": ["with hierarchical"], **small}], big("3.415"), ""], [[{"runs": ["Common baseline"]}, {"runs": ["with scotch"], **small}], big("3.576"), ""], ["Our baseline", big("3.650"), ""], [[{"runs": ["Basic"]}, {"runs": ["Basic restores the CPU and memory binding and balances the computation between ranks."], **small}], big("2.898"), "−20.6%"], [[{"runs": ["Bonus"]}, {"runs": ["The Bonus moves less data because memory bandwidth limits the solver."], **small}], big("2.360"), [{"runs": ["−18.6%"]}, {"runs": ["vs Basic"], **small}]]]
    colors = [[MUTED] * 3, [MUTED] * 3, [BASE] * 3, [BASIC] * 3, [BONUS] * 3]
    table(s, xr, 1.85, [2.55, 1.35, 1.38], rows, header=False, size=17, colors=colors, bolds=[[True] * 3] * 5, aligns=["l", "r", "r"], row_heights=[0.78, 0.78, 0.66, 1.3, 1.2])
    set_notes(s, PLAN_NOTES[0])
    return s


def m_criteria():
    s = reuse(2)
    set_title(s, "CRITERIA FOR KEEPING A CHANGE")
    rules = ["Candidate and control ran in turns in the same period with at least 3 jobs each on 4 nodes.", "We kept a change only if every candidate job was faster than every control job.", "Source changes had to keep Cd within 0.5% of the unmodified code.", "A profile had to explain why the change helped."]
    add_text(s, X0, 1.5, 6.05, 5.3, [{"runs": [rule], "bullet": {"number": True, "size_pct": 100, "indent": 0.42}, "space_after": 18} for rule in rules], size=19)
    picture(s, fig("p07_rule"), 7.08, 1.32, w=5.55)
    set_notes(s, PLAN_NOTES[1])
    return s


def m_profile_baseline():
    s = reuse(3)
    set_title(s, "PROFILING THE BASELINE")
    add_text(s, X0, 1.35, XW, 0.95, [{"runs": ["Our baseline was unmodified v2512 built with GCC 11.2 and run on Cray MPICH over UCX."], "space_after": 4}, "It took 3.650 s per step on 4 nodes with an SD of 4.1% over 3 jobs."], size=18)
    rows = [["Possible bottleneck", "How we measured it", "What we found"], ["MPI", "CrayPAT and OpenFOAM profiling", "46% of each rank's time"], ["Computation", "CrayPAT and AMD uProf", "The other 54% of the time"], ["Network transfer", "IMB after every run", "Global sums took about 0.02 s per step"], ["File I/O and OS noise", "Timers and interrupt counts", "0.01% and 0.8% of the time"]]
    table(s, X0, 2.6, [3.0, 4.2, 4.73], rows, row_heights=[0.55, 0.8, 0.8, 0.8, 0.8], size=17, bolds=[None] + [[True, False, False]] * 4, colors=[None, [INK, INK, BAD], None, None, None])
    set_notes(s, PLAN_NOTES[2])
    return s


def m_mpi():
    """The organisers' ISC26 SCC task asks for the 3 most used MPI calls on 4 nodes, by number of calls and by total CPU time;
    the APAC task rules strongly recommend MPI profiling."""
    s = reuse(4)
    set_title(s, "MPI CALLS ON 4 NODES")
    add_text(s, X0, 1.35, XW, 0.4, ["CrayPAT profile of the baseline with 512 ranks over 40 steps."], size=16, color=MUTED)
    rows = [["Most calls", "Calls", "Most time", "Time", "Share of MPI"], ["MPI_Isend", "290 M", "MPI_Waitall", "22,069 s", "55%"], ["MPI_Irecv", "290 M", "MPI_Allreduce", "14,140 s", "35%"], ["MPI_Test", "289 M", "MPI_Bcast", "1,289 s", "3%"]]
    table(s, X0, 1.85, [2.6, 1.6, 3.0, 2.2, 2.53], rows, row_heights=[0.55, 0.62, 0.62, 0.62], size=17, aligns=["l", "r", "l", "r", "r"], colors=[None, [INK, INK, BAD, BAD, BAD], [INK, INK, BAD, BAD, BAD], None])
    bullets(s, X0, 4.6, XW, 2.3, ["Most calls were the halo exchange with neighbouring subdomains.", "Waitall and Allreduce took 90% of the MPI time waiting for other ranks.", "With equal cells the slowest rank computed for 2.9 s per step and the median rank for 2.0 s."], size=18, space_after=10)
    set_notes(s, PLAN_NOTES[3])
    return s


def m_pinning():
    s = reuse(5)
    set_title(s, "CPU AND MEMORY PINNING")
    bullets(s, X0, 1.5, 6.0, 5.4, ["During the solve no rank stayed on its own core and only 9% of its memory was local.", "The launcher had bound each rank but MPI_Init removed the binding.", "Our job script binds the memory with numactl before each rank starts and re-pins the rank with taskset.", "With the case-default decomposition a step dropped from 3.670 to 3.257 s in the same period."], size=18, space_after=16)
    picture(s, fig("p10_pinning"), 6.93, 1.32, w=5.7)
    set_notes(s, PLAN_NOTES[4])
    return s


def m_decomposition():
    s = reuse(6)
    set_title(s, "DECOMPOSITION")
    pw = 2.95
    for i, (which, label) in enumerate((("hier", "hierarchical"), ("scotch", "scotch"))):
        x = X0 + i * (pw + 0.18)
        add_text(s, x, 1.3, pw, 0.38, [label], size=17, color=NAVY, bold=True, align="c")
        decomp_panel(s, which, x, 1.72, w=pw)
    bullets(s, 7.05, 1.5, 5.58, 5.4, ["With hierarchical the ranks whose slabs held much of the car's surface got more computation.", "scotch keeps the cell counts equal with 32% fewer faces between subdomains.", "The slowest rank fell from 1.16 to 1.06 times the median and a step from 3.257 to 2.915 s.", "Telling scotch about the sockets and NUMA domains saved another 0.7%."], size=18, space_after=16)
    set_notes(s, PLAN_NOTES[5])
    return s


def m_basic_results():
    s = reuse(7)
    set_title(s, "BASIC RESULTS")
    bullets(s, X0, 2.3, 6.1, 3.0, ["Basic took 2.898 s per step on 4 nodes against 3.650 for our baseline.", "The SD between identical jobs fell from 4.1% to 0.07%."], size=20, space_after=20)
    picture(s, fig("p12_basic"), 7.23, 1.32, w=5.4)
    set_notes(s, PLAN_NOTES[6])
    return s


def m_profile_basic():
    s = reuse(8)
    set_title(s, "PROFILING BASIC")
    rows = [["Possible bottleneck", "How we measured it", "What we found after Basic"], ["MPI", "CrayPAT", "Fell from 46% to 19% of the time"], ["Computation", "CrayPAT and AMD uProf", "81% of the time with about 0.1 flop per byte in the hottest loops"], ["Core speed", "Core counters and five compiler settings", "0.4 to 0.7 instructions per cycle and no compiler setting helped"], ["Memory bandwidth", "Memory controller counters", "Not readable by users on ASPIRE-2A"]]
    table(s, X0, 1.5, [2.9, 3.9, 5.13], rows, row_heights=[0.55, 0.85, 1.15, 1.15, 0.85], size=17, bolds=[None] + [[True, False, False]] * 4, colors=[None, None, None, None, [INK, INK, BAD]])
    set_notes(s, PLAN_NOTES[7])
    return s


def m_memory_limit():
    """No memory-controller counters on ASPIRE-2A, so the placement experiment of #61 stands in: Basic before the mapping,
    4 nodes, every rank pinned, STREAM triad on the same nodes after the solver."""
    s = reuse(9)
    set_title(s, "MEASURING THE MEMORY LIMIT")
    bullets(s, X0, 1.5, 5.9, 5.4, ["We could not read the memory counters so we changed only where the ranks ran.", "Half the cores on all 16 memory channels took the same time.", "The same ranks on 8 of the 16 channels took 2.2 times as long and STREAM fell by the same factor.", "About 97% of a step follows the memory bandwidth."], size=18, space_after=16)
    xr = 7.0
    placements = [("128 ranks per node on all 16 channels", 16, "2.920 s/step", "STREAM 274 GB/s", INK), ("64 ranks per node on all 16 channels", 16, "2.887 s/step", "STREAM 279 GB/s", INK), ("64 ranks per node on 8 of the 16 channels", 8, "6.347 s/step", "STREAM 125 GB/s", BAD)]
    for k, (label, used, time, bandwidth, color) in enumerate(placements):
        y = 1.45 + k * 1.78
        add_text(s, xr, y, 5.63, 0.38, [label], size=16, bold=True)
        channel_row(s, xr, y + 0.48, used, size=0.27, gap=0.075)
        add_text(s, xr, y + 0.88, 5.63, 0.55, [[(time, {"b": True, "color": color, "size": 22}), ("     " + bandwidth, {"color": MUTED, "size": 16})]], size=16, anchor="m")
    set_notes(s, PLAN_NOTES[8])
    return s


def u_diagram(s, x, y):
    """The second source change: the three components of U share one matrix, so one pass over it updates all three."""
    heading(s, x, y, 5.28, "Example: the three components of U")
    add_text(s, x, y + 0.48, 5.28, 0.32, ["Before: one pass per component"], size=14, bold=True)
    for k, component in enumerate(("Ux", "Uy", "Uz")):
        yy = y + 0.9 + k * 0.56
        shape_text(box(s, x, yy, 2.15, 0.44, fill=LIGHT, line=LINE, radius=0.12), "matrix", size=13, color=NAVY, bold=False)
        arrow_line(s, x + 2.2, yy + 0.22, x + 2.85, yy + 0.22, color=FAINT)
        shape_text(box(s, x + 2.9, yy, 2.2, 0.44, fill=BONUS_TINT, line=BONUS_LINE, radius=0.12), f"sweep {component}", size=13, color=INK, bold=False)
    add_text(s, x, y + 2.6, 5.1, 0.34, ["the matrix is read 3 times"], size=14, color=BAD, bold=True, align="c")
    add_text(s, x, y + 3.15, 5.28, 0.32, ["After: one pass for all three"], size=14, bold=True)
    shape_text(box(s, x, y + 3.57, 2.15, 1.1, fill=LIGHT, line=LINE, radius=0.08), "matrix", size=13, color=NAVY, bold=False)
    arrow_line(s, x + 2.2, y + 4.12, x + 2.85, y + 4.12, color=FAINT)
    shape_text(box(s, x + 2.9, y + 3.57, 2.2, 1.1, fill=BONUS_TINT, line=BONUS_LINE, radius=0.08), ["sweep Ux", "sweep Uy", "sweep Uz"], size=13, color=INK, bold=False)
    add_text(s, x, y + 4.77, 5.1, 0.34, ["the matrix is read once"], size=14, color=BONUS, bold=True, align="c")


def m_bonus_opt():
    s = reuse(10)
    set_title(s, "BONUS OPTIMIZATIONS")
    bullets(s, X0, 1.5, 6.1, 5.4, ["A multiLevel decomposition by nodes, sockets, NUMA domains and cores saved 1.5%.", "14 source changes reduced the data each step moves.", "None of them changes the iterations, the convergence tests or the discretisation."], size=18, space_after=18)
    u_diagram(s, 7.35, 1.35)
    set_notes(s, PLAN_NOTES[9])
    return s


def m_bonus_results():
    s = reuse(11)
    set_title(s, "BONUS RESULTS")
    bullets(s, X0, 1.5, 5.7, 5.4, ["The Bonus took 2.360 s per step on 4 nodes against 2.898 for Basic.", "The first four changes cut instructions by 4% but L1 refills from DRAM by 17%.", "With half the memory channels the same four changes gained 11.4% instead of 7.9%.", "Cd stayed within 0.0005% of the unmodified code at 1, 2 and 4 nodes."], size=18, space_after=16)
    xr = 6.7
    heading(s, xr, 1.35, 12.63 - xr, "The first four changes against none, 1 node")
    categories = ["L1 refills from DRAM", "L2 accesses incl. prefetch", "L1 data accesses", "Instructions", "Cycles", "Time per step"]
    bar_chart(s, xr - 0.15, 1.8, 12.63 - xr + 0.15, 5.1, categories, [("change", (-17.17, -9.61, -5.85, -4.07, -10.81, -12.28))], point_colors=[BONUS, BONUS_LIGHT, BONUS_LIGHT, FAINT, BONUS_LIGHT, BONUS_LIGHT], number_format='0.0"%";"−"0.0"%"', vmin=-25, vmax=0, font_size=15, label_size=16, gap=45, value_axis=False, gridlines=False)
    set_notes(s, PLAN_NOTES[10])
    return s


def m_scaling():
    s = reuse(12)
    set_title(s, "SCALING FROM 1 TO 4 NODES")
    picture(s, fig("p17_scaling"), X0 - 0.1, 1.3, w=7.6)
    xr = 8.65
    add_text(s, xr, 1.55, 12.63 - xr, 1.3, ["Basic and the Bonus were faster than our baseline at every node count."], size=19)
    heading(s, xr, 3.2, 12.63 - xr, "Parallel efficiency, 1 to 4 nodes")
    for k, (name, value, color) in enumerate((("Our baseline", "1.00", BASE), ("Basic", "1.15", BASIC), ("Bonus", "1.08", BONUS))):
        y = 3.7 + k * 0.9
        add_text(s, xr, y, 2.4, 0.75, [name], size=19, color=color, bold=True, anchor="m")
        add_text(s, xr + 2.3, y, 1.68, 0.75, [value], size=32, color=color, bold=True, anchor="m", align="r")
    set_notes(s, PLAN_NOTES[11])
    return s


def m_not_helped():
    s = reuse(14)
    set_title(s, "WHAT DID NOT HELP")
    rows = [["Idea that usually helps", "Time per step against its control"], ["Compiler flags, AOCC, LTO and PGO", "Within 0.13%"], ["UCX over RC with 55% more network bandwidth", "Within 0.2%"], ["Rank reordering with 92% fewer faces between nodes", "+0.1%"], ["Weights or METIS to balance the faces", "+1.5% to +6.1%"]]
    table(s, X0, 1.5, [6.93, 5.0], rows, row_heights=[0.55] + [0.66] * 4, size=17, aligns=["l", "r"], bolds=[None] + [[False, True]] * 4)
    bullets(s, X0, 5.05, XW, 1.9, ["None of them reduced the data that the slowest rank reads from memory.", [("Now a step is limited by memory traffic and by the ranks that read the most from DRAM.", {"b": True, "color": NAVY})]], size=19, space_after=14)
    set_notes(s, PLAN_NOTES[12])
    return s


def m_final():
    """Top half: the gain we did not count (#68); bottom half: the times of slide 1 as a path, and the final result."""
    s = reuse(15)
    set_title(s, "AN UNCOUNTED GAIN AND OUR RESULT")
    bullets(s, X0, 1.35, XW, 2.45, ["Many solvers still computed a residual and a global sum at every iteration for a test that fixed iterations never use.", "Doing it once after the last iteration took the Bonus to 2.166 s per step with a byte-identical coefficient.dat.", "We did not count it because only the benchmark's fixed iterations allow it."], size=17, space_after=8)
    arrow_line(s, X0, 3.9, X0 + XW, 3.9, color=LINE, width=1.25, head=False)
    stages = [("Our baseline", "3.650", "case defaults", BASE), ("Basic", "2.898", "binding and balance between ranks", BASIC), ("Bonus", "2.360", "less data moved per step", BONUS)]
    w = 3.3
    gap = (XW - 3 * w) / 2
    for k, (name, value, what, color) in enumerate(stages):
        x = X0 + k * (w + gap)
        add_text(s, x, 4.12, w, 0.42, [name], size=19, color=color, bold=True, align="c")
        add_text(s, x, 4.55, w, 0.95, [[(value, {"size": 46}), (" s/step", {"size": 16, "color": MUTED, "b": False})]], color=color, bold=True, align="c", anchor="m")
        add_text(s, x, 5.52, w, 0.4, [what], size=15, color=MUTED, align="c")
        if k:
            x1, x2 = x - gap + 0.1, x - 0.1
            arrow_line(s, x1, 5.02, x2, 5.02, color=FAINT, width=1.5)
            add_text(s, x1 - 0.2, 4.55, x2 - x1 + 0.4, 0.4, [("−20.6%", "−18.6%")[k - 1]], size=16, color=color, bold=True, align="c")
    add_text(s, X0, 6.25, XW, 0.5, ["The Bonus takes 35.3% less time per step than our baseline with the same computation."], size=18, color=NAVY, bold=True, align="c")
    set_notes(s, PLAN_NOTES[13])
    return s


# ====================================================================== supporting slides
def supp(i, title, notes_key):
    """Supporting slide on input slide i + 1."""
    s = reuse(i)
    set_title(s, title)
    set_notes(s, NOTES[notes_key])
    return s


def label_value_table(s, x, y, col_w, rows, row_h=0.6, size=16):
    return table(s, x, y, col_w, rows, row_h=row_h, size=size, header=False, bolds=[[True, False]] * len(rows), colors=[[NAVY, None]] * len(rows))


def s_aspire():
    s = supp(16, "ASPIRE-2A AND WHY WE CHOSE IT", "s_aspire")
    heading(s, X0, 1.35, 6.9, "One ASPIRE-2A node")
    rows = [["Processor", "2 × AMD EPYC 7713 (Zen 3) with 128 cores at 2.0 GHz"], ["NUMA and cache", "8 NUMA domains of 16 cores and 32 MB of L3 per 8 cores"], ["Memory", "512 GB DDR4-3200 on 16 channels and about 290 GB/s by STREAM"], ["Network", "HPE Slingshot-10 at 100 Gb/s in a dragonfly"], ["Software", "Cray PE with GCC 11.2, Cray MPICH 8.1.15 and PBS Pro"]]
    label_value_table(s, X0, 1.8, [1.95, 5.0], rows, row_h=0.8)
    xr = 8.0
    heading(s, xr, 1.35, 4.63, "Why ASPIRE-2A")
    bullets(s, xr, 1.85, 4.63, 5.0, ["Last year we competed on Gadi, so this year we wanted to learn the other machine.", "OpenFOAM uses very many files, and one build alone is about 36,000 files.", "Our Gadi project allowed 0.2 M files and 1 TB, and ASPIRE-2A allows 200 M files and 100 TB."], size=16, space_after=14)
    return s


def s_settings():
    s = supp(17, "BUILD, MPI AND RUN SETTINGS", "s_settings")
    rows = [["Build", "Official v2512 source with GCC 11.2 -O3 and AMD AOCL-LibM, as fast as the site module (−0.08%)"], ["MPI", "Cray MPICH 8.1.15 over UCX, because the default OFI crashed at MPI_Finalize on 2 and 4 nodes"], ["OFI with workarounds", "No crash and the same Cd, but 0.77% slower than UCX in 3 alternated jobs each"], ["Decomposition", "Baseline hierarchical (16 8 4), Basic scotch mapped onto the node, Bonus multiLevel (4 2 4 16)"], ["Placement", "128 ranks per node, numactl for the memory and a watcher that re-pins each rank with taskset"], ["Storage", "Each node solves from its own copy of the case in $TMPDIR, and file I/O is about 0.01% of a step"], ["Measurement", "The official metric over steps 2 to N, at least 3 jobs per condition, profilers only in separate runs"]]
    label_value_table(s, X0, 1.4, [2.9, 9.03], rows, row_h=0.74)
    return s


def s_noise():
    s = supp(18, "RUN-TO-RUN VARIATION OVER 92 JOBS", "s_noise")
    heading(s, X0, 1.35, 8.7, "Each job against the median of its configuration")
    picture(s, fig("fig08_variability"), 0.45, 1.8, w=8.85)
    bullets(s, 9.55, 1.6, 3.08, 5.35, ["92 jobs in 29 repeated configurations from 21 September to 5 October.", "Most jobs lie within 0.4% of their configuration's median.", "Two September jobs were 84% and 91% slower.", "So we never decide from one job, and we alternate candidate and control."], size=15, space_after=14, anchor="m")
    return s


def s_reference():
    s = supp(19, "THE ORGANISERS' REFERENCE", "s_reference")
    heading(s, X0, 1.35, XW, "Each job of the organisers' runs and of ours on the same machine")
    picture(s, fig("ps_reference"), X0, 1.8, w=XW)
    bullets(s, X0, 5.55, XW, 1.4, ["The percentages compare our means with the mean of the organisers' scotch jobs.", "The organisers used the site module and default MPI settings without binding, and their scotch jobs spread by 12% on 4 nodes.", "Build, MPI transport and placement all differ, so the gap has more than one cause."], size=15, space_after=6)
    return s


def s_repro():
    s = supp(20, "REPRODUCING OUR RESULTS", "s_repro")
    heading(s, X0, 1.35, XW, "Re-runs with the submitted scripts against our recorded means")
    rows = [["Configuration", "Nodes", "s/step", "Recorded mean", "Change", "coefficient.dat"], ["Basic (2026-10-16)", "1", "13.413150", "13.364504", "+0.36%", "identical"], ["Basic (2026-10-16)", "2", "6.390324", "6.371748", "+0.29%", "identical"], ["Basic (2026-10-16)", "4", "2.904620", "2.897638", "+0.24%", "identical"], ["Bonus (2026-10-26)", "1", "10.201813", "10.233606", "−0.31%", "identical"], ["Bonus (2026-10-26)", "2", "4.980185", "4.992196", "−0.24%", "identical"], ["Bonus (2026-10-26)", "4", "2.365118", "2.359976", "+0.22%", "identical"]]
    table(s, X0, 1.8, [2.85, 1.0, 2.0, 2.2, 1.6, 2.28], rows, row_h=0.58, size=15, colors=[None] + [[BASIC, INK, INK, INK, INK, INK]] * 3 + [[BONUS, INK, INK, INK, INK, INK]] * 3, bolds=[None] + [[True, False, False, False, False, True]] * 6, aligns=["l", "c", "r", "r", "r", "c"])
    bullets(s, X0, 6.0, XW, 0.95, ["build/build.pbs builds from the official public sources and run/submit.sh 1|2|4 runs the whole Allrun chain with plain qsub.", "Every step ended with End and returned 0, and every solve job reported bound=128/128 on every node."], size=14, space_after=4)
    return s


def s_network():
    s = supp(23, "IS THE NETWORK THE BOTTLENECK?", "s_network")
    heading(s, X0, 1.35, XW, "Four changes to the network side on 4 nodes")
    rows = [["What we changed on the network side", "How much the network side changed", "Step time (4 nodes)"], ["UCX over RC instead of UD between nodes", "IMB bandwidth (1 MiB Sendrecv) 6.7 → 10.4 GB/s, +55%", "−0.01% Basic, −0.16% Bonus of four changes (4 v 4)"], ["Rank reordering, hierarchical decomposition", "92% fewer faces between nodes", "+0.1%"], ["OFI instead of UCX, with the organisers' two workarounds", "Another transport and provider", "+0.77% (3 v 3), +0.50% (1 v 1)"], ["GAMG coarsest level solved on 32 ranks instead of 512", "Fewer ranks in 81% of the global sums", "−0.25% (1 v 1)"]]
    table(s, X0, 1.8, [4.3, 4.3, 3.33], rows, row_h=0.72, size=15, bolds=[None] + [[True, False, False]] * 4)
    bullets(s, X0, 5.55, XW, 1.4, ["One 8-byte global sum over 512 ranks takes about 12 µs (IMB), so 1,600 per step take about 0.02 s.", "A rank's MPI_Waitall follows its own computation (R² 0.77), and 13 of the 16 slowest ranks have no neighbours on other nodes.", "We did not read NIC or switch counters."], size=15, space_after=6)
    return s


def s_scotch():
    s = supp(24, "HIERARCHICAL AGAINST SCOTCH", "s_scotch")
    heading(s, X0, 1.35, XW, "The same placement with 3 alternated jobs each")
    picture(s, fig("p11_scotch"), X0, 1.8, w=XW)
    bullets(s, X0, 6.05, XW, 0.85, ["scotch was faster at every node count and gained more on more nodes, which we have not explained."], size=16)
    return s


def s_cores():
    s = supp(25, "THE PLACEMENT EXPERIMENT IN FULL", "s_cores")
    heading(s, X0, 1.35, XW, "Time per step under three placements, 4 nodes, 2 jobs each")
    rows = [["s/step (4 nodes, 2 jobs each)", "full128", "spread64", "packed64", "spread64 / full128", "packed64 / spread64"], ["Basic (before the mapping)", "2.920", "2.887", "6.347", "0.99", "2.20"], ["Bonus without the patches", "2.869", "2.874", "6.321", "1.00", "2.20"], ["Bonus, first four changes", "2.595", "2.649", "5.598", "1.02", "2.11"], ["Triad bandwidth per node", "274 GB/s", "279 GB/s", "125 GB/s", "—", "0.45"]]
    table(s, X0, 1.8, [3.5, 1.45, 1.5, 1.5, 1.95, 2.03], rows, row_h=0.58, size=15, bolds=[None] + [[True, False, False, False, True, True]] * 4, colors=[None] + [[INK, INK, INK, INK, NAVY, BAD]] * 4, aligns=["l", "r", "r", "r", "r", "r"])
    heading(s, X0, 4.9, 5.85, "The three placements", size=15)
    bullets(s, X0, 5.3, 5.85, 1.65, ["full128 has 128 ranks per node, as submitted.", "spread64 has 64 ranks per node, 4 per L3, on all 16 L3s and all 16 memory channels.", "packed64 has the same 64 ranks and decomposition, 8 per L3, on 8 L3s and 8 channels."], size=14, space_after=4)
    heading(s, 6.78, 4.9, 5.85, "What it shows", size=15)
    bullets(s, 6.78, 5.3, 5.85, 1.65, ["Half the cores changed a step by 0.99 to 1.02 times.", "Half the channels made a step 2.11 to 2.20 times slower as the triad bandwidth fell 2.22 times.", "packed64 also halves the L3, so DRAM bandwidth and L3 capacity are not separated."], size=14, space_after=4)
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
    heading(s, X0, 1.35, 7.6, "Share of the call-stack samples by phase of a step")
    bar_chart(s, 0.5, 1.8, 7.9, 5.1, [name for name, _, _ in phases], [("computation", [round((n - m) / total * 100, 1) for _, n, m in phases]), ("MPI", [round(m / total * 100, 1) for _, _, m in phases])], colors=["A9BCDD", "C7A3C2"], stacked=True, number_format='0.0"%"', label_format='[<2]"";0.0"%"', vmin=0, vmax=35, font_size=14, label_size=13, gap=50, overlap=100, legend=XL_LEGEND_POSITION.BOTTOM, value_axis=False, gridlines=False, label_pos="ctr")
    bullets(s, 8.7, 1.6, 3.93, 5.3, ["2,396 samples of 48 of the 512 ranks on 4 nodes, with the first four changes.", "The k-ω SST correction, the Gauss–Seidel sweeps and the global sums of the coarsest CG led us to the ten later changes.", "Stack samples count MPI about 1.8 times higher than CrayPAT's timers."], size=15, space_after=14, anchor="m")
    return s


def s_changes():
    s = supp(27, "THE SOURCE CHANGES (1/2)", "s_changes")
    heading(s, X0, 1.35, XW, "The first four patches, in full in bonus/patches/ of the submission")
    rows = [["Change (patch)", "What it removes", "Why the result is the same"], ["No copies in the solvers (0001)", "smoothSolver built each residual in a new field and copied it; GAMG copied the source, then subtracted", "The same function computes the same residual in place; source − A·psi is the same subtraction per cell"], ["U components in one pass (0002)", "Gauss–Seidel read the shared matrix of U three times, once per component", "The components are independent; each sees the same operations in the same order"], ["No unused boundary updates (0003)", "Six callers built boundary values of a surface integral, exchanged them, and used only the cell values", "The cell values come from the same loop; only values nobody reads are skipped"], ["Fused face loops (0004)", "Interpolated face fields and product fields built before every summation", "The same face expressions, evaluated inside the summation loop in the same face order"]]
    table(s, X0, 1.8, [3.05, 4.5, 4.38], rows, size=14, bolds=[None] + [[True, False, False]] * 4, colors=[None] + [[BONUS, INK, INK]] * 4, row_heights=[0.5, 1.15, 1.15, 1.15, 1.15])
    return s


def s_changes2():
    s = supp(28, "THE SOURCE CHANGES (2/2)", "s_changes2")
    heading(s, X0, 1.35, XW, "The ten later patches (0006, 0008–0016); F3 means rounding can change, so Cd is checked")
    f3 = ("F3: ", {"b": True, "color": NAVY})
    rows = [["Change (patch)", "What it removes", "Why the result is the same"], ["Laplacian coefficients with the diagonal (0006)", "A temporary product field, its copy and a re-read of upper", "The same operations per face in the same order"], ["Pressure reference decided once (0008)", "Patch loops and a global sum per step that did nothing here", "The same cells get the same change whenever one is needed"], ["Viscous stress in one pass (0009)", "Three whole-field passes for nuEff · dev2(T(grad U))", "The same operations on the same operands in the same order"], ["Wall shear stress on the walls only (0010)", "A full-volume field of which only the wall values were read", "The same expression on the walls, as the forces object uses"], ["Gauss–Seidel without the source copy (0011)", "A copy of the source into a work array in every sweep", [[f3, ("the same terms, but the source is added last", {})]]], ["One global sum per CG iteration (0012)", "Two of three global sums per iteration on the coarsest level", [[f3, ("the same iterates in exact arithmetic", {})]]], ["Turbulence model in single cell loops (0013)", "67 of the 80 passes over the cells per k-ω SST update", "The same operations in the same association, no new FMAs"], ["No zero fill of overwritten coefficients (0014)", "Zero fills of face coefficients, a copy of the U matrix", "No arithmetic changes"], ["GAMG correction and restriction in place (0015)", "Two passes over the finest level per V-cycle", "The same operations and summation order"], ["Gauss–Seidel residual from the sweep (0016)", "A matrix pass and a halo exchange per component and iteration", [[f3, ("still formed and tested every iteration", {})]]]]
    table(s, X0, 1.8, [3.95, 4.15, 3.83], rows, size=12, row_heights=[0.42] + [0.47] * 10, bolds=[None] + [[True, False, False]] * 10, colors=[None] + [[BONUS, INK, INK]] * 10, margins=(0.08, 0.03, 0.08, 0.03))
    return s


def s_each():
    s = supp(29, "EFFECT OF EACH BONUS CHANGE", "s_each")
    heading(s, X0, 1.35, 6.4, "Each change against the one before, 4 nodes")
    picture(s, fig("ps_each"), X0 - 0.05, 1.8, w=6.4)
    heading(s, 7.25, 1.35, 5.38, "Change per step, 1 / 2 / 4 nodes")
    rows = [["Change", "1 node", "2 nodes", "4 nodes"], ["multiLevel vs scotch", "−0.45%", "−0.38%", "−1.54%"], ["0001 no copies", "−2.19%", "−2.94%", "−3.39%"], ["0002 U in one pass", "−6.39%", "−4.13%", "−2.29%"], ["0003 no unused values", "−1.40%", "−1.88%", "−1.31%"], ["0004 fused face loops", "−2.88%", "−2.29%", "−2.82%"], ["0006, 0008–0010", "", "", "−1.99%"], ["0011 GS without copy", "", "", "−1.04%"], ["0012 one sum per CG", "", "", "−0.30%"], ["0013–0015 *", "", "", "−2.48%"], ["0016 sweep residual *", "", "", "−3.80%"], ["0006–0016, alternated", "−12.16%", "−11.44%", "−9.34%"]]
    table(s, 7.25, 1.8, [2.26, 1.04, 1.04, 1.04], rows, row_h=0.34, size=11.5, bolds=[None] + [[True, False, False, True]] * 10 + [[True, True, True, True]], colors=[None] + [[INK, INK, INK, BONUS]] * 10 + [[BONUS] * 4], aligns=["l", "r", "r", "r"], margins=(0.08, 0.02, 0.08, 0.02))
    bullets(s, 7.25, 6.2, 5.38, 0.8, ["4 nodes have 3 to 4 jobs each and * ran a few days after its control. Most 1- and 2-node values are single jobs.", "coefficient.dat is bit-identical for every change but 0011 and 0012, which move Cd by under 0.001% (F3)."], size=11, space_after=2)
    return s


def s_counters():
    s = supp(30, "HARDWARE COUNTERS", "s_counters")
    heading(s, X0, 1.35, 6.3, "The first four changes on 1 node, computation only")
    rows = [["Counter", "Change"], ["Time per step", "−12.3%"], ["Cycles", "−10.8%"], ["Instructions", "−4.1%"], ["L1 data accesses", "−5.9%"], ["L2 accesses including prefetch", "−9.6%"], ["L1 refills from DRAM", "−17.2%"], ["Instructions per cycle", "0.360 → 0.388"]]
    table(s, X0, 1.8, [4.3, 2.0], rows, row_h=0.6, size=16, aligns=["l", "r"], colors=[None, None, None, None, None, None, [INK, BONUS], None], bolds=[None, None, None, None, None, None, [False, True], None])
    xr = 7.5
    heading(s, xr, 1.35, 5.13, "The gain grows where bytes cost more")
    rows2 = [["Test", "Gain"], ["First four on all 16 channels", "−7.9%"], ["First four on 8 of the 16 channels", "−11.4%"], ["Ten later changes on 4 nodes", "−9.3%"], ["Ten later changes on 2 nodes", "−11.4%"], ["Ten later changes on 1 node", "−12.2%"]]
    table(s, xr, 1.8, [3.75, 1.38], rows2, row_h=0.6, size=16, aligns=["l", "r"])
    bullets(s, xr, 5.65, 5.13, 1.3, ["These are demand refills of L1, not DRAM bytes, because users cannot read the memory controller counters."], size=14)
    return s


def s_cd_iterations():
    s = supp(31, "DRAG COEFFICIENT OVER THE ITERATIONS", "s_cd_iterations")
    picture(s, fig("ps_cd_iterations"), X0, 1.35, w=XW)
    bullets(s, X0, 5.85, XW, 1.1, ["The Bonus and the same decomposition without its source changes lie on top of each other and end 0.0004% apart.", "Different decompositions end up to 7% apart after 150 iterations, as the organisers' notes also show."], size=15, space_after=8)
    return s


def s_cd():
    s = supp(32, "DRAG COEFFICIENT CHECKS", "s_cd")
    heading(s, X0, 1.35, XW, "Cd at the last step, 1 / 2 / 4 nodes")
    rows = [["Steps", "OHC-1 values", ["Baseline", "(hierarchical)"], ["scotch", "defaults"], ["Basic", "(mapped scotch)"], ["Bonus", "(multiLevel)"]], ["40", "0.433 – 0.436", "0.43305", "0.43599", "0.43958", "0.43828"], ["80", "0.334 – 0.345", "0.33733", "0.32714", "0.33410", "0.32286"], ["150", "0.284 – 0.292", "0.27356", "0.28405", "0.29302", "0.29139"]]
    table(s, X0, 1.8, [1.0, 2.0, 2.45, 1.95, 2.35, 2.18], rows, row_h=0.7, size=16, row_heights=[0.8, 0.62, 0.62, 0.62], colors=[None] + [[INK, MUTED, BASE, INK, BASIC, BONUS]] * 3, bolds=[None] + [[True, False, False, False, True, True]] * 3, aligns=["c"] * 6)
    bullets(s, X0, 4.7, XW, 2.25, ["The Bonus against the same decomposition with unchanged source differs by +1.2 × 10⁻¹² (relative), −0.00002% and −0.00041% on 1 / 2 / 4 nodes, over 1,000 times inside F3's ±0.5%.", "The organisers' notes show hierarchical and scotch 0.7 / 3.0 / 3.5% apart at 40 / 80 / 150 steps, and the node mapping moves Cd by +0.8 / +2.1 / +3.2%, within that.", "With the organisers' decomposition our 150-step Cd is 0.284049 against their 0.283983, and the site module with our scripts gives their value exactly, so the difference is our build (AMD's math library).", "Every job of the same configuration and node count produced a byte-identical coefficient.dat."], size=14, space_after=6)
    return s


def s_efficiency():
    s = supp(33, "WHY THE EFFICIENCY EXCEEDS 1", "s_efficiency")
    heading(s, X0, 1.35, XW, "Per cell and step, Basic before the node mapping, AMD uProf")
    rows = [["Per cell and step (Basic, uProf)", "1 node", "2 nodes", "4 nodes", "4 nodes / 1 node"], ["Cycles", "24,235", "22,860", "20,418", "0.843"], ["L1 demand refills from DRAM", "24.6", "20.7", "17.1", "0.697"], ["L1 demand refills from L3 (same CCX)", "5.4", "6.3", "9.4", "1.75"]]
    table(s, X0, 1.8, [4.7, 1.6, 1.6, 1.6, 2.43], rows, row_h=0.62, size=16, bolds=[None] + [[True, False, False, False, True]] * 3, colors=[None] + [[INK, INK, INK, INK, NAVY]] * 3, aligns=["l", "r", "r", "r", "r"])
    bullets(s, X0, 4.55, XW, 2.4, ["AMD uProf data_access on one rank per NUMA domain, normalised by ranks, steps and cells per rank.", "The sparse-matrix kernels gather cell arrays in face order, and their DRAM refills fall to 0.30 (Gauss–Seidel), 0.40 (residual) and 0.42 (A·x), while a loop that streams cell fields stays at 0.95.", "Cell arrays per rank are 4 MB on 1 node, 2 MB on 2 and 1 MB on 4, against 4 MB of L3 per core, while the face arrays of about 16 MB never fit.", "A rank's cycles follow its DRAM refills (r = +0.69), not its instructions (r = −0.09) or its cells (r = +0.24)."], size=14.5, space_after=8)
    return s


def s_rejected():
    s = supp(34, "NOT ADOPTED: THE FULL LIST", "s_rejected")
    rows = [["Idea (tier)", "Result, 4 nodes", "Why it did not help"], ["-march=znver3, AOCC 5.0, -O2, LTO (Basic)", "within ±0.1%", "The loops wait on memory, not on instructions"], ["GCC profile-guided optimisation (Basic)", "+0.13% (+0.08% on 1 node)", "The same; Cd bit-identical"], ["Default OFI with the organisers' workarounds (Basic)", "+0.77% (3 v 3), +0.50% (1 v 1)", "Not faster than UCX; same Cd, no SIGBUS"], ["UCX over RC instead of UD between nodes", "−0.01% Basic, −0.16% early Bonus", "IMB bandwidth +55%; steps do not wait on transfers"], ["OpenFOAM comm switches (topoControl, nbx, pbufs)", "no gain; commsType scheduled crashed", "MPI time is waiting for the slowest rank"], ["Rank reordering (MPICH_RANK_REORDER_METHOD=3)", "+0.1%, 92% fewer faces between nodes", "Fewer bytes between nodes do not shorten the wait"], ["glibc malloc thresholds (Basic)", "−0.4% (3 jobs)", "Too small to separate with 3 jobs; not re-tested"], ["SMT, 2 ranks per core (Basic)", "≈ 5.7× slower", "Stalls of minutes; cause not isolated"], ["GAMG coarsest level on fewer ranks (Bonus)", "−0.25% to +4.95%", "81% of the global sums, but ≈ 0.6% of the time"], ["Weighted cells (×2, ×12), METIS two constraints (Bonus)", "+1.5% to +6.1%", "Uneven cells, or 18% more processor faces"], ["Gauss–Seidel overlapped with its halo exchange (Bonus)", "+8.32% (3 v 3), Cd −1.20%", "Fails F3: Cd moves far beyond rounding"], ["bound() averaging only the bounded cells (Bonus)", "not run", "An extra global sum per call costs more than it saves"], ["Overlapping halo exchange with computation", "under 1% available", "Led to skipping unused exchanges instead (0003)"], ["File I/O in the timed steps", "≈ 0.01% of a step", "Not a factor"]]
    table(s, X0, 1.3, [5.0, 3.15, 3.78], rows, size=11, row_heights=[0.38] + [0.36] * 14, bolds=[None] + [[True, False, False]] * 14, margins=(0.08, 0.02, 0.08, 0.02))
    return s


def fill_index(s, groups):
    """Q&A index: one clickable line per supporting slide in two columns; call after the slide order is final."""
    set_title(s, "Q&A INDEX")
    for column, pair in enumerate((groups[:2], groups[2:])):
        x, y = (X0, 6.78)[column], 1.4
        for name, items in pair:
            add_text(s, x, y, 5.85, 0.4, [name], size=17, color=NAVY, bold=True)
            y += 0.48
            for title, target in items:
                line = add_text(s, x + 0.1, y, 5.75, 0.38, [[(f"{prs.slides.index(target) + 1}", {"b": True, "color": NAVY}), ("   " + title, {})]], size=15, anchor="m")
                line.click_action.target_slide = target
                y += 0.4
            y += 0.3
    set_notes(s, NOTES["index"])


def slide_reproducibility():
    """The shared reproducibility slide (the team's), with our patch list brought up to the final Bonus."""
    s = S[45]
    replace_run_text(s, "Compact_OFBuildBody", "Apply 0001 / 0002 / 0003 / 0004 in order", "Apply 0001–0004, 0006, 0008–0016 in order")
    return s


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
main = [m_summary(), m_criteria(), m_profile_baseline(), m_mpi(), m_pinning(), m_decomposition(), m_basic_results(), m_profile_basic(), m_memory_limit(), m_bonus_opt(), m_bonus_results(), m_scaling(), m_not_helped(), m_final()]
divider = S[21]
index_slide = reuse(22)
groups = [("Setup and measurement", [("ASPIRE-2A and why we chose it", s_aspire()), ("Build, MPI and run settings", s_settings()), ("Run-to-run variation over 92 jobs", s_noise()), ("The organisers' reference", s_reference()), ("Reproducing our results", s_repro())]), ("Basic", [("Is the network the bottleneck?", s_network()), ("hierarchical and scotch on 1, 2 and 4 nodes", s_scotch()), ("The placement experiment in full", s_cores())]), ("Bonus", [("Where a Bonus step goes: call stacks", s_callstack()), ("The source changes (1/2): the first four", s_changes()), ("The source changes (2/2): ten more", s_changes2()), ("Effect of each Bonus change", s_each()), ("Hardware counters of the first four changes", s_counters())]), ("Results", [("Drag coefficient over the iterations", s_cd_iterations()), ("Drag coefficient checks", s_cd()), ("Why the efficiency exceeds 1", s_efficiency()), ("Not adopted: the full list", s_rejected())])]
order = [cover] + main + [divider, index_slide] + [sl for _, items in groups for _, sl in items] + [slide_reproducibility()] + S[AI:]

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
