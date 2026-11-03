"""Colours of the deck and of its figures (decklib.py, build_deck.py, deck_figures.py, deck_plots.py).

Text colours are deep enough for a projector, and black text is pure black (the user, 11/01). The three tiers warm up as the
work goes on, green, yellow, red, and none is the blue of the accent. Emphasis is the accent blue, never a heavier weight,
since all slide text is bold. Fills stay light.
"""

NAVY = "14378F"  # accent: emphasis, headings, bullets, table headers
BASE = "1F7A4A"  # Baseline (green)
BASIC = "A07800"  # Basic (deep yellow)
BONUS = "B3261E"  # Bonus (red)
BONUS_LIGHT = "EBA9A3"  # Bonus bars that are not the point of the chart
BONUS_TINT = "FBEBE9"  # Bonus boxes in diagrams
BONUS_LINE = "E3A39C"  # border of the Bonus boxes
INK = "000000"  # body text: pure black
MUTED = "4A4A4A"  # secondary text: captions, tools, units
FAINT = "8C8C8C"  # bars, dots and arrows that stay in the background
LIGHT = "F3F6FA"  # card and zebra fill
TINT = "E6ECF6"  # highlighted card fill
LINE = "D3DAE6"  # table rules and card borders
GRID = "E4E9F1"  # chart gridlines and bar tracks
WHITE = "FFFFFF"
COMPUTATION = "A9BCDD"  # computation in the call-stack figures (the phase bars and the flame graph)
MPI = "C7A3C2"  # MPI in the call-stack figures
# the node figures (the user's hand edit of the memory-limit slide, 11/02): the cores that run ranks are NAVY and the memory
# channels in use green like a circuit board, the theme's green darker by 25% as the user chose it
MEMORY = "548235"
# pure red, as the user chose it by hand: what was halved on the memory-limit slide (11/02), the gain of each source
# change drawn in pictures (11/03), and the arrows over the per-job plots with their changes (11/03 19:19)
RED = "FF0000"
# the headings over the decomposition pictures, the blue the user gave them by hand (11/03 19:19)
PICTURE = "003894"
