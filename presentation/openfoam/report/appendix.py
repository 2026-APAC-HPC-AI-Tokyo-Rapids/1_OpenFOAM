"""Writes Appendix A of the technical report (every job behind every comparison) from the repo's presentation data, so that
no value or run ID is typed by hand. Also prints the largest Cd difference between the Bonus and its pre-change baseline over
all 150 iterations on 4 nodes."""
import csv
import statistics as st
import sys
from pathlib import Path

D = Path(sys.argv[1])
OUT = Path(sys.argv[2])


def rows(name):
    with open(D / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fmt_group(values, ids):
    return "<br>".join(f"{v:.4f} ({i})" for v, i in zip(values, ids))


def pc(ratio_minus_one):
    """A change in per cent with one decimal and a real minus sign, as in the rest of the submission."""
    return f"{ratio_minus_one * 100:+.1f}%".replace("-", "−")


def mean_sd(values):
    m = st.mean(values)
    sd = f"{st.stdev(values) / m * 100:.2f}%" if len(values) > 1 else ""
    return f"{m:.4f}", sd


lines = []
w = lines.append

w("### A.1 Basic: every 4-node job of every step")
w("")
w("Each cell lists the jobs as s/step (GitHub Actions run ID). Mean and SD are over the jobs of the row.")
w("")
w("| Group | Jobs: s/step (Actions run ID) | Mean | SD |")
w("|---|---|---:|---:|")
base = [r for r in rows("baseline_runs.csv") if r["nodes"] == "4" and r["configuration"].startswith("baseline")]
pin = rows("pinning.csv")
dec = rows("decomposition_basic.csv")
su = rows("start_unpinned.csv")
ab = rows("changes_ab.csv")


def row(label, values, ids):
    m, sd = mean_sd(values)
    w(f"| {label} | {fmt_group(values, ids)} | {m} | {sd} |")


row("Our Baseline: `hierarchical` (16 8 4), launcher binding only", [float(r["s_per_step"]) for r in base], [r["actions_run"] for r in base])
groups = [
    ("`scotch`, not pinned (PALS `--cpu-bind` and `--mem-bind`; or `--cpu-bind` only with the case prepared in its own job)", lambda c: c.startswith("PALS --cpu-bind")),
    ("`scotch`, CPU only (watcher with `taskset`)", lambda c: c.startswith("taskset keeper only")),
    ("`scotch`, memory only (`numactl --membind`)", lambda c: c.startswith("numactl --membind only")),
    ("`scotch`, CPU and memory (`numactl --membind` + watcher, as in Basic)", lambda c: c.startswith("numactl --membind + taskset")),
    ("`scotch`, CPU and memory with an `LD_PRELOAD` re-pin after `MPI_Init` (not used in Basic)", lambda c: c.startswith("LD_PRELOAD")),
    ("`scotch`, PALS `--mem-bind local` + watcher", lambda c: c.startswith("PALS --mem-bind")),
]
for label, pred in groups:
    g = [r for r in pin if pred(r["configuration"])]
    row(label, [float(r["s_per_step"]) for r in g], [r["actions_run"] for r in g])
row("`hierarchical` (16 8 4), not pinned, in turns with the two rows below", [float(r["s_per_step"]) for r in su], [r["actions_run"] for r in su])
for method, label in (("hierarchical", "`hierarchical` (16 8 4), pinned (`LD_PRELOAD` re-pin)"), ("scotch", "`scotch`, pinned (`LD_PRELOAD` re-pin), in turns with the row above")):
    g = [r for r in dec if r["nodes"] == "4" and r["method"] == method]
    row(label, [float(r["s_per_step"]) for r in g], [r["actions_run"] for r in g])
for role, label in (("control", "plain `scotch`, pinned: control of the node tree"), ("candidate", "**Basic**: `scotch` on the node tree, pinned (in turns with the row above)")):
    g = [r for r in ab if r["change"] == "mapping" and r["role"] == role]
    row(label, [float(r["s_per_step"]) for r in g], [r["actions_run"] for r in g])
w("")

w("### A.2 `hierarchical` against `scotch` at 1, 2 and 4 nodes, both pinned, in turns")
w("")
w("| Nodes | `hierarchical`: s/step (Actions run ID) | `scotch`: s/step (Actions run ID) | Change |")
w("|---:|---|---|---:|")
for n in ("1", "2", "4"):
    h = [r for r in dec if r["nodes"] == n and r["method"] == "hierarchical"]
    s = [r for r in dec if r["nodes"] == n and r["method"] == "scotch"]
    hv = [float(r["s_per_step"]) for r in h]
    sv = [float(r["s_per_step"]) for r in s]
    w(f"| {n} | {fmt_group(hv, [r['actions_run'] for r in h])} | {fmt_group(sv, [r['actions_run'] for r in s])} | {pc(st.mean(sv) / st.mean(hv) - 1)} |")
w("")

w("### A.3 Bonus: every 4-node comparison of a change against the configuration before it")
w("")
w("Each candidate's jobs became the control of the next change, so the same run IDs appear twice. The last row group is the final")
w("measurement, in which the Bonus and the first four changes (`fa4f5b0`) ran in turns at every node count.")
w("")
w("| Change (commit) | Control: s/step (Actions run ID) | Candidate: s/step (Actions run ID) | Change | Every candidate job faster |")
w("|---|---|---|---:|---|")
names = {
    "multiLevel": "`multiLevel` (4 2 4 16), unmodified source (`2eacff5`, `7325738`) against plain `scotch`",
    "0001": "+ 0001 (`e2730db`)",
    "0002": "+ 0002 (`57b6567`)",
    "0003": "+ 0003 (`20d285b`)",
    "0004": "+ 0004 (`fa4f5b0`)",
    "0006-0010": "+ 0006, 0008, 0009, 0010 (`4b1ed6a`)",
    "0011": "+ 0011 (`45a4e7b`)",
    "0012": "+ 0012 (`f99771e`)",
    "0013-0015": "+ 0013, 0014, 0015 (`af6b217`), a few days after its control",
    "0016": "+ 0016 (`1bc34b9`, the Bonus), a few days after its control",
}
for ch, label in names.items():
    c = [r for r in ab if r["change"] == ch and r["nodes"] == "4" and r["role"] == "control"]
    k = [r for r in ab if r["change"] == ch and r["nodes"] == "4" and r["role"] == "candidate"]
    cv = [float(r["s_per_step"]) for r in c]
    kv = [float(r["s_per_step"]) for r in k]
    change = pc(st.mean(kv) / st.mean(cv) - 1)
    w(f"| {label} | {fmt_group(cv, [r['actions_run'] for r in c])} | {fmt_group(kv, [r['actions_run'] for r in k])} | {change} | {'yes' if max(kv) < min(cv) else 'no'} |")
for n in ("1", "2", "4"):
    c = [r for r in ab if r["change"] == "0006-0016" and r["nodes"] == n and r["role"] == "control"]
    k = [r for r in ab if r["change"] == "0006-0016" and r["nodes"] == n and r["role"] == "candidate"]
    cv = [float(r["s_per_step"]) for r in c]
    kv = [float(r["s_per_step"]) for r in k]
    change = pc(st.mean(kv) / st.mean(cv) - 1)
    w(f"| Final measurement, {n} node{'s' if n != '1' else ''}: Bonus (`1bc34b9`) against `fa4f5b0` | {fmt_group(cv, [r['actions_run'] for r in c])} | {fmt_group(kv, [r['actions_run'] for r in k])} | {change} | {'yes' if max(kv) < min(cv) else 'no'} |")
w("")

w("### A.4 The submitted Basic and Bonus jobs")
w("")
w("These are the jobs of `scaling/scaling.txt`; `*` marks the job whose logs are in `results/<n>node/` (Basic) or")
w("`bonus/results/<n>node/` (Bonus). Every job of a configuration and node count wrote a byte-identical `coefficient.dat`.")
w("")
w("| Configuration | Nodes | PBS job | Actions run ID | s/step | Cd at the last step |")
w("|---|---:|---|---|---:|---|")
star = {"25837534.pbs101", "25837416.pbs101", "25827680.pbs101", "25988437.pbs101", "25988421.pbs101", "25988381.pbs101"}
for r in rows("final_runs.csv"):
    mark = " \\*" if r["pbs_job"] in star else ""
    w(f"| {r['configuration']} | {r['nodes']} | {r['pbs_job']}{mark} | {r['actions_run']} | {float(r['s_per_step']):.6f} | {r['cd']} |")
w("")

w("### A.5 The placement experiment (section 7.2)")
w("")
w("| Configuration | Placement | PBS job | Actions run ID | s/step | SHA-256 of `coefficient.dat` (first 16) |")
w("|---|---|---|---|---:|---|")
label = {"Basic": "Basic before the node mapping", "baseline": "`multiLevel` without the patches", "Bonus": "`multiLevel` with the first four changes"}
for r in rows("memory_placement.csv"):
    w(f"| {label[r['configuration']]} | {r['placement']} | {r['pbs_job']} | {r['actions_run']} | {float(r['s_per_step']):.4f} | `{r['coefficient_sha256_16']}` |")
w("")

w("### A.6 Compiler options against GCC `-O3` (section 6.8)")
w("")
w("| Option | Jobs: s/step (Actions run ID) | Mean |")
w("|---|---|---:|")
comp = rows("compiler_options.csv")
for opt in dict.fromkeys(r["option"] for r in comp):
    g = [r for r in comp if r["option"] == opt]
    v = [float(r["s_per_step"]) for r in g]
    w(f"| {opt} | {fmt_group(v, [r['actions_run'] for r in g])} | {st.mean(v):.4f} |")
w("")

w("### A.7 The official runs (organisers' jobs, from the ASPIRE-2A application notes)")
w("")
w("| Method | Nodes | Run | Setting | PBS jobs | s/step | Cd at the last step |")
w("|---|---:|---|---|---|---:|---|")
for r in rows("organiser_reference_aspire2a.csv"):
    w(f"| `{r['method']}` | {r['nodes']} | {r['run']} | {r['setting']} | {r['pbs_jobs']} | {float(r['s_per_step']):.4f} | {float(r['cd']):.17f} |")
w("")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

cd = rows("cd_iterations_4node.csv")
b = {int(r["iteration"]): float(r["cd"]) for r in cd if r["configuration"] == "Bonus"}
p = {int(r["iteration"]): float(r["cd"]) for r in cd if r["configuration"] == "Bonus without its source changes"}
worst = max(abs(b[i] / p[i] - 1) for i in b)
at = max(b, key=lambda i: abs(b[i] / p[i] - 1))
print(f"largest relative Cd difference Bonus vs pre-change baseline over 150 iterations: {worst:.3e} at iteration {at}")
