r"""Citations in prose: ``[@key]`` and the reference list (ADR-0011).

A bundle may hold one ``bibliography`` value (a BibTeX file and, optionally, a CSL style).
Markdown prose then cites with pandoc's syntax::

    Matched pairs agree with earlier work [@doe2020, p. 3; @smith2018].
    The result of [-@doe2020] is repeated here.

Only the **bracketed** form is read. The prose is first scanned for citation groups, which are
replaced by short alphanumeric tokens (:class:`Citations.protect`) so that either markup engine
converts the rest untouched. After the whole document is rendered, :meth:`Citations.resolve`
replaces the tokens:

* ``tex`` gets ``\autocite`` commands and the bibliography is printed by ``biblatex`` with
  ``biber`` (the writer adds ``\usepackage{biblatex}`` and ``references.bib``); pandoc is not
  needed;
* ``md`` and ``html`` get pandoc's citation processor (``citeproc``), run **once** over every
  group in the order of the document, so that numeric styles number consistently and the list
  holds exactly the works cited. This needs ``scireport[pandoc]`` (``E506`` otherwise).

Citation groups inside code spans and code blocks are left alone, and so is everything when the
bundle has no bibliography, so bundles written before this feature render as they did.
"""

from __future__ import annotations

import difflib
import json
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from scireport.errors import Issue
from scireport.render.escape import tex_escape
from scireport.render.pandoc import Node, iter_nodes, run_pandoc, write_ast
from scireport.spec.kinds import BibliographyValue

BIB_FILE = 'references.bib'
"""Name of the BibTeX file in a LaTeX project."""

_KEY = r'[A-Za-z0-9_](?:[A-Za-z0-9_:.#$%&\-+?<>~/]*[A-Za-z0-9_])?'
_GROUP_RE = re.compile(r'(?<![\\!\w\]])\[(?P<body>[^\[\]]*@[^\[\]]*)\](?![(\[:])')
_CODE_RE = re.compile(r'(```.*?```|~~~.*?~~~|`+[^`\n]*?`+)', re.DOTALL)
_BIB_ENTRY_RE = re.compile(r'@(?P<kind>[A-Za-z]+)\s*[{(]\s*(?P<key>[^\s,]+)\s*,')
_BIB_NON_ENTRIES = frozenset({'comment', 'string', 'preamble'})
_KEY_AT_START = re.compile(_KEY)
_SEPARATOR = '<!--SRSEP-->'
_TOKEN_PREFIX = 'SRCITE'
_REFS_PREFIX = 'SRREFS'
_CITE_READER = (
  'markdown-raw_html-raw_tex-raw_attribute-smart-auto_identifiers-implicit_figures'
  '-implicit_header_references-fenced_divs-bracketed_spans-inline_notes-footnotes'
)
_TOKEN_RE = re.compile(rf'(?:{_TOKEN_PREFIX}|{_REFS_PREFIX})\d+Z')

Target = Literal['md', 'html', 'tex']


@dataclass(frozen=True)
class CitedWork:
  """One work inside a citation group.

  Parameters
  ----------
  key : str
      The BibTeX key.
  prefix : str
      Text before the citation (``see``).
  suffix : str
      Text after it, locator included (``, p. 3``).
  suppress_author : bool
      Written ``-@key``: only the year is shown by an author-date style.
  """

  key: str
  prefix: str
  suffix: str
  suppress_author: bool


@dataclass(frozen=True)
class CitationGroup:
  """The works of one ``[@a; @b]``.

  Parameters
  ----------
  works : tuple of CitedWork
      At least one work, in the order written.
  source : str
      The group as written, brackets included, on one line.
  """

  works: tuple[CitedWork, ...]
  source: str


def bibliography_keys(bib: str) -> list[str]:
  """List the entry keys of a BibTeX text, in file order.

  Parameters
  ----------
  bib : str
      The content of a ``.bib`` file.

  Returns
  -------
  list of str
      One key per entry (``@comment``, ``@string`` and ``@preamble`` are not entries).
  """
  return [
    match['key']
    for match in _BIB_ENTRY_RE.finditer(bib)
    if match['kind'].lower() not in _BIB_NON_ENTRIES
  ]


def parse_group(body: str) -> tuple[CitedWork, ...] | None:
  """Parse the inside of ``[...]`` as citations, or return None when it is not one.

  Parameters
  ----------
  body : str
      For example ``'see @doe2020, p. 3; @smith2018'``.

  Returns
  -------
  tuple of CitedWork or None
      The works, or None when some part between semicolons has no ``@key``.
  """
  works: list[CitedWork] = []
  for part in body.split(';'):
    work = _parse_work(part)
    if work is None:
      return None
    works.append(work)
  return tuple(works)


class Citations:
  """The citations of one render: protects them in prose and resolves them at the end.

  Parameters
  ----------
  value : BibliographyValue
      The bundle's bibliography.
  bib : bytes
      The content of the ``.bib`` asset.
  csl : bytes or None
      The content of the ``.csl`` asset, when the bundle has one.
  target : {'md', 'html', 'tex'}
      The output format of this render.
  language : str, default='en'
      BCP 47 tag; citeproc uses it for words such as "and".
  """

  def __init__(
    self,
    value: BibliographyValue,
    bib: bytes,
    csl: bytes | None,
    target: Target,
    language: str = 'en',
  ) -> None:
    self.value = value
    self.target = target
    self._bib = bib
    self._csl = csl
    self._language = language
    self._keys = bibliography_keys(bib.decode('utf-8', 'replace'))
    self._groups: dict[str, CitationGroup] = {}
    self._refs: dict[str, bool] = {}
    self.used_pandoc = False

  @property
  def used(self) -> bool:
    """Whether the document cites, or asked for the reference list."""
    return bool(self._groups or self._refs)

  def protect(self, source: str) -> tuple[str, list[Issue]]:
    """Replace the citation groups of some prose by tokens.

    Parameters
    ----------
    source : str
        Markdown prose.

    Returns
    -------
    tuple of (str, list of Issue)
        The prose with a token for each group, and ``E212`` for every key the bibliography does
        not have.
    """
    issues: list[Issue] = []
    pieces = _CODE_RE.split(source)
    for index in range(0, len(pieces), 2):
      pieces[index] = _GROUP_RE.sub(lambda m: self._token(m, issues), pieces[index])
    return ''.join(pieces), issues

  def references(self, *, everything: bool = False) -> str:
    r"""Return a token that becomes the reference list of the output.

    Parameters
    ----------
    everything : bool, default=False
        List every work of the bibliography, not only the cited ones.

    Returns
    -------
    str
        The token (in LaTeX: the ``\printbibliography`` command itself).
    """
    if self.target == 'tex':
      self._refs[''] = everything
      return ('\\nocite{*}\n' if everything else '') + '\\printbibliography[heading=none]'
    token = f'{_REFS_PREFIX}{len(self._refs) + 1}Z'
    self._refs[token] = everything
    return token

  def resolve(self, *documents: str) -> tuple[str, ...]:
    """Replace the tokens in some rendered texts.

    Citations are numbered by their position in the first text that holds them, then in the
    later texts, so pass the document first and the body (if it is separate) after.

    Parameters
    ----------
    *documents : str
        Rendered output (the document skeleton, the body).

    Returns
    -------
    tuple of str
        The same texts with the tokens replaced.

    Raises
    ------
    MissingDependencyError
        With ``E506`` when ``md`` or ``html`` output needs pandoc and it is missing.
    PandocError
        With ``E507`` when pandoc fails.
    """
    if not self.used:
      return documents
    order = self._order(documents)
    cited = [token for token in order if token in self._groups]
    replacement = self._tex_replacements(cited) if self.target == 'tex' else self._citeproc(cited)
    return tuple(
      _TOKEN_RE.sub(lambda m: replacement.get(m.group(0), m.group(0)), d) for d in documents
    )

  def tex_preamble(self) -> str:
    """Return the ``biblatex`` preamble lines, or '' when nothing is cited or listed."""
    if self.target != 'tex' or not self.used:
      return ''
    options = ['backend=biber']
    if self.value.style:
      options.append(f'style={self.value.style}')
    return (
      '% scireport: citations (bibliography kind), printed by biblatex and biber.\n'
      f'\\usepackage[{",".join(options)}]{{biblatex}}\n'
      f'\\addbibresource{{{BIB_FILE}}}\n'
    )

  def tex_files(self) -> dict[str, bytes]:
    """Return the files a LaTeX project needs for its citations."""
    return {BIB_FILE: self._bib} if self.target == 'tex' and self.used else {}

  # ---- internals ------------------------------------------------------------------------

  def _token(self, match: re.Match[str], issues: list[Issue]) -> str:
    """Turn one matched ``[...]`` into a token, or leave it when it is not a citation."""
    works = parse_group(match['body'])
    if works is None:
      return match.group(0)
    for work in works:
      if work.key not in self._keys:
        close = difflib.get_close_matches(work.key, self._keys, n=1)
        issues.append(
          Issue(
            'E212',
            f'citation of {work.key!r}, which the bibliography does not have',
            expected='a key of the .bib file',
            found=work.key,
            hint=f'Did you mean {close[0]!r}?' if close else 'Add the entry to the .bib file.',
          )
        )
    token = f'{_TOKEN_PREFIX}{len(self._groups) + 1}Z'
    self._groups[token] = CitationGroup(works, ' '.join(match.group(0).split()))
    return token

  def _order(self, documents: Iterable[str]) -> list[str]:
    """List the citation tokens in the order they appear, each once."""
    seen: dict[str, None] = {}
    for text in documents:
      for match in _TOKEN_RE.finditer(text):
        if match.group(0) in self._groups:
          seen.setdefault(match.group(0))
    for token in self._groups:
      seen.setdefault(token)
    return list(seen)

  def _tex_replacements(self, cited: list[str]) -> dict[str, str]:
    """Write each group as a biblatex command."""
    return {token: _biblatex(self._groups[token]) for token in cited}

  def _citeproc(self, cited: list[str]) -> dict[str, str]:
    """Run pandoc's citation processor once and map each token to its text."""
    self.used_pandoc = True
    fmt = 'html' if self.target == 'html' else 'gfm-raw_html'
    everything = any(self._refs.values())
    front = f'---\nlang: {self._language}\n' + ("nocite: '@*'\n" if everything else '') + '---\n\n'
    body = '\n\n'.join(self._groups[token].source for token in cited) or 'x'
    with tempfile.TemporaryDirectory(prefix='scireport-cite-') as tmp:
      folder = Path(tmp)
      (folder / 'refs.bib').write_bytes(self._bib)
      args = ['-f', _CITE_READER, '-t', 'json', '--citeproc', '--bibliography=refs.bib']
      if self._csl is not None:
        (folder / 'style.csl').write_bytes(self._csl)
        args.append('--csl=style.csl')
      out = run_pandoc(args, (front + body).encode('utf-8'), cwd=folder)
    document: Node = json.loads(out)
    blocks: list[Node] = document['blocks']
    refs = [b for b in blocks if b['t'] == 'Div' and b['c'][0][0] == 'refs']
    paragraphs = [b for b in blocks if b['t'] == 'Para'][: len(cited)]
    shown = _join([{'t': 'Plain', 'c': p['c']} for p in paragraphs], document, fmt)
    result = dict(zip(cited, shown, strict=False))
    if self._refs:
      listing = _reference_list(refs[0] if refs else None, document, fmt)
      result.update({token: listing for token in self._refs})
    return result


def _parse_work(part: str) -> CitedWork | None:
  """Parse one part of a group (``see -@doe2020, p. 3``)."""
  for at, char in enumerate(part):
    if char != '@' or (at > 0 and (part[at - 1].isalnum() or part[at - 1] == '_')):
      continue
    match = _KEY_AT_START.match(part, at + 1)
    if match is None:
      continue
    before = part[:at]
    suppress = before.endswith('-')
    if suppress:
      before = before[:-1]
    return CitedWork(match.group(0), before.strip(), part[match.end() :].strip(), suppress)
  return None


def _biblatex(group: CitationGroup) -> str:
  r"""Write a group as ``\autocite`` (one work) or ``\autocites`` (several)."""
  if len(group.works) == 1:
    work = group.works[0]
    star = '*' if work.suppress_author else ''
    return f'\\autocite{star}{_notes(work)}{{{work.key}}}'
  cites = ''.join(f'{_notes(work)}{{{work.key}}}' for work in group.works)
  return f'\\autocites{cites}'


def _notes(work: CitedWork) -> str:
  """Write the optional prenote and postnote arguments of a biblatex command."""
  post = work.suffix.lstrip(' ,')
  pre = work.prefix
  if not pre and not post:
    return ''
  if not pre:
    return f'[{tex_escape(post)}]'
  return f'[{tex_escape(pre)}][{tex_escape(post)}]'


def _join(blocks: list[Node], document: Node, fmt: str) -> list[str]:
  """Write blocks with a separator between them and split the text back into one per block."""
  parts: list[Node] = []
  for block in blocks:
    parts.extend([block, {'t': 'RawBlock', 'c': ['html', _SEPARATOR]}])
  text = write_ast({**document, 'blocks': parts}, fmt, ['--wrap=none'])
  pieces = [piece.strip() for piece in text.split(_SEPARATOR)][: len(blocks)]
  return [piece.replace('\n', ' ') for piece in pieces]


def _reference_list(refs: Node | None, document: Node, fmt: str) -> str:
  """Write citeproc's ``#refs`` division as an HTML list or as plain paragraphs."""
  if refs is None:
    return ''
  if fmt == 'html':
    return write_ast({**document, 'blocks': [refs]}, 'html', ['--wrap=none']).strip()
  entries = [
    node
    for node in iter_nodes(refs['c'][1])
    if node['t'] == 'Div' and 'csl-entry' in node['c'][0][1]
  ]
  paragraphs = [{'t': 'Plain', 'c': _entry_inlines(entry)} for entry in entries]
  return '\n\n'.join(_join(paragraphs, document, fmt))


def _entry_inlines(entry: Node) -> list[Node]:
  """Flatten a ``csl-entry`` division into one run of inlines (a numeric label and its text)."""
  inlines: list[Node] = []
  for node in iter_nodes(entry['c'][1]):
    if node['t'] in ('Plain', 'Para'):
      if inlines:
        inlines.append({'t': 'Space'})
      inlines.extend(node['c'])
  return inlines
