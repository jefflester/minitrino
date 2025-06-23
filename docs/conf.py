"""Sphinx configuration for Minitrino documentation."""

import os
import sys

# -- Project information -----------------------------------------------------
project = "Minitrino"
author = "jefflester"


def _read_version_file():
    try:
        here = os.path.dirname(__file__)
        with open(os.path.abspath(os.path.join(here, "../src/lib/version")), "r") as f:
            return f.read().strip()
    except Exception:
        return "unknown"


release = _read_version_file()

# -- General configuration ---------------------------------------------------
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinxext.opengraph",
    "sphinx_copybutton",
]

# -- MyST configuration ------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",  # ::: for admonitions
    "deflist",  # definition lists
    "html_admonition",  # HTML-style admonitions
    "html_image",  # HTML-style images
    "substitution",  # |subst| replacements
    "tasklist",  # [ ] task lists
]
myst_heading_anchors = 4  # auto-anchor up to h4

# -- Paths -------------------------------------------------------------------
sys.path.insert(0, os.path.abspath("../src/cli"))

# -- Options for autodoc -----------------------------------------------------
autoclass_content = "both"
autodoc_member_order = "bysource"

# -- Options for HTML output -------------------------------------------------
html_theme = "furo"
pygments_dark_style = "github-dark"

# -- Other options -----------------------------------------------------------
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
