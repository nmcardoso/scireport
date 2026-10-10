"""Sphinx configuration for the scireport documentation."""

from __future__ import annotations

import sys
from pathlib import Path

import scireport

sys.path.insert(0, str(Path(__file__).resolve().parent / '_ext'))

project = 'scireport'
author = 'N. Cardoso'
copyright = '2026, N. Cardoso'
release = scireport.__version__
version = '.'.join(release.split('.')[:2])

extensions = [
  'myst_parser',
  'sphinx.ext.autodoc',
  'sphinx.ext.napoleon',
  'sphinx.ext.viewcode',
  'sphinxcontrib.typer',
  'sphinx_llms_txt',
  'sphinx_markdown_builder',
  'site_assets',
]
source_suffix = {'.md': 'markdown'}
exclude_patterns = ['_build', '_ext']
myst_enable_extensions = ['colon_fence', 'deflist']
myst_heading_anchors = 3

napoleon_google_docstring = False
napoleon_numpy_docstring = True
autodoc_member_order = 'bysource'
typer_playwright_install = False

html_baseurl = 'https://nmcardoso.github.io/scireport/'
html_theme = 'furo'
html_title = f'scireport {release}'
html_theme_options = {
  'source_repository': 'https://github.com/nmcardoso/scireport/',
  'source_branch': 'main',
  'source_directory': 'docs/',
}

llms_txt_uri_template = '{base_url}{docname}.md'
llms_txt_title = 'scireport'
llms_txt_summary = (
  'Data-centric scientific report engine: one data file (a report bundle), a Jinja2 template and a '
  'layout are rendered to Markdown, HTML, LaTeX and PDF.'
)

linkcheck_ignore = [r'https://nmcardoso\.github\.io/scireport/.*']
