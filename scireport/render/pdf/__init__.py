"""The PDF engines (ADR-0004): WeasyPrint prints the HTML output, LaTeX compiles the TeX project.

PDF is not rendered from the template: it is made from another output. The ``weasyprint`` engine
prints the self-contained HTML (CSS Paged Media, so it reproduces the MOSAICS look) and the
``latex`` engine runs ``latexmk`` on the LaTeX project. Both are optional dependencies, imported
or started only when a PDF is asked for; a missing system dependency (pango, TeX Live) is
:class:`~scireport.errors.MissingDependencyError` with an install hint and exit code 3.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

PdfEngine = Literal['weasyprint', 'latex']
PDF_ENGINES: tuple[PdfEngine, ...] = ('weasyprint', 'latex')
"""The PDF engines, WeasyPrint first (the default)."""
LatexEngine = Literal['lualatex', 'xelatex', 'pdflatex']
LATEX_ENGINES: tuple[LatexEngine, ...] = ('lualatex', 'xelatex', 'pdflatex')
"""The TeX engines ``latexmk`` can run, LuaLaTeX first (the default)."""
PDF_NAME = 'report.pdf'
"""Name of the PDF inside its output folder."""
EPOCH_DEFAULT = 315532800
"""1980-01-01T00:00:00Z: the ``SOURCE_DATE_EPOCH`` used when nothing better is known."""


@contextmanager
def fixed_epoch(epoch: int) -> Iterator[None]:
  """Set ``SOURCE_DATE_EPOCH`` for the duration of a ``with`` block, then restore it.

  fontTools, which WeasyPrint uses to subset fonts when HarfBuzz-Subset is missing, stamps the
  ``head`` table of every embedded font with the current time unless this variable is set.

  Parameters
  ----------
  epoch : int
      Seconds since 1970-01-01T00:00:00Z.

  Yields
  ------
  None
      Nothing; the variable is set while the block runs.
  """
  before = os.environ.get('SOURCE_DATE_EPOCH')
  os.environ['SOURCE_DATE_EPOCH'] = str(epoch)
  try:
    yield
  finally:
    if before is None:
      os.environ.pop('SOURCE_DATE_EPOCH', None)
    else:
      os.environ['SOURCE_DATE_EPOCH'] = before


def source_date_epoch(date: str | None) -> int:
  """Choose the ``SOURCE_DATE_EPOCH`` of a build.

  Parameters
  ----------
  date : str or None
      The ``meta.date`` of the bundle (ISO 8601), or None.

  Returns
  -------
  int
      The environment's ``SOURCE_DATE_EPOCH`` when it is set; otherwise midnight UTC of ``date``;
      otherwise 1980-01-01. Never the wall clock.
  """
  given = os.environ.get('SOURCE_DATE_EPOCH', '')
  if given.isdecimal():
    return int(given)
  if date:
    from datetime import UTC, datetime

    try:
      stamp = datetime.fromisoformat(date.replace('Z', '+00:00'))
    except ValueError:
      return EPOCH_DEFAULT
    return int((stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)).timestamp())
  return EPOCH_DEFAULT
