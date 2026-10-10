"""scireport: a data-centric scientific report engine.

One data file (a report bundle), a Jinja2 template and a layout are rendered to Markdown,
HTML, LaTeX and PDF (and, through pandoc, Word, OpenDocument and EPUB). See ``docs/adr/`` for
the design decisions.

Everything in ``__all__`` is the public API: it follows semantic versioning (ADR-0008), and a
test compares it with a committed snapshot. Anything else, including every ``scireport.<module>``
not re-exported here, may change between minor versions.

Typical use::

    from scireport import Report, open_bundle, render_bundle

    report = Report('Cross-match report').add_number('crossmatch.n_pairs', 3061)
    report.write('crossmatch.scireport.zip')
    with open_bundle('crossmatch.scireport.zip') as bundle:
        render_bundle(bundle, formats=['md', 'html']).write('out')
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from scireport._version import __version__
from scireport.bundle import Bundle, open_bundle, write_bundle
from scireport.errors import (
  BundleError,
  ExportError,
  Issue,
  KeyConflictError,
  MissingDependencyError,
  PandocError,
  PdfError,
  PreprocessError,
  PreprocessRunError,
  RenderError,
  ScireportError,
  SpecError,
  SpecVersionError,
  TemplateError,
)
from scireport.report import Report
from scireport.spec import SPEC_VERSION, Manifest, parse_manifest
from scireport.styles import figure, mplstyle, mplstyle_path, palette

if TYPE_CHECKING:
  from scireport.export import ExportResult, export_tex, write_export
  from scireport.preprocess import preprocess_bundle, preprocessor
  from scireport.render import RenderResult, list_layouts, list_templates, render_bundle
  from scireport.render.pipeline import check_bundle
  from scireport.validate import ValidationReport

_LAZY = {
  'ExportResult': 'scireport.export',
  'ValidationReport': 'scireport.validate',
  'RenderResult': 'scireport.render',
  'check_bundle': 'scireport.render.pipeline',
  'export_tex': 'scireport.export',
  'list_layouts': 'scireport.render',
  'list_templates': 'scireport.render',
  'preprocess_bundle': 'scireport.preprocess',
  'preprocessor': 'scireport.preprocess',
  'render_bundle': 'scireport.render',
  'write_export': 'scireport.export',
}
"""Public names that load their module on first use, so that ``import scireport`` stays fast."""

__all__ = [
  'SPEC_VERSION',
  'Bundle',
  'BundleError',
  'ExportError',
  'ExportResult',
  'Issue',
  'KeyConflictError',
  'Manifest',
  'MissingDependencyError',
  'PandocError',
  'PdfError',
  'PreprocessError',
  'PreprocessRunError',
  'RenderError',
  'RenderResult',
  'Report',
  'ScireportError',
  'SpecError',
  'SpecVersionError',
  'TemplateError',
  'ValidationReport',
  '__version__',
  'check_bundle',
  'export_tex',
  'figure',
  'list_layouts',
  'list_templates',
  'mplstyle',
  'mplstyle_path',
  'open_bundle',
  'palette',
  'parse_manifest',
  'preprocess_bundle',
  'preprocessor',
  'render_bundle',
  'write_bundle',
  'write_export',
]


def __getattr__(name: str) -> Any:
  """Load the heavier public names (rendering, export, pre-processing) on first use."""
  module = _LAZY.get(name)
  if module is None:
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
  value = getattr(importlib.import_module(module), name)
  globals()[name] = value
  return value


def __dir__() -> list[str]:
  """List the public names, lazy ones included."""
  return sorted(__all__)
