"""Copy the manuscript's figures from the reproduction output.

``paper/run_all.py`` writes every figure to ``paper/output/figures``
as PNG (600 dpi preview), PDF (used by LaTeX), editable SVG, and EPS
for pure vector figures. This script copies, for each
``\\plot{name}`` of ``paper.tex``, these files into ``Fig/`` and
reports figures that are missing.

    python paper/run_all.py
    python paper/manuscript/update_figures.py
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "output" / "figures"
TARGET = HERE / "Fig"
FORMATS = (".pdf", ".png", ".svg", ".eps")


def figure_names(tex: Path) -> list[str]:
    """Names of the figures included with ``\\plot`` in *tex*."""
    text = tex.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"\\plot\{([A-Za-z0-9_]+)\}", text)))


def main() -> int:
    TARGET.mkdir(exist_ok=True)
    missing = []
    names = figure_names(HERE / "paper.tex")
    for name in names:
        for suffix in FORMATS:
            src = SOURCE / f"{name}{suffix}"
            dst = TARGET / src.name
            if src.exists():
                shutil.copy2(src, dst)
            elif suffix == ".eps":
                # EPS is written only for pure vector figures.
                dst.unlink(missing_ok=True)
            else:
                missing.append(src.name)
    print(f"{len(names)} figures copied to {TARGET}")
    if missing:
        print("missing (run paper/run_all.py):", ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
