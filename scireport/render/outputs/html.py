"""HTML output: one self-contained file with its CSS inlined and its pictures embedded."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from scireport.render.outputs import tidy
from scireport.render.safe import Safe
from scireport.styles.fonts import font_face_css

if TYPE_CHECKING:
  from scireport.render.session import RenderSession

DOCUMENT = 'report.html'
"""Name of the file."""


def variables(session: RenderSession) -> dict[str, Any]:
  """Return ``css`` and ``fonts_css``.

  ``css`` is the layout's stylesheets for this format, concatenated and marked safe. ``fonts_css``
  holds the ``@font-face`` rules of the fonts the layout lists, each inlined as a ``data:`` URI,
  so that the file needs no font installed; it is empty for a layout without fonts.
  """
  files = session.layout.files('html')
  return {
    'css': Safe('\n'.join(session.layout.read(name) for name in files.css)),
    'fonts_css': Safe(font_face_css(session.layout.definition.fonts)),
  }


def split(session: RenderSession, body: str) -> tuple[str, dict[str, str]]:
  """Return the body unchanged: HTML is never split."""
  del session
  return body, {}


def assemble(session: RenderSession, document: str, parts: dict[str, str]) -> dict[str, bytes]:
  """Return the single HTML file."""
  del session, parts
  return {DOCUMENT: tidy(document, 'html')}
