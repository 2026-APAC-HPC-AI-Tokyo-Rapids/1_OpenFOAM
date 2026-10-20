# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow"]
# ///
"""Measure the empty band under each slide's content: qa_gaps.py DIR (the slide-NN.png files from render.ps1).

Prints, per slide, the distance in inches from the lowest content to the bottom edge, for the whole width and for four
vertical strips. The title, the message line, the template's left bar and the slide number are not counted.
Content slides end about 0.6-0.8 in above the edge: the bottom line at 7.0 in plus the descent of the last line of text.
A larger value means a band was left empty, unless that strip only holds a short LESSON pill or vertically centred notes.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image


def gap(ink, per_inch):
    rows = np.flatnonzero(ink.any(axis=1))
    return (ink.shape[0] - (rows.max() if rows.size else 0)) / per_inch


for png in sorted(Path(sys.argv[1]).glob("slide-*.png")):
    ink = np.asarray(Image.open(png).convert("L")) < 235
    h, w = ink.shape
    per_inch = h / 7.5
    ink[: int(h * 0.18), :] = False  # title and message line
    ink[:, : int(w * 0.013)] = False  # left bar
    ink[int(h * 0.94) :, int(w * 0.97) :] = False  # slide number
    strips = [gap(ink[:, int(w * (0.04 + 0.235 * k)) : int(w * (0.04 + 0.235 * (k + 1)))], per_inch) for k in range(4)]
    print(f"{png.stem}: {gap(ink, per_inch):.2f} in   strips " + " ".join(f"{g:.2f}" for g in strips))
