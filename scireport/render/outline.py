"""Anchors, numbering and the table of contents, collected while the body renders.

Rendering is single-pass, as in the MOSAICS engine: ``chapter`` and ``heading`` components call
into one :class:`Outline` as the body template runs, and the layout skeleton, rendered afterwards,
reads :attr:`Outline.entries` to write the table of contents. No second walk is needed, and page
numbers (PDF) come from the layout, not from here.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

INDEX_FILE = 'index.md'
"""Name of the Markdown file that holds everything before the first chapter with its own file."""

_SLUG_DROP_RE = re.compile(r'[^\w\- ]')


@dataclass(frozen=True)
class TocEntry:
  """One row of the table of contents.

  Parameters
  ----------
  text : str
      Title as written, without escaping.
  anchor : str
      Unique identifier (``a1``, ``a2`` ...) for HTML ids and LaTeX labels.
  level : int
      0 for a chapter, 1 to 3 for headings below it.
  number : str
      Section number such as ``2`` or ``2.1``; headings before the first chapter count from 1.
      Empty for a heading that is not listed in the contents, which is not numbered either.
  slug : str
      GitHub-style heading anchor, unique within ``md_file``.
  md_file : str
      The Markdown file the heading is written to (``index.md`` unless the document is split).
  """

  text: str
  anchor: str
  level: int
  number: str
  slug: str
  md_file: str = INDEX_FILE


class Outline:
  """Per-render anchor counter, section numbering and table-of-contents accumulator.

  Create exactly one per render. Its counters are per instance, so a second instance in the same
  render would restart at ``a1`` and collide with the first.
  """

  def __init__(self) -> None:
    self._anchors = itertools.count(1)
    self._entries: list[TocEntry] = []
    self._counters: list[int] = []
    self._file = INDEX_FILE
    self._slugs: dict[str, dict[str, int]] = {}
    self.files: list[str] = [INDEX_FILE]
    """Markdown files in the order they start, ``index.md`` first."""

  @property
  def entries(self) -> tuple[TocEntry, ...]:
    """The listed headings so far, in the order the template rendered them."""
    return tuple(self._entries)

  @property
  def current_file(self) -> str:
    """The Markdown file receiving the content being rendered."""
    return self._file

  def chapter(self, text: str, *, md_file: str | None = None, in_contents: bool = True) -> TocEntry:
    """Record a chapter and, when it names a file, start that Markdown file.

    Parameters
    ----------
    text : str
        Chapter title.
    md_file : str or None, default=None
        Write this chapter, and what follows until the next such chapter, to its own file.
    in_contents : bool, default=True
        List it in the table of contents.

    Returns
    -------
    TocEntry
        The entry, whether or not it is listed.
    """
    if md_file is not None:
      self._file = md_file
      if md_file not in self.files:
        self.files.append(md_file)
    if in_contents:
      self._counters = [self._counters[0] + 1 if self._counters else 1]
    return self._record(text, 0, in_contents)

  def heading(self, text: str, level: int = 1, *, in_contents: bool = True) -> TocEntry:
    """Record a heading below the current chapter.

    Parameters
    ----------
    text : str
        Heading text.
    level : int, default=1
        1 to 3; a deeper heading is treated as level 3.
    in_contents : bool, default=True
        List it in the table of contents.

    Returns
    -------
    TocEntry
        The entry, whether or not it is listed.
    """
    level = min(max(level, 1), 3)
    if in_contents:
      if not self._counters:
        self._counters = [0]
      while len(self._counters) <= level:
        self._counters.append(0)
      del self._counters[level + 1 :]
      self._counters[level] += 1
    return self._record(text, level, in_contents)

  def _record(self, text: str, level: int, in_contents: bool) -> TocEntry:
    """Build the entry for a heading and list it when asked."""
    numbers = (
      (self._counters if self._counters[:1] != [0] else self._counters[1:]) if in_contents else []
    )
    entry = TocEntry(
      text=text,
      anchor=f'a{next(self._anchors)}',
      level=level,
      number='.'.join(str(n) for n in numbers),
      slug=self._unique_slug(text),
      md_file=self._file,
    )
    if in_contents:
      self._entries.append(entry)
    return entry

  def _unique_slug(self, text: str) -> str:
    """Return the GitHub heading anchor for ``text``, unique within the current file."""
    base = _SLUG_DROP_RE.sub('', text.lower()).replace(' ', '-')
    seen = self._slugs.setdefault(self._file, {})
    count = seen.get(base, 0)
    seen[base] = count + 1
    return base if count == 0 else f'{base}-{count}'
