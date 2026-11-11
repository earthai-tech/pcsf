"""Make the links of README.md absolute, for the page on PyPI.

The README uses paths relative to the repository (``docs/_static/
logo/pcsf-logo.svg``, ``CHANGELOG.md``), which GitHub renders on any
branch, also while the repository is private. PyPI has no
repository to resolve them against, so before a build the release
workflow rewrites them to URLs of the commit being published:
images to ``raw.githubusercontent.com``, other files to
``github.com/.../blob``. Anchors (``#...``) and absolute URLs are
left alone.

    python tools/pypi_readme.py README.md <commit or tag>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = "earthai-tech/pcsf"
_IMAGE = (".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp")


def _absolute(target: str, ref: str) -> str:
    if re.match(r"^([a-z][a-z0-9+.-]*:|#|/)", target, re.I):
        return target
    path = target.lstrip("./")
    if path.split("#")[0].lower().endswith(_IMAGE):
        return f"https://raw.githubusercontent.com/{REPO}/{ref}/{path}"
    return f"https://github.com/{REPO}/blob/{ref}/{path}"


def rewrite(text: str, ref: str) -> str:
    """Return *text* with its relative links made absolute.

    Parameters
    ----------
    text : str
        Markdown with inline HTML.
    ref : str
        Commit, tag or branch the links point to.

    Returns
    -------
    str
        The rewritten text.

    Examples
    --------
    >>> rewrite('<img src="docs/a.svg"/> [log](CHANGELOG.md)', "v1")
    ... # doctest: +NORMALIZE_WHITESPACE
    '<img src="https://raw.githubusercontent.com/earthai-tech/pcsf/v1/docs/a.svg"/>
     [log](https://github.com/earthai-tech/pcsf/blob/v1/CHANGELOG.md)'
    """
    text = re.sub(
        r'\b(src|srcset|href)="([^"]+)"',
        lambda m: f'{m.group(1)}="{_absolute(m.group(2), ref)}"',
        text,
    )
    return re.sub(
        r"\]\(([^)\s]+)\)",
        lambda m: f"]({_absolute(m.group(1), ref)})",
        text,
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path, ref = Path(argv[0]), argv[1]
    path.write_text(
        rewrite(path.read_text(encoding="utf-8"), ref),
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
