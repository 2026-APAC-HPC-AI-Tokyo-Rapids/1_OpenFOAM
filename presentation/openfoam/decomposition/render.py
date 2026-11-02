"""Renders the 512-subdomain decompositions (Issue #39) with ParaView.

    pvbatch render.py RUN_DIR OUT_DIR [METHOD ...]

RUN_DIR is the unpacked output of a decomposition job: postProcessing/decomposition/<surface>/<surface>.case with the
cellDist of time 1, 2, ... and logFiles/decomposePar-<method>.log. The METHODs name the decompositions in time order: by
default hierarchical, scotch and multiLevel, as decomposition.pbs ran them on ASPIRE-2A (10/09); scotchDomains and
multiLevel for decomposition-genkai.pjm (11/02). OUT_DIR gets one picture per decomposition, view and colouring
(panels/<method>-<view>-<colouring>.png) and stats.json with the numbers of the decomposePar logs, which compose.py writes
under the pictures.

Two colourings: "subdomains" gives each of the 512 subdomains its own colour (the colour key is the fractional part of
subdomain x golden ratio, so that subdomains with near numbers, which are often neighbours, get distant colours); "numa" gives
each node a hue and each of its 8 NUMA domains a shade (rank r runs on node r // 128 and NUMA domain (r // 16) % 8, as the
runs place them).

pvbatch runs Python calculators in this module's namespace, so this module avoids numpy's names.
"""
import json
import re
import sys
from pathlib import Path

from paraview import simple as pv

RUN_DIR, OUT_DIR = Path(sys.argv[1]), Path(sys.argv[2])
SURFACES = RUN_DIR / "postProcessing" / "decomposition"
# Plain scotch was Basic's decomposition until the node tree of #63 (10/16).
TITLES = {"hierarchical": "Case default: hierarchical (16 8 4)", "scotch": "Plain scotch", "scotchDomains": "Basic: scotch on the node tree (2 4 16)", "multiLevel": "Bonus (final): multiLevel (4 2 4 16)"}
METHODS = [(float(time), method, TITLES[method]) for time, method in enumerate(sys.argv[3:] or ["hierarchical", "scotch", "multiLevel"], 1)]
GROUND_Z = -0.3176
WHITE = [0.95, 0.95, 0.95]
GREY = [0.55, 0.57, 0.61]
# Base colours of the 4 nodes; the 8 NUMA domains of a node run from dark to light.
NODE_COLOURS = [(0.12, 0.47, 0.71), (1.0, 0.50, 0.05), (0.17, 0.63, 0.17), (0.58, 0.40, 0.74)]

pv._DisableFirstRenderCameraReset()


def view(width, height):
    v = pv.CreateView("RenderView")
    v.ViewSize = [width, height]
    v.OrientationAxesVisibility = 0
    v.UseColorPaletteForBackground = 0
    v.BackgroundColorMode = "Gradient"
    v.Background = [0.07, 0.08, 0.10]
    v.Background2 = [0.20, 0.22, 0.27]
    return v


def label(v):
    source = pv.Text(Text="")
    shown = pv.Show(source, v)
    shown.FontSize = 26
    shown.Color = WHITE
    shown.WindowLocation = "Upper Left Corner"
    shown.BackgroundColor = [0.07, 0.08, 0.10, 0.7]
    return source


def surface(name):
    """A sampled surface with the colour key of each subdomain and its NUMA domain (0 to 31) as cell data."""
    reader = pv.EnSightReader(CaseFileName=str(SURFACES / name / f"{name}.case"))
    merged = pv.MergeBlocks(Input=reader)
    keyed = pv.PythonCalculator(Input=merged, ArrayAssociation="Cell Data", ArrayName="subdomainKey", Expression="(inputs[0].CellData['cellDist'] * 0.6180339887498949) % 1.0")
    return pv.PythonCalculator(Input=keyed, ArrayAssociation="Cell Data", ArrayName="numaDomain", Expression="inputs[0].CellData['cellDist'] // 16")


def colourings():
    """(name in the file names, cell array, colour table with its value range)."""
    subdomains = pv.GetColorTransferFunction("subdomainKey")
    subdomains.ApplyPreset("Rainbow Uniform", True)
    points = []
    for domain in range(32):
        base = NODE_COLOURS[domain // 8]
        # From 45 % darker to 45 % lighter across the 8 NUMA domains of the node.
        shade = (domain % 8) / 7.0 * 0.9 - 0.45
        points += [float(domain)] + [c * (1 + shade) if shade < 0 else c + (1 - c) * shade for c in base]
    numa = pv.GetColorTransferFunction("numaDomain")
    numa.RGBPoints = points
    numa.ColorSpace = "RGB"
    numa.Discretize = 1
    numa.NumberOfTableValues = 32
    return [("subdomains", "subdomainKey", subdomains, (0.0, 1.0)), ("numa", "numaDomain", numa, (-0.5, 31.5))]


def colour_by(shown, v, array, table, value_range):
    pv.ColorBy(shown, ("CELLS", array))
    table.AutomaticRescaleRangeMode = "Never"
    table.RescaleTransferFunction(*value_range)
    shown.LookupTable = table
    shown.SetScalarBarVisibility(v, False)


def plain(shown, colour):
    shown.ColorArrayName = ["POINTS", ""]
    shown.AmbientColor = colour
    shown.DiffuseColor = colour


def render_all(v, shown, title, where, kind, tables):
    for time, method, name in METHODS:
        v.ViewTime = time
        title.Text = f"{name}: {where}"
        for colouring, array, table, value_range in tables:
            colour_by(shown, v, array, table, value_range)
            path = OUT_DIR / "panels" / f"{method}-{kind}-{colouring}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            pv.SaveScreenshot(str(path), v, ImageResolution=list(v.ViewSize))


def car_panels(car, tables):
    """The car surface from the front left."""
    v = view(1920, 1080)
    floor = pv.Plane(Origin=[-4.0, -5.0, GROUND_Z], Point1=[8.0, -5.0, GROUND_Z], Point2=[-4.0, 5.0, GROUND_Z])
    plain(pv.Show(floor, v), [0.16, 0.17, 0.20])
    shown = pv.Show(car, v)
    v.CameraFocalPoint = [1.5, 0.0, 0.25]
    v.CameraPosition = [-3.0, -3.35, 2.45]
    v.CameraViewUp = [0.0, 0.0, 1.0]
    v.CameraViewAngle = 30.0
    render_all(v, shown, label(v), "the car surface", "car", tables)
    pv.Delete(v)


def side_panels(plane, car, tables):
    """The centre plane seen from the side, with the far half of the car behind it in grey: 11 m around the car and its wake."""
    width, height = 1920, 840
    v = view(width, height)
    shown = pv.Show(plane, v)
    far_half = pv.Clip(Input=car, ClipType="Plane", Invert=1)
    far_half.ClipType.Origin = [0.0, 0.0, 0.0]
    far_half.ClipType.Normal = [0.0, -1.0, 0.0]
    plain(pv.Show(far_half, v), GREY)
    v.CameraParallelProjection = 1
    v.CameraFocalPoint = [3.0, 0.0, 1.6]
    v.CameraPosition = [3.0, -60.0, 1.6]
    v.CameraViewUp = [0.0, 0.0, 1.0]
    v.CameraParallelScale = 11.0 * height / width / 2
    render_all(v, shown, label(v), "the centre plane y = 0", "side", tables)
    pv.Delete(v)


def cross_panels(plane, car, tables):
    """The cross-section at the middle of the wheelbase, seen from behind it towards the nose, with the front of the car in grey."""
    width, height = 1920, 840
    v = view(width, height)
    shown = pv.Show(plane, v)
    front = pv.Clip(Input=car, ClipType="Plane", Invert=1)
    front.ClipType.Origin = [1.40009, 0.0, 0.0]
    front.ClipType.Normal = [1.0, 0.0, 0.0]
    plain(pv.Show(front, v), GREY)
    v.CameraParallelProjection = 1
    v.CameraFocalPoint = [1.40009, 0.0, 1.2]
    v.CameraPosition = [61.4, 0.0, 1.2]
    v.CameraViewUp = [0.0, 0.0, 1.0]
    v.CameraParallelScale = 8.0 * height / width / 2
    render_all(v, shown, label(v), "the cross-section at the middle of the wheelbase", "cross", tables)
    pv.Delete(v)


def log_numbers(method):
    text = (RUN_DIR / "logFiles" / f"decomposePar-{method}.log").read_text()
    cells = re.search(r"Max number of cells = (\d+) \(([0-9.eE+-]+)% above average ([0-9.eE+-]+)\)", text)
    # Each subdomain lists its own processor faces, indented; the total is the line that starts the line.
    return {"processor_faces": int(re.search(r"^Number of processor faces = (\d+)", text, re.MULTILINE).group(1)), "max_cells": int(cells.group(1)), "max_cells_above_average_percent": float(cells.group(2)), "average_cells": float(cells.group(3))}


tables = colourings()
car = surface("car")
car_panels(car, tables)
side_panels(surface("centrePlane"), car, tables)
cross_panels(surface("crossPlane"), car, tables)
(OUT_DIR / "stats.json").write_text(json.dumps({method: log_numbers(method) for _, method, _ in METHODS}, indent=1))
