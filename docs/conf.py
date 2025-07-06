"""Sphinx configuration for Minitrino documentation."""

import os
import sys

# -- Project information
# -----------------------------------------------------
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


# -- Extensions
# ---------------------------------------------------
extensions = [
    "ablog",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_favicon",
    "sphinx_togglebutton",
    "sphinxext.opengraph",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.linkcode",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.graphviz",
]


# -- MyST configuration
# ------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 4
myst_substitutions = {
    "coordinator_shell": """
Open a shell to the coordinator:

```sh
minitrino exec -i
```
""",
    "connect_trino_cli": """
Connect to the coordinator container's Trino CLI:

```sh
minitrino exec -i 'trino-cli'
```
""",
    "connect_trino_cli_admin": """
Connect to the coordinator container's Trino CLI as the `admin` user:

```sh
minitrino exec -i 'trino-cli --user admin'
```
""",
    "starburst_license_warning": """
:::{admonition} License Required
:class: warning

This module requires a Starburst distribution and license.
:::
""",
    "persistent_storage_warning": """
:::{admonition} Module Uses **Persistent Storage**
:class: warning

This module uses named volumes to persist data. To delete these volumes, run:

```sh
minitrino remove --volumes --module ${module}
```
:::
""",
}


# -- Paths
# -------------------------------------------------------------------
sys.path.insert(0, os.path.abspath("../src/cli"))


# -- Autodoc Options
# -----------------------------------------------------
autoclass_content = "both"
autodoc_member_order = "bysource"


# -- HTML Options
# -------------------------------------------------
html_theme = "pydata_sphinx_theme"
pygments_dark_style = "github-dark"

html_theme_options = {
    "logo": {
        "text": "Minitrino",
    },
    "external_links": [
        {
            "url": "https://github.com/jefflester/minitrino",
            "name": "GitHub",
        }
    ],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/jefflester/minitrino",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "PyPi",
            "url": "https://pypi.org/project/minitrino",
            "icon": "fa-solid fa-box",
        },
        {
            "name": "Starburst Docs",
            "url": "https://docs.starburst.io/latest/index.html",
            "icon": "fa-solid fa-star-of-life",
        },
        {
            "name": "Trino Docs",
            "url": "https://trino.io/docs/current/index.html",
            "icon": "fa-solid fa-book",
        },
    ],
    "header_links_before_dropdown": 4,
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "navbar_align": "left",
    "announcement": None,
    "show_version_warning_banner": True,
    "navbar_center": ["version-switcher", "navbar-nav"],
    "footer_start": ["copyright"],
    "footer_center": ["sphinx-version"],
    "secondary_sidebar_items": {
        "**/*": ["page-toc", "edit-this-page", "sourcelink"],
        "examples/no-sidebar": [],
    },
    "switcher": {
        "json_url": "_static/switcher.json",
        "version_match": release,
    },
}


# -- Linkcode Options
# -------------------------------------------------
def linkcode_resolve(domain, info):
    if domain != "py":
        return None
    if not info["module"]:
        return None
    filename = info["module"].replace(".", "/")
    tag = release
    return f"https://github.com/jefflester/minitrino/blob/{tag}/src/cli/{filename}.py"


# -- Misc. options
# -----------------------------------------------------------
root_doc = "home"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]
html_static_path = ["_static"]
templates_path = ["_templates"]
html_css_files = [
    "custom.css",
]
html_logo = "_static/minitrino-small.svg"
html_favicon = "_static/minitrino-small.svg"
# -- Sidebars and context for advanced nav/footer --
html_sidebars = {}
html_context = {
    "github_user": "jefflester",
    "github_repo": "minitrino",
    "github_version": "main",
    "doc_path": "docs",
}
