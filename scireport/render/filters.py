"""The number vocabulary of reports, ported from the MOSAICS report engine.

Every formatter is a plain function and a Jinja filter, so a template writes
``{{ n | fmt_int }}`` and Python code calls ``fmt_int(n)``. :func:`missing` is the gate every
formatter goes through first: ``None``, NaN and infinity are three different claims (absent,
undefined, unbounded), and a report that rendered all three alike, or as ``0``, would misstate
what the data holds.

``fmt_int``, ``fmt_float`` and ``fmt_bytes`` keep the MOSAICS prefix because ``int`` and
``float`` are Jinja built-ins whose numeric result templates rely on.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

_BREAK_AFTER = frozenset('/_-.')
ZERO_WIDTH_SPACE = '​'
"""Inserted by :func:`breakable` after path separators to give a line break opportunity."""
_SLUG_RE = re.compile(r'[^a-z0-9]+')


@dataclass(frozen=True)
class Scientific:
  """A number in scientific notation, kept as data so that each format can typeset it.

  Parameters
  ----------
  mantissa : str
      The leading digits, already rounded to the requested precision.
  exponent : int
      The power of ten.
  """

  mantissa: str
  exponent: int

  def __str__(self) -> str:
    """Return the plain-text form, for example ``3.14e+05``."""
    return f'{self.mantissa}e{self.exponent:+03d}'


def missing(value: Any) -> str | None:
  """Return the placeholder for a value that has no number, or None when it has one.

  Parameters
  ----------
  value : Any
      The value about to be formatted.

  Returns
  -------
  str or None
      ``'--'`` for None, ``'NaN'`` for a NaN float, ``'∞'`` or ``'−∞'`` for an infinite one;
      None when the caller should carry on formatting.
  """
  if value is None:
    return '--'
  if isinstance(value, float):
    if math.isnan(value):
      return 'NaN'
    if math.isinf(value):
      return '∞' if value > 0 else '−∞'
  return None


def number(value: Any) -> float:
  """Coerce a value to a finite float, with everything that is not a number as 0.0.

  Parameters
  ----------
  value : Any
      The value.

  Returns
  -------
  float
      The number, or ``0.0`` for a bool, a string, None, NaN or infinity.
  """
  if isinstance(value, bool) or not isinstance(value, int | float):
    return 0.0
  coerced = float(value)
  return coerced if math.isfinite(coerced) else 0.0


def is_numeric(value: Any) -> bool:
  """Say whether ``value`` is an int or a float and not a bool."""
  return isinstance(value, int | float) and not isinstance(value, bool)


def fmt_int(value: Any) -> str:
  """Format a count with thousands separators.

  Parameters
  ----------
  value : Any
      The value.

  Returns
  -------
  str
      For example ``'12,483,921'``; ``'--'``, ``'NaN'`` or ``'∞'`` when there is no finite number.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  return f'{number(value):,.0f}' if is_numeric(value) else '--'


def fmt_float(value: Any, digits: int = 4) -> str:
  """Format a statistic to a number of significant figures.

  Parameters
  ----------
  value : Any
      The value.
  digits : int, default=4
      Significant figures.

  Returns
  -------
  str
      For example ``'0.9972'``; the placeholder of :func:`missing` when there is no number.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  return f'{float(value):.{digits}g}' if is_numeric(value) else '--'


def share(part: Any, whole: Any) -> str:
  """Format one number as a percentage of another.

  Parameters
  ----------
  part, whole : Any
      Numerator and denominator.

  Returns
  -------
  str
      For example ``'12.50%'``; ``'--'`` when the denominator is zero or not a number.
  """
  denominator = number(whole)
  return f'{number(part) / denominator:.2%}' if denominator else '--'


def fmt_bytes(value: Any) -> str:
  """Format a byte count in the largest binary unit that keeps it readable.

  Parameters
  ----------
  value : Any
      Bytes. None means "not recorded", which is not the same claim as zero bytes.

  Returns
  -------
  str
      For example ``'4.2 GiB'`` or ``'0 B'``; ``'not recorded'`` for None.
  """
  if value is None:
    return 'not recorded'
  gate = missing(value)
  if gate is not None:
    return gate
  if not is_numeric(value):
    return '--'
  size = number(value)
  if not size:
    return '0 B'
  for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
    if abs(size) < 1024 or unit == 'TiB':
      return f'{size:,.1f} {unit}'
    size /= 1024
  return f'{size:,.1f} TiB'


def duration(value: Any) -> str:
  """Format seconds as ``<h>h<m>m<s>s``, leaving out zero parts.

  Parameters
  ----------
  value : Any
      Seconds.

  Returns
  -------
  str
      For example ``'1h1m1s'``, ``'2m5s'``, ``'43s'``, ``'1h'``. Below one second one decimal is
      kept (``'0.3s'``), because a measured duration must not read ``'0s'``. ``'--'`` when
      there is none.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  if not is_numeric(value):
    return '--'
  return _format_seconds(number(value))


def pct(value: Any, digits: int = 2) -> str:
  """Format a ratio that is already computed as a percentage.

  Parameters
  ----------
  value : Any
      A ratio, for example ``0.9972`` for ``99.72%``.
  digits : int, default=2
      Decimal places.

  Returns
  -------
  str
      For example ``'99.72%'``; the placeholder of :func:`missing` when there is no number.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  return f'{float(value):.{digits}%}' if is_numeric(value) else '--'


def ppm(value: Any) -> str:
  """Format a parts-per-million value with thousands separators.

  Parameters
  ----------
  value : Any
      Parts per million.

  Returns
  -------
  str
      For example ``'800,000 ppm'``; the placeholder of :func:`missing` when there is no number.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  return f'{number(value):,.0f} ppm' if is_numeric(value) else '--'


def sci(value: Any, digits: int = 3) -> Scientific | str:
  """Format a number in scientific notation.

  Parameters
  ----------
  value : Any
      The value.
  digits : int, default=3
      Significant figures of the mantissa.

  Returns
  -------
  Scientific or str
      A :class:`Scientific` for a finite number, which each output format typesets with a
      superscript exponent; the placeholder string of :func:`missing` otherwise.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  if not is_numeric(value):
    return '--'
  numeric = float(value)
  if numeric == 0:
    return Scientific('0', 0)
  exponent = math.floor(math.log10(abs(numeric)))
  mantissa = f'{numeric / (10**exponent):.{digits - 1}f}'
  if abs(float(mantissa)) >= 10:
    exponent += 1
    mantissa = f'{numeric / (10**exponent):.{digits - 1}f}'
  return Scientific(mantissa, exponent)


def compact(value: Any, digits: int = 1) -> str:
  """Abbreviate a large count with a magnitude suffix.

  Parameters
  ----------
  value : Any
      The value.
  digits : int, default=1
      Decimal places before the suffix.

  Returns
  -------
  str
      For example ``'12.5M'`` or ``'3.2B'``; the placeholder of :func:`missing` when there is no
      number.
  """
  gate = missing(value)
  if gate is not None:
    return gate
  if not is_numeric(value):
    return '--'
  magnitude = float(value)
  sign = '-' if magnitude < 0 else ''
  magnitude = abs(magnitude)
  for threshold, suffix in ((1e12, 'T'), (1e9, 'B'), (1e6, 'M'), (1e3, 'K')):
    if magnitude >= threshold:
      return f'{sign}{magnitude / threshold:.{digits}f}{suffix}'
  return f'{sign}{magnitude:,.0f}'


def breakable(text: Any) -> str:
  """Insert a zero-width space after every path separator so that long paths can wrap.

  Parameters
  ----------
  text : Any
      The text; None gives an empty string.

  Returns
  -------
  str
      ``text`` with ``U+200B`` after each of ``/ _ - .``.
  """
  if text is None:
    return ''
  return ''.join(
    f'{char}{ZERO_WIDTH_SPACE}' if char in _BREAK_AFTER else char for char in str(text)
  )


def slug(text: Any) -> str:
  """Turn text into a lowercase, hyphen-separated identifier.

  Parameters
  ----------
  text : Any
      The text, for example a heading.

  Returns
  -------
  str
      Letters and digits joined by single hyphens; ``'section'`` when nothing is left.
  """
  return _SLUG_RE.sub('-', str(text).lower()).strip('-') or 'section'


FILTERS: dict[str, Callable[..., Any]] = {
  'fmt_int': fmt_int,
  'fmt_float': fmt_float,
  'share': share,
  'fmt_bytes': fmt_bytes,
  'duration': duration,
  'pct': pct,
  'ppm': ppm,
  'sci': sci,
  'compact': compact,
  'missing': missing,
  'breakable': breakable,
  'slug': slug,
}
"""Filter name to function, registered in every environment."""


def _format_seconds(seconds: float) -> str:
  """Write a duration in seconds as ``h``, ``m`` and ``s`` parts (see :func:`duration`)."""
  if seconds < 0:
    return f'-{_format_seconds(-seconds)}'
  if seconds < 1:
    return f'{seconds:.1f}s'
  total = round(seconds)
  hours, remainder = divmod(total, 3600)
  minutes, secs = divmod(remainder, 60)
  parts = []
  if hours:
    parts.append(f'{hours}h')
  if minutes:
    parts.append(f'{minutes}m')
  if secs or not parts:
    parts.append(f'{secs}s')
  return ''.join(parts)
