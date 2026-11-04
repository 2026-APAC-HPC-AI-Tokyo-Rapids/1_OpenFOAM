# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""The deck's per-job plots for the technical report: deck_plots.py as it is, except that the arrows, the changes and the
speedups, which the deck lays over the plots as movable slide shapes, are drawn into the images here, and the images are
saved at 200 dpi.

usage: report_plots.py <deck dir> <output dir>
"""
import sys
from pathlib import Path

deck = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(deck))
source = (deck / "deck_plots.py").read_text(encoding="utf-8")
start, end = source.index("def save(figure, name):"), source.index("def percent(")
report_marks = '''
def save(figure, name):
    figure.savefig(OUT / f"{name}.png", dpi=200, facecolor="white")
    plt.close(figure)


def layout(figure, name, arrows=(), texts=(), lift=()):
    """Draw what the deck lays over the plot into the image: the layout is frozen first, so that the marks stand where the
    deck's shapes would. Texts that the deck lifts out of the image (lift) simply stay in it."""
    from matplotlib.patches import FancyArrowPatch
    figure.canvas.draw()
    figure.set_layout_engine("none")
    to_figure = figure.transFigure.inverted()

    def at(axis, point):
        return tuple(point) if axis is None else tuple(to_figure.transform(axis.transData.transform(point)))

    for axis, start, end in arrows:
        figure.add_artist(FancyArrowPatch(at(axis, start), at(axis, end), transform=figure.transFigure, arrowstyle="-|>", mutation_scale=20, color="#" + palette.RED, linewidth=3.2, shrinkA=0, shrinkB=0, zorder=10))
    for axis, point, text, options in texts:
        x, y = at(axis, point)
        color = options.get("color", palette.INK)
        figure.text(x, y, text, ha={"l": "left", "c": "center", "r": "right"}[options.get("align", "l")], va={"t": "top", "m": "center", "b": "bottom"}[options.get("anchor", "b")], fontsize=options.get("size", 12), color=color if color.startswith("#") else "#" + color, fontweight="bold", linespacing=1.05, zorder=11)


'''
source = source[:start] + report_marks + source[end:]
sys.argv = [str(deck / "deck_plots.py"), str(deck.parent / "figures.py"), str(out)]
exec(compile(source, str(deck / "deck_plots.py"), "exec"), {"__name__": "__main__", "__file__": str(deck / "deck_plots.py")})
print("\n".join(sorted(p.name for p in out.glob("*.png"))))
