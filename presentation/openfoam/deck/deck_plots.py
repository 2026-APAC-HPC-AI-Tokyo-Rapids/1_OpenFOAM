# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Per-job plots for the deck, each drawn at the size it takes on its slide.

usage: deck_plots.py <path/to/figures.py> <output_dir>

Every point is one job's official time per step and a bar is the mean of the jobs, so a plot shows the change, the scaling
and how many jobs stand behind each number. Each mean is written with four significant figures and the standard deviation
of its jobs (slides.md, 数値の決まり). The data and their readers come from figures.py, the colours from palette.py. A plot is
drawn at its size on the slide, so 12 pt here is 12 pt there.
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
from matplotlib.ticker import MaxNLocator

import palette

spec = importlib.util.spec_from_file_location("team_figures", sys.argv[1])
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
OUT = Path(sys.argv[2])
BASE, BASIC, BONUS, BONUS_LIGHT, BAD, NAVY, INK, MUTED, FAINT, GRID = ("#" + getattr(palette, name) for name in ("BASE", "BASIC", "BONUS", "BONUS_LIGHT", "BAD", "NAVY", "INK", "MUTED", "FAINT", "GRID"))
plt.rcParams.update({"font.size": 13, "axes.titlesize": 14, "axes.labelsize": 13, "xtick.labelsize": 12.5, "ytick.labelsize": 12.5, "legend.fontsize": 12.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK})
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
CHANGES = F.changes_by_role()


def save(figure, name):
    figure.savefig(OUT / f"{name}.png", dpi=300, facecolor="white")
    plt.close(figure)


def percent(candidate, control, digits=1):
    return f"{F.change(candidate, control):+.{digits}f}%".replace("-", "−")


def four(value):
    """A time in s/step with four significant figures: 14.57, 7.427, 3.650."""
    return f"{value:.{max(0, 3 - math.floor(math.log10(abs(value))))}f}"


def stats(values):
    """The mean in four significant figures and the jobs' standard deviation in %: '2.898, SD 0.07%'; one job has none."""
    mean = statistics.fmean(values)
    if len(values) < 2:
        return f"{four(mean)}, 1 job"
    sd = statistics.stdev(values) / mean * 100
    return f"{four(mean)}, SD {sd:.2f}%" if sd < 1 else f"{four(mean)}, SD {sd:.1f}%"


def jobs(axis, x, values, color, width=0.3, hollow=False, horizontal=False):
    """One dot per job around x, and the mean of the jobs as a bar; returns the mean."""
    spread = F.spread(values, x, width)
    xs, ys = (values, spread) if horizontal else (spread, values)
    if hollow:
        axis.scatter(xs, ys, s=50, facecolor="white", edgecolor=color, linewidth=1.6, zorder=3)
    else:
        axis.scatter(xs, ys, s=50, color=color, edgecolor="black", linewidth=0.5, zorder=3)
    mean = statistics.fmean(values)
    lines = axis.vlines if horizontal else axis.hlines
    lines(mean, x - width / 2 - 0.1, x + width / 2 + 0.1, color=color, linewidth=2.5, zorder=2)
    return mean


def jobs_label(n):
    return f"{n} job{'s' if n > 1 else ''}"


def colour_ticks(labels, colors):
    for label, color in zip(labels, colors):
        label.set_color(color)


def rule():
    """Main slide 2: the second test on a change that passed and on one that did not, 4 nodes, each job. The panels do not
    name the changes (the node mapping and AOCC); the slide is about the test."""
    compilers = runs("compiler_options.csv", "option")
    examples = [("Kept", CHANGES[("mapping", 4, "control")], CHANGES[("mapping", 4, "candidate")], NAVY), ("Not kept", compilers["control (GCC -O3, scotch)"], compilers["AOCC 5.0 / AOCL 5.1"], BAD)]
    figure, axes = plt.subplots(2, 1, figsize=(5.55, 5.3), layout="constrained")
    for axis, (title, control, candidate, color) in zip(axes, examples):
        for row, values, dot in ((0, control, FAINT), (1, candidate, color)):
            jobs(axis, row, values, dot, width=0.36, horizontal=True)
            axis.annotate(stats(values), (max(values), row), textcoords="offset points", xytext=(10, 0), va="center", fontsize=12.5, color=INK)
        if max(candidate) < min(control):
            axis.axvspan(max(candidate), min(control), color=GRID, zorder=0)
        axis.set_title(title, loc="left", fontweight="bold", color=color)
        axis.set_yticks([0, 1], [f"control\n{jobs_label(len(control))}", f"candidate\n{jobs_label(len(candidate))}"])
        colour_ticks(axis.get_yticklabels(), [INK, color])
        axis.set_ylim(1.6, -0.6)
        low, high = min(control + candidate), max(control + candidate)
        axis.set_xlim(low - (high - low) * 0.12, high + (high - low) * 1.25)
        axis.xaxis.set_major_locator(MaxNLocator(4))
        axis.grid(axis="x", color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
    axes[-1].set_xlabel("s/step on 4 nodes, each job")
    save(figure, "p07_rule")


PLACEMENTS = [("CPU and\nmemory", "numactl --membind + taskset keeper (adopted for Basic)", BASIC), ("CPU only", "taskset keeper only (re-pins 12-16 s after start)", FAINT), ("Neither", "PALS --cpu-bind and --mem-bind only", FAINT), ("Memory\nonly", "numactl --membind only", BAD)]


def pinning():
    """Main slide 5: which half of the placement fix matters (4 nodes, scotch decomposition)."""
    data = runs("pinning.csv", "configuration")
    figure, axis = plt.subplots(figsize=(5.7, 5.2), layout="constrained")
    for row, (_, key, color) in enumerate(PLACEMENTS):
        jobs(axis, row, data[key], color, width=0.28, horizontal=True)
        axis.annotate(stats(data[key]), (max(data[key]), row), textcoords="offset points", xytext=(10, 0), va="center", fontsize=12.5, fontweight="bold", color=color if color != FAINT else MUTED)
    axis.set_yticks(range(len(PLACEMENTS)), [label for label, _, _ in PLACEMENTS])
    colour_ticks(axis.get_yticklabels(), [BASIC, INK, INK, INK])
    axis.set_ylim(len(PLACEMENTS) - 0.45, -0.55)
    axis.set_xlim(2.75, 5.6)
    axis.set_xlabel("s/step on 4 nodes, each job")
    axis.grid(axis="x", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    save(figure, "p10_pinning")


def scotch():
    """Supporting slide: scotch against the case-default hierarchical decomposition at 1, 2 and 4 nodes, same placement."""
    data = runs("decomposition_basic.csv", "nodes", "method")
    figure, axes = plt.subplots(1, 3, figsize=(11.9, 4.1), layout="constrained")
    for axis, n in zip(axes, NODES):
        hierarchical, split = data[(n, "hierarchical")], data[(n, "scotch")]
        for x, values, color in ((0, hierarchical, FAINT), (1, split, BASIC)):
            mean = jobs(axis, x, values, color)
            axis.annotate(four(mean), (x + 0.27, mean), textcoords="offset points", xytext=(4, 0), va="center", fontsize=12, fontweight="bold", color=color if color != FAINT else MUTED)
        axis.set_xticks([0, 1], ["hierarchical", "scotch"])
        colour_ticks(axis.get_xticklabels(), [INK, BASIC])
        axis.set_xlim(-0.6, 1.8)
        axis.set_title(f"{n} node{'s' if n > 1 else ''}")
        axis.text(0.5, 0.98, percent(split, hierarchical), transform=axis.transAxes, ha="center", va="top", fontsize=14, fontweight="bold", color=NAVY)
        both = hierarchical + split
        span = max(both) - min(both)
        axis.set_ylim(min(both) - span * 0.15, max(both) + span * 0.5)
        axis.yaxis.set_major_locator(MaxNLocator(4))
    axes[0].set_ylabel("s/step, each job")
    save(figure, "p11_scotch")


def basic_4node():
    """Main slide 7: our baseline and Basic on 4 nodes, each job."""
    baseline, basic = BASELINE[4], FINAL[("Basic", 4)]
    figure, axis = plt.subplots(figsize=(5.4, 5.2), layout="constrained")
    for x, values, color in ((0, baseline, BASE), (1, basic, BASIC)):
        jobs(axis, x, values, color, width=0.34)
        axis.annotate(stats(values).replace(", ", "\n"), (x, max(values)), textcoords="offset points", xytext=(0, 10), ha="center", va="bottom", fontsize=13, fontweight="bold", color=color)
    axis.text(0.5, (statistics.fmean(baseline) + statistics.fmean(basic)) / 2, percent(basic, baseline), ha="center", va="center", fontsize=17, fontweight="bold", color=NAVY)
    axis.set_xticks([0, 1], [f"baseline\n{jobs_label(len(baseline))}", f"Basic\n{jobs_label(len(basic))}"])
    colour_ticks(axis.get_xticklabels(), [BASE, BASIC])
    axis.set_xlim(-0.6, 1.6)
    axis.set_ylim(2.75, 4.15)
    axis.set_yticks([2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0])
    axis.set_ylabel("s/step on 4 nodes")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    save(figure, "p12_basic")


def scaling():
    """Main slide 12: baseline, Basic and Bonus on 1, 2 and 4 nodes, each job, on log axes where ideal scaling is a straight
    line. The parallel efficiencies stand on the slide beside the plot."""
    series = [("baseline", BASELINE, BASE, 0.87), ("Basic", {n: FINAL[("Basic", n)] for n in NODES}, BASIC, 1.0), ("Bonus", {n: FINAL[("Bonus", n)] for n in NODES}, BONUS, 1.15)]
    figure, axis = plt.subplots(figsize=(7.6, 5.5), layout="constrained")
    handles = []
    for name, data, color, factor in series:
        one = statistics.fmean(data[1])
        axis.plot([factor, 4 * factor], [one, one / 4], "--", color=color, linewidth=0.9, alpha=0.55, zorder=1)
        for n in NODES:
            x = n * factor
            values = data[n]
            xs = [x * (1 + 0.035 * (k - (len(values) - 1) / 2) / max(len(values) - 1, 1)) for k in range(len(values))]
            axis.scatter(xs, values, s=40, color=color, edgecolor="black", linewidth=0.45, zorder=3)
            mean = statistics.fmean(values)
            axis.hlines(mean, x * 0.955, x * 1.045, color=color, linewidth=2.4, zorder=2)
            axis.annotate(four(mean), (x * 1.045, mean), textcoords="offset points", xytext=(3, 0), va="center", fontsize=11.5, fontweight="bold", color=color)
        handles.append(Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=color, markeredgecolor="black", markeredgewidth=0.45, label=name))
    handles.append(Line2D([], [], linestyle="--", color=MUTED, linewidth=1.1, label="ideal from 1 node"))
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xticks(NODES, ["1", "2", "4"])
    axis.set_yticks([2.5, 3, 4, 6, 8, 10, 15], ["2.5", "3", "4", "6", "8", "10", "15"])
    axis.minorticks_off()
    axis.set_xlim(0.72, 5.9)
    axis.set_ylim(2.1, 17.5)
    axis.set_xlabel("Nodes (128 ranks per node)")
    axis.set_ylabel("s/step, each job (log scale)")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(handles=handles, frameon=False, loc="upper right")
    save(figure, "p17_scaling")


def reference():
    """Supporting slide: our Basic and Bonus against the organisers' own runs on the same machine."""
    groups = [("organisers'\nhierarchical", lambda n: ORGANISERS[("hierarchical", n)], MUTED, True), ("organisers'\nscotch", lambda n: ORGANISERS[("scotch", n)], FAINT, False), ("our\nBasic", lambda n: FINAL[("Basic", n)], BASIC, False), ("our\nBonus", lambda n: FINAL[("Bonus", n)], BONUS, False)]
    figure, axes = plt.subplots(1, 3, figsize=(11.9, 3.6), layout="constrained")
    for axis, n in zip(axes, NODES):
        everything = []
        for x, (_, values_of, color, hollow) in enumerate(groups):
            values = values_of(n)
            everything += values
            mean = jobs(axis, x, values, color, hollow=hollow)
            if x >= 2:
                axis.annotate(percent(values, ORGANISERS[("scotch", n)]), (x, min(values)), textcoords="offset points", xytext=(0, -9), ha="center", va="top", fontsize=12, fontweight="bold", color=NAVY)
            else:
                axis.annotate(four(mean), (x + 0.27, mean), textcoords="offset points", xytext=(4, 0), va="center", fontsize=11, color=MUTED)
        axis.set_xticks(range(len(groups)), [label for label, _, _, _ in groups], fontsize=10)
        colour_ticks(axis.get_xticklabels(), [INK, INK, BASIC, BONUS])
        axis.set_xlim(-0.6, 3.5)
        axis.set_title(f"{n} node{'s' if n > 1 else ''}")
        span = max(everything) - min(everything)
        axis.set_ylim(min(everything) - span * 0.22, max(everything) + span * 0.08)
        axis.yaxis.set_major_locator(MaxNLocator(4))
    axes[0].set_ylabel("s/step, each job")
    save(figure, "ps_reference")


# Every Bonus change on 4 nodes in the order it was added, by patch number; the table beside the plot names them.
# * marks the two candidates that ran a few days after their control instead of alternated with it.
EACH = [("multiLevel", "multi-\nLevel"), ("0001", "0001"), ("0002", "0002"), ("0003", "0003"), ("0004", "0004"), ("0006-0010", "0006,\n08–10"), ("0011", "0011"), ("0012", "0012"), ("0013-0015", "0013–\n15 *"), ("0016", "0016 *")]


def each_change():
    """Supporting slide: each Bonus change against the configuration just before it, 4 nodes, each job against its control's mean."""
    figure, axis = plt.subplots(figsize=(6.4, 5.1), layout="constrained")
    axis.axhline(0, color=MUTED, linewidth=0.9, zorder=1)
    for index, (key, _) in enumerate(EACH):
        control, candidate = CHANGES[(key, 4, "control")], CHANGES[(key, 4, "candidate")]
        mean = statistics.fmean(control)
        jobs(axis, index - 0.17, [(value / mean - 1) * 100 for value in control], FAINT, width=0.13)
        after = jobs(axis, index + 0.17, [(value / mean - 1) * 100 for value in candidate], BONUS, width=0.13)
        axis.text(index + 0.17, after - 0.28, percent(candidate, control), ha="center", va="top", fontsize=10.5, fontweight="bold", color=NAVY)
        axis.text(index, 0.42, f"{len(control)} v {len(candidate)}", ha="center", va="bottom", fontsize=9.5, color=MUTED)
    axis.set_xticks(range(len(EACH)), [label for _, label in EACH], fontsize=10)
    axis.set_xlim(-0.6, len(EACH) - 0.3)
    axis.set_ylim(-4.6, 0.95)
    axis.set_ylabel("Each job against the mean of its control (%)")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(handles=[Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=FAINT, markeredgecolor="black", markeredgewidth=0.45, label="before (control)"), Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=BONUS, markeredgecolor="black", markeredgewidth=0.45, label="after (candidate)")], frameon=False, loc="lower left", ncols=2)
    save(figure, "ps_each")


# The 4-node runs in data/cd_iterations_4node.csv, in drawing order: name, colour, line style, line width
CD_RUNS = [("organisers hierarchical", MUTED, ":", 1.6), ("organisers scotch", FAINT, "-", 1.6), ("Basic", BASIC, "-", 2.2), ("Bonus without its source changes", BONUS_LIGHT, "-", 4.5), ("Bonus", BONUS, "--", 1.8)]


def cd_iterations():
    """Supporting slide: Cd at every iteration of the 4-node runs (ISC26 Task 4), the whole run and its last 50 iterations.

    The Bonus and the same decomposition without its source changes lie on top of each other; different decompositions
    end a few per cent apart.
    """
    cd = defaultdict(list)
    for row in F.read("cd_iterations_4node.csv"):
        cd[row["configuration"]].append((int(row["iteration"]), float(row["cd"])))
    figure, (whole, end) = plt.subplots(1, 2, figsize=(11.9, 4.3), layout="constrained", width_ratios=(1.15, 1))
    for name, color, style, width in CD_RUNS:
        iterations, values = zip(*cd[name])
        label = name.replace("organisers", "organisers'")
        whole.plot(iterations, values, style, color=color, linewidth=width, label=label)
        tail = [(i, v) for i, v in cd[name] if i >= 100]
        end.plot(*zip(*tail), style, color=color, linewidth=width)
        end.annotate(f"{tail[-1][1]:.4f}", tail[-1], textcoords="offset points", xytext=(6, 0), va="center", fontsize=11.5, fontweight="bold", color=color if color not in (FAINT, BONUS_LIGHT) else MUTED)
    whole.set_title("All 150 iterations", loc="left")
    end.set_title("Iterations 100 to 150", loc="left")
    for axis in (whole, end):
        axis.set_xlabel("Iteration (4 nodes)")
        axis.grid(color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
    whole.set_ylabel("Cd")
    whole.set_xlim(0, 152)
    end.set_xlim(100, 163)
    whole.legend(frameon=False, loc="upper right")
    save(figure, "ps_cd_iterations")


rule()
pinning()
scotch()
basic_4node()
scaling()
reference()
each_change()
cd_iterations()
