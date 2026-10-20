# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Run the team's figures.py for the deck: without the captions under the plots, in the deck's colours and number style.

usage: deck_figures.py <path/to/figures.py> <output_dir>

- Captions (figure text below the axes, y < 0) are dropped; the slides restate them at a readable size.
- The tier colours come from palette.py, and the labels that figures.py draws in red become navy (red is for what is slow
  or wrong on the slides), so the figures match the slide text.
- Labels follow the slides: s/step, no space before %, and a minus sign instead of a hyphen.
figures.py itself is unchanged, so the figures of the report keep their style.
"""

import importlib.util
import re
import sys
from pathlib import Path

import matplotlib
from matplotlib.figure import Figure
from matplotlib.text import Text

import palette

matplotlib.use("Agg")  # before figures.py imports pyplot
_figure_text = Figure.text
_set_text = Text.set_text


def text_above_axes(self, x, y, s, *args, **kwargs):
    if y < 0:  # caption under the plot
        return None
    return _figure_text(self, x, y, s, *args, **kwargs)


def set_text_deck_style(self, s):
    if isinstance(s, str):
        s = re.sub(r"(\d) %", r"\1%", s).replace("s / step", "s/step")
        s = re.sub(r"(?<![\w.])-(?=\d)", "−", s)
    return _set_text(self, s)


Figure.text = text_above_axes
Text.set_text = set_text_deck_style

src, out = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("team_figures", src)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
colours = {"BASELINE": palette.BASE, "BASIC": palette.BASIC, "BONUS": palette.BONUS, "ACCENT": palette.NAVY}
for name, colour in colours.items():
    setattr(module, name, "#" + colour)
module.PLACEMENT_CONFIGS.update({"Basic": module.BASIC, "Bonus": module.BONUS})  # built from the old colours at import
sys.argv = [str(src), str(out)]
module.main()
