# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Put slide renders side by side for a quick look: qa_grid.py OUT.jpg COLUMNS slide-01.png slide-02.png ...

The renders come from render.ps1. Look at each slide at full size too: a grid hides small overflows.
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

out, columns, files = Path(sys.argv[1]), int(sys.argv[2]), [Path(f) for f in sys.argv[3:]]
images = [Image.open(f).convert("RGB") for f in files]
cell_w = 800
cell_h = int(cell_w * images[0].height / images[0].width)
rows = (len(images) + columns - 1) // columns
sheet = Image.new("RGB", (columns * (cell_w + 10) + 10, rows * (cell_h + 34) + 10), "white")
draw = ImageDraw.Draw(sheet)
for i, (path, image) in enumerate(zip(files, images)):
    x, y = 10 + (i % columns) * (cell_w + 10), 10 + (i // columns) * (cell_h + 34)
    draw.text((x, y), path.name, fill="black")
    sheet.paste(image.resize((cell_w, cell_h), Image.LANCZOS), (x, y + 22))
sheet.save(out, quality=88)
print(out)
