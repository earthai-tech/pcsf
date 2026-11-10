# Manuscript: Geophysics (SEG), Software and Algorithms

*A geometry-aware exchange format for electromagnetic inversion
models.*

| File | Content |
|---|---|
| `paper.tex` | the manuscript (SEG `geophysics` class, `manuscript` option) |
| `pcsf.bib` | bibliography; entries marked `VERIFY` must be checked against the publisher record |
| `Fig/` | the 9 figures: PDF (used by LaTeX), PNG preview (600 dpi), editable SVG (text as text) and EPS |
| `listings/` | the inversion record printed in the appendix |
| `geophysics.cls`, `seg.sty`, `seg.bst` | SEG class and styles (S. Fomel, LaTeX Project Public License 1.3, unmodified) |
| `update_figures.py` | copies the figures from the reproduction output into `Fig/` |
| `notes/` | the authors' working notes (not in git) |

## Build

```bash
pdflatex paper && bibtex paper && pdflatex paper && pdflatex paper
```

`\reviewtrue` (the default, near the top of `paper.tex`) builds the
double-anonymous review version: no acknowledgments and an anonymised
code link. `\reviewfalse` builds the accepted version. Red
`[PENDING: ...]` markers flag information only the authors can
supply.

## Figures

Every figure is produced by the scripts of `paper/` (see
`paper/README.md`):

```bash
python paper/run_all.py
python paper/manuscript/update_figures.py
```

The storage benchmark (Figure of Test 4) reports times that depend on
the computer; the manuscript shows the run recorded in
`paper/expected/test4_storage.csv`, redrawn with
`python paper/scripts/test4_storage_benchmark.py plot` after copying
that file to `paper/output/results/`.
