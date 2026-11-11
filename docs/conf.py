"""Sphinx configuration of the pcsf documentation.

Build locally with::

    pip install -e ".[docs]"
    sphinx-build -b html docs docs/_build/html
    sphinx-build -b doctest docs docs/_build/doctest

Read the Docs builds the same sources from ``.readthedocs.yaml``.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The sources are imported from the checkout, so that the pages
# always describe the code they sit next to.
sys.path.insert(0, str(ROOT / "src"))

from pcsf._version import FORMAT_VERSION, __version__  # noqa: E402

# ------------------------------------------------------------ project
project = "pcsf"
author = "Kouao Laurent Kouadio"
copyright = f"{date.today().year}, {author}"
release = __version__
version = ".".join(__version__.split(".")[:2])

# ------------------------------------------------------------ general
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "numpydoc",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
]
# Pages are reStructuredText; Markdown is parsed only where a page
# includes the specification or the changelog, kept in one place.
source_suffix = {".rst": "restructuredtext"}
root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]
default_role = "obj"
rst_epilog = f"""
.. |format_version| replace:: {FORMAT_VERSION}
.. |release| replace:: {release}
"""

# ------------------------------------------------------- autodoc, API
autosummary_generate = True
autodoc_typehints = "none"  # numpydoc sections give the types
autodoc_member_order = "bysource"
autodoc_default_options = {"show-inheritance": True}
# PCSF Studio needs Qt; its pages are built without it.
autodoc_mock_imports = [
    "PySide6",
    "matplotlib.backends.backend_qtagg",
]
numpydoc_show_class_members = False
numpydoc_class_members_toctree = False
numpydoc_xref_param_type = True
numpydoc_xref_ignore = {
    "of",
    "or",
    "optional",
    "default",
    "shape",
    "path-like",
    "array-like",
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "h5py": ("https://docs.h5py.org/en/stable", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
}
# A build without network still succeeds, with fewer links.
intersphinx_timeout = 10

# ------------------------------------------------------------ doctest
doctest_global_setup = """
import os, tempfile
import numpy as np
import pcsf
np.set_printoptions(precision=4, suppress=True)
_cwd = os.getcwd()
os.chdir(tempfile.mkdtemp())
"""
doctest_global_cleanup = "os.chdir(_cwd)"

# -------------------------------------------------------------- myst
myst_heading_anchors = 3
suppress_warnings = ["myst.xref_missing", "myst.header"]

# -------------------------------------------------------------- HTML
html_theme = "pydata_sphinx_theme"
html_title = f"pcsf {release}"
html_logo = "_static/pcsf-studio.svg"
html_favicon = "_static/pcsf-studio.svg"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
# Version switcher. Every version reads the list of the latest build,
# so a new release only needs an entry in _static/switcher.json (and
# the version activated on Read the Docs). Read the Docs sets
# READTHEDOCS_VERSION to the slug of the version being built
# ("latest", "stable", "dev", "v0.1.0"); local builds use "dev".
SWITCHER_URL = "https://pcsf.readthedocs.io/en/latest/_static/switcher.json"
switcher_version = os.environ.get("READTHEDOCS_VERSION", "dev")

html_theme_options = {
    "logo": {"text": "pcsf"},
    "github_url": "https://github.com/earthai-tech/pcsf",
    "navbar_align": "left",
    "switcher": {
        "json_url": SWITCHER_URL,
        "version_match": switcher_version,
    },
    # The list is read from the published site; a build made before
    # the list is online must not fail on the warning.
    "check_switcher": False,
    "navbar_end": [
        "version-switcher",
        "theme-switcher",
        "navbar-icon-links",
    ],
    "show_version_warning_banner": True,
    "show_toc_level": 2,
    "navigation_with_keys": False,
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version"],
}
html_context = {
    "github_user": "earthai-tech",
    "github_repo": "pcsf",
    "github_version": "master",
    "doc_path": "docs",
}
copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True
