"""The WeasyPrint engine: self-contained HTML in, PDF bytes out (ADR-0004).

WeasyPrint is imported only here and only when a PDF is asked for: it costs about a second to
load and it needs the pango system libraries. When they are missing the import (or the first
call into them) fails with an ``OSError`` or ``ImportError``; both become
:class:`~scireport.errors.MissingDependencyError` with the install command for the platform.

Documented limits of the service: none (a local library, no network). The HTML is rendered with
no base URL and no external resource: fonts and pictures are ``data:`` URIs, so a render never
touches the network or the file system.
"""

from __future__ import annotations

import logging
import sys
from importlib import metadata
from typing import Any

from scireport.errors import Issue, MissingDependencyError, PdfError
from scireport.logging_utils import get_logger

log = get_logger(__name__)

INSTALL_HINT = {
  'linux': 'Install pango, for example: sudo apt install libpango-1.0-0 libpangoft2-1.0-0 '
  'libharfbuzz-subset0 (Debian, Ubuntu) or sudo dnf install pango (Fedora).',
  'darwin': 'Install pango with Homebrew: brew install pango (and set '
  'DYLD_FALLBACK_LIBRARY_PATH=$(brew --prefix)/lib).',
  'win32': 'Install pango with MSYS2 (pacman -S mingw-w64-ucrt-x86_64-pango) and set '
  'WEASYPRINT_DLL_DIRECTORIES to its ucrt64\\bin folder. See '
  'https://doc.courtbouillon.org/weasyprint/stable/first_steps.html',
}
"""Install command per ``sys.platform`` prefix."""


def weasyprint_version() -> str:
  """Return the installed WeasyPrint version, or an empty string when it is not installed."""
  try:
    return metadata.version('weasyprint')
  except metadata.PackageNotFoundError:
    return ''


def html_to_pdf(html: str) -> tuple[bytes, list[Issue]]:
  """Print a self-contained HTML document to PDF.

  Parameters
  ----------
  html : str
      The document, with CSS, fonts and pictures inlined.

  Returns
  -------
  tuple
      The PDF bytes and the warnings WeasyPrint logged while printing (as issues, empty when
      there were none). The same HTML gives the same bytes: the document carries no run-time
      date and WeasyPrint adds none (checked in ``tests/integration/test_pdf_weasyprint.py``).

  Raises
  ------
  MissingDependencyError
      With ``E901`` when WeasyPrint or the pango libraries are not installed.
  PdfError
      With ``E902`` when WeasyPrint fails on the document.
  """
  weasyprint = _import()
  collector = _Collector()
  logger = logging.getLogger('weasyprint')
  logger.addHandler(collector)
  try:
    document = weasyprint.HTML(string=html)
    data: bytes = document.write_pdf(pdf_tags=True)
  except (OSError, ImportError) as exc:
    raise _missing(exc) from exc
  except Exception as exc:  # WeasyPrint raises many types on a document it cannot lay out
    raise PdfError(f'WeasyPrint failed: {exc}', code='E902') from exc
  finally:
    logger.removeHandler(collector)
  for message in collector.messages:
    log.debug('weasyprint: %s', message)
  return data, []


def _import() -> Any:
  """Import WeasyPrint, turning a missing library into an install hint."""
  try:
    import weasyprint
  except (ImportError, OSError) as exc:
    raise _missing(exc) from exc
  return weasyprint


def _missing(exc: BaseException) -> MissingDependencyError:
  """Build the error for a WeasyPrint that cannot load, with the hint for this platform."""
  platform = 'linux' if sys.platform.startswith('linux') else sys.platform
  hint = INSTALL_HINT.get(platform, INSTALL_HINT['linux'])
  if isinstance(exc, ImportError) and not isinstance(exc, OSError) and not weasyprint_version():
    hint = 'Install the extra: pip install "scireport[pdf]". ' + hint
  return MissingDependencyError(
    f'the WeasyPrint PDF engine cannot start: {exc}', code='E901', hint=hint
  )


class _Collector(logging.Handler):
  """Collect the messages WeasyPrint logs, so that they can be shown at debug level."""

  def __init__(self) -> None:
    super().__init__(level=logging.WARNING)
    self.messages: list[str] = []

  def emit(self, record: logging.LogRecord) -> None:
    """Keep the formatted message of a record."""
    self.messages.append(record.getMessage())
