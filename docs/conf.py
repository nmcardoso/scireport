"""Sphinx configuration for the scireport documentation."""

from __future__ import annotations

import scireport

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
  'sphinx_llms_txt',
  'sphinx_markdown_builder',
]
source_suffix = {'.md': 'markdown'}
exclude_patterns = ['_build']
myst_enable_extensions = ['colon_fence', 'deflist']
myst_heading_anchors = 3

html_theme = 'furo'
html_title = f'scireport {release}'

llms_txt_title = 'scireport'
llms_txt_summary = (
  'Data-centric scientific report engine: one data file (a report bundle), a Jinja2 template and a '
  'layout are rendered to Markdown, HTML, LaTeX and PDF.'
)

linkcheck_ignore = [r'https://nmcardoso\.github\.io/scireport/.*']
