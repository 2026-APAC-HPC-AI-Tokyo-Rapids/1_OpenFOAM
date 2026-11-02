# /// script
# requires-python = ">=3.11"
# ///
"""Collect the renumberMesh comparison of renumber-genkai.pjm into one CSV and print a summary.

usage: uv run --no-project python -I analyse.py <results dir copied from Genkai> <output csv>

One row per simpleFoam run: the round, the method, the iterations, the PJM job and host, the time per step as the case's
own wallClockTimeStatistics prints it (the mean over steps 2 to N, the official metric), Cd at the last step, and the band
and profile that renumberMesh reported for the method's order (band the largest over the 448 subdomains, profile their
sum). The summary gives each method's mean and SD over the complete rounds, and its change against the default
Cuthill-McKee within each round, whose runs shared the nodes of one job.
"""

import csv
import re
import statistics
import sys
from pathlib import Path

RESULTS, OUT = Path(sys.argv[1]), Path(sys.argv[2])
METHODS = ["CuthillMcKee", "RCM", "none", "spring", "random"]
CELLS = 65334765


def after_renumbering(method):
    """band and profile of the new order: the last pair in the method's renumberMesh log."""
    text = (RESULTS / f"{method}-renumberMesh.log").read_text(encoding="utf-8")
    bands, profiles = re.findall(r"band\s+:\s+(\d+)", text), re.findall(r"profile\s+:\s+(\d+)", text)
    return int(bands[-1]), int(profiles[-1])


def last_cd(run):
    """Iterations and Cd at the last step of a run, from its forceCoeffs coefficient.dat."""
    lines = next((RESULTS / f"{run}-postProcessing").glob("**/coefficient*.dat")).read_text(encoding="utf-8").splitlines()
    header = next(line for line in lines if line.startswith("#") and "Cd" in line).lstrip("#").split()
    last = [line.split() for line in lines if line.strip() and not line.startswith("#")][-1]
    return int(float(last[0])), float(last[header.index("Cd")])


rows = []
for log in sorted(RESULTS.glob("*-simpleFoam.log")):
    run, method = re.match(r"(round\d+)-(.+)-simpleFoam\.log", log.name).groups()
    mean = float(re.findall(r"Average wall-clock time per time step = ([0-9.eE+-]+)", log.read_text(encoding="utf-8"))[-1])
    job, host = (RESULTS / f"{run}-{method}-job.txt").read_text(encoding="utf-8").split()
    iterations, cd = last_cd(f"{run}-{method}")
    band, profile = after_renumbering(method)
    rows.append({"run": run, "method": method, "iterations": iterations, "pjm_job": job, "host": host, "s_per_step": f"{mean:.6f}", "cd": f"{cd:.17g}", "band": band, "profile": profile})
rows.sort(key=lambda row: (int(row["run"][5:]), METHODS.index(row["method"])))
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

by = {(row["method"], row["run"]): row for row in rows}
rounds = sorted({row["run"] for row in rows if all((m, row["run"]) in by for m in METHODS)}, key=lambda r: int(r[5:]))
print(f"{len(rows)} runs, complete rounds: {', '.join(rounds)}")
print(f"{'method':<14}{'s/step':>9}{'SD %':>7}{'vs CM %':>9}{'each round vs CM %':>32}{'band':>9}{'profile/cell':>14}{'Cd(40)':>11}")
for method in METHODS:
    times = [float(by[(method, r)]["s_per_step"]) for r in rounds]
    control = [float(by[("CuthillMcKee", r)]["s_per_step"]) for r in rounds]
    paired = [(t / c - 1) * 100 for t, c in zip(times, control)]
    mean = statistics.fmean(times)
    sd = statistics.stdev(times) / mean * 100 if len(times) > 1 else float("nan")
    first = by[(method, rounds[0])]
    print(f"{method:<14}{mean:9.4f}{sd:7.2f}{(mean / statistics.fmean(control) - 1) * 100:+9.2f}{' '.join(f'{p:+.2f}' for p in paired):>32}{first['band']:>9}{first['profile'] / CELLS:>14.0f}{float(first['cd']):11.6f}")
