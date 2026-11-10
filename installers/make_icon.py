"""Draw the PCSF Studio icon (PNG and multi-size ICO).

The icon is a 4 x 4 block of resistivity colours (the ``jet_r`` map
of the Studio) with a dark frame: a model section in miniature. Run
from the repository root; it writes ``installers/assets/`` and
the copy in ``src/pcsf/studio/resources/``.

    python installers/make_icon.py
"""

from pathlib import Path

import numpy as np
from matplotlib import colormaps
from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent / "assets"
#: Copy shipped with the package, used as the window icon.
PACKAGE = (
    Path(__file__).resolve().parents[1] / "src/pcsf/studio/resources"
)
SIZE = 256
# log10 resistivity pattern: a conductor under a resistive cover
PATTERN = np.array(
    [
        [3.6, 3.8, 3.7, 3.5],
        [2.9, 2.2, 2.4, 3.1],
        [2.6, 1.6, 1.9, 2.8],
        [3.0, 2.7, 2.9, 3.3],
    ]
)


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    cmap = colormaps["jet_r"]
    lo, hi = 1.5, 4.0
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad, gap = 16, 6
    cell = (SIZE - 2 * pad - 3 * gap) / 4
    draw.rounded_rectangle(
        [4, 4, SIZE - 5, SIZE - 5], radius=36, fill=(30, 34, 44, 255)
    )
    for i in range(4):
        for j in range(4):
            r, g, b, _ = cmap((PATTERN[i, j] - lo) / (hi - lo))
            x0 = pad + j * (cell + gap)
            y0 = pad + i * (cell + gap)
            draw.rounded_rectangle(
                [x0, y0, x0 + cell, y0 + cell],
                radius=10,
                fill=(int(r * 255), int(g * 255), int(b * 255), 255),
            )
    img.save(ASSETS / "pcsf-studio.png")
    PACKAGE.mkdir(exist_ok=True)
    img.save(PACKAGE / "pcsf-studio.png")
    img.save(
        ASSETS / "pcsf-studio.ico",
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)],
    )
    print(f"wrote {ASSETS}")


if __name__ == "__main__":
    main()
