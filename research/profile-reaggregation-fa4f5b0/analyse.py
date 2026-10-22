"""Analyse CrayPAT/eu-stack stack samples of simpleFoam (profile53).

usage: uv run -q --no-project python -I profile53_analyse.py <stack-samples-dir> <out.md>

Sample file format (one file per sampled rank):
    === round=<n> t=<epoch seconds>
    TID <tid>:
    #0  0x<addr> <symbol>          (innermost / leaf frame)
    #1  0x<addr> <symbol>
    ...
    #k  0x<addr> main
    #k+1 ... __libc_start_main
    #k+2 ... _start
A round may instead carry an "eu-stack: ... " error line and no frames.
"""
import collections
import os
import re
import sys

ROOT = sys.argv[1]
OUT = sys.argv[2]

HDR = re.compile(r"^=== round=(\d+) t=([\d.]+)")
FRM = re.compile(r"^#(\d+)\s+0x([0-9a-f]+)\s+(.*)$")


# --------------------------------------------------------------------------- symbol normalisation
def strip_args(sym):
    """Drop the parameter list and the return type of a demangled C++ symbol."""
    s = sym
    if s.startswith("non-virtual thunk to "):
        s = s[len("non-virtual thunk to "):]
    for a, b in (("operator()", "operatorCALL"), ("operator<<", "operatorSHL"), ("operator>>", "operatorSHR"),
                 ("operator<=", "operatorLE"), ("operator>=", "operatorGE"), ("operator<", "operatorLT"),
                 ("operator>", "operatorGT")):
        s = s.replace(a, b)
    depth = 0
    cut = len(s)
    last_space = -1
    for i, c in enumerate(s):
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
        elif depth == 0 and c == "(":
            cut = i
            break
        elif depth == 0 and c == " ":
            last_space = i
    s = s[:cut]
    if last_space >= 0 and last_space < cut:
        s = s[last_space + 1:]
    return s


SUBS = [
    ("Foam::", ""),
    ("Vector<double>", "vector"), ("Tensor<double>", "tensor"), ("SymmTensor<double>", "symmTensor"),
    ("outerProduct<vector, double>::type", "vector"), ("outerProduct<vector, vector>::type", "tensor"),
    ("innerProduct<vector, tensor>::type", "vector"), ("typeOfSum<double, double>::type", "double"),
    ("typeOfSum<vector, vector>::type", "vector"), ("typeOfMag<double>::type", "double"),
    ("scalarProduct<double, double>::type", "double"),
    ("GeometricField<double, fvPatchField, volMesh>", "volScalarField"),
    ("GeometricField<vector, fvPatchField, volMesh>", "volVectorField"),
    ("GeometricField<tensor, fvPatchField, volMesh>", "volTensorField"),
    ("GeometricField<symmTensor, fvPatchField, volMesh>", "volSymmTensorField"),
    ("GeometricField<double, fvsPatchField, surfaceMesh>", "surfaceScalarField"),
    ("GeometricField<vector, fvsPatchField, surfaceMesh>", "surfaceVectorField"),
    ("kOmegaSSTBase<eddyViscosity<RASModel<IncompressibleTurbulenceModel<transportModel> > > >", "kOmegaSSTBase<...>"),
    ("IncompressibleTurbulenceModel<transportModel>", "IncompressibleTurbulenceModel<...>"),
    ("fv::gradientLimiters::minmod", "minmod"),
    (" >", ">"),
]


def display(short):
    s = short
    for a, b in SUBS:
        s = s.replace(a, b)
    return s


# --------------------------------------------------------------------------- parsing
class Sample:
    __slots__ = ("rank", "rnd", "t", "frames", "err", "main_idx", "cls")

    def __init__(self, rank, rnd, t):
        self.rank, self.rnd, self.t = rank, rnd, t
        self.frames = []  # list of (addr, raw_symbol, short, disp), innermost first
        self.err = None
        self.main_idx = None
        self.cls = None


def parse_file(path, rank):
    samples = []
    cur = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = HDR.match(line)
            if m:
                cur = Sample(rank, int(m.group(1)), float(m.group(2)))
                samples.append(cur)
                continue
            if cur is None:
                continue
            if line.startswith("eu-stack:"):
                cur.err = line
                continue
            m = FRM.match(line)
            if m:
                short = strip_args(m.group(3))
                cur.frames.append((int(m.group(2), 16), m.group(3), short, display(short)))
    return samples


samples = []
for name in sorted(os.listdir(ROOT)):
    m = re.match(r"rank-(\d+)\.txt$", name)
    if m:
        samples.extend(parse_file(os.path.join(ROOT, name), int(m.group(1))))
ranks = sorted({s.rank for s in samples})

# --------------------------------------------------------------------------- classification
TEARDOWN_RE = re.compile(r"__run_exit_handlers|__pat_exit|_dl_fini|::~staticFvMesh|::~fvMesh|::~Time\b")
STARTUP_RE = re.compile(r"fvMesh::fvMesh\(|polyMesh::polyMesh\(|Time::Time\(|argList::argList|::readField\(|readFields\(|decompos|"
                        r"turbulenceModel::New|RASModel<.*>::New|pressureReference::pressureReference|"
                        r"singlePhaseTransportModel::singlePhaseTransportModel|functionObjectList::read|IOobjectList::IOobjectList|"
                        r"createFields|fvSchemes::fvSchemes|fvSolution::fvSolution|::readMesh")

for s in samples:
    if s.err is not None or not s.frames:
        s.cls = "error"
        continue
    syms = [f[1] for f in s.frames]
    if "main" not in syms:
        s.cls = "exit" if TEARDOWN_RE.search(" ".join(syms)) else "nomain-truncated"
        continue
    s.main_idx = syms.index("main")
    if TEARDOWN_RE.search(" ".join(syms)):
        s.cls = "teardown"
    elif STARTUP_RE.search(" ".join(syms)):
        s.cls = "startup"
    else:
        s.cls = "inloop"

inloop = [s for s in samples if s.cls == "inloop"]
N = len(inloop)
cls_counts = collections.Counter(s.cls for s in samples)


def pct(n):
    return 100.0 * n / N


def top_frame(s):
    """Frame directly above main (the step-phase entry) as display name, plus main's return address."""
    if s.main_idx == 0:
        return "<main self>", s.frames[0][0]
    return s.frames[s.main_idx - 1][3], s.frames[s.main_idx][0]


# --------------------------------------------------------------------------- MPI detection
MPI_RE = re.compile(r"^(MPI_|PMPI_|MPIR_|MPIDI_|MPIDIG_|MPID_|MPIC_|MPIU_|MPL_|ucp_|uct_|ucs_|ucm_|mlx5_|ibv_|fi_|cxi|_pmi|PMI|"
                    r"get_sw_cqe|opal_|ompi_|hwloc|pthread_spin|__pat_mpi)")


def is_mpi(frame):
    return bool(MPI_RE.match(frame[1]))


def mpi_top_idx(s):
    """Index of the MPI frame closest to the OpenFOAM caller (highest index matching), or None."""
    idx = None
    for i, f in enumerate(s.frames[: s.main_idx]):
        if is_mpi(f):
            idx = i
    return idx


# --------------------------------------------------------------------------- phase labelling (C)
# Labels of the frames directly under main.  Call-site addresses (return address inside main) are listed in the
# output so the per-address labels below can be audited; fvc::grad<double> and operator* occur at two call sites.
PHASE_BY_CALLEE = {
    "fvm::div<vector>": "UEqn assembly",
    "IncompressibleTurbulenceModel<...>::divDevReff": "UEqn assembly",
    "fvMatrix<vector>::relax": "UEqn assembly",
    "operator==<vector>": "UEqn assembly",
    "operator+<vector>": "UEqn assembly",
    "fvMatrix<vector>::operator+=": "UEqn assembly",
    "fv::optionList::source<vector>": "UEqn assembly",
    "fv::optionList::constrain<vector>": "UEqn assembly",
    "operator-<vector, vector, fvPatchField, volMesh>": "U/phi correction",
    "operator-<double, double, fvsPatchField, surfaceMesh>": "U/phi correction",
    "fvMatrix<double>::flux": "U/phi correction",
    "solve<vector>": "UEqn solve",
    "fvMatrix<vector>::H": "pEqn assembly",
    "fvMatrix<vector>::H1": "pEqn assembly",
    "fvMatrix<vector>::A": "pEqn assembly",
    "operator*<vector, fvPatchField, volMesh>": "pEqn assembly",
    "operator/<fvPatchField, volMesh>": "pEqn assembly",
    "surfaceInterpolationScheme<double>::interpolate": "pEqn assembly",
    "fvc::flux": "pEqn assembly",
    "adjustPhi": "pEqn assembly",
    "fvc::snGrad<double>": "pEqn assembly",
    "operator*<fvsPatchField, surfaceMesh>": "pEqn assembly",
    "surfaceScalarField::operator+=": "pEqn assembly",
    "fvm::laplacian<double, double>": "pEqn assembly",
    "volScalarField::needReference": "pEqn assembly",
    "fvMatrix<double>::solve": "pEqn solve",
    "kOmegaSSTBase<...>::correct": "turbulence->correct",
    "Time::loop": "Time::loop (function objects)",
    "DimensionedField<double, volMesh>::weightedAverage": "continuityErrs",
    "fvc::surfaceIntegrateInternal<double>": "continuityErrs",
    "mag<double, volMesh>": "continuityErrs",
    "operator-<double, double, fvPatchField, volMesh>": "continuityErrs",
}

# Per-call-site labels for callees that occur at several call sites in main (same symbol, different return address).
# The source statement is inferred from the position of the return address relative to its unambiguous neighbours
# (see the C table), i.e. from code layout, not from symbols.
PHASE_BY_ADDR = {
    0x4265d1: ("UEqn assembly", "UEqn.H: solve(UEqn == -fvc::grad(p)) -- grad(p) evaluated just before solve<vector> at 0x426608"),
    0x42696f: ("pEqn assembly", "pEqn.H consistent: rAtU() - rAU (between snGrad(p) and interpolate)"),
    0x426b2e: ("pEqn assembly", "pEqn.H consistent: HbyA -= (rAU - rAtU())*fvc::grad(p) (right after phiHbyA += ...)"),
    0x4270a8: ("continuityErrs", "continuityErrs.H: fvc::div(phi) inlined to surfaceIntegrateInternal (followed by mag/weightedAverage)"),
    0x4272a3: ("U/phi correction", "pEqn.H: U = HbyA - rAtU()*fvc::grad(p) (followed by operator- at 0x4272cf)"),
    0x4273e7: ("pEqn assembly", "pEqn.H non-orth loop: fvc::div(phiHbyA) inlined to surfaceIntegrateInternal (just before fvm::laplacian at 0x42740c)"),
}


def phase_of(s):
    top, addr = top_frame(s)
    if addr in PHASE_BY_ADDR:
        return PHASE_BY_ADDR[addr][0]
    return PHASE_BY_CALLEE.get(top, "UNLABELLED:" + top)


site_counts = collections.Counter()
for s in inloop:
    site_counts[top_frame(s)] += 1

# --------------------------------------------------------------------------- helpers
out = []


def w(line=""):
    out.append(line)


def table(header, rows):
    w("| " + " | ".join(header) + " |")
    w("|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        w("| " + " | ".join(str(x) for x in r) + " |")
    w()


def any_frame(s, rx):
    return any(rx.search(f[3]) for f in s.frames[: s.main_idx])


def first_idx(s, rx):
    for i, f in enumerate(s.frames[: s.main_idx]):
        if rx.search(f[3]):
            return i
    return None


def last_idx(s, rx):
    idx = None
    for i, f in enumerate(s.frames[: s.main_idx]):
        if rx.search(f[3]):
            idx = i
    return idx


def matched_names(sel, rx):
    c = collections.Counter()
    for s in sel:
        for f in s.frames[: s.main_idx]:
            if rx.search(f[3]):
                c[f[2]] += 1
    return c


def inclusive(label, pattern, show_phases=True, show_matches=True):
    rx = re.compile(pattern)
    sel = [s for s in inloop if any_frame(s, rx)]
    n = len(sel)
    w(f"**{label}** regex `{pattern}`: **{n}** samples = **{pct(n):.2f}%**")
    if show_matches:
        names = matched_names(sel, rx)
        w("matched frame strings (frame occurrences): " + "; ".join(f"`{k}` ({v})" for k, v in names.most_common()))
    if show_phases and n:
        ph = collections.Counter(phase_of(s) for s in sel)
        w("by step phase: " + ", ".join(f"{k} {v} ({pct(v):.2f}%)" for k, v in ph.most_common()))
    w()
    return sel


def children_table(label, pattern, limit=30, innermost=False, phase=None):
    """Direct children (frame just inside the matched frame).  By default the outermost matching frame is used;
    innermost=True uses the innermost one (for functions that call same-named overloads).  phase restricts to a C phase."""
    rx = re.compile(pattern)
    c = collections.Counter()
    tot = 0
    for s in inloop:
        if phase is not None and phase_of(s) != phase:
            continue
        i = first_idx(s, rx) if innermost else last_idx(s, rx)
        if i is None:
            continue
        tot += 1
        c["<self (leaf)>" if i == 0 else s.frames[i - 1][3]] += 1
    which = "innermost" if innermost else "outermost"
    ph = f", phase={phase}" if phase else ""
    w(f"**Direct children of `{label}`** (regex `{pattern}`{ph}, {tot} samples = {pct(tot):.2f}%; child = frame immediately inside the {which} matching frame):")
    w()
    table(["child frame", "samples", "% in-loop", "% of parent"],
          [(f"`{k}`", v, f"{pct(v):.2f}", f"{100.0 * v / max(1, tot):.1f}") for k, v in c.most_common(limit)])


# =========================================================================== report
w("# profile53: CrayPAT stack-sample breakdown of simpleFoam (occDrivAerStaticMesh, 512 ranks, 48 sampled)")
w()
w(f"Source: `{ROOT}` ({len(ranks)} rank files: {', '.join(str(r) for r in ranks)})")
w()
w("## Sample classification")
w()
w("Each file holds one sample (one call stack of the main thread) per `=== round=N` header, about every 1.2 s. "
  "Classes: `inloop` = stack contains `main` and no teardown/startup frame; `teardown` = `~staticFvMesh`/exit handlers reached through `main`; "
  "`exit` = no `main` frame, stack is in `exit -> __pat_exit` (CrayPAT writing its data after the solver finished); "
  "`error` = eu-stack could not read the process (`Permission denied` / `No such file` on the final round); `startup` = any frame matching "
  f"`{STARTUP_RE.pattern}` (mesh/field construction, decomposition, model construction).")
w()
table(["class", "samples"], [(k, v) for k, v in sorted(cls_counts.items(), key=lambda kv: -kv[1])])
t0 = min(s.t for s in inloop)
t1 = max(s.t for s in inloop)
w(f"In-loop samples: **{N}** over {len(ranks)} ranks ({N / len(ranks):.1f} per rank); in-loop sample times span {t1 - t0:.1f} s "
  f"(epoch {t0:.1f} .. {t1:.1f}). The first sample of every rank is already inside the time loop (no startup frame was ever observed), "
  "so the sampler started after initialisation; the exclusion is therefore effectively 'drop exit/teardown/error samples'.")
w()
per_rank = collections.Counter(s.rank for s in inloop)
w("in-loop samples per rank: " + ", ".join(f"{r}:{per_rank[r]}" for r in ranks))
w()
w("Frame names below are demangled symbols with the argument list and return type removed and these abbreviations applied: "
  "`Foam::` dropped, `Vector<double>`→`vector`, `Tensor<double>`→`tensor`, `GeometricField<double,fvPatchField,volMesh>`→`volScalarField` (etc.), "
  "`outerProduct<vector,double>::type`→`vector`, `outerProduct<vector,vector>::type`→`tensor`, "
  "`kOmegaSSTBase<eddyViscosity<RASModel<IncompressibleTurbulenceModel<transportModel>>>>`→`kOmegaSSTBase<...>`. "
  "Regexes are applied to the abbreviated names; the 'matched frame strings' lists show the un-abbreviated symbol (minus arguments).")
w()

# --------------------------------------------------------------------------- A: flat leaf
w("## A. Flat self (leaf-frame) time, top 50")
w()
leaf = collections.Counter()
leaf_mpi = {}
for s in inloop:
    f0 = s.frames[0]
    key = f0[3]
    leaf[key] += 1
    if is_mpi(f0):
        leaf_mpi[key] = "MPI"
    elif mpi_top_idx(s) is not None:
        leaf_mpi[key] = "MPI (libc/UCX helper under MPI)"
    else:
        leaf_mpi.setdefault(key, "")
rows = []
cum = 0
for i, (k, v) in enumerate(leaf.most_common(50), 1):
    cum += v
    rows.append((i, f"`{k}`", v, f"{pct(v):.2f}", f"{pct(cum):.1f}", leaf_mpi[k]))
table(["#", "leaf frame", "samples", "%", "cum %", "MPI?"], rows)
mpi_leaf_total = sum(v for k, v in leaf.items() if leaf_mpi[k].startswith("MPI"))
w(f"Sum of MPI-marked leaf frames: {mpi_leaf_total} ({pct(mpi_leaf_total):.2f}%). Distinct leaf frames: {len(leaf)}.")
w()

# --------------------------------------------------------------------------- C first (phases are referenced by B)
w("## C. Top-level step phases (frames directly under `main`)")
w()
w("`main` return address = call site inside simpleFoam's inlined loop body (UEqn.H, pEqn.H, turbulence->correct(), runTime.loop()). "
  "Sorted by address. The layout mostly follows source order, except that the compiler placed the non-orthogonal corrector loop body "
  "(fvm::laplacian / setReference / pEqn.solve / pEqn.flux, 0x42740c..0x427655) after `turbulence->correct()` (0x42739c). "
  "Phase labels are assigned per callee symbol; symbols that occur at several call sites (`fvc::grad<double>` x3, "
  "`fvc::surfaceIntegrateInternal<double>` x2, `operator-<double,double,fvPatchField,volMesh>`) are labelled per address from their "
  "position relative to unambiguous neighbours (note column) -- an inference from code layout, not from symbols.")
w()
rows = []
for (top, addr), v in sorted(site_counts.items(), key=lambda kv: kv[0][1]):
    if addr in PHASE_BY_ADDR:
        lab, note = PHASE_BY_ADDR[addr]
    else:
        lab, note = PHASE_BY_CALLEE.get(top, "UNLABELLED"), ""
    rows.append((f"0x{addr:x}", f"`{top}`", v, f"{pct(v):.2f}", lab, note))
table(["main ret addr", "callee (frame directly under main)", "samples", "%", "phase label", "call-site note"], rows)
phase_counts = collections.Counter(phase_of(s) for s in inloop)
w("### Phase totals")
w()
table(["phase", "samples", "%"], [(k, v, f"{pct(v):.2f}") for k, v in phase_counts.most_common()])

# --------------------------------------------------------------------------- B
w("## B. Inclusive call-path shares")
w()
w("A sample counts for an item if any frame on its stack (below `main`) matches the regex. Percentages are of the "
  f"{N} in-loop samples. 'by step phase' uses the C labels.")
w()

# ---- B1
w("### B1. Gauss gradient (`fv::gaussGrad<T>::calcGrad` / `gradf*`)")
w()
GRAD_RX = re.compile(r"fv::gaussGrad<.*>::(calcGrad|gradf\w*)")
grad_sel = inclusive("B1 total gaussGrad calcGrad/gradf", GRAD_RX.pattern)
WRAP_RX = re.compile(r"^(fvc::grad<|fv::gradScheme<|fv::gaussGrad<|fv::cellLimitedGrad<|tmp<|volVectorField::operator=|volTensorField::operator=|GeometricField)")
cat = collections.Counter()
cat_other = collections.Counter()
st = collections.Counter()
for s in grad_sel:
    i = last_idx(s, GRAD_RX)
    gfr = s.frames[i][3]
    scalar = "gaussGrad<double>" in gfr
    kind = "scalar grad (gaussGrad<double>, result vector)" if scalar else "vector grad (gaussGrad<vector>, result tensor)"
    st[kind] += 1
    c = None
    for j in range(i + 1, s.main_idx):
        f = s.frames[j][3]
        if "correctedSnGrad" in f and ("::correction" in f or "::fullGradCorrection" in f):
            c = "(a) correctedSnGrad::correction / fullGradCorrection"
            break
        if "kOmegaSST" in f:
            c = "(b) kOmegaSSTBase::correct"
            break
        if "linearUpwind" in f or "ConvectionScheme" in f or "fvm::div" in f:
            c = "(d) linearUpwindV / convection scheme"
            break
        if WRAP_RX.search(f):
            continue
        c = "(e) other: " + f
        cat_other[f] += 1
        break
    if c is None:
        c = "(c) simpleFoam main directly (fvc::grad(p))"
    cat[(c, kind)] += 1
    cat[(c, "all")] += 1
w("Split by nearest distinguishing caller (walk from the gaussGrad frame towards `main`, skipping grad wrappers "
  f"`{WRAP_RX.pattern}`; first match of correctedSnGrad::correction|fullGradCorrection / kOmegaSST / linearUpwind|ConvectionScheme|fvm::div / other non-wrapper; "
  "if `main` is reached first it is (c)). Note: the scalar laplacian's non-orthogonal correction appears as "
  "`correctedSnGrad<double>::correction -> fullGradCorrection -> fvc::grad -> gaussGrad<double>::calcGrad`.")
w()
rows = []
for (c, kind), v in sorted(cat.items(), key=lambda kv: (kv[0][0], kv[0][1] != "all", -kv[1])):
    rows.append((c, kind, v, f"{pct(v):.2f}"))
table(["caller category", "gradient type", "samples", "%"], rows)
table(["gradient type (template argument of gaussGrad)", "samples", "%"], [(k, v, f"{pct(v):.2f}") for k, v in st.most_common()])
# where inside gaussGrad does time go
w("Deepest gaussGrad-related frame reached (which part of the gradient):")
w()
part = collections.Counter()
for s in grad_sel:
    i = first_idx(s, re.compile(r"fv::gaussGrad<"))
    part[s.frames[i][3] + ("" if i else "  [leaf]")] += 1
table(["innermost gaussGrad frame", "samples", "%"], [(f"`{k}`", v, f"{pct(v):.2f}") for k, v in part.most_common()])
children_table("fv::gaussGrad<double>::calcGrad", r"fv::gaussGrad<double>::calcGrad")
children_table("fv::gaussGrad<vector>::calcGrad", r"fv::gaussGrad<vector>::calcGrad")
inclusive("fvc::grad<vector> via cellLimitedGrad<vector,minmod>::calcGrad (grad(U), includes limiter)", r"fv::cellLimitedGrad<vector, minmod>::calcGrad")
children_table("fv::cellLimitedGrad<vector, minmod>::calcGrad", r"fv::cellLimitedGrad<vector, minmod>::calcGrad")
inclusive("any fvc::grad<...> (all gradient evaluations incl. limiter)", r"^fvc::grad<")

# ---- B2
w("### B2. fvMatrix / lduMatrix H and H1")
w()
inclusive("fvMatrix<vector>::H()", r"^fvMatrix<vector>::H$")
inclusive("fvMatrix<...>::H1()", r"^fvMatrix<.*>::H1$")
inclusive("lduMatrix::H<T>", r"^lduMatrix::H<")
inclusive("lduMatrix::H1", r"^lduMatrix::H1$")
children_table("fvMatrix<vector>::H", r"^fvMatrix<vector>::H$")

# ---- B3
w("### B3. pEqn assembly pieces")
w()
items3 = [("fvc::flux", r"^fvc::flux$"), ("fvMatrix<double>::flux (pEqn.flux())", r"^fvMatrix<double>::flux$"),
          ("constrainHbyA", r"^constrainHbyA"), ("fvc::interpolate", r"^fvc::interpolate"),
          ("surfaceInterpolationScheme<double>::interpolate (fvc::interpolate inlined caller)", r"^surfaceInterpolationScheme<double>::interpolate"),
          ("fvc::snGrad", r"^fvc::snGrad"), ("fvc::div", r"^fvc::div<"), ("adjustPhi", r"^adjustPhi"),
          ("constrainPressure", r"^constrainPressure"), ("fvm::laplacian<double,double> (pEqn operator)", r"^fvm::laplacian<double, double>"),
          ("volScalarField::needReference (pEqn.setReference allreduce)", r"needReference")]
w("`constrainHbyA`, `constrainPressure` and `fvc::interpolate` never appear as frames in any sample (inlined into `main`; "
  "the body of fvc::interpolate shows up as `surfaceInterpolationScheme<double>::interpolate`, and fvc::div(phiHbyA) as "
  "`fvc::surfaceIntegrateInternal<double>` at call site 0x4273e7). They are reported as 0 or via those frames.")
w()
union = set()
for lab, pat in items3:
    sel = inclusive(lab, pat)
    union.update(id(s) for s in sel)
div_phi = [s for s in inloop if top_frame(s)[1] == 0x4273e7]
w(f"**fvc::div(phiHbyA) (inlined; `fvc::surfaceIntegrateInternal<double>` at main call site 0x4273e7)**: {len(div_phi)} samples = {pct(len(div_phi)):.2f}%")
w()
union.update(id(s) for s in div_phi)
w(f"**Union of the B3 items (all call sites, including the fvm::laplacian/fvc::div inside kOmegaSST and divDevReff)**: {len(union)} samples = {pct(len(union)):.2f}%")
w()
pa = [s for s in inloop if phase_of(s) == "pEqn assembly"]
w(f"**pEqn assembly phase total (C label, everything under main between UEqn solve and pEqn solve)**: {len(pa)} = {pct(len(pa)):.2f}%; "
  "its top-level callees: " + ", ".join(f"`{k}` {v}" for k, v in collections.Counter(top_frame(s)[0] for s in pa).most_common()))
w()

# ---- B4
w("### B4. bound / fvc::average / surfaceSum")
w()
inclusive("Foam::bound", r"^bound$")
inclusive("fvc::average", r"^fvc::average")
inclusive("fvc::surfaceSum", r"^fvc::surfaceSum")

# ---- B5
w("### B5. GaussSeidelSmoother::smooth")
w()
sm_sel = inclusive("GaussSeidelSmoother::smooth (incl. scalarSmooth)", r"GaussSeidelSmoother::(smooth|scalarSmooth)")
lc = collections.Counter((s.frames[0][3], mpi_top_idx(s) is not None) for s in sm_sel)
COPY_RX = re.compile(r"memmove|memcpy|memset|Field<double>::operator=|UList<double>::operator=|deepCopy|::assign")
copy_of = sum(v for (k, m), v in lc.items() if COPY_RX.search(k) and not m)
copy_mpi = sum(v for (k, m), v in lc.items() if COPY_RX.search(k) and m)
sm_mpi = sum(v for (k, m), v in lc.items() if m)
w("Leaf frames beneath smooth (the `under MPI` column says whether an MPI/UCX frame lies between the leaf and smooth):")
w()
table(["leaf frame", "under MPI", "samples", "% in-loop", "% of smooth"],
      [(f"`{k}`", "yes" if m else "", v, f"{pct(v):.2f}", f"{100.0 * v / max(1, len(sm_sel)):.1f}") for (k, m), v in lc.most_common(24)])
w(f"Copy-type leaves (regex `{COPY_RX.pattern}`) directly in OpenFOAM code beneath smooth (bPrime = source etc.): {copy_of} samples = "
  f"{pct(copy_of):.2f}% in-loop = {100.0 * copy_of / max(1, len(sm_sel)):.1f}% of smooth; copy-type leaves inside MPI/UCX beneath smooth: {copy_mpi}; "
  f"all MPI beneath smooth: {sm_mpi} = {pct(sm_mpi):.2f}% in-loop = {100.0 * sm_mpi / max(1, len(sm_sel)):.1f}% of smooth.")
w()
mm = collections.Counter()
for s in sm_sel:
    if COPY_RX.search(s.frames[0][3]) and mpi_top_idx(s) is None:
        mm[" <- ".join(f[3] for f in s.frames[1:4])] += 1
w("callers of those OpenFOAM copy leaves: " + ", ".join(f"`{k}` {v}" for k, v in mm.most_common()))
w()
children_table("GaussSeidelSmoother::smooth (innermost smooth frame; the static smooth() overload calls the member smooth())", r"GaussSeidelSmoother::smooth$", innermost=True)
children_table("GaussSeidelSmoother::scalarSmooth", r"GaussSeidelSmoother::scalarSmooth$")

# ---- B6
w("### B6. GAMG (p equation)")
w()
for lab, pat in [("GAMGSolver::solve", r"^GAMGSolver::solve$"), ("GAMGSolver::Vcycle", r"^GAMGSolver::Vcycle$"),
                 ("GAMGSolver::scale", r"^GAMGSolver::scale$"), ("GAMGSolver::solveCoarsestLevel", r"^GAMGSolver::solveCoarsestLevel$"),
                 ("PCG::scalarSolve (coarsest-level solver)", r"^PCG::scalarSolve$"),
                 ("GAMGAgglomeration::restrictField", r"GAMGAgglomeration::restrictField"), ("GAMGAgglomeration::prolongField", r"GAMGAgglomeration::prolongField"),
                 ("GAMGSolver::interpolate", r"^GAMGSolver::interpolate"), ("GAMGSolver constructor / agglomerateMatrix / New", r"GAMGSolver::GAMGSolver|agglomerateMatrix|ConstructorToTable<GAMGSolver>"),
                 ("GAMGSolver::~GAMGSolver", r"GAMGSolver::~GAMGSolver")]:
    inclusive(lab, pat)
children_table("GAMGSolver::solve", r"^GAMGSolver::solve$")
children_table("GAMGSolver::Vcycle", r"^GAMGSolver::Vcycle$")
children_table("GAMGSolver::scale", r"^GAMGSolver::scale$")
children_table("GAMGSolver::solveCoarsestLevel", r"^GAMGSolver::solveCoarsestLevel$")
children_table("PCG::scalarSolve", r"^PCG::scalarSolve$")

# ---- B7
w("### B7. lduMatrix kernels")
w()
for lab, pat in [("lduMatrix::Amul", r"^lduMatrix::Amul$"), ("lduMatrix::residual", r"^lduMatrix::residual$"),
                 ("lduMatrix::sumA", r"^lduMatrix::sumA$"), ("lduMatrix::solver::normFactor", r"normFactor"),
                 ("lduMatrix::negSumDiag", r"negSumDiag")]:
    inclusive(lab, pat)
children_table("lduMatrix::Amul", r"^lduMatrix::Amul$")
children_table("lduMatrix::residual", r"^lduMatrix::residual$")

# ---- B8
w("### B8. smoothSolver (U, k, omega)")
w()
inclusive("smoothSolver::solve", r"^smoothSolver::solve$")
inclusive("smoothSolver::solveGaussSeidelComponents", r"^smoothSolver::solveGaussSeidelComponents")
children_table("smoothSolver::solve", r"^smoothSolver::solve$")
children_table("smoothSolver::solveGaussSeidelComponents", r"^smoothSolver::solveGaussSeidelComponents")
children_table("fvMatrix<vector>::solveSegregated (UEqn)", r"^fvMatrix<vector>::solveSegregated$")
children_table("fvMatrix<double>::solveSegregated (p, k, omega)", r"^fvMatrix<double>::solveSegregated$")

# ---- B9
w("### B9. kOmegaSSTBase::correct")
w()
k_sel = inclusive("kOmegaSSTBase::correct total", r"kOmegaSSTBase<\.\.\.>::correct$")
KO = re.compile(r"kOmegaSSTBase<\.\.\.>::correct$")
sub = [("F1", r"kOmegaSSTBase<\.\.\.>::F1$"), ("F2", r"kOmegaSSTBase<\.\.\.>::F2$"), ("F23", r"kOmegaSSTBase<\.\.\.>::F23$"),
       ("S2", r"kOmegaSSTBase<\.\.\.>::S2$"), ("GbyNu0", r"kOmegaSSTBase<\.\.\.>::GbyNu0$"), ("Pk", r"kOmegaSSTBase<\.\.\.>::Pk$"),
       ("correctNut", r"kOmegaSSTBase<\.\.\.>::correctNut$"), ("kSource/omegaSource", r"kOmegaSSTBase<\.\.\.>::(kSource|omegaSource)$"),
       ("fvc::grad (CDkOmega: grad(k)&grad(omega), tgradU)", r"^fvc::grad<"), ("fvc::grad<double> (grad(k), grad(omega))", r"^fvc::grad<double>"),
       ("fvc::grad<vector> (tgradU)", r"^fvc::grad<vector>"),
       ("operator&<...> (CDkOmega dot product)", r"^operator&"),
       ("fvm::laplacian", r"^fvm::laplacian<"), ("fvm::div", r"^fvm::div<"), ("fvm::Sp", r"^fvm::Sp<"), ("fvm::SuSp", r"^fvm::SuSp<"),
       ("solve<double> (k and omega solves, incl. relax? no: solve only)", r"^solve<double>$"),
       ("fvMatrix<double>::relax", r"^fvMatrix<double>::relax$"), ("bound", r"^bound$"),
       ("fvMatrix<double>::boundaryManipulate", r"boundaryManipulate"), ("fvMatrix<double>::setValues*", r"setValues"),
       ("MPI (any MPI frame) inside correct", r"__MPI__")]
rows = []
for lab, pat in sub:
    if pat == "__MPI__":
        n = sum(1 for s in k_sel if mpi_top_idx(s) is not None)
        rows.append((lab, "(any frame matching MPI regex)", n, f"{pct(n):.2f}", f"{100.0 * n / max(1, len(k_sel)):.1f}"))
        continue
    rx = re.compile(pat)
    n = 0
    for s in k_sel:
        ki = last_idx(s, KO)
        if any(rx.search(f[3]) for f in s.frames[:ki]):
            n += 1
    rows.append((lab, f"`{pat}`", n, f"{pct(n):.2f}", f"{100.0 * n / max(1, len(k_sel)):.1f}"))
table(["sub-item (frames inside correct)", "regex", "samples", "% in-loop", "% of correct"], rows)
children_table("kOmegaSSTBase<...>::correct", r"kOmegaSSTBase<\.\.\.>::correct$", limit=40)

# ---- B10
w("### B10. Laplacian and convection scheme assembly")
w()
for lab, pat in [("gaussLaplacianScheme<*>::fvmLaplacian (any T)", r"gaussLaplacianScheme<.*>::fvmLaplacian$"),
                 ("gaussLaplacianScheme<double,double>::fvmLaplacian (p, k, omega)", r"gaussLaplacianScheme<double, double>::fvmLaplacian$"),
                 ("gaussLaplacianScheme<vector,double>::fvmLaplacian (U, inside divDevReff)", r"gaussLaplacianScheme<vector, double>::fvmLaplacian$"),
                 ("gaussLaplacianScheme<*>::fvmLaplacianUncorrected", r"fvmLaplacianUncorrected"),
                 ("gaussLaplacianScheme<*>::gammaMagSf", r"gammaMagSf"),
                 ("correctedSnGrad<*>::correction (non-orthogonal correction)", r"correctedSnGrad<.*>::correction"),
                 ("gaussConvectionScheme<*>::fvmDiv (any T)", r"gaussConvectionScheme<.*>::fvmDiv"),
                 ("gaussConvectionScheme<vector>::fvmDiv (U)", r"gaussConvectionScheme<vector>::fvmDiv"),
                 ("gaussConvectionScheme<double>::fvmDiv (k, omega)", r"gaussConvectionScheme<double>::fvmDiv"),
                 ("boundedConvectionScheme<*>::fvmDiv (wrapper, includes fvm::Sp(-div(phi)))", r"boundedConvectionScheme<.*>::fvmDiv"),
                 ("linearUpwindV<vector>::correction", r"linearUpwindV<vector>::correction")]:
    inclusive(lab, pat)
children_table("gaussLaplacianScheme<double, double>::fvmLaplacian", r"gaussLaplacianScheme<double, double>::fvmLaplacian$")
children_table("gaussLaplacianScheme<vector, double>::fvmLaplacian", r"gaussLaplacianScheme<vector, double>::fvmLaplacian$")
children_table("gaussConvectionScheme<vector>::fvmDiv", r"gaussConvectionScheme<vector>::fvmDiv")
children_table("gaussConvectionScheme<double>::fvmDiv", r"gaussConvectionScheme<double>::fvmDiv")
children_table("boundedConvectionScheme<vector>::fvmDiv", r"boundedConvectionScheme<vector>::fvmDiv")

# ---- B11
w("### B11. Matrix allocation / zero fill")
w()
union = set()
for lab, pat in [("memset leaf (any caller)", r"memset"), ("lduMatrix::upper()", r"^lduMatrix::upper$"), ("lduMatrix::lower()", r"^lduMatrix::lower$"),
                 ("lduMatrix::diag()", r"^lduMatrix::diag$"), ("fvMatrix<*>::fvMatrix constructor", r"^fvMatrix<.*>::fvMatrix$"),
                 ("lduMatrix::lduMatrix (constructor incl. copy)", r"^lduMatrix::lduMatrix$"),
                 ("fvMatrix<*>::~fvMatrix / lduMatrix::~lduMatrix", r"::~(fvMatrix|lduMatrix)$"),
                 ("malloc/free family leaf", r"^(_int_malloc|_int_free|malloc|free|cfree|__GI___libc_malloc|malloc_consolidate|unlink_chunk|sysmalloc|__libc_malloc)")]:
    sel = inclusive(lab, pat)
    union.update(id(s) for s in sel)
w(f"**Union of B11 items**: {len(union)} = {pct(len(union)):.2f}%")
w()
memset_callers = collections.Counter()
for s in inloop:
    if re.search(r"memset", s.frames[0][3]):
        memset_callers[s.frames[1][3] if len(s.frames) > 1 else "?"] += 1
w("memset leaf by immediate caller:")
w()
table(["caller of memset", "samples", "%"], [(f"`{k}`", v, f"{pct(v):.2f}") for k, v in memset_callers.most_common()])
memmove_callers = collections.Counter()
for s in inloop:
    if re.search(r"memmove|memcpy", s.frames[0][3]):
        memmove_callers[" <- ".join(f[3] for f in s.frames[1:3])] += 1
w("memmove/memcpy leaf by immediate two callers:")
w()
table(["callers of memmove", "samples", "%"], [(f"`{k}`", v, f"{pct(v):.2f}") for k, v in memmove_callers.most_common(25)])

# ---- B12
w("### B12. relax / solveSegregated outside the solver / boundary manipulation")
w()
inclusive("fvMatrix<*>::relax (any)", r"^fvMatrix<.*>::relax$")
inclusive("fvMatrix<vector>::relax (UEqn.relax)", r"^fvMatrix<vector>::relax$")
inclusive("fvMatrix<double>::relax (k, omega, p.relax is a field relax not matrix)", r"^fvMatrix<double>::relax$")
SOLVER_RX = re.compile(r"^(GAMGSolver|smoothSolver|PCG|PBiCG|PBiCGStab|diagonalSolver)::(solve|scalarSolve|solveGaussSeidelComponents)$")
for lab, pat in [("fvMatrix<vector>::solveSegregated", r"^fvMatrix<vector>::solveSegregated$"), ("fvMatrix<double>::solveSegregated", r"^fvMatrix<double>::solveSegregated$")]:
    rx = re.compile(pat)
    sel = [s for s in inloop if any_frame(s, rx)]
    outside = [s for s in sel if not any_frame(s, SOLVER_RX)]
    w(f"**{lab}**: inclusive {len(sel)} = {pct(len(sel)):.2f}%; **outside the lduMatrix::solver (no `{SOLVER_RX.pattern}` frame)**: {len(outside)} = {pct(len(outside)):.2f}%")
    c = collections.Counter()
    for s in outside:
        i = last_idx(s, rx)
        c["<self (leaf)>" if i == 0 else s.frames[i - 1][3]] += 1
    w("  children of solveSegregated outside the solver: " + ", ".join(f"`{k}` {v}" for k, v in c.most_common()))
    w()
for lab, pat in [("fvMatrix::setValues* (setValuesFromList)", r"setValues"), ("fvMatrix::boundaryManipulate", r"boundaryManipulate"),
                 ("GeometricField<*>::correctBoundaryConditions", r"::correctBoundaryConditions$"),
                 ("GeometricBoundaryField<*>::evaluate (field boundary evaluation)", r"^GeometricBoundaryField<.*>::evaluate$"),
                 ("evaluateCoupled / evaluate_if", r"evaluateCoupled|evaluate_if"),
                 ("processorFvPatchField<*>::initEvaluate / evaluate", r"processorFvPatchField<.*>::(initEvaluate|evaluate)$"),
                 ("gaussGrad<*>::correctBoundaryConditions", r"gaussGrad<.*>::correctBoundaryConditions")]:
    inclusive(lab, pat)
children_table("GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate", r"^GeometricBoundaryField<vector, fvPatchField, volMesh>::evaluate$")

# ---- B13
w("### B13. continuity, fvOptions, function objects")
w()
ce = phase_counts.get("continuityErrs", 0)
w(f"**continuityErrs (C phase label: call sites 0x4270a8..0x4271c2 under main = fvc::div(phi) inlined to surfaceIntegrateInternal, mag, weightedAverage)**: {ce} samples = {pct(ce):.2f}%")
w()
inclusive("fv::optionList::* (fvOptions)", r"^fv::optionList::")
fo_sel = inclusive("functionObjectList::execute subtree", r"^functionObjectList::execute$")
inclusive("Time::loop (whole, includes functionObjects + readModifiedObjects)", r"^Time::loop$")
inclusive("Time::write / regIOobject::write (field output)", r"^(Time::write|regIOobject::write|Time::writeNow|fvMesh::write|GeometricField<.*>::write)")
fo = collections.Counter()
for s in fo_sel:
    name = None
    for f in s.frames[: s.main_idx]:
        m = re.search(r"functionObjects::(\w+)::", f[3])
        if m and m.group(1) != "timeControl":
            name = m.group(1)
            break
        if "Probes<" in f[3]:
            name = "probes"
            break
    if name is None:
        name = "other: " + s.frames[0][3]
    fo[name] += 1
w("function objects by type (first `functionObjects::<type>::` frame other than timeControl, or `Probes<`):")
w()
table(["function object type", "samples", "%"], [(k, v, f"{pct(v):.2f}") for k, v in fo.most_common()])
children_table("Time::loop", r"^Time::loop$")

# ---- B14
w("### B14. MPI")
w()
mpi_sel = [s for s in inloop if mpi_top_idx(s) is not None]
w(f"**MPI total** (any frame matching `{MPI_RE.pattern}`): **{len(mpi_sel)}** = **{pct(len(mpi_sel)):.2f}%**")
w()
ALLRED_RX = re.compile(r"allReduce|reduceAnd|reduceOr|::reduce|gSum|gMax|gMin|gAverage|returnReduce|MPI_Allreduce|mpi_allgather|allGather|gatherList|listCombine|combineAllGather")
IFACE_RX = re.compile(r"initMatrixInterfaces|updateMatrixInterfaces|initEvaluate|::evaluate$|initInterfaceMatrixUpdate|updateInterfaceMatrix|evaluate_if|evaluateCoupled")
catc = collections.Counter()
cat_caller = collections.defaultdict(collections.Counter)
entry = collections.Counter()
caller = collections.Counter()
phase_mpi = collections.Counter()
for s in mpi_sel:
    i = mpi_top_idx(s)
    entry[s.frames[i][3]] += 1
    nearest = s.frames[i + 1][3] if i + 1 < s.main_idx else "main"
    caller[nearest] += 1
    c = "other"
    for j in range(i + 1, s.main_idx):
        f = s.frames[j][3]
        if ALLRED_RX.search(f):
            c = "Allreduce (reduce/gSum*/returnReduce/allGather)"
            break
        if IFACE_RX.search(f):
            c = "interface exchange (init/updateMatrixInterfaces, initEvaluate/evaluate)"
            break
    catc[c] += 1
    cat_caller[c][nearest] += 1
    phase_mpi[phase_of(s)] += 1
w("Caller category (walk from the outermost MPI frame towards `main`; first frame matching "
  f"Allreduce regex `{ALLRED_RX.pattern}` or interface regex `{IFACE_RX.pattern}` decides):")
w()
table(["category", "samples", "% in-loop", "% of MPI"], [(k, v, f"{pct(v):.2f}", f"{100.0 * v / len(mpi_sel):.1f}") for k, v in catc.most_common()])
for c in catc:
    w(f"nearest OpenFOAM caller for **{c}**: " + ", ".join(f"`{k}` {v}" for k, v in cat_caller[c].most_common(12)))
    w()
w("MPI entry function (outermost MPI frame):")
w()
table(["MPI entry", "samples", "%"], [(f"`{k}`", v, f"{pct(v):.2f}") for k, v in entry.most_common()])
w("MPI by step phase:")
w()
table(["phase", "MPI samples", "% in-loop", "% of phase"], [(k, v, f"{pct(v):.2f}", f"{100.0 * v / phase_counts[k]:.1f}") for k, v in phase_mpi.most_common()])
w("MPI by OpenFOAM reduction/communication primitive (first OpenFOAM frame above MPI) and its caller:")
w()
cc = collections.Counter()
for s in mpi_sel:
    i = mpi_top_idx(s)
    chain = [f[3] for f in s.frames[i + 1: min(i + 4, s.main_idx)]]
    cc[" <- ".join(chain)] += 1
table(["OpenFOAM caller chain (3 frames above MPI)", "samples", "%"], [(f"`{k}`", v, f"{pct(v):.2f}") for k, v in cc.most_common(40)])

# --------------------------------------------------------------------------- per-phase children (C detail)
w("## C (detail). Children of each phase entry frame")
w()
children_table("fvMatrix<double>::solveSegregated, p equation only", r"^fvMatrix<double>::solveSegregated$", phase="pEqn solve")
children_table("fvMatrix<double>::solveSegregated, k and omega only", r"^fvMatrix<double>::solveSegregated$", phase="turbulence->correct")
children_table("fvMatrix<vector>::solveSegregated (UEqn)", r"^fvMatrix<vector>::solveSegregated$", phase="UEqn solve")
for lab, pat, inner, ph in [("fvm::div<vector> (UEqn convection)", r"^fvm::div<vector>$", False, None),
                            ("divDevReff -> divDevRhoReff (UEqn diffusion)", r"::divDevRhoReff$", True, None),
                            ("fvm::laplacian<double, double> (innermost wrapper), pEqn only", r"^fvm::laplacian<double, double>$", True, "pEqn assembly"),
                            ("fvm::laplacian<double, double> (innermost wrapper), k/omega only", r"^fvm::laplacian<double, double>$", True, "turbulence->correct"),
                            ("fvc::snGrad<double>", r"^fvc::snGrad<double>$", True, None),
                            ("fv::optionList::constrain<vector>", r"^fv::optionList::constrain<vector>$", True, None),
                            ("volScalarField::needReference", r"needReference$", True, None),
                            ("fvc::grad<double> (innermost), all call sites", r"^fvc::grad<double>$", True, None),
                            ("Time::run", r"^Time::run$", True, None)]:
    children_table(lab, pat, innermost=inner, phase=ph)

# --------------------------------------------------------------------------- hot stacks
w("## Most frequent full stacks (abbreviated, leaf first), top 40")
w()
stacks = collections.Counter()
for s in inloop:
    stacks[" <- ".join(f[3] for f in s.frames[: s.main_idx])] += 1
rows = [(v, f"{pct(v):.2f}", f"`{k}`") for k, v in stacks.most_common(40)]
table(["samples", "%", "stack"], rows)

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out) + "\n")
print(f"wrote {OUT}: {N} in-loop samples, classes {dict(cls_counts)}")
