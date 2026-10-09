"""Turn numbers, units and table cells into text for each output format.

A ``number`` value carries a number, a ``format`` (a filter name such as ``int`` or ``sci``, or a
Python format specification such as ``,.2f``), a unit, an uncertainty or interval and a
placeholder for a missing value. The functions here resolve the format and typeset the result for
Markdown, HTML or LaTeX. Whatever they return is already escaped for that format
(:class:`~scireport.render.safe.Safe`), or plain text that the caller still escapes.
"""

from __future__ import annotations

import datetime as dt
import html
import re
from collections.abc import Callable
from typing import Any, Literal

from scireport.render.escape import md_escape, tex_escape
from scireport.render.filters import (
  Scientific,
  compact,
  duration,
  fmt_bytes,
  fmt_float,
  fmt_int,
  is_numeric,
  missing,
  pct,
  ppm,
  sci,
)
from scireport.render.safe import Safe
from scireport.spec.kinds import NumberValue

Target = Literal['md', 'html', 'tex']
"""The three text formats scireport writes."""

NUMBER_FORMATS: dict[str, Callable[[Any], Scientific | str]] = {
  'int': fmt_int,
  'float': fmt_float,
  'pct': pct,
  'ppm': ppm,
  'sci': sci,
  'compact': compact,
  'bytes': fmt_bytes,
  'duration': duration,
}
"""Format names accepted in ``NumberValue.format`` and ``Column.format``."""

_SUPERSCRIPT = str.maketrans('0123456789-+', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺')
_UNIT_POWER_RE = re.compile(r'\^(-?\d+)')


def format_problem(spec: str | None) -> str | None:
  """Say why a ``format`` string cannot be used, or None when it can.

  Parameters
  ----------
  spec : str or None
      A name from :data:`NUMBER_FORMATS` or a Python format specification.

  Returns
  -------
  str or None
      A one-line reason, or None when ``spec`` is None, a known name or a valid specification.
  """
  if spec is None or spec in NUMBER_FORMATS:
    return None
  for sample in (1234, 1234.5):
    try:
      format(sample, spec)
    except (ValueError, TypeError):
      continue
    return None
  return (
    f'{spec!r} is neither one of {", ".join(sorted(NUMBER_FORMATS))} nor a Python format '
    'specification such as ",.2f"'
  )


def format_scalar(value: Any, spec: str | None = None) -> Scientific | str:
  """Format one value with a ``format`` string.

  Parameters
  ----------
  value : Any
      A number, or anything else (kept as text).
  spec : str or None, default=None
      A name from :data:`NUMBER_FORMATS` or a Python format specification. None writes the
      shortest exact text (``str(value)``).

  Returns
  -------
  Scientific or str
      A :class:`~scireport.render.filters.Scientific` for ``sci``, otherwise plain text. A
      missing value gives the placeholder of :func:`~scireport.render.filters.missing`.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  if isinstance(value, bool):
    return 'true' if value else 'false'
  if isinstance(value, dt.date | dt.datetime):
    return value.isoformat()
  if not is_numeric(value):
    return str(value)
  if spec is None:
    return str(value)
  if spec in NUMBER_FORMATS:
    return NUMBER_FORMATS[spec](value)
  try:
    return format(value, spec)
  except (ValueError, TypeError):
    return str(value)


def typeset_scalar(value: Scientific | str, target: Target) -> str:
  """Typeset the result of :func:`format_scalar` for one format.

  Parameters
  ----------
  value : Scientific or str
      The formatted value; plain text is escaped for ``target``.
  target : {'md', 'html', 'tex'}
      The output format.

  Returns
  -------
  str
      Text that is safe in ``target``. Scientific notation becomes ``3.14×10<sup>5</sup>`` in
      HTML, inline math in LaTeX and ``3.14×10⁵`` in Markdown.
  """
  if isinstance(value, Scientific):
    return typeset_scientific(value, target)
  return escape_text(value, target)


def typeset_scientific(value: Scientific, target: Target) -> str:
  """Typeset ``3.14×10^5`` for one format (see :func:`typeset_scalar`)."""
  if value.mantissa == '0' and value.exponent == 0:
    return '0'
  if target == 'html':
    return f'{value.mantissa}×10<sup>{value.exponent}</sup>'
  if target == 'tex':
    return rf'\ensuremath{{{value.mantissa}\times10^{{{value.exponent}}}}}'
  return f'{value.mantissa}×10{str(value.exponent).translate(_SUPERSCRIPT)}'


def escape_text(text: str, target: Target) -> str:
  """Escape plain text for one format; used for text that lives inside a number or a cell."""
  if target == 'html':
    return html.escape(text, quote=True)
  if target == 'tex':
    return tex_escape(text, inline=True)
  return md_escape(text)


def typeset_unit(unit: str, target: Target) -> str:
  r"""Typeset a unit, turning ``^n`` into a superscript.

  Parameters
  ----------
  unit : str
      Free text such as ``arcsec`` or ``objects deg^-2``.
  target : {'md', 'html', 'tex'}
      The output format.

  Returns
  -------
  str
      Text that is safe in ``target``: ``deg<sup>2</sup>`` in HTML, ``deg\ensuremath{^{2}}`` in
      LaTeX, ``deg²`` in Markdown.
  """
  pieces = _UNIT_POWER_RE.split(unit)
  out: list[str] = []
  for index, piece in enumerate(pieces):
    if index % 2 == 0:
      out.append(escape_text(piece, target) if piece.strip() else piece)
    elif target == 'html':
      out.append(f'<sup>{html.escape(piece)}</sup>')
    elif target == 'tex':
      out.append(rf'\ensuremath{{^{{{piece}}}}}')
    else:
      out.append(piece.translate(_SUPERSCRIPT))
  return ''.join(out)


def format_number_value(value: NumberValue, target: Target) -> Safe:
  """Typeset a ``number`` value with its uncertainty or interval and unit.

  Parameters
  ----------
  value : NumberValue
      The value from the bundle.
  target : {'md', 'html', 'tex'}
      The output format.

  Returns
  -------
  Safe
      For example ``1,234 ± 12 arcsec`` or ``1.5 [1.1, 1.9] mag``, escaped for ``target``. A
      missing value gives ``value.missing`` or ``--``.
  """
  if value.value is None:
    return Safe(escape_text(value.missing if value.missing is not None else '--', target))

  def one(number: Any) -> str:
    return typeset_scalar(format_scalar(number, value.format), target)

  text = one(value.value)
  if value.uncertainty is not None:
    text += f' {"±" if target != "tex" else r"\ensuremath{\pm}"} {one(value.uncertainty)}'
  elif value.interval is not None:
    text += f' [{one(value.interval[0])}, {one(value.interval[1])}]'
  if value.unit:
    gap = '&nbsp;' if target == 'html' else ('~' if target == 'tex' else ' ')
    text += f'{gap}{typeset_unit(value.unit, target)}'
  return Safe(text)


def format_cell(value: Any, spec: str | None, target: Target) -> str:
  """Format one table cell.

  Parameters
  ----------
  value : Any
      The cell content from the data: a number, text, bool, date or None.
  spec : str or None
      The column's ``format``.
  target : {'md', 'html', 'tex'}
      The output format.

  Returns
  -------
  str
      Plain text for ordinary cells (the component macro escapes it); a
      :class:`~scireport.render.safe.Safe` string for scientific notation, which is typeset here.
  """
  result = format_scalar(value, spec)
  if isinstance(result, Scientific):
    return Safe(typeset_scientific(result, target))
  return result
