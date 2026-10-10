"""Canonicalise rendered HTML for a DOM-equivalent comparison (ported from the MOSAICS tests).

A layout may change how its HTML is spelled without changing what a browser or WeasyPrint sees:
attribute order is not meaningful, whitespace between tags is not meaningful outside a
``<pre>``, and an entity means the same once decoded. Comparing two renders byte for byte
would fail on all three without the page differing, so this module walks a document with
the standard-library parser and writes one token per line: an opening tag with its
attributes sorted, a closing tag, or a run of text with entities decoded and whitespace
collapsed. Two documents are DOM-equivalent exactly when their canonical forms are equal.

A ``data:`` URI (a figure, an equation, a font face) is replaced by a stable hash of its own text:
exactly as sensitive to a one-pixel change as comparing the bytes would be, without the expected
file carrying megabytes of base64.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from html.parser import HTMLParser

_UNSTABLE_URI = re.compile(r'(?:data|file):[^\s"\')]+')


def _hash_uri(match: re.Match[str]) -> str:
  """Replace one matched URI by a short, stable stand-in."""
  return f'sha256:{hashlib.sha256(match.group(0).encode("utf-8")).hexdigest()}'


def _stabilise(text: str) -> str:
  """Replace every ``data:`` or ``file:`` URI of a text by a hash of itself."""
  return _UNSTABLE_URI.sub(_hash_uri, text)


class _Canonicaliser(HTMLParser):
  """Collect one canonical line per token of an HTML document."""

  def __init__(self) -> None:
    super().__init__(convert_charrefs=True)
    self.lines: list[str] = []
    self._pre = 0

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    self.lines.append(self._tag(tag, attrs))
    if tag == 'pre':
      self._pre += 1

  def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    self.lines.append(self._tag(tag, attrs, closing=True))

  def handle_endtag(self, tag: str) -> None:
    if tag == 'pre':
      self._pre = max(0, self._pre - 1)
    self.lines.append(f'</{tag}>')

  def handle_data(self, data: str) -> None:
    text = _stabilise(data)
    if self._pre:
      if text:
        self.lines.append(f'TEXT:{text!r}')
      return
    collapsed = ' '.join(text.split())
    if collapsed:
      self.lines.append(f'TEXT:{collapsed}')

  def handle_comment(self, data: str) -> None:
    """Drop a comment: it carries no weight in what is laid out."""

  @staticmethod
  def _tag(tag: str, attrs: list[tuple[str, str | None]], *, closing: bool = False) -> str:
    """Write one opening tag with its attributes sorted by name."""
    rendered = [
      f'{name}="{_stabilise(value)}"' if value is not None else name
      for name, value in sorted(attrs, key=lambda pair: pair[0])
    ]
    return f'<{tag}{" " + " ".join(rendered) if rendered else ""}{"/" if closing else ""}>'


def canonicalise(html: str) -> str:
  """Reduce an HTML document to a stable, diffable text form, one token per line.

  Parameters
  ----------
  html : str
      A full HTML document.

  Returns
  -------
  str
      The canonical form; equal for DOM-equivalent documents.
  """
  parser = _Canonicaliser()
  parser.feed(html)
  parser.close()
  return '\n'.join(parser.lines) + '\n'


def diff(expected: str, actual: str) -> str:
  """Return a unified diff of two canonical documents; empty when they are identical."""
  return ''.join(
    difflib.unified_diff(
      expected.splitlines(keepends=True),
      actual.splitlines(keepends=True),
      fromfile='expected',
      tofile='actual',
    )
  )
