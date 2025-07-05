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
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.linkcode",
    "sphinxext.opengraph",
    "sphinx_copybutton",
    # PyData theme advanced extensions
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.graphviz",
    "sphinxext.rediraffe",
    "sphinx_design",
    "sphinx_togglebutton",
    "ablog",
    "sphinx_favicon",
    # Optionally add more as needed
]

# -- MyST configuration
# ------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",  # ::: for admonitions
    "deflist",  # definition lists
    "html_admonition",  # HTML-style admonitions
    "html_image",  # HTML-style images
    "substitution",  # |subst| replacements
    "tasklist",  # [ ] task lists
]
myst_heading_anchors = 4  # auto-anchor up to h4
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
    # Keep your logo and branding
    "logo": {
        "text": "Minitrino",
    },
    # Advanced PyData theme options
    "external_links": [
        # Add your own links here if desired
    ],
    "header_links_before_dropdown": 4,
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
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "navbar_align": "left",
    "announcement": None,  # Set to a URL or string if you want an announcement bar
    "show_version_warning_banner": True,
    "navbar_center": ["version-switcher", "navbar-nav"],
    "footer_start": ["copyright"],
    "footer_center": ["sphinx-version"],
    "secondary_sidebar_items": {
        "**/*": ["page-toc", "edit-this-page", "sourcelink"],
    },
    "switcher": {
        "json_url": "_static/switcher.json",  # Update as needed
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

root_doc = "home"
# -----------------------------------------------------------

# Minimal rediraffe config to silence warning
rediraffe_redirects = {}
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]
html_static_path = ["_static"]
html_css_files = [
    "hide-color-mode.css",
]
html_js_files = [
    ("custom-icons.js", {"defer": "defer"}),
]

html_logo = "_static/minitrino-small.svg"
html_favicon = "_static/minitrino-small.svg"

# -- Sidebars and context for advanced nav/footer --
html_sidebars = {
    # Example: add custom sidebars if desired
}

html_context = {
    "github_user": "jefflester",
    "github_repo": "minitrino",
    "github_version": "main",
    "doc_path": "docs",
}
