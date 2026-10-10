"""scireport: a data-centric scientific report engine.

One data file (a report bundle), a Jinja2 template and a layout are rendered to Markdown,
HTML, LaTeX and PDF. See ``docs/adr/`` for the design decisions.
"""

from __future__ import annotations

from scireport._version import __version__
from scireport.bundle import Bundle, open_bundle, write_bundle
from scireport.errors import (
  BundleError,
  Issue,
  KeyConflictError,
  ScireportError,
  SpecError,
  SpecVersionError,
)
from scireport.report import Report
from scireport.spec import SPEC_VERSION, Manifest, parse_manifest
from scireport.styles import figure, mplstyle, mplstyle_path, palette

__all__ = [
  'SPEC_VERSION',
  'Bundle',
  'BundleError',
  'Issue',
  'KeyConflictError',
  'Manifest',
  'Report',
  'ScireportError',
  'SpecError',
  'SpecVersionError',
  '__version__',
  'figure',
  'mplstyle',
  'mplstyle_path',
  'open_bundle',
  'palette',
  'parse_manifest',
  'write_bundle',
]
