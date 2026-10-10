r"""LaTeX fragments for manuscripts: tables, figures and the numbers of a bundle (ADR-0010).

``scireport export tex BUNDLE --keys ... -o paper/generated/`` writes files a paper can
``\input``, so that every number and table in a manuscript comes from the data file:

``numbers.tex``
    One ``\newcommand`` per ``number`` value. The macro name is the key in CamelCase after an
    optional prefix (``crossmatch.n_pairs`` is ``\CrossmatchNPairs``), and the macro holds the
    typeset value with its uncertainty and unit. LaTeX command names may only contain letters,
    so digits become words (``run2`` is ``RunTwo``); two keys that give the same name are
    error ``E807``, and a command that already exists makes LaTeX stop at ``\newcommand``.
``tab_<key>.tex``
    A ``table`` value as a ``table`` float with caption and label (``tab:<key>``), using
    ``booktabs``; tables over 40 rows use ``longtable``. Row verdicts and cell emphasis are not
    exported.
``fig_<key>.tex`` and ``fig_<key>.pdf`` (or ``.png``)
    A ``figure`` value as a ``figure`` float with caption and label (``fig:<key>``), and the file
    it includes, PDF preferred over PNG.

With ``bare=True`` the tables are a bare ``tabular`` and the figures a bare ``\includegraphics``,
without float, caption or label, for authors who write their own.
"""

from __future__ import annotations

import difflib
import fnmatch
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from scireport._version import __version__
from scireport.bundle.reader import Bundle
from scireport.errors import ExportError, Issue
from scireport.hashing import sha256_bytes
from scireport.logging_utils import get_logger
from scireport.render.escape import tex_escape
from scireport.render.markup import default_converter
from scireport.render.numbers import format_number_value
from scireport.render.safe import Safe
from scireport.render.specs import ColSpec
from scireport.render.tables import build_table
from scireport.spec.keys import suggest_key
from scireport.spec.kinds import FigureValue, NumberValue, TableValue
from scireport.spec.manifest import manifest_to_json

log = get_logger(__name__)

NUMBERS_FILE = 'numbers.tex'
"""Name of the file with the number macros."""
LONG_TABLE_ROWS = 40
"""Tables with more rows than this use ``longtable`` instead of a ``table`` float."""
FIGURE_ORDER = ('pdf', 'png')
"""Figure renditions LaTeX can include, in order of preference (SVG never)."""

_DIGITS = ('Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine')
_PREFIX_RE = re.compile(r'[A-Za-z]*')
_ALIGN = {'left': 'l', 'right': 'r', 'center': 'c', 'path': 'l'}


@dataclass(frozen=True)
class ExportResult:
  """What an export produced.

  Parameters
  ----------
  files : dict
      File name (relative to the output directory) to content, sorted by name.
  macros : dict
      Macro name (without the backslash) to the key of the number it holds.
  """

  files: dict[str, bytes]
  macros: dict[str, str]


def macro_name(key: str, prefix: str = '') -> str:
  r"""Turn a value key into the name of a LaTeX macro (without the backslash).

  Parameters
  ----------
  key : str
      A key such as ``crossmatch.n_pairs``.
  prefix : str, default=''
      Letters put in front of the name, to avoid clashes with existing commands.

  Returns
  -------
  str
      Each word of the key (split at ``.``, ``_`` and ``-``) with a capital letter, digits
      spelled out, after the prefix: ``CrossmatchNPairs``.

  Raises
  ------
  ValueError
      When ``prefix`` holds anything but letters.
  """
  if _PREFIX_RE.fullmatch(prefix) is None:
    raise ValueError(f'the macro prefix must hold letters only, got {prefix!r}')
  words = [word for word in re.split(r'[._-]+', key) if word]
  return prefix + ''.join(_capitalise(_spell_digits(word)) for word in words)


def export_tex(
  bundle: Bundle,
  keys: Sequence[str] | None = None,
  *,
  prefix: str = '',
  bare: bool = False,
  graphics_prefix: str = '',
  max_rows: int | None = None,
) -> ExportResult:
  r"""Export values of a bundle as LaTeX fragments.

  Parameters
  ----------
  bundle : Bundle
      The opened bundle.
  keys : sequence of str or None, default=None
      Keys to export; ``*`` and ``?`` match several (``crossmatch.*``). None exports every
      number, table and figure. A key named in full that has no fragment (a text, say) is
      ``E808``; one that does not exist is ``E103``.
  prefix : str, default=''
      Letters in front of every macro name (see :func:`macro_name`).
  bare : bool, default=False
      Write bare ``tabular`` and ``\includegraphics``, without float, caption or label.
  graphics_prefix : str, default=''
      Written in front of the figure file name in ``\includegraphics``; the path from the
      directory LaTeX runs in to the output directory (for example ``generated/``).
  max_rows : int or None, default=None
      Cut tables to this many rows; None uses the value's own ``max_rows``, else all rows.

  Returns
  -------
  ExportResult
      The files and the macros.

  Raises
  ------
  ExportError
      With ``E103`` (unknown key), ``E807`` (two keys, one macro name), ``E808`` (a key that
      cannot be exported) or ``E210`` (a figure with no PDF or PNG).
  """
  selected, named = _select(bundle, keys)
  manifest_digest = sha256_bytes(manifest_to_json(bundle.manifest).encode('utf-8'))[:12]
  header = (
    f'% Generated by scireport {__version__} from a bundle with manifest sha256 '
    f'{manifest_digest}. Do not edit.\n'
  )
  files: dict[str, bytes] = {}
  macros: dict[str, str] = {}
  problems: list[Issue] = []
  numbers: list[tuple[str, NumberValue]] = []
  for key in selected:
    value = bundle.manifest.values[key]
    if isinstance(value, NumberValue):
      numbers.append((key, value))
    elif isinstance(value, TableValue):
      files[f'tab_{key}.tex'] = _table(
        bundle, key, value, header, bare=bare, max_rows=max_rows
      ).encode('utf-8')
    elif isinstance(value, FigureValue):
      fragment = _figure(
        bundle, key, value, header, bare=bare, graphics=graphics_prefix, problems=problems
      )
      if fragment is not None:
        files.update(fragment)
    elif key in named:
      problems.append(
        Issue(
          'E808',
          f'{key!r} is a {value.kind} value, and only number, table and figure values '
          'have a LaTeX fragment',
          pointer=f'/values/{key}',
          key=key,
          expected='number, table or figure',
          found=value.kind,
        )
      )
  problems.extend(_collisions(numbers, prefix, macros))
  if problems:
    raise ExportError(
      problems[0].message
      if len(problems) == 1
      else f'{len(problems)} problems, first: {problems[0].message}',
      code=problems[0].code,
      issues=problems,
    )
  if numbers:
    files[NUMBERS_FILE] = _numbers_file(numbers, prefix, header).encode('utf-8')
  log.debug('exported %d number(s) and %d other file(s)', len(numbers), len(files) - bool(numbers))
  return ExportResult(dict(sorted(files.items())), dict(sorted(macros.items())))


def write_export(result: ExportResult, out_dir: Path | str) -> list[Path]:
  """Write the files of an export.

  Parameters
  ----------
  result : ExportResult
      What :func:`export_tex` returned.
  out_dir : pathlib.Path or str
      The directory; created when missing. Files with the same name are replaced.

  Returns
  -------
  list of pathlib.Path
      The written files, in name order.
  """
  root = Path(out_dir)
  root.mkdir(parents=True, exist_ok=True)
  written = []
  for name, data in result.files.items():
    path = root / name
    path.write_bytes(data)
    written.append(path)
  return written


def _spell_digits(word: str) -> str:
  """Replace each digit by its English name, because a macro name may only hold letters."""
  return re.sub(r'\d', lambda match: _DIGITS[int(match.group())], word)


def _capitalise(word: str) -> str:
  """Upper-case the first letter of a word and keep the rest."""
  return word[:1].upper() + word[1:]


def _select(bundle: Bundle, keys: Sequence[str] | None) -> tuple[list[str], set[str]]:
  """Resolve the requested keys and patterns; return the sorted selection and the exact names."""
  values = bundle.manifest.values
  if not keys:
    return sorted(values), set()
  chosen: set[str] = set()
  named: set[str] = set()
  problems: list[Issue] = []
  for request in keys:
    if any(char in request for char in '*?['):
      matches = fnmatch.filter(sorted(values), request)
      if not matches:
        problems.append(_unknown(request, values))
      chosen.update(matches)
    elif request in values:
      chosen.add(request)
      named.add(request)
    else:
      problems.append(_unknown(request, values))
  if problems:
    raise ExportError(problems[0].message, code='E103', issues=problems)
  return sorted(chosen), named


def _unknown(request: str, values: Mapping[str, object]) -> Issue:
  """Describe a requested key that the bundle does not have."""
  close = difflib.get_close_matches(request, list(values), n=1)
  hint = close[0] if close else suggest_key(request)
  return Issue(
    'E103',
    f'no value matches {request!r}',
    pointer=f'/values/{request}',
    key=request,
    hint=f'Did you mean {hint!r}?' if hint else None,
  )


def _collisions(
  numbers: list[tuple[str, NumberValue]], prefix: str, macros: dict[str, str]
) -> list[Issue]:
  """Fill ``macros`` and report keys whose macro names are equal."""
  problems: list[Issue] = []
  for key, _ in numbers:
    name = macro_name(key, prefix)
    if name in macros:
      problems.append(
        Issue(
          'E807',
          f'keys {macros[name]!r} and {key!r} both give the macro \\{name}',
          pointer=f'/values/{key}',
          key=key,
          hint='Rename one key, or export them separately with different prefixes.',
        )
      )
    else:
      macros[name] = key
  return problems


def _numbers_file(numbers: list[tuple[str, NumberValue]], prefix: str, header: str) -> str:
  r"""Write ``numbers.tex``: one ``\newcommand`` per number."""
  lines = [header.rstrip('\n'), '% Needs no package; units use \\ensuremath.']
  for key, value in numbers:
    text = format_number_value(value, 'tex')
    lines.append(f'% {key}')
    lines.append(f'\\newcommand{{\\{macro_name(key, prefix)}}}{{{text}}}')
  return '\n'.join(lines) + '\n'


def _caption(text: str) -> str:
  """Convert a caption (inline Markdown) to LaTeX."""
  return str(default_converter().convert(text, 'tex', inline=True).text)


def _table(
  bundle: Bundle, key: str, value: TableValue, header: str, *, bare: bool, max_rows: int | None
) -> str:
  """Write a ``table`` value as a LaTeX fragment."""
  spec = build_table(
    bundle,
    value,
    target='tex',
    number=0,
    caption=None,
    max_rows=max_rows,
    report=_raise_on_problem,
    key=key,
    overflow=lambda _key: None,
  )
  columns = ''.join(_ALIGN[c.align] for c in spec.columns)
  head = ' & '.join(_heading(column) for column in spec.columns)
  rows = [' & '.join(_cell(cell) for cell in row.cells) + r' \\' for row in spec.rows]
  note = f'% showing the first {len(spec.rows)} of {spec.total} rows\n' if spec.truncated else ''
  caption = _caption(spec.caption) if spec.caption and not bare else ''
  label = f'\\label{{tab:{key}}}' if caption else ''
  out = [header.rstrip('\n'), '% Needs: booktabs' + ('' if bare else ', longtable')]
  if note:
    out.append(note.rstrip('\n'))
  if bare:
    out += [f'\\begin{{tabular}}{{{columns}}}', r'\toprule', f'{head} \\\\', r'\midrule']
    out += [*rows, r'\bottomrule', r'\end{tabular}']
  elif len(spec.rows) > LONG_TABLE_ROWS:
    top = [r'\toprule', f'{head} \\\\', r'\midrule']
    out += [f'\\begin{{longtable}}{{{columns}}}']
    out += [f'\\caption{{{caption}}}{label}\\\\'] if caption else []
    out += [*top, r'\endfirsthead', *top, r'\endhead', r'\bottomrule', r'\endlastfoot', *rows]
    out += [r'\end{longtable}']
  else:
    out += [r'\begin{table}[tbp]', r'\centering']
    out += [f'\\caption{{{caption}}}'] if caption else []
    out += [label, f'\\begin{{tabular}}{{{columns}}}', r'\toprule', f'{head} \\\\', r'\midrule']
    out += [*rows, r'\bottomrule', r'\end{tabular}', r'\end{table}']
  return '\n'.join(line for line in out if line) + '\n'


def _cell(cell: str) -> str:
  """Escape a table cell, unless the table builder already typeset it."""
  return str(cell) if isinstance(cell, Safe) else tex_escape(cell, inline=True)


def _heading(column: ColSpec) -> str:
  """Write the header cell of a column: the label and, below it in parentheses, the unit."""
  label = tex_escape(column.label, inline=True)
  return f'{label} ({column.unit})' if column.unit else label


def _raise_on_problem(code: str, message: str, **details: object) -> None:
  """Turn a table problem found while reading the data into an export error."""
  raise ExportError(message, code=code)


def _figure(
  bundle: Bundle,
  key: str,
  value: FigureValue,
  header: str,
  *,
  bare: bool,
  graphics: str,
  problems: list[Issue],
) -> dict[str, bytes] | None:
  """Write a ``figure`` value as a fragment and the file it includes."""
  available = {rendition.format: rendition for rendition in value.renditions}
  chosen = next((fmt for fmt in FIGURE_ORDER if fmt in available), None)
  if chosen is None:
    problems.append(
      Issue(
        'E210',
        f'figure {key!r} has no pdf or png file, which LaTeX needs',
        pointer=f'/values/{key}',
        key=key,
        expected='pdf or png',
        found=', '.join(sorted(available)),
      )
    )
    return None
  picture = f'fig_{key}.{chosen}'
  width = f'{value.width:g}\\linewidth'
  include = f'\\includegraphics[width={width}]{{{graphics}{picture}}}'
  out = [header.rstrip('\n'), '% Needs: graphicx']
  if bare:
    out.append(include)
  else:
    out += [r'\begin{figure}[tbp]', r'\centering', include]
    if value.caption:
      out.append(f'\\caption{{{_caption(value.caption)}}}')
    out += [f'\\label{{fig:{key}}}'] if value.caption else []
    out += [r'\end{figure}']
  return {
    f'fig_{key}.tex': ('\n'.join(out) + '\n').encode('utf-8'),
    picture: bundle.read_asset(available[chosen]),
  }
