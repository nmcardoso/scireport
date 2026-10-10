"""Markdown output: one file, or an index plus one file per chapter that names a file.

Figures go to ``figures/``, images to ``images/`` and attachments to ``attachments/``. Every
file starts with a generated-file notice (written by the layout in the main file and by
:func:`assemble` in the chapter files) so that nobody edits it by mistake. Chapters with an
``md_file`` keep their file names, which lets a project keep the names its readers already know.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from scireport.render.components import FILE_MARKER
from scireport.render.outputs import tidy

if TYPE_CHECKING:
  from scireport.render.session import RenderSession

SINGLE_FILE = 'report.md'
"""Name of the document when it is not split."""
INDEX_FILE = 'index.md'
"""Name of the main document when it is split."""

_MARKER_RE = re.compile(
  r'^' + re.escape(FILE_MARKER).replace(r'\{name\}', r'(?P<name>[^ ]+)') + r'\n', re.M
)


def variables(session: RenderSession) -> dict[str, Any]:
  """Return the Markdown-specific names of the document skeleton: ``split`` and ``files``."""
  return {'split': session.md_split, 'files': list(session.outline.files)}


def split(session: RenderSession, body: str) -> tuple[str, dict[str, str]]:
  """Separate a split document's body into the main part and one part per file.

  Parameters
  ----------
  session : RenderSession
      The render.
  body : str
      The rendered body, with a marker line at the start of every chapter that has a file.

  Returns
  -------
  tuple of (str, dict)
      Everything before the first marker, and file name to content for the rest. A chapter file
      continues until the next marker.
  """
  if not session.md_split:
    return body, {}
  pieces = _MARKER_RE.split(body)
  main, rest = pieces[0], pieces[1:]
  parts: dict[str, str] = {}
  for name, content in zip(rest[0::2], rest[1::2], strict=True):
    parts[name] = parts.get(name, '') + content
  return main, parts


def assemble(session: RenderSession, document: str, parts: dict[str, str]) -> dict[str, bytes]:
  """Return the Markdown files: the document, and the chapter files of a split document."""
  notice = f'<!-- {session.info.generated} -->\n\n'
  files = {(INDEX_FILE if session.md_split else SINGLE_FILE): tidy(document, 'md')}
  for name, content in parts.items():
    files[name] = tidy(notice + content, 'md')
  return files
