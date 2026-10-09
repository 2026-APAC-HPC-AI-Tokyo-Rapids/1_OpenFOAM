"""Renders the flow visualization run (Issue #39) into PNG frames and stills with ParaView.

    pvbatch render.py RUN_DIR OUT_DIR MACHINE

RUN_DIR is the unpacked flow-visualization.tar.zst of the run (postProcessing/ written by flowVisualization). MACHINE names
where it ran for the footer, for example "Genkai, 4 nodes / 448 ranks". OUT_DIR gets
frames-iterations/ (the centre plane and the wheel-axle plane from iteration 5 to 150), frames-streamlines/ (the car and its
streamlines at iteration 150, with dashes that move along each streamline at the local flow speed while the camera circles the
car) and stills/. README.md says how to turn the frames into MP4.

pvbatch runs a ProgrammableFilter's script in this module's namespace, so the script below keeps its names inside a function.
"""
import shutil
import sys
from pathlib import Path

import numpy as np
from paraview import simple as pv

RUN_DIR, OUT_DIR, MACHINE = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
POST = RUN_DIR / "postProcessing"
WIDTH, HEIGHT = 1920, 1080
FPS = 30
U_RANGE = (0.0, 50.0)
CP_RANGE = (-1.0, 1.0)
CAR_CENTRE = (1.5, 0.0, 0.25)
GROUND_Z = -0.3176
FOOTER = f"OpenFOAM v2512 simpleFoam, occDrivAerStaticMesh (65.3 M cells), 150 iterations on {MACHINE}"
WHITE = [0.95, 0.95, 0.95]
GREY = [0.62, 0.64, 0.68]
# Dashes on the streamlines: one every 0.1 s of flow time, each 15 % of that long, shown 10 times slower than real time.
DASH_PERIOD, DASH_WIDTH, SLOW_MOTION = 0.1, 0.15, 10.0

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


def text(v, value, size, color, bold=False, location="Upper Left Corner", position=None):
    source = pv.Text(Text=value)
    shown = pv.Show(source, v)
    shown.FontSize = size
    shown.Color = color
    shown.Bold = int(bold)
    shown.WindowLocation = location if position is None else "Any Location"
    if position is not None:
        shown.Position = position
    return source


def colour(shown, association, name, preset, value_range):
    """Colours by an array with a fixed range. ColorBy rescales a new table to the data, so the range is set after it."""
    pv.ColorBy(shown, (association, name, "Magnitude") if name == "U" else (association, name))
    table = pv.GetColorTransferFunction(name)
    table.ApplyPreset(preset, True)
    table.AutomaticRescaleRangeMode = "Never"
    table.RescaleTransferFunction(*value_range)
    shown.LookupTable = table
    return table


def plain(shown, color):
    shown.ColorArrayName = ["POINTS", ""]
    shown.AmbientColor = color
    shown.DiffuseColor = color


def scalar_bar(table, v, title, position, label_format):
    bar = pv.GetScalarBar(table, v)
    bar.Title = title
    bar.ComponentTitle = ""
    bar.Orientation = "Horizontal"
    bar.WindowLocation = "Any Location"
    bar.Position = position
    bar.ScalarBarLength = 0.3
    bar.TitleFontSize = 20
    bar.LabelFontSize = 18
    bar.TitleColor = WHITE
    bar.LabelColor = WHITE
    bar.AutomaticLabelFormat = 0
    bar.LabelFormat = label_format
    bar.AddRangeLabels = 0
    bar.Visibility = 1


# The car surface (5.2 M faces) and the iso-surface (4.1 M faces) are read once and shared by every view, so that a laptop
# holds one copy of each. Their faces are small enough to render without computed normals.
CAR = pv.XMLPolyDataReader(FileName=[str(next((POST / "flowCar").glob("*/car.vtp")))])


def ground(v):
    floor = pv.Plane(Origin=[-4.0, -5.0, GROUND_Z], Point1=[14.0, -5.0, GROUND_Z], Point2=[-4.0, 5.0, GROUND_Z])
    plain(pv.Show(floor, v), [0.16, 0.17, 0.20])


def camera_on_circle(v, azimuth_deg, elevation_deg, distance, focal=CAR_CENTRE):
    azimuth, elevation = np.radians(azimuth_deg), np.radians(elevation_deg)
    x, y, z = focal
    v.CameraFocalPoint = list(focal)
    v.CameraPosition = [x + distance * np.cos(elevation) * np.cos(azimuth), y + distance * np.cos(elevation) * np.sin(azimuth), z + distance * np.sin(elevation)]
    v.CameraViewUp = [0.0, 0.0, 1.0]
    v.CameraViewAngle = 30.0


def screenshot(target, path, resolution=(WIDTH, HEIGHT)):
    path.parent.mkdir(parents=True, exist_ok=True)
    pv.SaveScreenshot(str(path), target, ImageResolution=list(resolution), SeparatorWidth=2, SeparatorColor=[0.30, 0.32, 0.36])


def drag_by_iteration():
    values = {}
    for line in (POST / "forceCoeffsAll" / "0" / "coefficient.dat").read_text().splitlines():
        if line and not line.startswith("#"):
            fields = line.split()
            values[int(float(fields[0]))] = float(fields[1])
    return values


def iterations():
    """The centre plane seen from the side and the wheel-axle plane seen from above, one picture per saved iteration."""
    side = view(WIDTH, HEIGHT // 2)
    top = view(WIDTH, HEIGHT // 2)
    layout = pv.CreateLayout("iterations")
    layout.SplitVertical(0, 0.5)
    layout.AssignView(1, side)
    layout.AssignView(2, top)
    layout.SetSize(WIDTH, HEIGHT)

    readers = {}
    for name, v in (("centrePlane", side), ("wheelPlane", top)):
        readers[name] = pv.EnSightReader(CaseFileName=str(POST / "flowPlanes" / name / f"{name}.case"))
        shown = pv.Show(pv.MergeBlocks(Input=readers[name]), v)
        u_table = colour(shown, "POINTS", "U", "Turbo", U_RANGE)
        shown.SetScalarBarVisibility(v, False)

    # Seen from -y, the near half of the car would hide the centre plane: show only the far half (y > 0) behind it.
    far_half = pv.Clip(Input=CAR, ClipType="Plane", Invert=1)
    far_half.ClipType.Origin = [0.0, 0.0, 0.0]
    far_half.ClipType.Normal = [0.0, -1.0, 0.0]
    plain(pv.Show(far_half, side), GREY)
    plain(pv.Show(CAR, top), GREY)

    # Parallel projections of the same 13 m: the car and 7 m of its wake.
    scale = 13.0 * (HEIGHT / 2) / WIDTH / 2
    for v, focal, position, up in ((side, [4.5, 0.0, 1.3], [4.5, -40.0, 1.3], [0.0, 0.0, 1.0]), (top, [4.5, 0.0, 0.0], [4.5, 0.0, 40.0], [0.0, 1.0, 0.0])):
        v.CameraParallelProjection = 1
        v.CameraFocalPoint = focal
        v.CameraPosition = position
        v.CameraViewUp = up
        v.CameraParallelScale = scale

    text(side, "Side: centre plane y = 0", 20, GREY, location="Upper Right Corner")
    text(top, "Top: plane through the wheel axles, z = 0", 20, GREY, location="Upper Right Corner")
    text(top, FOOTER, 16, GREY, location="Lower Left Corner")
    scalar_bar(u_table, top, "Velocity magnitude (m/s)", [0.66, 0.12], "%-.0f")
    counter = text(side, "", 30, WHITE, bold=True)

    drag = drag_by_iteration()
    times = list(readers["centrePlane"].TimestepValues)
    frames = OUT_DIR / "frames-iterations"
    index = 0
    for time in times:
        iteration = int(round(time))
        counter.Text = f"simpleFoam iteration {iteration} of {int(round(times[-1]))}     Cd = {drag[iteration]:.4f}"
        side.ViewTime = time
        top.ViewTime = time
        first = frames / f"{index:04d}.png"
        screenshot(layout, first)
        repeats = 3 * FPS if time == times[-1] else FPS // 5
        for offset in range(1, repeats):
            shutil.copyfile(first, frames / f"{index + offset:04d}.png")
        index += repeats
    screenshot(layout, OUT_DIR / "stills" / "planes-iteration-150.png", (2 * WIDTH, 2 * HEIGHT))
    pv.RemoveLayout(layout)
    pv.Delete(side)
    pv.Delete(top)
    pv.Delete(far_half)


# Cuts each streamline into the dashes of one frame. The time along a streamline is the integral of ds / |U| (|U| at least
# 1 m/s, so that a line stopping at the wall does not stall); a dash is where (time - tau) mod period is below width * period.
DASHES = """
def _flow_dashes(source, target, tau, period, width):
    import numpy
    from vtkmodules.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkCommonDataModel import vtkCellArray
    points = vtk_to_numpy(source.GetPoints().GetData()).astype(float)
    velocity = vtk_to_numpy(source.GetPointData().GetArray("U")).astype(float)
    speed = numpy.maximum(numpy.linalg.norm(velocity, axis=1), 1.0)
    offsets = vtk_to_numpy(source.GetLines().GetOffsetsArray())
    connectivity = vtk_to_numpy(source.GetLines().GetConnectivityArray())
    runs = []
    for begin, end in zip(offsets[:-1], offsets[1:]):
        ids = connectivity[begin:end]
        if len(ids) < 2:
            continue
        step = numpy.linalg.norm(numpy.diff(points[ids], axis=0), axis=1) / (0.5 * (speed[ids][1:] + speed[ids][:-1]))
        inside = numpy.mod(numpy.concatenate([[0.0], numpy.cumsum(step)]) - tau, period) < width * period
        edges = numpy.flatnonzero(numpy.diff(numpy.concatenate([[0], inside.astype(numpy.int8), [0]])))
        runs += [ids[first:last] for first, last in zip(edges[0::2], edges[1::2]) if last - first >= 2]
    ids = numpy.concatenate(runs) if runs else numpy.zeros(0, dtype=numpy.int64)
    dash_points = vtkPoints()
    dash_points.SetData(numpy_to_vtk(points[ids], deep=1))
    cells = vtkCellArray()
    cells.SetData(numpy_to_vtkIdTypeArray(numpy.concatenate([[0], numpy.cumsum([len(run) for run in runs])]).astype(numpy.int64), deep=1), numpy_to_vtkIdTypeArray(numpy.arange(len(ids), dtype=numpy.int64), deep=1))
    target.SetPoints(dash_points)
    target.SetLines(cells)
    u = numpy_to_vtk(velocity[ids], deep=1)
    u.SetName("U")
    target.GetPointData().AddArray(u)
"""


def dash_script(tau):
    return DASHES + f"_flow_dashes(self.GetPolyDataInput(), self.GetPolyDataOutput(), {tau!r}, {DASH_PERIOD!r}, {DASH_WIDTH!r})\n"


def streamlines():
    """The car coloured by Cp, its streamlines, and dashes moving along them at the local speed."""
    v = view(WIDTH, HEIGHT)
    ground(v)
    body = pv.Show(CAR, v)
    cp_table = colour(body, "CELLS", "cp", "Cool to Warm", CP_RANGE)
    body.Specular = 0.3
    body.SetScalarBarVisibility(v, False)

    tracks = pv.XMLPolyDataReader(FileName=[str(next((POST / "sets" / "flowStreamLines").glob("*/*.vtp")))])
    lines = pv.Show(tracks, v)
    plain(lines, [0.85, 0.88, 0.95])
    lines.Opacity = 0.12

    dashes = pv.ProgrammableFilter(Input=tracks, OutputDataSetType="vtkPolyData", Script=dash_script(0.0))
    moving = pv.Show(dashes, v)
    u_table = colour(moving, "POINTS", "U", "Turbo", U_RANGE)
    moving.RenderLinesAsTubes = 1
    moving.LineWidth = 2.5
    moving.SetScalarBarVisibility(v, False)

    title = text(v, "Flow around the car after 150 iterations", 30, WHITE, bold=True)
    caption = text(v, f"Streamlines from a rake 0.7 m ahead of the car. The dashes move at the local flow speed, {SLOW_MOTION:.0f} times slower than real time.", 18, GREY, position=[0.01, 0.89])
    text(v, FOOTER, 16, GREY, location="Lower Left Corner")
    scalar_bar(u_table, v, "Velocity magnitude (m/s)", [0.66, 0.10], "%-.0f")
    scalar_bar(cp_table, v, "Pressure coefficient Cp on the car", [0.66, 0.22], "%-.1f")

    count = 14 * FPS
    for index in range(count):
        dashes.Script = dash_script(index / FPS / SLOW_MOTION)
        camera_on_circle(v, 215.0 + 120.0 * (0.5 - 0.5 * np.cos(np.pi * index / (count - 1))), 24.0, 10.5)
        screenshot(v, OUT_DIR / "frames-streamlines" / f"{index:04d}.png")
    camera_on_circle(v, 235.0, 24.0, 10.0)
    screenshot(v, OUT_DIR / "stills" / "streamlines-iteration-150.png", (2 * WIDTH, 2 * HEIGHT))

    pv.Hide(tracks, v)
    pv.Hide(dashes, v)
    pv.Hide(caption, v)
    title.Text = "Pressure coefficient on the car after 150 iterations"
    pv.GetScalarBar(u_table, v).Visibility = 0
    camera_on_circle(v, 215.0, 20.0, 8.0)
    screenshot(v, OUT_DIR / "stills" / "car-cp-iteration-150.png", (2 * WIDTH, 2 * HEIGHT))
    pv.Delete(v)


def wake():
    """The surface where the total pressure coefficient is 0: the boundary layer and the wake."""
    v = view(WIDTH, HEIGHT)
    ground(v)
    plain(pv.Show(CAR, v), GREY)
    iso = pv.XMLPolyDataReader(FileName=[str(next((POST / "flowWake").glob("*/totalPressureZero.vtp")))])
    above_ground = pv.Clip(Input=iso, ClipType="Plane", Invert=0)
    above_ground.ClipType.Origin = [0.0, 0.0, GROUND_Z + 0.03]
    above_ground.ClipType.Normal = [0.0, 0.0, 1.0]
    shown = pv.Show(above_ground, v)
    u_table = colour(shown, "POINTS", "U", "Turbo", U_RANGE)
    shown.Specular = 0.3
    shown.SetScalarBarVisibility(v, False)
    text(v, "Where the flow has lost its energy: total pressure coefficient = 0, iteration 150", 28, WHITE, bold=True)
    text(v, FOOTER, 16, GREY, location="Lower Left Corner")
    scalar_bar(u_table, v, "Velocity magnitude (m/s)", [0.66, 0.84], "%-.0f")
    # Aimed behind the car, so that the wake fits in the picture.
    camera_on_circle(v, 320.0, 24.0, 8.5, (3.2, 0.0, 0.2))
    screenshot(v, OUT_DIR / "stills" / "wake-total-pressure-iteration-150.png", (2 * WIDTH, 2 * HEIGHT))


iterations()
streamlines()
wake()
