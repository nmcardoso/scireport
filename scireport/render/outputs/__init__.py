"""Output writers: they complete a rendered document with the files its format needs.

Each writer module has the same three functions: ``variables(session, body)`` returns the extra
names the layout's document skeleton can use, ``split(session, body)`` separates the body into
the main part and any further files, and ``assemble(session, document, parts)`` returns every
file of the output (relative path to bytes) in a fixed order.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal

from scireport.render.safe import Safe

if TYPE_CHECKING:
  from scireport.render.session import RenderSession


def skeleton_variables(session: RenderSession, body: str) -> dict[str, Any]:
  """Return the names the document skeleton of the session's format can use.

  Parameters
  ----------
  session : RenderSession
      The render in progress.
  body : str
      The rendered body.

  Returns
  -------
  dict
      ``body`` (the main part for Markdown, the whole body otherwise), ``toc`` (the listed
      headings) and the extras of the format: ``css`` for HTML, ``style`` for TeX, ``split`` and
      ``files`` for Markdown.
  """
  from scireport.render.outputs import html, md, tex

  writer = {'md': md, 'html': html, 'tex': tex}[session.fmt]
  main, _ = writer.split(session, body)
  return {
    'body': Safe(main),
    'toc': session.outline.entries,
    **writer.variables(session),
  }


def assemble(session: RenderSession, body: str, document: str) -> dict[str, bytes]:
  """Build every file of the output from the rendered body and document.

  Parameters
  ----------
  session : RenderSession
      The render that produced them.
  body : str
      The rendered body.
  document : str
      The rendered document skeleton.

  Returns
  -------
  dict
      Relative path to content, sorted by path.
  """
  from scireport.render.outputs import html, md, tex

  writer = {'md': md, 'html': html, 'tex': tex}[session.fmt]
  _, parts = writer.split(session, body)
  files = writer.assemble(session, document, parts)
  files.update(session.files)
  return dict(sorted(files.items()))


_TEX_OPEN = re.compile(r'\\begin\{verbatim\}')
_TEX_CLOSE = re.compile(r'\\end\{verbatim\}')
_FENCE = re.compile(r'^\s*(```|~~~)')


def tidy(text: str, kind: Literal['md', 'html', 'tex']) -> bytes:
  r"""Tidy a rendered document and encode it as UTF-8.

  Lines lose their trailing spaces and runs of blank lines become one, except inside literal
  text (a fenced code block, ``<pre>``, a ``verbatim`` environment), which is kept as it is. The
  document ends with exactly one newline.

  Parameters
  ----------
  text : str
      The rendered document.
  kind : {'md', 'html', 'tex'}
      Decides what counts as literal text.

  Returns
  -------
  bytes
      UTF-8 text with ``\n`` line endings.
  """
  lines: list[str] = []
  literal = False
  fence = ''
  blank = True
  for line in text.replace('\r\n', '\n').split('\n'):
    if kind == 'md':
      match = _FENCE.match(line)
      if match and not literal:
        literal, fence = True, match.group(1)
      elif literal and line.strip().startswith(fence):
        lines.append(line)
        literal = False
        blank = False
        continue
    elif kind == 'tex':
      if not literal and _TEX_OPEN.search(line) and not _TEX_CLOSE.search(line):
        literal = True
      elif literal and _TEX_CLOSE.search(line):
        lines.append(line)
        literal = False
        blank = False
        continue
    elif not literal and '<pre' in line and '</pre>' not in line:
      literal = True
    elif literal and '</pre>' in line:
      lines.append(line)
      literal = False
      blank = False
      continue
    if literal:
      lines.append(line)
      continue
    line = line.rstrip()
    if not line:
      if blank:
        continue
      blank = True
    else:
      blank = False
    lines.append(line)
  while lines and not lines[-1].strip():
    lines.pop()
  return ('\n'.join(lines) + '\n').encode('utf-8')
