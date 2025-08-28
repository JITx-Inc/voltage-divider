# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Add jitx source to import path
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path("..", "..", "src").resolve()))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "jitxlib-voltage-divider"
copyright = "2025, JITX Inc"  # noqa: A001
author = "JITX Inc"
version = "0.1"
release = "0.1.0dev1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

needs_sphinx = "8.1"
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.githubpages",
    "sphinx_autodoc_typehints",
]
myst_enable_extensions = ["colon_fence"]
myst_links_external_new_tab = True

source_suffix = [".rst", ".md"]
html_static_path = ["_static"]
templates_path = ["_templates"]
exclude_patterns = []

language = "en"
html_show_sphinx = False
keep_warnings = True  # keep warnings in rendered documents - disable for prod release
nitpicky = True  # extra warnings

latex_engine = "xelatex"
# latex_logo = "images/favicon.png"
latex_elements = {
    "fontpkg": """
\\setmainfont{FreeSerif}[
  UprightFont    = *,
  ItalicFont     = *Italic,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldItalic
]
\\setsansfont{FreeSans}[
  UprightFont    = *,
  ItalicFont     = *Oblique,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldOblique,
]
\\setmonofont{FreeMono}[
  UprightFont    = *,
  ItalicFont     = *Oblique,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldOblique,
]
""",
}

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    # "announcement": "This is an annoucement",
    # "show_version_warning_banner": True,
    # "logo": {
    #    "alt_text": "JITX Documentation - Home",
    #    "image_light": "images/docs_jitx_logo_light.svg",
    #    "image_dark": "images/docs_jitx_logo_dark.svg",
    # },
    # "content_footer_items": ["last-updated"],
    "show_nav_level": 1,
    "navigation_depth": 6,
    "show_toc_level": 4,  # right sidebar
}
