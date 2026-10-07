# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Figures and table images for the OpenFOAM part of the interview deck.

Usage: uv run presentation/openfoam/figures.py OUTPUT_DIR

Reads presentation/openfoam/data/*.csv and writes <name>.png (for pasting) and <name>.svg (editable) to OUTPUT_DIR.
Every timing point is one job's official "Average wall-clock time per time step" unless a figure says otherwise.
"""

import csv
import statistics
import sys
import textwrap
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

DATA = Path(__file__).resolve().parent / "data"
BASIC = "#3b6ea8"
BONUS = "#d9822b"
CONTROL = "#8c8c8c"
CANDIDATE = "#2e8b57"
ACCENT = "#c0392b"
LIGHT = "#eef2f7"
WIDE = (12.8, 6.4)

plt.rcParams.update({"font.size": 14, "axes.titlesize": 15, "axes.labelsize": 14, "legend.fontsize": 12, "svg.fonttype": "none", "axes.spines.top": False, "axes.spines.right": False})


def read(name):
    with open(DATA / name, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save(figure, output, name):
    figure.savefig(output / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
    figure.savefig(output / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(figure)


def spread(values, center, width=0.16):
    if len(values) == 1:
        return [center]
    return [center - width / 2 + width * index / (len(values) - 1) for index in range(len(values))]


def change(candidate, control):
    return (statistics.fmean(candidate) / statistics.fmean(control) - 1) * 100


def final_runs(output):
    runs = defaultdict(list)
    for row in read("final_runs.csv"):
        runs[(row["configuration"], int(row["nodes"]))].append(float(row["s_per_step"]))
    figure, axes = plt.subplots(1, 3, figsize=WIDE)
    for axis, nodes in zip(axes, (1, 2, 4)):
        for position, (configuration, color) in enumerate((("Basic", BASIC), ("Bonus", BONUS))):
            values = runs[(configuration, nodes)]
            axis.scatter(spread(values, position), values, s=70, color=color, edgecolor="black", linewidth=0.6, zorder=3)
            mean = statistics.fmean(values)
            axis.hlines(mean, position - 0.25, position + 0.25, color=color, linewidth=2.5)
            axis.annotate(f"{mean:.3f}\nn = {len(values)}", (position + 0.28, mean), va="center", fontsize=12)
        axis.set_xticks([0, 1], ["Basic", "Bonus"])
        axis.set_xlim(-0.5, 1.85)
        axis.set_title(f"{nodes} node{'s' if nodes > 1 else ''} ({nodes * 128} ranks, {dict([(1, 40), (2, 80), (4, 150)])[nodes]} steps)")
        diff = change(runs[("Bonus", nodes)], runs[("Basic", nodes)])
        axis.text(0.5, 0.5, f"{diff:+.1f} %", transform=axis.transAxes, ha="center", fontsize=18, fontweight="bold", color=ACCENT)
        low = min(runs[("Bonus", nodes)])
        high = max(runs[("Basic", nodes)])
        axis.set_ylim(low - (high - low) * 0.15, high + (high - low) * 0.15)
    axes[0].set_ylabel("Average wall-clock time per time step (s)")
    figure.text(0.5, -0.04, "Each point is one job (official metric, steps 2 to N). Lines are means; y-axes do not start at 0. ASPIRE-2A, Basic 2026-10-04/05, Bonus 2026-10-06.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig01_final_runs")


def scaling(output):
    runs = defaultdict(list)
    for row in read("final_runs.csv"):
        runs[(row["configuration"], int(row["nodes"]))].append(float(row["s_per_step"]))
    nodes = [1, 2, 4]
    figure, (left, right) = plt.subplots(1, 2, figsize=WIDE, gridspec_kw={"width_ratios": [1.2, 1]})
    for configuration, color, offset in (("Basic", BASIC, (10, 8)), ("Bonus", BONUS, (-46, -20))):
        means = [statistics.fmean(runs[(configuration, n)]) for n in nodes]
        left.plot(nodes, means, "o-", color=color, linewidth=2.5, markersize=9, label=configuration)
        left.plot(nodes, [means[0] / n for n in nodes], "--", color=color, linewidth=1.2, alpha=0.8)
        for n, mean in zip(nodes, means):
            left.annotate(f"{mean:.2f}", (n, mean), textcoords="offset points", xytext=offset, fontsize=12, color=color, fontweight="bold")
    left.set_xscale("log", base=2)
    left.set_yscale("log")
    left.set_xticks(nodes, ["1", "2", "4"])
    left.set_yticks([2.5, 3, 4, 6, 8, 10, 13], ["2.5", "3", "4", "6", "8", "10", "13"])
    left.set_ylim(2.25, 15)
    left.set_xlim(0.7, 4.9)
    left.minorticks_off()
    left.set_xlabel("Nodes (128 ranks per node)")
    left.set_ylabel("s / step (mean of runs)")
    left.legend(title="dashed: ideal from 1 node", frameon=False)
    width = 0.36
    for offset, (configuration, color) in zip((-width / 2, width / 2), (("Basic", BASIC), ("Bonus", BONUS))):
        one = statistics.fmean(runs[(configuration, 1)])
        efficiency = [one / (n * statistics.fmean(runs[(configuration, n)])) for n in nodes]
        bars = right.bar([index + offset for index in range(3)], efficiency, width, color=color, label=configuration)
        right.bar_label(bars, labels=[f"{value:.2f}" for value in efficiency], fontsize=11, padding=2)
    right.axhline(1, color="black", linewidth=1, linestyle=":")
    right.set_xticks(range(3), ["1", "2", "4"])
    right.set_xlabel("Nodes")
    right.set_ylabel("Parallel efficiency vs 1 node")
    right.set_ylim(0, 1.3)
    right.legend(frameon=False, loc="upper left")
    figure.tight_layout()
    save(figure, output, "fig02_scaling")


CHANGES = [("multiLevel", "multiLevel decomposition\nvs Basic scotch"), ("0001", "+0001 solver copies\nvs multiLevel"), ("0002", "+0002 U components\ntogether"), ("0003", "+0003 discarded\nboundary updates"), ("0004", "+0004 fused gradient\nand products")]


def changes_by_role():
    data = defaultdict(list)
    for row in read("changes_ab.csv"):
        data[(row["change"], int(row["nodes"]), row["role"])].append(float(row["s_per_step"]))
    return data


def changes_4node(output):
    data = changes_by_role()
    figure, axis = plt.subplots(figsize=WIDE)
    for index, (key, label) in enumerate(CHANGES):
        control = data[(key, 4, "control")]
        candidate = data[(key, 4, "candidate")]
        axis.scatter(spread(control, index - 0.17, 0.12), control, s=60, color=CONTROL, edgecolor="black", linewidth=0.5, zorder=3, label="before (control)" if index == 0 else None)
        axis.scatter(spread(candidate, index + 0.17, 0.12), candidate, s=60, color=CANDIDATE, edgecolor="black", linewidth=0.5, zorder=3, label="after (candidate)" if index == 0 else None)
        axis.annotate("", xy=(index + 0.17, statistics.fmean(candidate)), xytext=(index - 0.17, statistics.fmean(control)), arrowprops={"arrowstyle": "->", "color": "black", "linewidth": 1})
        axis.text(index, max(control) + 0.012, f"{change(candidate, control):+.2f} %\nn = {len(control)} vs {len(candidate)}", ha="center", fontsize=12)
    axis.set_xticks(range(len(CHANGES)), [label for _, label in CHANGES], fontsize=12)
    axis.set_ylabel("4 nodes, s / step")
    axis.set_ylim(2.57, 2.98)
    axis.legend(frameon=False, loc="lower left")
    figure.text(0.5, -0.03, "Each change against the configuration just before it, measured in the same period (4 nodes, 512 ranks, 150 steps).\nSeparate experiments: the percentages are not added up. coefficient.dat bit-identical for every source patch.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig03_changes_4node")


def changes_by_nodes(output):
    data = changes_by_role()
    figure, axis = plt.subplots(figsize=WIDE)
    width = 0.26
    colors = {1: "#9ecae1", 2: "#4292c6", 4: "#08519c"}
    for offset, nodes in zip((-width, 0, width), (1, 2, 4)):
        values = [change(data[(key, nodes, "candidate")], data[(key, nodes, "control")]) for key, _ in CHANGES]
        bars = axis.bar([index + offset for index in range(len(CHANGES))], values, width, color=colors[nodes], label=f"{nodes} node{'s' if nodes > 1 else ''}")
        counts = [f"{len(data[(key, nodes, 'control')])}v{len(data[(key, nodes, 'candidate')])}" for key, _ in CHANGES]
        axis.bar_label(bars, labels=[f"{value:.1f}\n{count}" for value, count in zip(values, counts)], fontsize=9, padding=2)
    axis.axhline(0, color="black", linewidth=1)
    axis.set_xticks(range(len(CHANGES)), [label for _, label in CHANGES], fontsize=12)
    axis.set_ylabel("Change in s / step vs the configuration before (%)")
    axis.set_ylim(-7.8, 0.5)
    axis.legend(frameon=False, loc="lower right")
    figure.text(0.5, -0.03, "Labels: change (%) and number of runs (before v after). Most 1- and 2-node values compare single runs.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig04_changes_by_nodes")


def decomposition(output):
    data = defaultdict(list)
    for row in read("decomposition_basic.csv"):
        data[(int(row["nodes"]), row["method"])].append(float(row["s_per_step"]))
    figure, axes = plt.subplots(1, 3, figsize=WIDE)
    for axis, nodes in zip(axes, (1, 2, 4)):
        for position, (method, color) in enumerate((("hierarchical", CONTROL), ("scotch", BASIC))):
            values = data[(nodes, method)]
            axis.scatter(spread(values, position), values, s=70, color=color, edgecolor="black", linewidth=0.6, zorder=3)
            axis.hlines(statistics.fmean(values), position - 0.25, position + 0.25, color=color, linewidth=2.5)
        axis.set_xticks([0, 1], ["hierarchical\n(case default)", "scotch"])
        axis.set_xlim(-0.6, 1.6)
        axis.set_title(f"{nodes} node{'s' if nodes > 1 else ''}")
        axis.text(0.5, 0.92, f"{change(data[(nodes, 'scotch')], data[(nodes, 'hierarchical')]):+.1f} %", transform=axis.transAxes, ha="center", fontsize=17, fontweight="bold", color=ACCENT)
        values = data[(nodes, "hierarchical")] + data[(nodes, "scotch")]
        span = max(values) - min(values)
        axis.set_ylim(min(values) - span * 0.15, max(values) + span * 0.3)
    axes[0].set_ylabel("s / step")
    figure.text(0.5, -0.03, "Unmodified v2512, same build and placement. 3 runs each, alternated in the same period (4 nodes: 2026-10-02; 1 and 2 nodes: 2026-10-04).", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig05_decomposition_basic")


def pinning(output):
    groups = defaultdict(list)
    pinned = {}
    local = {}
    for row in read("pinning.csv"):
        groups[row["configuration"]].append(float(row["s_per_step"]))
        pinned[row["configuration"]] = row["pinned_during_solve"]
        if row["local_pages_median"]:
            local[row["configuration"]] = row["local_pages_median"]
    order = sorted(groups, key=lambda name: statistics.fmean(groups[name]))
    figure, axis = plt.subplots(figsize=WIDE)
    for index, name in enumerate(order):
        values = groups[name]
        fast = pinned[name] == "128/128" and name.startswith(("LD_PRELOAD", "numactl --membind +"))
        color = CANDIDATE if fast else ACCENT
        axis.scatter(values, [index] * len(values), s=70, color=color, edgecolor="black", linewidth=0.6, zorder=3)
        axis.text(4.62, index, f"{pinned[name]:>7}   {local.get(name, '–'):>4}", va="center", fontsize=12, family="monospace")
    axis.text(4.62, -0.75, "pinned   local\nranks    pages", fontsize=11, family="monospace", va="bottom")
    axis.set_yticks(range(len(order)), order, fontsize=12)
    axis.set_xlim(2.8, 4.5)
    axis.set_ylim(-0.6, len(order) - 0.1)
    axis.set_xlabel("4 nodes, s / step (scotch, 150 steps)")
    axis.invert_yaxis()
    figure.text(0.5, -0.04, "Fast only when the CPU is pinned for the whole solve and the memory was allocated on the rank's own NUMA domain.\n'pinned ranks': ranks on their own CPU during the solve (node 0). 'local pages': median share of each rank's pages on its NUMA domain.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig06_pinning")


def compiler(output):
    groups = defaultdict(list)
    for row in read("compiler_options.csv"):
        groups[row["option"]].append(float(row["s_per_step"]))
    names = list(groups)
    control = groups[names[0]]
    figure, axis = plt.subplots(figsize=(12.8, 5.6))
    axis.axhspan(min(control), max(control), color=LIGHT, zorder=0)
    for index, name in enumerate(names):
        values = groups[name]
        color = CONTROL if index == 0 else BASIC
        axis.scatter(spread(values, index), values, s=70, color=color, edgecolor="black", linewidth=0.6, zorder=3)
        axis.hlines(statistics.fmean(values), index - 0.22, index + 0.22, color=color, linewidth=2.5)
        if index:
            axis.text(index, 2.927, f"{change(values, control):+.2f} %", ha="center", fontsize=13, color=ACCENT)
    axis.set_xticks(range(len(names)), names, fontsize=12)
    axis.set_ylim(2.895, 2.932)
    axis.set_ylabel("4 nodes, s / step")
    figure.text(0.5, -0.03, "3 runs each in the same period (2026-10-03). Shaded: range of the control runs. Every mean lies inside that range.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig07_compiler_options")


def variability(output):
    groups = defaultdict(list)
    for row in read("bench_runs_sep21_oct05.csv"):
        key = (row["commit"], row["build"], row["nodes"], row["method"], row["domains"])
        groups[key].append((datetime.strptime(row["start_utc"], "%Y-%m-%dT%H:%M:%SZ"), float(row["s_per_step"]), int(row["nodes"])))
    points = []
    for runs in groups.values():
        if len(runs) < 3:
            continue
        median = statistics.median(value for _, value, _ in runs)
        points.extend((start, (value / median - 1) * 100, nodes) for start, value, nodes in runs)
    colors = {1: "#9ecae1", 2: "#4292c6", 4: "#08519c"}
    figure, (top, bottom) = plt.subplots(2, 1, figsize=WIDE, sharex=True, gridspec_kw={"height_ratios": [1, 1.6]})
    for nodes in (1, 2, 4):
        selected = [(start, deviation) for start, deviation, n in points if n == nodes]
        for axis in (top, bottom):
            axis.scatter([start for start, _ in selected], [deviation for _, deviation in selected], s=36, color=colors[nodes], edgecolor="black", linewidth=0.4, label=f"{nodes} node{'s' if nodes > 1 else ''}", zorder=3)
    top.set_ylabel("all runs (%)")
    top.set_ylim(-10, 100)
    bottom.set_ylim(-1.6, 1.6)
    bottom.axhspan(-0.4, 0.4, color=LIGHT, zorder=0)
    bottom.set_ylabel("zoom (%)")
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    top.legend(frameon=False, ncol=3, loc="upper right")
    figure.supylabel("Deviation from the median of the same configuration", fontsize=13)
    outliers = sum(1 for _, deviation, _ in points if abs(deviation) > 1.6)
    figure.text(0.5, -0.03, f"{len(points)} runs in {sum(1 for runs in groups.values() if len(runs) >= 3)} configurations with 3 or more runs (same commit, build, nodes, decomposition), 2026-09-21 to 10-05.\n{outliers} runs lie outside the zoom; two September runs were 84 % and 91 % slower. Shaded: ±0.4 %.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig08_variability")


def mpi_breakdown(output):
    rows = read("craypat_summary.csv")
    figure, axis = plt.subplots(figsize=(12.8, 5.2))
    labels = [row["configuration"] for row in rows]
    parts = [("computation (process − MPI)", lambda row: float(row["process_s"]) - float(row["mpi_s"]), "#bcbddc"), ("MPI_Allreduce", lambda row: float(row["allreduce_s"]), "#e6550d"), ("MPI_Waitall", lambda row: float(row["waitall_s"]), "#fdae6b"), ("other MPI", lambda row: float(row["mpi_s"]) - float(row["allreduce_s"]) - float(row["waitall_s"]), "#fdd0a2")]
    left = [0.0] * len(rows)
    for name, value, color in parts:
        widths = [value(row) for row in rows]
        bars = axis.barh(range(len(rows)), widths, left=left, color=color, edgecolor="white", label=name)
        axis.bar_label(bars, labels=[f"{width:.1f}" if width >= 5 else "" for width in widths], label_type="center", fontsize=11)
        left = [start + width for start, width in zip(left, widths)]
    for index, row in enumerate(rows):
        share = float(row["mpi_s"]) / float(row["process_s"]) * 100
        axis.text(left[index] + 3, index, f"{float(row['process_s']):.1f} s   (MPI {share:.1f} %)", va="center", fontsize=12)
    axis.set_yticks(range(len(rows)), labels)
    axis.invert_yaxis()
    axis.set_xlim(0, 175)
    axis.set_xlabel("Seconds per rank (mean of 512 ranks), whole process")
    axis.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.16))
    figure.text(0.5, -0.02, "CrayPAT pat_run -g mpi, 4 nodes, 512 ranks, 40 steps (separate diagnostic runs, not the benchmark runs). Other MPI: Bcast, Isend, Irecv, Comm_dup.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig09_mpi_breakdown")


def rank_compute(output):
    rows = read("rank_compute.csv")
    before = sorted(float(row["before_0002_0004_s"]) for row in rows)
    after = sorted(float(row["final_bonus_s"]) for row in rows)
    figure, axis = plt.subplots(figsize=WIDE)
    for values, color, label in ((before, CONTROL, "before patches 0002–0004"), (after, BONUS, "final Bonus")):
        median = statistics.median(values)
        axis.plot(range(len(values)), values, color=color, linewidth=2.5, label=f"{label}: median {median:.1f} s, max {max(values):.1f} s (max/median {max(values) / median:.3f})")
    axis.set_xlabel("Ranks sorted by computation time")
    axis.set_ylabel("Computation time per rank (s, process − MPI)")
    axis.legend(frameon=False, loc="upper left")
    figure.text(0.5, -0.03, "CrayPAT diagnostic runs, 4 nodes, 512 ranks, 40 steps. The whole distribution moves down by about 9 %; the spread between ranks stays.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig10_rank_compute")


def reference_comparison(output):
    ours = defaultdict(list)
    for row in read("final_runs.csv"):
        ours[(row["configuration"], int(row["nodes"]))].append(float(row["s_per_step"]))
    theirs = defaultdict(list)
    for row in read("organiser_reference_aspire2a.csv"):
        if row["setting"] == "defaults":
            theirs[(row["method"], int(row["nodes"]))].append(float(row["s_per_step"]))
    groups = [("Organisers\nhierarchical", CONTROL, lambda n: theirs[("hierarchical", n)]), ("Organisers\nscotch", "#5f5f5f", lambda n: theirs[("scotch", n)]), ("Our Basic\n(scotch)", BASIC, lambda n: ours[("Basic", n)]), ("Our Bonus", BONUS, lambda n: ours[("Bonus", n)])]
    figure, axes = plt.subplots(1, 3, figsize=WIDE)
    for axis, nodes in zip(axes, (1, 2, 4)):
        for position, (label, color, values_of) in enumerate(groups):
            values = values_of(nodes)
            axis.scatter(spread(values, position, 0.3), values, s=55, color=color, edgecolor="black", linewidth=0.5, zorder=3)
            axis.hlines(statistics.fmean(values), position - 0.3, position + 0.3, color=color, linewidth=2.5)
        reference = theirs[("scotch", nodes)]
        for position, key in ((2, "Basic"), (3, "Bonus")):
            values = ours[(key, nodes)]
            axis.annotate(f"{change(values, reference):+.0f} %", (position, statistics.fmean(values)), textcoords="offset points", xytext=(0, -24), ha="center", fontsize=12, fontweight="bold", color=ACCENT)
        axis.set_xticks(range(len(groups)), [label for label, _, _ in groups], fontsize=10)
        axis.set_xlim(-0.6, len(groups) - 0.4)
        axis.set_title(f"{nodes} node{'s' if nodes > 1 else ''}")
        everything = [value for _, _, values_of in groups for value in values_of(nodes)]
        span = max(everything) - min(everything)
        axis.set_ylim(min(everything) - span * 0.18, max(everything) + span * 0.08)
    axes[0].set_ylabel("s / step (each point is one job)")
    figure.text(0.5, -0.06, "Organisers: ASPIRE-2A notes (tasks 4.3): site module, mpirun with no options, default MPI settings, no binding; full-chain, split and simpleFoam-only runs.\nRed: our mean against the organisers' scotch mean. Different builds, MPI transport and placement, so the gap has more than one cause. y-axes do not start at 0.", ha="center", fontsize=10.5)
    figure.tight_layout()
    save(figure, output, "fig14_vs_organiser_reference")


def counters(output):
    values = defaultdict(lambda: defaultdict(list))
    seconds = defaultdict(dict)
    for row in read("counters_1node.csv"):
        values[row["metric"]][row["condition"]].append(float(row["per_rank_mean"]))
        seconds[row["condition"]][row["actions_run"]] = float(row["s_per_step_under_uprof"])
    rows = [("s / step", list(seconds["unpatched"].values()), list(seconds["patched"].values()))]
    rows += [(metric, values[metric]["unpatched"], values[metric]["patched"]) for metric in ("cycles", "instructions", "L1 data accesses", "L1 refills from L2", "L1 refills from L3", "L1 refills from DRAM", "L2 accesses incl. prefetch")]
    figure, axis = plt.subplots(figsize=WIDE)
    for index, (metric, before, after) in enumerate(rows):
        color = ACCENT if metric == "L1 refills from DRAM" else BONUS
        axis.barh(index, change(after, before), color=color, height=0.6)
        pairs = [(b / a - 1) * 100 for a in before for b in after]
        axis.scatter(pairs, [index] * len(pairs), s=28, color="black", zorder=3)
        axis.text(min(min(pairs), change(after, before)) - 0.5, index, f"{change(after, before):+.1f} %", va="center", ha="right", fontsize=13, fontweight="bold", color=color)
    axis.axvline(0, color="black", linewidth=1)
    axis.set_yticks(range(len(rows)), [metric for metric, _, _ in rows], fontsize=13)
    axis.invert_yaxis()
    axis.set_xlim(-22, 4.5)
    axis.set_xlabel("Patches 0001-0004 against the same build without them (%)")
    figure.text(0.5, -0.06, "1 node, 128 ranks, 40 steps, multiLevel (2 4 16). AMD uProf data_access on one rank per NUMA domain (rank 0 left out: it also writes the output);\ncomputation only (MPI, UCX and Pstream left out). Bars: mean of 2 runs per side; dots: the 4 run pairs. Refills count demand misses only;\nhardware prefetches are in the L2 accesses. Instructions fall 4 % while DRAM refills fall 17 %: the same math with less data moved.", ha="center", fontsize=10.5)
    figure.tight_layout()
    save(figure, output, "fig17_counters")


def journey(output):
    methods = defaultdict(list)
    for row in read("decomposition_basic.csv"):
        methods[(int(row["nodes"]), row["method"])].append(float(row["s_per_step"]))
    final = defaultdict(list)
    for row in read("final_runs.csv"):
        final[(row["configuration"], int(row["nodes"]))].append(float(row["s_per_step"]))
    changes = changes_by_role()
    organisers = [float(row["s_per_step"]) for row in read("organiser_reference_aspire2a.csv") if row["method"] == "scotch" and row["nodes"] == "4" and row["setting"] == "defaults"]
    start = [float(row["s_per_step"]) for row in read("start_unpinned.csv")]
    steps = [("Start:\nhierarchical,\nbinding lost", start, CONTROL, None), ("+ CPU and\nNUMA pinning", methods[(4, "hierarchical")], BASIC, change(methods[(4, "hierarchical")], start)), ("+ scotch\n= Basic", final[("Basic", 4)], BASIC, change(methods[(4, "scotch")], methods[(4, "hierarchical")]))]
    for key, label in (("multiLevel", "+ multiLevel\n(4 2 4 16)"), ("0001", "+ 0001\nsolver copies"), ("0002", "+ 0002\nU together"), ("0003", "+ 0003\ndiscarded updates"), ("0004", "+ 0004 fused loops\n= Bonus")):
        steps.append((label, changes[(key, 4, "candidate")], BONUS, change(changes[(key, 4, "candidate")], changes[(key, 4, "control")])))
    figure, axis = plt.subplots(figsize=WIDE)
    axis.axhline(statistics.fmean(organisers), color=CONTROL, linestyle="--", linewidth=1.5)
    axis.text(len(steps) - 0.45, statistics.fmean(organisers) + 0.012, f"organisers' vanilla scotch, mean of {len(organisers)}: {statistics.fmean(organisers):.3f}", ha="right", fontsize=12, color="#555555")
    means = [statistics.fmean(values) for _, values, _, _ in steps]
    axis.plot(range(len(steps)), means, color="#555555", linewidth=1.2, zorder=2)
    for index, (label, values, color, percent) in enumerate(steps):
        axis.scatter(spread(values, index, 0.24), values, s=60, color=color, edgecolor="black", linewidth=0.5, zorder=3)
        axis.hlines(means[index], index - 0.22, index + 0.22, color=color, linewidth=2.5, zorder=3)
        axis.annotate(f"{means[index]:.3f}", (index, min(values)), textcoords="offset points", xytext=(0, -24), ha="center", fontsize=12, color=color, fontweight="bold")
        if percent is not None:
            axis.text(index - 0.45, (means[index - 1] + means[index]) / 2 + 0.035, f"{percent:+.1f} %", ha="left", fontsize=13, fontweight="bold", color=ACCENT)
    axis.set_xticks(range(len(steps)), [label for label, _, _, _ in steps], fontsize=11)
    axis.set_xlim(-0.5, len(steps) - 0.4)
    axis.set_ylim(2.5, 3.78)
    axis.set_ylabel("4 nodes, s / step (each point is one job)")
    figure.text(0.5, -0.06, f"Grey: where we started. Blue: Basic (unmodified v2512). Orange: Bonus. Red: each change against its own control, run in the same period; not added up.\nStart to Basic: {change(steps[2][1], start):+.1f} %. Basic {means[2]:.3f} (n = {len(steps[2][1])}) to Bonus {means[-1]:.3f} (n = {len(steps[-1][1])}): {change(steps[-1][1], steps[2][1]):+.1f} %. The y-axis does not start at 0.\nThe pinned hierarchical runs pinned with an LD_PRELOAD interposer; Basic pins with numactl and taskset, at the same speed.", ha="center", fontsize=11)
    figure.tight_layout()
    save(figure, output, "fig16_journey")


def box(axis, x, y, width, height, text, color, size=12, weight="normal"):
    axis.add_patch(FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0.01,rounding_size=0.015", facecolor=color, edgecolor="#333333", linewidth=1))
    axis.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=size, fontweight=weight, wrap=True)


def arrow(axis, start, end):
    axis.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, color="#333333", linewidth=1.3))


def node_layout(output):
    figure, axis = plt.subplots(figsize=WIDE)
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    axis.add_patch(Rectangle((0.01, 0.12), 0.98, 0.83, facecolor="#f7f7f7", edgecolor="black", linewidth=1.5))
    axis.text(0.02, 0.91, "One ASPIRE-2A CPU node: 2 × AMD EPYC 7713 (Zen 3), 128 cores, 8 NUMA domains", fontsize=14, fontweight="bold")
    for socket in range(2):
        x0 = 0.03 + socket * 0.48
        axis.add_patch(Rectangle((x0, 0.16), 0.46, 0.7, facecolor="white", edgecolor="#555555", linewidth=1.2))
        axis.text(x0 + 0.01, 0.82, f"socket {socket}", fontsize=13, fontweight="bold")
        for numa in range(4):
            domain = socket * 4 + numa
            y0 = 0.18 + (3 - numa) * 0.155
            axis.add_patch(Rectangle((x0 + 0.01, y0), 0.44, 0.14, facecolor="#e8f0fa", edgecolor="#3b6ea8", linewidth=1))
            first = domain * 16
            axis.text(x0 + 0.015, y0 + 0.115, f"NUMA {domain}: cores and ranks {first}–{first + 15}", fontsize=11)
            for ccx in range(2):
                cx = x0 + 0.02 + ccx * 0.215
                axis.add_patch(Rectangle((cx, y0 + 0.012), 0.205, 0.085, facecolor="#fff4e6", edgecolor="#d9822b", linewidth=0.8))
                axis.text(cx + 0.1025, y0 + 0.07, "8 cores", ha="center", fontsize=10)
                axis.text(cx + 0.1025, y0 + 0.03, "32 MB L3", ha="center", fontsize=10, color="#8a4b00")
    axis.text(0.5, 0.05, "Local rank r runs on core r (mpiexec --cpu-bind depth, re-pinned by the keeper) and allocates its memory on NUMA r/16 (numactl --membind).\nBonus multiLevel follows the same tree: (nodes, 2 sockets, 4 NUMA domains, 16 cores) = (4 2 4 16) on 4 nodes.", ha="center", fontsize=12)
    save(figure, output, "fig11_node_layout")


def pipeline(output):
    figure, axis = plt.subplots(figsize=(12.8, 5.6))
    figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    steps = [
        ("git push /\nmanual run", "#e8e8e8"),
        ("select build\n(reuse if build\ninputs unchanged)", "#e8f0fa"),
        ("build\nOpenFOAM\n(1-node job)", "#e8f0fa"),
        ("prepare case\n(decomposePar,\ncached)", "#e8f0fa"),
        ("run job\nAllrun chain\n+ simpleFoam", "#fff4e6"),
        ("official parser\n+ Cd file", "#e9f5ec"),
        ("archive raw\nrecords +\nmetrics DB", "#e9f5ec"),
    ]
    width = 0.116
    gap = (0.98 - len(steps) * width) / (len(steps) - 1)
    for index, (text, color) in enumerate(steps):
        x = 0.01 + index * (width + gap)
        box(axis, x, 0.5, width, 0.25, text, color, size=11)
        if index:
            arrow(axis, (x - gap + 0.004, 0.625), (x - 0.004, 0.625))
    axis.text(0.5, 0.9, "One commit = one tracked experimental condition; every run is started by GitHub Actions", ha="center", fontsize=14, fontweight="bold")
    notes = [
        "Each condition is a commit (compiler flag, decomposition, patch), so every result can be traced to its exact scripts.",
        "Build archives and decomposed cases are reused only when their inputs are identical; nothing is shared between clusters.",
        "Profilers run only in separate diagnostic jobs; nothing is measured inside the timed solver run of a benchmark.",
        "Several runners submit jobs in parallel, so control and candidate runs are measured in the same period.",
    ]
    for index, note in enumerate(notes):
        axis.text(0.02, 0.36 - index * 0.085, "• " + note, fontsize=12)
    save(figure, output, "fig12_pipeline")


def solver_flow(output):
    figure, axis = plt.subplots(figsize=(12.8, 7.2))
    figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    prep = ["decomposePar", "restore0Dir", "renumberMesh", "potentialFoam", "applyBoundaryLayer"]
    axis.text(0.01, 0.955, "Preparation (not timed)", fontsize=13, fontweight="bold")
    width = 0.168
    gap = (0.98 - len(prep) * width) / (len(prep) - 1)
    for index, name in enumerate(prep):
        x = 0.01 + index * (width + gap)
        box(axis, x, 0.84, width, 0.075, name, "#eeeeee", size=11)
        if index:
            arrow(axis, (x - gap + 0.003, 0.8775), (x - 0.003, 0.8775))
    axis.text(0.01, 0.765, "simpleFoam: one SIMPLE iteration (timed: steps 2 to N)", fontsize=13, fontweight="bold")
    stages = [
        ("U equation\nassemble:\nconvection,\nLaplacian, gradient", "0003  0004"),
        ("U solve\nsmoothSolver +\nGaussSeidel,\n3 components", "0001  0002"),
        ("p equation\nassemble, flux,\ncontinuity error", "0003"),
        ("p solve\nGAMG V-cycles\n(halo exchange\n+ Allreduce)", "0001"),
        ("k, omega\nassemble + solve\n(kOmegaSST)", "0001  0003\n0004"),
        ("function objects\nforces →\ncoefficient.dat", ""),
    ]
    width = 0.143
    gap = (0.98 - len(stages) * width) / (len(stages) - 1)
    for index, (text, patches) in enumerate(stages):
        x = 0.01 + index * (width + gap)
        box(axis, x, 0.5, width, 0.215, text, "#e8f0fa" if patches else "#eeeeee", size=11)
        axis.text(x + width / 2, 0.47, patches, ha="center", va="top", fontsize=13, fontweight="bold", color=BONUS)
        if index:
            arrow(axis, (x - gap + 0.003, 0.6075), (x - 0.003, 0.6075))
    legend = [
        "0001  no temporary residual field or copy in smoothSolver and GAMG",
        "0002  three U components smoothed in one pass over the shared matrix",
        "0003  no boundary update where only internal values are used; one-pass convection coefficients",
        "0004  face interpolation and face products formed inside the summation loops",
    ]
    axis.text(0.01, 0.31, "Bonus patches (same expressions and order; bit-identical coefficient.dat):", fontsize=12, fontweight="bold")
    for index, line in enumerate(legend):
        axis.text(0.02, 0.245 - index * 0.06, line, fontsize=12, family="monospace")
    save(figure, output, "fig13_solver_flow")


def storage_flow(output):
    figure, axis = plt.subplots(figsize=(12.8, 6.6))
    figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    columns = [(0.01, "GitHub Actions runner\n(team server)", "#eeeeee"), (0.345, "ASPIRE-2A login node\n/scratch (Lustre, shared)", "#e8f0fa"), (0.68, "Compute nodes\n$TMPDIR (node-local)", "#fff4e6")]
    for x, title, color in columns:
        axis.add_patch(Rectangle((x, 0.16), 0.31, 0.74, facecolor=color, edgecolor="#555555", linewidth=1.2))
        axis.text(x + 0.155, 0.85, title, ha="center", va="center", fontsize=13, fontweight="bold")
    runner = ["start build, case and run jobs\n(ssh + qsub)", "after the job: pack the run,\ncopy it to the archive,\nsend metrics to the database"]
    scratch = ["mesh archive (3.2 GB)", "build archive per build\n(OpenFOAM tree, flags, hashes)", "decomposed case per\nbuild and decomposition", "run directory per run\n(logs, results, records)"]
    compute = ["unpack the OpenFOAM build", "copy the decomposed case,\nrestore0Dir", "Allrun chain + simpleFoam:\nall case I/O stays local\n(-hostRoots, -ioRanks)", "write logs and\ncoefficient.dat back"]
    for index, text in enumerate(runner):
        box(axis, 0.035, 0.6 - index * 0.33, 0.26, 0.17, text, "white", size=11)
    for index, text in enumerate(scratch):
        box(axis, 0.37, 0.68 - index * 0.155, 0.26, 0.12, text, "white", size=11)
    for index, text in enumerate(compute):
        box(axis, 0.705, 0.68 - index * 0.155, 0.26, 0.12, text, "white", size=11)
    arrow(axis, (0.295, 0.685), (0.345, 0.685))
    arrow(axis, (0.63, 0.585), (0.705, 0.74))
    arrow(axis, (0.63, 0.43), (0.705, 0.585))
    arrow(axis, (0.705, 0.275), (0.63, 0.275))
    arrow(axis, (0.37, 0.275), (0.295, 0.355))
    axis.text(0.5, 0.07, "Home is not used for runs. /dev/shm is noexec, so it only holds the compiler cache during builds.\nMeasured file I/O inside the timed steps: about 0.01 % of the run time (Issue #46).", ha="center", fontsize=11.5)
    save(figure, output, "fig15_storage_flow")


def environment_tables(output):
    environment_rows = [
        ["OpenFOAM", "v2512 rebuilt from the official source: GCC 11.2, -O3, AOCL-LibM, label 32, double precision. PBS build job, 16 cores, compiler cache on /scratch", "Same speed as the site module; we know exactly what ran; the Bonus patches need a build anyway"],
        ["MPI", "Cray MPICH 8.1.15 over UCX (craype-network-ucx, cray-mpich-ucx/8.1.15)", "The default OFI provider died with SIGBUS at MPI_Finalize on 2 and 4 nodes in our September tests; UCX completed every run"],
        ["Launch and placement", "PALS mpiexec --cpu-bind depth -d 1; numactl --membind per rank; a taskset watcher per node", "The launcher's binding is removed during MPI_Init (slide 6)"],
        ["/scratch (Lustre, shared)", "Mesh, build archives, decomposed cases, run directories", "Shared by the login node and all compute nodes"],
        ["$TMPDIR (node-local)", "OpenFOAM tree and the decomposed case on every node; all solver file I/O", "No case I/O on Lustre while the solver runs"],
    ]
    table(output, "tab05_environment", ["Item", "What we use", "Why"], environment_rows, [0.18, 0.44, 0.38])
    profiling_rows = [
        ["Official metric", "Every benchmark run; no profiler attached", "Average wall-clock time per step (steps 2 to N)", "The result; 3 or more runs per condition"],
        ["CrayPAT 22.04, pat_run -g mpi", "Separate 4-node, 40-step diagnostic runs; simpleFoam only, after a warm-up step", "Time, calls and bytes of every MPI call, per rank", "MPI is about 19 % of the time, mostly waiting in Allreduce and Waitall"],
        ["eu-stack call stacks", "The same diagnostic runs, 48 ranks (slow, median, one per NUMA domain)", "Which solver phase each rank is in, and whether it is inside MPI", "Phase shares; found the copies (0001) and discarded exchanges (0003)"],
        ["AMD uProf 5.3, timer hotspots", "Separate profile runs, one rank per NUMA domain", "CPU time per function", "Copies and zero-fills were large in September (18.8 %)"],
        ["/proc sampler in the job", "Diagnostic jobs", "CPU affinity, NUMA page placement, I/O bytes and waits per rank", "Binding lost during MPI_Init; solver I/O negligible"],
        ["IMB-MPI1", "After the solver in every benchmark run", "Ping-pong bandwidth and Allreduce latency", "A network baseline for each job"],
    ]
    table(output, "tab06_profiling", ["Tool", "When", "What it collects", "What it showed"], profiling_rows, [0.2, 0.28, 0.26, 0.26])


def table(output, name, header, rows, widths, fontsize=12):
    width_in = 12.8
    wraps = [max(8, int(width * width_in * 72 / (fontsize * 0.62)) - 3) for width in widths]
    head = ["\n".join(textwrap.wrap(text, limit)) for text, limit in zip(header, wraps)]
    cells = [["\n".join(textwrap.wrap(str(value), limit)) for value, limit in zip(row, wraps)] for row in rows]
    line_in = fontsize * 1.3 / 72
    heights = [max(text.count("\n") + 1 for text in head) * line_in + 0.16] + [max(text.count("\n") + 1 for text in row) * line_in + 0.16 for row in cells]
    figure = plt.figure(figsize=(width_in, sum(heights)))
    axis = figure.add_axes([0, 0, 1, 1])
    axis.axis("off")
    rendered = axis.table(cellText=cells, colLabels=head, colWidths=widths, cellLoc="left", colLoc="left", bbox=[0, 0, 1, 1])
    rendered.auto_set_font_size(False)
    rendered.set_fontsize(fontsize)
    for (row, column), cell in rendered.get_celld().items():
        cell.set_edgecolor("#bbbbbb")
        cell.set_height(heights[row] / sum(heights))
        cell.PAD = 0.012 / widths[column]
        if row == 0:
            cell.set_facecolor("#2f4f6f")
            cell.get_text().set_color("white")
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("white" if row % 2 else LIGHT)
    save(figure, output, name)


def tables(output):
    runs = defaultdict(list)
    for row in read("final_runs.csv"):
        runs[(row["configuration"], int(row["nodes"]))].append(float(row["s_per_step"]))
    rows = []
    for nodes in (1, 2, 4):
        basic = runs[("Basic", nodes)]
        bonus = runs[("Bonus", nodes)]
        rows.append([f"{nodes} ({nodes * 128} ranks, {dict([(1, 40), (2, 80), (4, 150)])[nodes]} steps)", f"{statistics.fmean(basic):.3f}  (n={len(basic)}, range {(max(basic) - min(basic)) / statistics.fmean(basic) * 100:.2f} %)", f"{statistics.fmean(bonus):.3f}  (n={len(bonus)}, range {(max(bonus) - min(bonus)) / statistics.fmean(bonus) * 100:.2f} %)", f"{change(bonus, basic):+.2f} %", f"{statistics.fmean(basic) / statistics.fmean(bonus):.3f} ×"])
    table(output, "tab01_final_results", ["Nodes", "Basic s/step (mean)", "Bonus s/step (mean)", "Bonus vs Basic", "Speedup"], rows, [0.22, 0.27, 0.27, 0.13, 0.11])
    f3_rows = [
        ["1 (40)", "25682093", "25709674, 25706195, 25709663", "bit-identical (SHA-256 36d35283…)", "0.43827636195043501"],
        ["2 (80)", "25682094", "25709665, 25706306, 25709682", "bit-identical (SHA-256 2a49a26d…)", "0.32285935413723610"],
        ["4 (150)", "25682211", "25706165, 25706131, 25706125", "bit-identical (SHA-256 8952a056…)", "0.29138777754153217"],
    ]
    table(output, "tab02_f3_check", ["Nodes (steps)", "Pre-change baseline (PBS job)", "Bonus runs (PBS jobs)", "coefficient.dat", "Cd at last step"], f3_rows, [0.12, 0.19, 0.25, 0.25, 0.19])
    data = changes_by_role()
    measured = {key: f"{change(data[(key, 4, 'candidate')], data[(key, 4, 'control')]):+.2f} %  ({len(data[(key, 4, 'control')])} v {len(data[(key, 4, 'candidate')])})" for key, _ in CHANGES}
    change_rows = [
        ["multiLevel decomposition", "Partition follows node / socket / NUMA / core", "Decomposition only; unmodified source", measured["multiLevel"]],
        ["0001 solver copies", "Temporary residual field and its copy (smoothSolver); copy + subtract (GAMG)", "Same function, same per-cell subtraction", measured["0001"]],
        ["0002 U components together", "Three passes over the shared matrix arrays for Ux, Uy, Uz", "Components are independent; each sees the same operations in the same order", measured["0002"]],
        ["0003 discarded boundary updates", "Boundary values and processor exchanges that six callers threw away; extra face loops in convection", "Internal values from the same loop; fused loop uses the same expressions and order", measured["0003"]],
        ["0004 fused gradient and products", "Interpolated surface field and product field built before summation", "Same face expressions, summed in the same face order", measured["0004"]],
    ]
    table(output, "tab03_bonus_changes", ["Change", "What it removes", "Why the result is the same", "4 nodes (runs before v after)"], change_rows, [0.19, 0.33, 0.31, 0.17])
    rejected_rows = [
        ["Compiler: -march=znver3, AOCC 5.0, -O2, LTO (Basic)", "Within ±0.1 % of the control", "Code generation does not limit the run time"],
        ["Scotch tree coefficients domains / domainWeights (Basic)", "−0.82 % at 4 nodes, none at 1 and 2 nodes", "Fewer cross-node faces, more faces in total; below our 1 % threshold"],
        ["Weighted multiLevel cells (Bonus)", "+2.2 % (weight ×2), +6.1 % (×12)", "Static weights unbalance the cell counts; even cell counts matter most"],
        ["METIS two-constraint partition (Bonus)", "+1.46 %", "Better face balance, but 18 % more processor faces"],
        ["OpenFOAM comm switches (Basic)", "No gain; commsType scheduled crashed in GAMG", "MPI time is mostly waiting for slower ranks"],
        ["SMT, 2 ranks per core (Basic)", "About 5.7 × slower (stopped after 22 steps)", "More ranks on the same cores do not help this solver"],
        ["Overlap of halo exchange and computation", "Under 1 % available (stack samples)", "Led to removing discarded exchanges instead (0003)"],
        ["File I/O in the timed steps", "About 0.01 % of the run time", "Not a factor"],
    ]
    table(output, "tab04_not_adopted", ["Candidate (tier)", "Result (4 nodes unless noted)", "What we learned"], rejected_rows, [0.36, 0.3, 0.34])


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: figures.py OUTPUT_DIR")
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    for make in (final_runs, scaling, changes_4node, changes_by_nodes, decomposition, pinning, compiler, variability, mpi_breakdown, rank_compute, reference_comparison, journey, counters, node_layout, pipeline, solver_flow, storage_flow, tables, environment_tables):
        make(output)


if __name__ == "__main__":
    main()
