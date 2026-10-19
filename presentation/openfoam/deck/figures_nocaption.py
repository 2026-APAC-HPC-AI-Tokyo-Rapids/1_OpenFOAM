# /// script
# requires-python = ">=3.11"
# dependencies = ["matplotlib>=3.8"]
# ///
"""Run the team's figures.py, but drop the figure-level captions (figure.text below the axes, y < 0).

usage: figures_nocaption.py <path/to/figures.py> <output_dir>
The captions are restated on the slides at a readable size instead.
"""
import importlib.util
import sys
from pathlib import Path

import matplotlib
from matplotlib.figure import Figure

matplotlib.use("Agg")  # before figures.py imports pyplot
_orig_text = Figure.text


def _text(self, x, y, s, *args, **kwargs):
    if y < 0:  # caption under the plot
        return None
    return _orig_text(self, x, y, s, *args, **kwargs)


Figure.text = _text

src, out = Path(sys.argv[1]), Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("team_figures", src)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.argv = [str(src), str(out)]
module.main()
