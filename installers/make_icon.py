"""Render the PCSF Studio icons from the SVG logo.

The logo, ``src/pcsf/studio/resources/pcsf-studio.svg``, is the only
source: a section of resistivity cells (``jet_r``, conductors in red)
under a topography line with three stations. This script renders it
with Qt's SVG renderer into

- ``installers/assets/pcsf-studio.png`` (256 px, Linux, AppImage);
- ``installers/assets/pcsf-studio.ico`` (16-256 px, Windows);
- ``src/pcsf/studio/resources/pcsf-studio.png`` (fallback window
  icon).

Run from the repository root with PySide6 and Pillow installed::

    python installers/make_icon.py
"""

import io
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG = ROOT / "src/pcsf/studio/resources/pcsf-studio.svg"
ASSETS = ROOT / "installers/assets"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def render(size: int) -> bytes:
    """PNG bytes of the logo at *size* x *size* pixels."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(str(SVG)).render(painter)
    painter.end()
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(data)


def main() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PIL import Image
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication([])  # noqa: F841 (needed by QPainter)
    ASSETS.mkdir(exist_ok=True)
    big = render(256)
    for dst in (ASSETS / "pcsf-studio.png", SVG.with_suffix(".png")):
        dst.write_bytes(big)
    frames = [Image.open(io.BytesIO(render(s))) for s in SIZES]
    frames[-1].save(
        ASSETS / "pcsf-studio.ico",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[:-1],
    )
    print(f"wrote icons from {SVG.name}")


if __name__ == "__main__":
    main()
