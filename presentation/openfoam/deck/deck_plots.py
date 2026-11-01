# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Per-job plots for the deck, each drawn at the size it takes on its slide.

usage: deck_plots.py <path/to/figures.py> <output_dir>

Every point is one job's official time per step and a bar is the mean of the jobs, so a plot shows the change, the scaling
and how many jobs stand behind each number. Time runs up the vertical axis, every mean is written next to its jobs with its
unit and the standard deviation of the jobs, and all text is bold, as on the slides (the user, 11/01). The data and their
readers come from figures.py, the colours from palette.py. A plot is drawn at its size on the slide, so 12 pt here is 12 pt
there.
"""

import importlib.util
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator

import palette

spec = importlib.util.spec_from_file_location("team_figures", sys.argv[1])
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
OUT = Path(sys.argv[2])
BASE, BASIC, BONUS, BONUS_LIGHT, NAVY, INK, MUTED, FAINT, GRID, COMPUTATION, MPI = ("#" + getattr(palette, name) for name in ("BASE", "BASIC", "BONUS", "BONUS_LIGHT", "NAVY", "INK", "MUTED", "FAINT", "GRID", "COMPUTATION", "MPI"))
plt.rcParams.update({"font.size": 13, "font.weight": "bold", "axes.titlesize": 14, "axes.titleweight": "bold", "axes.labelsize": 13, "axes.labelweight": "bold", "xtick.labelsize": 12.5, "ytick.labelsize": 12.5, "legend.fontsize": 12.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK})
NODES = (1, 2, 4)
STEPS = {1: 40, 2: 80, 4: 150}


def runs(name, *keys, where=None):
    data = defaultdict(list)
    for row in F.read(name):
        if where is None or where(row):
            key = tuple(int(row[k]) if k == "nodes" else row[k] for k in keys)
            data[key[0] if len(key) == 1 else key].append(float(row["s_per_step"]))
    return data


BASELINE = F.baseline_runs()
FINAL = runs("final_runs.csv", "configuration", "nodes")
ORGANISERS = runs("organiser_reference_aspire2a.csv", "method", "nodes", where=lambda row: row["setting"] == "defaults")
# the official runs: the organisers' reference results (full chain, site module, case defaults), one job per method and node
# count; on 4 nodes they are the Common Baselines, 3.415 s (hierarchical) and 3.576 s (scotch)
OFFICIAL = runs("organiser_reference_aspire2a.csv", "method", "nodes", where=lambda row: row["setting"] == "defaults" and row["run"] == "full chain")
CHANGES = F.changes_by_role()


def save(figure, name):
    figure.savefig(OUT / f"{name}.png", dpi=300, facecolor="white")
    plt.close(figure)


def percent(candidate, control, digits=1):
    return f"{F.change(candidate, control):+.{digits}f}%".replace("-", "−")


def four(value):
    """A time in s/step with four significant figures: 14.57, 7.427, 3.650."""
    return f"{value:.{max(0, 3 - math.floor(math.log10(abs(value))))}f}"


def sd_text(values):
    """The jobs' standard deviation in % of their mean ('SD 0.07%'), or '1 job'."""
    if len(values) < 2:
        return "1 job"
    sd = statistics.stdev(values) / statistics.fmean(values) * 100
    return f"SD {sd:.2f}%" if sd < 1 else f"SD {sd:.1f}%"


def stats(values):
    """Two lines for a group of jobs: the mean in four significant figures with its unit, then the SD."""
    return f"{four(statistics.fmean(values))} s\n{sd_text(values)}"


def jobs(axis, x, values, color, width=0.3, hollow=False):
    """One dot per job around x, and the mean of the jobs as a bar; returns the mean."""
    spread = F.spread(values, x, width)
    if hollow:
        axis.scatter(spread, values, s=50, facecolor="white", edgecolor=color, linewidth=1.6, zorder=3)
    else:
        axis.scatter(spread, values, s=50, color=color, edgecolor="black", linewidth=0.5, zorder=3)
    mean = statistics.fmean(values)
    axis.hlines(mean, x - width / 2 - 0.1, x + width / 2 + 0.1, color=color, linewidth=2.5, zorder=2)
    return mean


def label_above(axis, x, values, color=INK, size=12, text=None, top=None):
    """The mean and SD of the jobs at x (or text), above the highest job, or above top when a mark drawn there is higher."""
    y = max(values) if top is None else max(max(values), top)
    axis.annotate(text or stats(values), (x, y), textcoords="offset points", xytext=(0, 9), ha="center", va="bottom", fontsize=size, color=color, linespacing=1.05)


def jobs_label(n):
    return f"{n} job{'s' if n > 1 else ''}"


def colour_ticks(labels, colors):
    for label, color in zip(labels, colors):
        label.set_color(color)


def finish(axis, ylabel="s/step on 4 nodes, each job"):
    axis.set_ylabel(ylabel)
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)


def rule():
    """Main slide 2: the second test on a change that was kept and on one that was not, 4 nodes, each job. The panels do
    not name the changes (the node mapping and AOCC); the slide is about the test."""
    compilers = runs("compiler_options.csv", "option")
    examples = [("Kept", CHANGES[("mapping", 4, "control")], CHANGES[("mapping", 4, "candidate")], NAVY), ("Not kept", compilers["control (GCC -O3, scotch)"], compilers["AOCC 5.0 / AOCL 5.1"], INK)]
    figure, axes = plt.subplots(1, 2, figsize=(5.58, 4.95), layout="constrained")
    for axis, (title, control, candidate, color) in zip(axes, examples):
        for x, values, dot in ((0, control, FAINT), (1, candidate, color)):
            jobs(axis, x, values, dot, width=0.36)
            label_above(axis, x, values, size=11.5)
        if max(candidate) < min(control):
            axis.axhspan(max(candidate), min(control), color=GRID, zorder=0)
        axis.set_title(title, color=color)
        axis.set_xticks([0, 1], [f"control\n{jobs_label(len(control))}", f"candidate\n{jobs_label(len(candidate))}"], fontsize=10.5)
        colour_ticks(axis.get_xticklabels(), [INK, color])
        axis.set_xlim(-0.7, 1.7)
        low, high = min(control + candidate), max(control + candidate)
        axis.set_ylim(low - (high - low) * 0.3, high + (high - low) * 1.0)
        axis.yaxis.set_major_locator(MaxNLocator(5))
        finish(axis, "s/step on 4 nodes, each job" if axis is axes[0] else "")
    save(figure, "p07_rule")


PLACEMENTS = [("CPU and\nmemory", "numactl --membind + taskset keeper (adopted for Basic)", BASIC), ("CPU\nonly", "taskset keeper only (re-pins 12-16 s after start)", FAINT), ("Neither", "PALS --cpu-bind and --mem-bind only", FAINT), ("Memory\nonly", "numactl --membind only", FAINT)]


def pinning():
    """Main slide 5: which half of the placement fix matters (4 nodes, scotch decomposition)."""
    data = runs("pinning.csv", "configuration")
    figure, axis = plt.subplots(figsize=(5.7, 4.95), layout="constrained")
    for x, (_, key, color) in enumerate(PLACEMENTS):
        jobs(axis, x, data[key], color, width=0.3)
        label_above(axis, x, data[key], color=BASIC if color == BASIC else INK)
    axis.set_xticks(range(len(PLACEMENTS)), [label for label, _, _ in PLACEMENTS])
    colour_ticks(axis.get_xticklabels(), [BASIC, INK, INK, INK])
    axis.set_xlim(-0.6, len(PLACEMENTS) - 0.4)
    axis.set_ylim(2.6, 4.95)
    finish(axis)
    save(figure, "p10_pinning")


def scotch():
    """Supporting slide: scotch against the case-default hierarchical decomposition at 1, 2 and 4 nodes, same placement."""
    data = runs("decomposition_basic.csv", "nodes", "method")
    figure, axes = plt.subplots(1, 3, figsize=(11.9, 4.2), layout="constrained")
    for axis, n in zip(axes, NODES):
        hierarchical, split = data[(n, "hierarchical")], data[(n, "scotch")]
        for x, values, color in ((0, hierarchical, FAINT), (1, split, BASIC)):
            jobs(axis, x, values, color)
            label_above(axis, x, values, color=BASIC if color == BASIC else INK, size=11.5)
        axis.set_xticks([0, 1], ["hierarchical", "scotch"])
        colour_ticks(axis.get_xticklabels(), [INK, BASIC])
        axis.set_xlim(-0.6, 1.6)
        axis.set_title(f"{n} node{'s' if n > 1 else ''}, {percent(split, hierarchical)}")
        both = hierarchical + split
        span = max(both) - min(both)
        axis.set_ylim(min(both) - span * 0.15, max(both) + span * 0.75)
        axis.yaxis.set_major_locator(MaxNLocator(4))
        finish(axis, "s/step, each job" if n == 1 else "")
    save(figure, "p11_scotch")


def before_after(name, groups, size, ylim, yticks):
    """Two configurations on 4 nodes, each job, with the mean, SD and job count of each and the change between them."""
    figure, axis = plt.subplots(figsize=size, layout="constrained")
    for x, (_, values, color) in enumerate(groups):
        jobs(axis, x, values, color, width=0.34)
        label_above(axis, x, values, color=color, size=13)
    (_, before, _), (_, after, _) = groups
    axis.text(0.5, (statistics.fmean(before) + statistics.fmean(after)) / 2, percent(after, before), ha="center", va="center", fontsize=17, color=NAVY)
    axis.set_xticks([0, 1], [f"{label}\n{jobs_label(len(values))}" for label, values, _ in groups])
    colour_ticks(axis.get_xticklabels(), [color for _, _, color in groups])
    axis.set_xlim(-0.6, 1.6)
    axis.set_ylim(*ylim)
    axis.set_yticks(yticks)
    finish(axis)
    save(figure, name)


def basic_4node():
    """Main slide 7: our Baseline and Basic on 4 nodes, each job."""
    before_after("p12_basic", [("Baseline", BASELINE[4], BASE), ("Basic", FINAL[("Basic", 4)], BASIC)], (5.9, 5.05), (2.75, 4.2), [2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0])


def bonus_4node():
    """Main slide 11: Basic and the Bonus on 4 nodes, each job (the Bonus jobs of the final measurement, 10/26)."""
    before_after("p15_bonus", [("Basic", FINAL[("Basic", 4)], BASIC), ("Bonus", FINAL[("Bonus", 4)], BONUS)], (4.3, 3.65), (2.25, 3.1), [2.3, 2.5, 2.7, 2.9])


# The counters of the first four changes on 1 node (#55), in the order of the slide; label, metric in counters_1node.csv
COUNTERS = [("Time\nper step", None), ("Cycles", "cycles"), ("Instruc-\ntions", "instructions"), ("L1 data\naccesses", "L1 data accesses"), ("L2\naccesses\nincl. pre-\nfetch", "L2 accesses incl. prefetch"), ("L1\nrefills\nfrom\nDRAM", "L1 refills from DRAM")]


def counters():
    """Main slide 11: each counter with the first four changes against the same build without them, 1 node; the bar is the
    change of the means, the dots the four pairs of jobs, and the SD is that of the four pairs."""
    values = defaultdict(lambda: defaultdict(list))
    seconds = defaultdict(dict)
    for row in F.read("counters_1node.csv"):
        values[row["metric"]][row["condition"]].append(float(row["per_rank_mean"]))
        seconds[row["condition"]][row["actions_run"]] = float(row["s_per_step_under_uprof"])
    figure, axis = plt.subplots(figsize=(7.3, 3.65), layout="constrained")
    for x, (label, metric) in enumerate(COUNTERS):
        if metric is None:
            before, after = list(seconds["unpatched"].values()), list(seconds["patched"].values())
        else:
            before, after = values[metric]["unpatched"], values[metric]["patched"]
        pairs = [(b / a - 1) * 100 for a in before for b in after]
        mean = F.change(after, before)
        color = BONUS if metric == "L1 refills from DRAM" else (FAINT if metric == "instructions" else BONUS_LIGHT)
        axis.bar(x, mean, width=0.62, color=color, zorder=2)
        axis.scatter([x] * len(pairs), pairs, s=16, color="black", zorder=3)
        sd = statistics.stdev(pairs)
        axis.annotate(f"{mean:+.1f}%\nSD {sd:.2f}%".replace("-", "−") if sd < 1 else f"{mean:+.1f}%\nSD {sd:.1f}%".replace("-", "−"), (x, min(pairs + [mean])), textcoords="offset points", xytext=(0, -5), ha="center", va="top", fontsize=11, color=BONUS if metric == "L1 refills from DRAM" else INK, linespacing=1.05)
    axis.axhline(0, color=INK, linewidth=1)
    axis.set_xticks(range(len(COUNTERS)), [label for label, _ in COUNTERS], fontsize=10.5)
    axis.set_ylim(-27, 1.5)
    axis.set_yticks([0, -5, -10, -15, -20, -25], ["0%", "−5%", "−10%", "−15%", "−20%", "−25%"])
    finish(axis, "Change against none")
    save(figure, "p15_counters")


def scaling():
    """Main slide 12: every job on 1, 2 and 4 nodes on one linear axis from 0, grouped by node count (the user, 11/01): the
    official runs, then our Baseline, Basic and Bonus. The official runs are one hierarchical (hollow) and one scotch (grey)
    job, drawn as on the supporting slide of the organisers' runs. The dashed marks are ideal scaling from each tier's
    1-node mean. Our tiers are labelled above their jobs or mark, whichever is higher, and the official runs under theirs,
    so that no mark crosses a label; the plot spans the slide so that labels side by side have room. The parallel
    efficiencies stand under the plot."""
    tiers = [("Baseline", BASELINE, BASE), ("Basic", {n: FINAL[("Basic", n)] for n in NODES}, BASIC), ("Bonus", {n: FINAL[("Bonus", n)] for n in NODES}, BONUS)]
    official = [("hierarchical", -0.13, True), ("scotch", 0.13, False)]  # method, offset from the column, hollow
    pitch = 4.7  # from one node count to the next: four columns 1 apart and a gap
    figure, axis = plt.subplots(figsize=(12.03, 3.85), layout="constrained")
    for g, n in enumerate(NODES):
        x0 = pitch * g
        for method, offset, hollow in official:
            if hollow:
                axis.scatter([x0 + offset], OFFICIAL[(method, n)], s=50, facecolor="white", edgecolor=MUTED, linewidth=1.6, zorder=3)
            else:
                axis.scatter([x0 + offset], OFFICIAL[(method, n)], s=50, color=FAINT, edgecolor="black", linewidth=0.5, zorder=3)
        lines = sorted(((OFFICIAL[(method, n)][0], method) for method, _, _ in official), reverse=True)  # as the jobs stand
        axis.annotate("\n".join(f"{method} {four(value)} s" for value, method in lines), (x0, lines[-1][0]), textcoords="offset points", xytext=(0, -9), ha="center", va="top", fontsize=10, color=INK, linespacing=1.05)
        for k, (_, data, color) in enumerate(tiers, 1):
            x = x0 + k
            ideal = statistics.fmean(data[1]) / n if n > 1 else None
            if ideal:
                axis.hlines(ideal, x - 0.42, x + 0.42, color=color, linestyle="--", linewidth=1.3, zorder=1)
            jobs(axis, x, data[n], color, width=0.48)
            label_above(axis, x, data[n], color=color, size=10, top=ideal)
    axis.set_xticks([pitch * g + k for g in range(len(NODES)) for k in range(4)], [name for _ in NODES for name in ("Official", "Baseline", "Basic", "Bonus")], minor=True)
    axis.set_xticks([pitch * g + 1.5 for g in range(len(NODES))], [f"{n} node{'s' if n > 1 else ''}" for n in NODES])
    axis.tick_params(axis="x", which="minor", labelsize=10.5)
    axis.tick_params(axis="x", which="major", labelsize=13, length=0, pad=19)
    colour_ticks(axis.get_xticklabels(minor=True), [color for _ in NODES for color in (INK, BASE, BASIC, BONUS)])
    axis.set_xlim(-1.15, pitch * (len(NODES) - 1) + 3.6)
    axis.set_ylim(0, 18.5)
    axis.set_yticks([0, 4, 8, 12, 16])
    finish(axis, "s/step, each job")
    axis.legend(handles=[Line2D([], [], linestyle="--", color=MUTED, linewidth=1.3, label="ideal from 1 node"), Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor="white", markeredgecolor=MUTED, markeredgewidth=1.6, label="official hierarchical, 1 job"), Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=FAINT, markeredgecolor="black", markeredgewidth=0.5, label="official scotch, 1 job")], frameon=False, loc="upper right", fontsize=11)
    save(figure, "p17_scaling")


def reference():
    """Supporting slide: our Basic and Bonus against the organisers' own runs on the same machine."""
    groups = [("theirs\nhierarchical", lambda n: ORGANISERS[("hierarchical", n)], MUTED, True), ("theirs\nscotch", lambda n: ORGANISERS[("scotch", n)], FAINT, False), ("our\nBasic", lambda n: FINAL[("Basic", n)], BASIC, False), ("our\nBonus", lambda n: FINAL[("Bonus", n)], BONUS, False)]
    figure, axes = plt.subplots(1, 3, figsize=(11.9, 3.8), layout="constrained")
    for axis, n in zip(axes, NODES):
        everything = []
        for x, (_, values_of, color, hollow) in enumerate(groups):
            values = values_of(n)
            everything += values
            jobs(axis, x, values, color, hollow=hollow)
            label_above(axis, x, values, color=color if color not in (MUTED, FAINT) else INK, size=9)
            if x >= 2:
                axis.annotate(percent(values, ORGANISERS[("scotch", n)]), (x, min(values)), textcoords="offset points", xytext=(0, -9), ha="center", va="top", fontsize=11, color=NAVY)
        axis.set_xticks(range(len(groups)), [label for label, _, _, _ in groups], fontsize=9.5)
        colour_ticks(axis.get_xticklabels(), [INK, INK, BASIC, BONUS])
        axis.set_xlim(-0.6, 3.6)
        axis.set_title(f"{n} node{'s' if n > 1 else ''}")
        span = max(everything) - min(everything)
        axis.set_ylim(min(everything) - span * 0.25, max(everything) + span * 0.35)
        axis.yaxis.set_major_locator(MaxNLocator(4))
        finish(axis, "s/step, each job" if n == 1 else "")
    save(figure, "ps_reference")


# Every Bonus change on 4 nodes in the order it was added, by patch number; the table beside the plot names them.
# * marks the two candidates that ran a few days after their control instead of alternated with it.
EACH = [("multiLevel", "multi-\nLevel"), ("0001", "0001"), ("0002", "0002"), ("0003", "0003"), ("0004", "0004"), ("0006-0010", "0006,\n08–10"), ("0011", "0011"), ("0012", "0012"), ("0013-0015", "0013–\n15 *"), ("0016", "0016 *")]


def each_change():
    """Supporting slide: each Bonus change against the configuration just before it, 4 nodes, each job against its control's
    mean, with the change and the SD of the candidate jobs."""
    figure, axis = plt.subplots(figsize=(6.4, 5.1), layout="constrained")
    axis.axhline(0, color=MUTED, linewidth=0.9, zorder=1)
    for index, (key, _) in enumerate(EACH):
        control, candidate = CHANGES[(key, 4, "control")], CHANGES[(key, 4, "candidate")]
        mean = statistics.fmean(control)
        jobs(axis, index - 0.17, [(value / mean - 1) * 100 for value in control], FAINT, width=0.13)
        after = jobs(axis, index + 0.17, [(value / mean - 1) * 100 for value in candidate], BONUS, width=0.13)
        axis.text(index + 0.17, after - 0.25, f"{percent(candidate, control)}\n{sd_text(candidate)}", ha="center", va="top", fontsize=8, color=NAVY, linespacing=1.0)
        axis.text(index, 0.42, f"{len(control)} v {len(candidate)}", ha="center", va="bottom", fontsize=9, color=INK)
    axis.set_xticks(range(len(EACH)), [label for _, label in EACH], fontsize=9.5)
    axis.set_xlim(-0.6, len(EACH) - 0.3)
    axis.set_ylim(-4.9, 0.95)
    finish(axis, "Each job against the mean of its control (%)")
    axis.legend(handles=[Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=FAINT, markeredgecolor="black", markeredgewidth=0.45, label="before (control)"), Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=BONUS, markeredgecolor="black", markeredgewidth=0.45, label="after (candidate)")], frameon=False, loc="lower left", ncols=2)
    save(figure, "ps_each")


# The 4-node runs in data/cd_iterations_4node.csv, in drawing order: name, colour, line style, line width
CD_RUNS = [("organisers hierarchical", MUTED, ":", 1.6), ("organisers scotch", FAINT, "-", 1.6), ("Basic", BASIC, "-", 2.2), ("Bonus without its source changes", BONUS_LIGHT, "-", 4.5), ("Bonus", BONUS, "--", 1.8)]


def cd_iterations():
    """Supporting slide: Cd at every iteration of the 4-node runs (ISC26 Task 4), the whole run and its last 50 iterations.

    The Bonus and the same decomposition without its source changes lie on top of each other; different decompositions
    end a few per cent apart. Every job of a configuration gives the same Cd, so there is no spread to draw.
    """
    cd = defaultdict(list)
    for row in F.read("cd_iterations_4node.csv"):
        cd[row["configuration"]].append((int(row["iteration"]), float(row["cd"])))
    figure, (whole, end) = plt.subplots(1, 2, figsize=(11.9, 4.0), layout="constrained", width_ratios=(1.15, 1))
    for name, color, style, width in CD_RUNS:
        iterations, values = zip(*cd[name])
        label = name.replace("organisers", "organisers'")
        whole.plot(iterations, values, style, color=color, linewidth=width, label=label)
        tail = [(i, v) for i, v in cd[name] if i >= 100]
        end.plot(*zip(*tail), style, color=color, linewidth=width)
        end.annotate(f"{tail[-1][1]:.4f}", tail[-1], textcoords="offset points", xytext=(6, 0), va="center", fontsize=11.5, color=color if color not in (FAINT, BONUS_LIGHT, MUTED) else INK)
    whole.set_title("All 150 iterations", loc="left")
    end.set_title("Iterations 100 to 150", loc="left")
    for axis in (whole, end):
        axis.set_xlabel("Iteration (4 nodes)")
        axis.grid(color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
    whole.set_ylabel("Cd")
    whole.set_xlim(0, 152)
    whole.set_ylim(0, 1.25)
    end.set_xlim(100, 163)
    whole.legend(frameon=False, loc="upper right")
    save(figure, "ps_cd_iterations")


def flame(levels=14):
    """Supporting slide: the 2,396 CrayPAT stack samples in the time loop of the Bonus with the first four changes (#53, 48
    of 512 ranks on 4 nodes) as a flame graph, from data/callstack_folded_fa4f5b0.txt.

    The bottom row is the time loop, the next the phase of the step as in the phase bars before it, and each box above is a
    function called by the box under it, as wide as its share of the samples, the widest on the left. A tower in MPI ends at
    the MPI call that OpenFOAM made, which holds the library's own functions. Rows above the 14th hold 2 samples, too narrow
    to see, and are not drawn. A box shows its name and share where they fit, else its name, else the function without its
    class, else the start of that.
    """
    inclusive = defaultdict(int)
    with open(F.DATA / "callstack_folded_fa4f5b0.txt", encoding="utf-8") as f:
        for line in f:
            stack, samples = line.rstrip("\n").rsplit(" ", 1)
            frames = tuple(stack.split(";"))
            for k in range(len(frames) + 1):
                inclusive[frames[:k]] += int(samples)
    total = inclusive[()]
    children = defaultdict(list)
    for path in inclusive:
        if path:
            children[path[:-1]].append(path)
    figure = plt.figure(figsize=(11.93, 4.1))
    axis = figure.add_axes((0, 0, 1, 1))
    axis.set_xlim(0, total)
    axis.set_ylim(0, levels + 1)
    axis.axis("off")
    renderer = figure.canvas.get_renderer()

    def put(x, n, level, text):
        """Write text in the box if it fits; returns its width in pixels and whether it stayed."""
        shown = axis.text(x + n / 2, level + 0.5, text, ha="center", va="center", fontsize=9)
        width = shown.get_window_extent(renderer).width
        room = axis.transData.transform((n, 0))[0] - axis.transData.transform((0, 0))[0] - 8
        if width > room:
            shown.remove()
        return width, room, width <= room

    def label(x, n, level, name, share):
        if share and put(x, n, level, f"{name}  {share}")[2]:
            return
        short = name.rsplit("::", 1)[-1]  # the function without its class or namespace
        for text in dict.fromkeys((name, short)):
            width, room, fits = put(x, n, level, text)
            if fits:
                return
        k = int(len(short) * room / width)
        while k > 3 and not put(x, n, level, short[:k] + "…")[2]:
            k -= 1

    def draw(path, x, level):
        n = inclusive[path]
        name = path[-1] if path else f"time loop of simpleFoam, {total:,} samples on 48 ranks"
        axis.add_patch(Rectangle((x, level), n, 1, facecolor=MPI if name.startswith(("MPI_", "PMPI_")) else COMPUTATION, edgecolor="white", linewidth=0.8))
        if n / total > 0.004:
            label(x, n, level, name, f"{100 * n / total:.1f}%" if path else "")
        if level < levels:
            for child in sorted(children[path], key=lambda p: (-inclusive[p], p[-1])):
                draw(child, x, level + 1)
                x += inclusive[child]

    draw((), 0, 0)
    save(figure, "ps_flame")


rule()
pinning()
scotch()
basic_4node()
bonus_4node()
counters()
scaling()
reference()
each_change()
cd_iterations()
flame()
