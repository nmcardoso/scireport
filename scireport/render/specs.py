"""Plain-data descriptions of what a component macro draws.

The Python side of a component turns a bundle value into one of these objects, already escaped
and formatted for the output format, and hands it to the layout's macro. The macro decides how it
looks; it never has to know where the numbers came from. Field names are the contract between
the engine and every layout, so they are part of the layout API (ADR-0008).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColSpec:
  """One table column.

  Parameters
  ----------
  label : str
      Header text (plain text; the macro escapes it).
  unit : str
      The unit, already typeset for the format; empty when there is none.
  align : {'left', 'right', 'center', 'path'}
      Cell alignment; ``path`` is monospace and may break anywhere.
  width : float
      Share of the table width in (0, 1], normalised so that the columns sum to 1.
  width_given : bool
      Whether the bundle set the width; a layout may let columns without one size themselves.
  """

  label: str
  unit: str = ''
  align: str = 'left'
  width: float = 1.0
  width_given: bool = False


@dataclass(frozen=True)
class RowSpec:
  """One table row.

  Parameters
  ----------
  cells : tuple of str
      The cells; plain text, or :class:`~scireport.render.safe.Safe` text already typeset.
  verdict : str or None
      ``pass``, ``warn``, ``fail`` or None.
  emphasis : tuple of (str or None)
      Per cell: ``strong``, ``muted``, ``pass``, ``warn``, ``fail`` or None.
  """

  cells: tuple[str, ...]
  verdict: str | None = None
  emphasis: tuple[str | None, ...] = ()


@dataclass(frozen=True)
class LinkSpec:
  """A file offered next to the report.

  Parameters
  ----------
  filename : str
      Name shown to the reader.
  href : str
      Where the file is: a relative path (Markdown, LaTeX) or a ``data:`` URI (HTML).
  media_type : str
      MIME type, or an empty string.
  description : str
      What the file holds, or an empty string.
  size : str
      Human-readable size, for example ``12.3 KiB``.
  embedded : bool
      Whether the file travels inside the output (a ``data:`` link) rather than next to it.
  """

  filename: str
  href: str
  media_type: str = ''
  description: str = ''
  size: str = ''
  embedded: bool = False


@dataclass(frozen=True)
class TableSpec:
  """A table ready to draw.

  Parameters
  ----------
  columns : tuple of ColSpec
      The columns.
  rows : tuple of RowSpec
      The rows shown.
  caption : str
      Caption; plain text, or a :class:`~scireport.render.safe.Safe` string. Empty for none.
  number : int
      Table number, counted from 1 through the document.
  total : int
      Rows in the data.
  truncated : bool
      Whether ``rows`` is only the first part of the data.
  overflow : LinkSpec or None
      The file with all rows, when the table was cut and the bundle offers one.
  headed : bool
      Whether any column has a header.
  has_verdicts : bool
      Whether any row has a verdict.
  """

  columns: tuple[ColSpec, ...]
  rows: tuple[RowSpec, ...]
  caption: str = ''
  number: int = 0
  total: int = 0
  truncated: bool = False
  overflow: LinkSpec | None = None
  headed: bool = True
  has_verdicts: bool = False


@dataclass(frozen=True)
class FigureSpec:
  """A figure or image ready to draw.

  Parameters
  ----------
  src : str
      Where the picture is: a relative path (Markdown, LaTeX) or a ``data:`` URI (HTML).
  alt : str
      Alternative text; empty for a decorative image.
  caption : str
      Caption; plain text or :class:`~scireport.render.safe.Safe`. Empty for none.
  width : float
      Width as a fraction of the text width, in (0, 1].
  number : int
      Figure number, counted from 1 through the document; 0 for an image.
  key : str
      The value key, usable as an identifier.
  """

  src: str
  alt: str = ''
  caption: str = ''
  width: float = 1.0
  number: int = 0
  key: str = ''


@dataclass(frozen=True)
class EquationSpec:
  """An equation ready to draw.

  Parameters
  ----------
  body : str
      The typeset equation, :class:`~scireport.render.safe.Safe`: an ``<img>`` in HTML, LaTeX
      math in TeX and ``$$...$$`` in Markdown.
  latex : str
      The LaTeX source, plain text (usable as alternative text).
  display : bool
      Whether it is a standalone equation.
  number : int
      Equation number, or 0 when it is not numbered.
  caption : str
      Text below the equation, or an empty string.
  """

  body: str
  latex: str
  display: bool = True
  number: int = 0
  caption: str = ''


@dataclass(frozen=True)
class MetricSpec:
  """One headline number.

  Parameters
  ----------
  label : str
      What it measures.
  value : str
      The formatted value, plain text or Safe.
  detail : str
      A line of context, or an empty string.
  """

  label: str
  value: str
  detail: str = ''


@dataclass(frozen=True)
class StageSpec:
  """One stage of a flow.

  Parameters
  ----------
  number : int
      Position, from 1.
  label : str
      Stage name.
  detail : tuple of str
      Lines under the name.
  state : str
      ``done``, ``reused``, ``skipped``, ``failed``, ``running`` or ``pending``.
  """

  number: int
  label: str
  detail: tuple[str, ...] = ()
  state: str = 'done'


@dataclass(frozen=True)
class CoverSpec:
  """What the cover of a report shows (the ``meta`` block, flattened).

  Parameters
  ----------
  title : str
      Report title.
  subtitle : str
      Subtitle, or an empty string.
  authors : tuple of str
      Author names, with affiliations in parentheses where known.
  date : str
      ISO date or an empty string.
  version : str
      Version or an empty string.
  pipeline : str
      Producing pipeline or an empty string.
  """

  title: str
  subtitle: str = ''
  authors: tuple[str, ...] = ()
  date: str = ''
  version: str = ''
  pipeline: str = ''
  extra: tuple[tuple[str, str], ...] = field(default=())
