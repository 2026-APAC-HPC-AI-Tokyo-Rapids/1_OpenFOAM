# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Per-job plots for the deck, each drawn at the size it takes on its slide.

usage: deck_plots.py <path/to/figures.py> <output_dir>

Every point is one job's official time per step and a bar is the mean of the jobs, so a plot shows the change, the scaling
and how many jobs stand behind each number. The data and their readers come from figures.py, the colours from palette.py.
A plot is drawn at its size on the slide, so 12 pt here is 12 pt there.
"""

import importlib.util
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
plt.rcParams.update({"font.size": 12, "axes.titlesize": 12.5, "axes.labelsize": 12, "xtick.labelsize": 11.5, "ytick.labelsize": 11.5, "legend.fontsize": 11.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK})
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


def jobs(axis, x, values, color, width=0.3, hollow=False, horizontal=False):
    """One dot per job around x, and the mean of the jobs as a bar; returns the mean."""
    spread = F.spread(values, x, width)
    xs, ys = (values, spread) if horizontal else (spread, values)
    if hollow:
        axis.scatter(xs, ys, s=44, facecolor="white", edgecolor=color, linewidth=1.6, zorder=3)
    else:
        axis.scatter(xs, ys, s=44, color=color, edgecolor="black", linewidth=0.5, zorder=3)
    mean = statistics.fmean(values)
    lines = axis.vlines if horizontal else axis.hlines
    lines(mean, x - width / 2 - 0.1, x + width / 2 + 0.1, color=color, linewidth=2.5, zorder=2)
    return mean


def jobs_label(n):
    return f"{n} job{'s' if n > 1 else ''}"


def colour_ticks(labels, colors):
    for label, color in zip(labels, colors):
        label.set_color(color)


def baseline_scaling():
    """Slide 5: our baseline on 1, 2 and 4 nodes, each job, with the organisers' one hierarchical run per node count."""
    one = statistics.fmean(BASELINE[1])
    figure, axis = plt.subplots(figsize=(8.4, 4.5), layout="constrained")
    ideal = [1 + k * 0.05 for k in range(69)]
    axis.plot(ideal, [one / x for x in ideal], "--", color=MUTED, linewidth=1.2, label="ideal: our 1-node mean ÷ nodes")
    for n in NODES:
        value = ORGANISERS[("hierarchical", n)][0]
        axis.scatter([n - 0.17], [value], s=58, facecolor="white", edgecolor=MUTED, linewidth=1.6, zorder=3)
        axis.annotate(f"{value:.2f}", (n - 0.17, value), textcoords="offset points", xytext=(-8, 0), ha="right", va="center", fontsize=11.5, color=MUTED)
        mean = jobs(axis, n + 0.12, BASELINE[n], BASE, width=0.16)
        axis.annotate(f"{mean:.2f}", (n + 0.3, mean), textcoords="offset points", xytext=(4, 0), va="center", fontsize=12.5, fontweight="bold", color=BASE)
    axis.scatter([], [], s=58, facecolor="white", edgecolor=MUTED, linewidth=1.6, label="organisers' hierarchical run: site build, no binding")
    axis.scatter([], [], s=44, color=BASE, edgecolor="black", linewidth=0.5, label="our baseline: each job; bar = mean")
    axis.set_xticks(NODES, ["1", "2", "4"])
    axis.set_xlim(0.4, 4.75)
    axis.set_ylim(0, 16)
    axis.set_yticks([0, 3, 6, 9, 12, 15])
    axis.set_xlabel("Nodes (128 ranks per node)")
    axis.set_ylabel("s/step")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="upper right")
    save(figure, "p05_baseline_scaling")


def rule():
    """Slide 7: the second test on two small changes, 4 nodes, each job: kept only when every job beats every control job."""
    compilers = runs("compiler_options.csv", "option")
    examples = [("Kept: mapped onto the node", "scotch defaults", CHANGES[("mapping", 4, "control")], "mapped", CHANGES[("mapping", 4, "candidate")], BASIC), ("Not kept: AOCC instead of GCC", "GCC", compilers["control (GCC -O3, scotch)"], "AOCC", compilers["AOCC 5.0 / AOCL 5.1"], NAVY)]
    figure, axes = plt.subplots(2, 1, figsize=(5.3, 3.95), layout="constrained")
    for axis, (title, control_name, control, candidate_name, candidate, color) in zip(axes, examples):
        jobs(axis, 0, control, FAINT, width=0.36, horizontal=True)
        jobs(axis, 1, candidate, color, width=0.36, horizontal=True)
        kept = max(candidate) < min(control)
        if kept:
            axis.axvspan(max(candidate), min(control), color=GRID, zorder=0)
        axis.set_title(f"{title}, {percent(candidate, control, 2)}", loc="left", fontsize=12, fontweight="bold", color=INK)
        axis.text(0.99, 0.5, "no overlap" if kept else "overlap", transform=axis.transAxes, ha="right", va="center", fontsize=12, fontweight="bold", color=NAVY if kept else BAD)
        axis.set_yticks([0, 1], [f"{control_name}\n{jobs_label(len(control))}", f"{candidate_name}\n{jobs_label(len(candidate))}"])
        colour_ticks(axis.get_yticklabels(), [INK, color])
        axis.set_ylim(1.55, -0.55)
        low, high = min(control + candidate), max(control + candidate)
        axis.set_xlim(low - (high - low) * 0.1, high + (high - low) * 0.45)
        axis.xaxis.set_major_locator(MaxNLocator(4))
        axis.grid(axis="x", color=GRID, linewidth=0.8)
        axis.set_axisbelow(True)
    axes[-1].set_xlabel("s/step on 4 nodes, each job")
    save(figure, "p07_rule")


PLACEMENTS = [("Both: Basic\n(numactl + keeper)", "numactl --membind + taskset keeper (adopted for Basic)", BASIC), ("CPU only\n(taskset keeper)", "taskset keeper only (re-pins 12-16 s after start)", FAINT), ("Neither: the launcher's\nbinding, lost", "PALS --cpu-bind and --mem-bind only", FAINT), ("Memory only\n(numactl)", "numactl --membind only", BAD)]


def pinning():
    """Slide 10: which half of the placement fix matters (4 nodes, scotch split)."""
    data = runs("pinning.csv", "configuration")
    figure, axis = plt.subplots(figsize=(5.9, 4.4), layout="constrained")
    for row, (_, key, color) in enumerate(PLACEMENTS):
        mean = jobs(axis, row, data[key], color, width=0.28, horizontal=True)
        axis.annotate(f"{mean:.2f}", (max(data[key]), row), textcoords="offset points", xytext=(9, 0), va="center", fontsize=12.5, fontweight="bold", color=color if color != FAINT else MUTED)
    axis.set_yticks(range(len(PLACEMENTS)), [label for label, _, _ in PLACEMENTS])
    colour_ticks(axis.get_yticklabels(), [BASIC, INK, INK, INK])
    axis.set_ylim(len(PLACEMENTS) - 0.45, -0.55)
    axis.set_xlim(2.75, 4.7)
    axis.set_xlabel("s/step on 4 nodes, each job")
    axis.grid(axis="x", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    save(figure, "p10_pinning")


def scotch():
    """Slide 11: scotch against the case-default hierarchical split at 1, 2 and 4 nodes, same placement."""
    data = runs("decomposition_basic.csv", "nodes", "method")
    figure, axes = plt.subplots(1, 3, figsize=(5.5, 2.95), layout="constrained")
    for axis, n in zip(axes, NODES):
        hierarchical, split = data[(n, "hierarchical")], data[(n, "scotch")]
        jobs(axis, 0, hierarchical, FAINT)
        jobs(axis, 1, split, BASIC)
        axis.set_xticks([0, 1], ["hier.", "scotch"])
        colour_ticks(axis.get_xticklabels(), [INK, BASIC])
        axis.set_xlim(-0.6, 1.6)
        axis.set_title(f"{n} node{'s' if n > 1 else ''}")
        axis.text(0.5, 0.98, percent(split, hierarchical), transform=axis.transAxes, ha="center", va="top", fontsize=13, fontweight="bold", color=NAVY)
        both = hierarchical + split
        span = max(both) - min(both)
        axis.set_ylim(min(both) - span * 0.15, max(both) + span * 0.5)
        axis.yaxis.set_major_locator(MaxNLocator(4))
    axes[0].set_ylabel("s/step, each job")
    save(figure, "p11_scotch")


def basic_4node():
    """Slide 12: our baseline and Basic on 4 nodes, each job."""
    baseline, basic = BASELINE[4], FINAL[("Basic", 4)]
    figure, axis = plt.subplots(figsize=(3.7, 4.45), layout="constrained")
    for x, values, color in ((0, baseline, BASE), (1, basic, BASIC)):
        mean = jobs(axis, x, values, color, width=0.34)
        axis.annotate(f"{mean:.2f}", (x + 0.27, mean), textcoords="offset points", xytext=(5, 0), va="center", fontsize=13, fontweight="bold", color=color)
    axis.text(0.5, (statistics.fmean(baseline) + statistics.fmean(basic)) / 2, percent(basic, baseline, 0), ha="center", va="center", fontsize=16, fontweight="bold", color=NAVY)
    axis.set_xticks([0, 1], [f"baseline\n{jobs_label(len(baseline))}", f"Basic\n{jobs_label(len(basic))}"])
    colour_ticks(axis.get_xticklabels(), [BASE, BASIC])
    axis.set_xlim(-0.55, 1.75)
    axis.set_ylim(2.75, 3.95)
    axis.set_yticks([2.8, 3.0, 3.2, 3.4, 3.6, 3.8])
    axis.set_ylabel("s/step on 4 nodes")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    save(figure, "p12_basic")


def bonus():
    """Slide 15: Basic, the Bonus split with the source unchanged (the pre-change baseline), the first four changes and the Bonus.

    The first four changes are the control jobs of the final measurement, alternated with the Bonus jobs.
    """
    groups = [("Basic", lambda n: FINAL[("Basic", n)], BASIC, False), ("multiLevel\nonly", lambda n: CHANGES[("multiLevel", n, "candidate")], BONUS, True), ("first four\nchanges", lambda n: CHANGES[("0006-0016", n, "control")], BONUS_LIGHT, False), ("Bonus", lambda n: FINAL[("Bonus", n)], BONUS, False)]
    figure, axes = plt.subplots(1, 3, figsize=(11.9, 2.95), layout="constrained")
    for axis, n in zip(axes, NODES):
        everything = []
        for x, (_, values_of, color, hollow) in enumerate(groups):
            values = values_of(n)
            everything += values
            mean = jobs(axis, x, values, color, hollow=hollow)
            axis.annotate(f"{mean:.3f}\n{jobs_label(len(values))}", (x, max(values)), textcoords="offset points", xytext=(0, 7), ha="center", va="bottom", fontsize=10.5, color=INK, linespacing=1.0)
        basic, bonus_values = FINAL[("Basic", n)], FINAL[("Bonus", n)]
        axis.text(3.0, (statistics.fmean(basic) + statistics.fmean(bonus_values)) / 2, f"{percent(bonus_values, basic)}\nvs Basic", ha="center", va="center", fontsize=12, fontweight="bold", color=NAVY, linespacing=1.0)
        axis.set_xticks(range(len(groups)), [label for label, _, _, _ in groups], fontsize=10.5)
        colour_ticks(axis.get_xticklabels(), [BASIC, INK, INK, BONUS])
        axis.set_xlim(-0.55, 3.55)
        axis.set_title(f"{n} node{'s' if n > 1 else ''} ({128 * n} ranks, {STEPS[n]} steps)")
        span = max(everything) - min(everything)
        axis.set_ylim(min(everything) - span * 0.1, max(everything) + span * 0.42)
        axis.yaxis.set_major_locator(MaxNLocator(4))
    axes[0].set_ylabel("s/step, each job")
    save(figure, "p15_bonus")


def scaling():
    """Slide 17: baseline, Basic and Bonus on 1, 2 and 4 nodes, each job, on log axes where ideal scaling is a straight line."""
    series = [("baseline", BASELINE, BASE, 0.87), ("Basic", {n: FINAL[("Basic", n)] for n in NODES}, BASIC, 1.0), ("Bonus", {n: FINAL[("Bonus", n)] for n in NODES}, BONUS, 1.15)]
    figure, axis = plt.subplots(figsize=(6.45, 4.95), layout="constrained")
    handles = []
    for name, data, color, factor in series:
        one = statistics.fmean(data[1])
        axis.plot([factor, 4 * factor], [one, one / 4], "--", color=color, linewidth=0.9, alpha=0.55, zorder=1)
        for n in NODES:
            x = n * factor
            values = data[n]
            xs = [x * (1 + 0.035 * (k - (len(values) - 1) / 2) / max(len(values) - 1, 1)) for k in range(len(values))]
            axis.scatter(xs, values, s=36, color=color, edgecolor="black", linewidth=0.45, zorder=3)
            mean = statistics.fmean(values)
            axis.hlines(mean, x * 0.955, x * 1.045, color=color, linewidth=2.4, zorder=2)
            axis.annotate(f"{mean:.2f}", (x * 1.045, mean), textcoords="offset points", xytext=(3, 0), va="center", fontsize=10.5, fontweight="bold", color=color)
        efficiency = one / (4 * statistics.fmean(data[4]))
        handles.append(Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=color, markeredgecolor="black", markeredgewidth=0.45, label=f"{name}: efficiency {efficiency:.2f}"))
    handles.append(Line2D([], [], linestyle="--", color=MUTED, linewidth=1.1, label="dashed: ideal from 1 node"))
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xticks(NODES, ["1", "2", "4"])
    axis.set_yticks([2.5, 3, 4, 6, 8, 10, 15], ["2.5", "3", "4", "6", "8", "10", "15"])
    axis.minorticks_off()
    axis.set_xlim(0.72, 5.6)
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
    figure, axes = plt.subplots(1, 3, figsize=(11.9, 3.35), layout="constrained")
    for axis, n in zip(axes, NODES):
        everything = []
        for x, (_, values_of, color, hollow) in enumerate(groups):
            values = values_of(n)
            everything += values
            mean = jobs(axis, x, values, color, hollow=hollow)
            if x >= 2:
                axis.annotate(percent(values, ORGANISERS[("scotch", n)]), (x, min(values)), textcoords="offset points", xytext=(0, -9), ha="center", va="top", fontsize=11.5, fontweight="bold", color=NAVY)
            else:
                axis.annotate(f"{mean:.2f}", (x + 0.27, mean), textcoords="offset points", xytext=(4, 0), va="center", fontsize=10.5, color=MUTED)
        axis.set_xticks(range(len(groups)), [label for label, _, _, _ in groups], fontsize=10.5)
        colour_ticks(axis.get_xticklabels(), [INK, INK, BASIC, BONUS])
        axis.set_xlim(-0.5, 3.5)
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
    figure, axis = plt.subplots(figsize=(6.4, 4.85), layout="constrained")
    axis.axhline(0, color=MUTED, linewidth=0.9, zorder=1)
    for index, (key, _) in enumerate(EACH):
        control, candidate = CHANGES[(key, 4, "control")], CHANGES[(key, 4, "candidate")]
        mean = statistics.fmean(control)
        jobs(axis, index - 0.17, [(value / mean - 1) * 100 for value in control], FAINT, width=0.13)
        after = jobs(axis, index + 0.17, [(value / mean - 1) * 100 for value in candidate], BONUS, width=0.13)
        axis.text(index + 0.17, after - 0.28, percent(candidate, control), ha="center", va="top", fontsize=10.5, fontweight="bold", color=NAVY)
        axis.text(index, 0.42, f"{len(control)} v {len(candidate)}", ha="center", va="bottom", fontsize=9, color=MUTED)
    axis.set_xticks(range(len(EACH)), [label for _, label in EACH], fontsize=9.5)
    axis.set_xlim(-0.6, len(EACH) - 0.3)
    axis.set_ylim(-4.6, 0.95)
    axis.set_ylabel("Each job against the mean of its control (%)")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(handles=[Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=FAINT, markeredgecolor="black", markeredgewidth=0.45, label="before (control)"), Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=BONUS, markeredgecolor="black", markeredgewidth=0.45, label="after (candidate)")], frameon=False, loc="lower left", ncols=2)
    save(figure, "ps_each")


def path():
    """Supporting slide: the path on 4 nodes, from the start to the Bonus, each step against its own control; figures.py's
    fig16_journey with the same data, drawn at slide size."""
    methods = runs("decomposition_basic.csv", "nodes", "method")
    start = [float(row["s_per_step"]) for row in F.read("start_unpinned.csv")]
    organisers = ORGANISERS[("scotch", 4)]
    steps = [("start:\nbinding\nlost", start, BASE, None), ("+ CPU and\nNUMA\npinning", methods[(4, "hierarchical")], BASIC, percent(methods[(4, "hierarchical")], start)), ("+ scotch", methods[(4, "scotch")], BASIC, percent(methods[(4, "scotch")], methods[(4, "hierarchical")])), ("+ node\nmapping\n= Basic", FINAL[("Basic", 4)], BASIC, percent(CHANGES[("mapping", 4, "candidate")], CHANGES[("mapping", 4, "control")]))]
    labels = {"multiLevel": "+ multi-\nLevel", "0001": "+ no\ncopies", "0002": "+ U in\none pass", "0003": "+ no unused\nboundary\nvalues", "0004": "+ fused\nface loops", "0006-0010": "+ Laplacian,\np reference,\nstress,\nwalls", "0011": "+ Gauss–\nSeidel\nno copy", "0012": "+ one sum\nper CG\niteration", "0013-0015": "+ k-ω SST,\nzero fills,\nGAMG *", "0016": "+ residual\nfrom the\nsweep *"}
    for key, _ in EACH:
        steps.append((labels[key], CHANGES[(key, 4, "candidate")], BONUS, percent(CHANGES[(key, 4, "candidate")], CHANGES[(key, 4, "control")])))
    # the last point is the final Bonus from its alternated final runs, the value the report gives
    steps[-1] = (steps[-1][0] + "\n= Bonus", FINAL[("Bonus", 4)], BONUS, steps[-1][3])
    figure, axis = plt.subplots(figsize=(11.9, 4.6), layout="constrained")
    axis.axhline(statistics.fmean(organisers), color=MUTED, linestyle="--", linewidth=1.2)
    axis.text(len(steps) - 0.45, statistics.fmean(organisers) + 0.015, f"organisers' scotch, mean of {len(organisers)}: {statistics.fmean(organisers):.3f}", ha="right", fontsize=10.5, color=MUTED)
    means = [statistics.fmean(values) for _, values, _, _ in steps]
    axis.plot(range(len(steps)), means, color=MUTED, linewidth=1.0, zorder=1)
    for index, (_, values, color, change) in enumerate(steps):
        jobs(axis, index, values, color, width=0.3)
        axis.annotate(f"{means[index]:.3f}", (index, min(values)), textcoords="offset points", xytext=(0, -7), ha="center", va="top", fontsize=10, fontweight="bold", color=color)
        if change is not None:
            axis.annotate(change, (index, max(values)), textcoords="offset points", xytext=(0, 7), ha="center", va="bottom", fontsize=10.5, fontweight="bold", color=NAVY, bbox={"boxstyle": "square,pad=0.05", "facecolor": "white", "edgecolor": "none"})
    axis.set_xticks(range(len(steps)), [label for label, _, _, _ in steps], fontsize=9)
    colour_ticks(axis.get_xticklabels(), [BASE] + [BASIC] * 3 + [BONUS] * (len(steps) - 4))
    axis.set_xlim(-0.55, len(steps) - 0.45)
    axis.set_ylim(2.25, 3.8)
    axis.set_ylabel("s/step on 4 nodes, each job")
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    save(figure, "ps_path")


baseline_scaling()
rule()
pinning()
scotch()
basic_4node()
bonus()
scaling()
reference()
each_change()
path()
