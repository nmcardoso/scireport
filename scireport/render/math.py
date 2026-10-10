"""LaTeX math to a themed SVG, the equation renderer for HTML and WeasyPrint (ADR-0010).

WeasyPrint runs no JavaScript, so KaTeX cannot be used; matplotlib's mathtext parser draws the
equation as vector paths instead. ``svg.fonttype: path`` makes the SVG self-contained (no font
is referenced by name) and ``svg.hashsalt`` makes the generated ids, and so the bytes,
deterministic. Mathtext implements a large subset of LaTeX math, not all of it; a construct it
cannot draw gives warning ``W601`` and the renderer shows the source instead. The ``usetex``
renderer (full LaTeX through matplotlib) is added with the PDF engines in phase S3.
"""

from __future__ import annotations

import base64
import functools
import io
from dataclasses import dataclass
from typing import Any

from scireport.errors import ScireportError

DISPLAY_FONTSIZE = 14.0
"""Point size of a standalone (display) equation."""
INLINE_FONTSIZE = 10.0
"""Point size of inline math; matches the body text of the built-in layouts."""
DEFAULT_COLOR = '#1a1a1a'
"""Colour of the glyphs when the layout does not give one."""

_MEASURE_DPI = 200
_RC: dict[Any, Any] = {
  'svg.fonttype': 'path',
  'mathtext.fontset': 'dejavusans',
  'svg.hashsalt': 'scireport',
}
_SVG_METADATA: dict[str, str | None] = {'Creator': None, 'Date': None}


class MathError(ScireportError):
  """The math cannot be drawn by mathtext (warning ``W601``)."""

  def __init__(self, latex: str, reason: str) -> None:
    super().__init__(
      f'cannot draw {latex!r}: {reason}',
      code='W601',
      hint='Mathtext draws a subset of LaTeX math; the source is shown instead.',
    )


@dataclass(frozen=True)
class MathSvg:
  """A drawn equation.

  Parameters
  ----------
  data_uri : str
      ``data:image/svg+xml;base64,...``, usable as an ``<img>`` source.
  depth_pt : float
      How far the expression descends below its baseline, in points; an inline image is
      shifted down by this much to sit on the text baseline.
  """

  data_uri: str
  depth_pt: float


def math_problem(latex: str) -> str | None:
  """Say why mathtext cannot draw an expression, or None when it can.

  Parameters
  ----------
  latex : str
      The expression, without ``$`` delimiters.

  Returns
  -------
  str or None
      The parser's complaint, or None.
  """
  from matplotlib import mathtext

  try:
    mathtext.MathTextParser('path').parse(f'${latex}$', dpi=_MEASURE_DPI)
  except (ValueError, RuntimeError, KeyError) as exc:
    return str(exc).replace('\n', ' ')
  return None


@functools.cache
def render_math(latex: str, *, display: bool, color: str = DEFAULT_COLOR) -> MathSvg:
  """Draw an expression with mathtext.

  Parameters
  ----------
  latex : str
      The expression, without ``$`` delimiters.
  display : bool
      Draw at the display size (a standalone equation) rather than the inline size.
  color : str, default=DEFAULT_COLOR
      Glyph colour, any matplotlib colour.

  Returns
  -------
  MathSvg
      The SVG and its descent.

  Raises
  ------
  MathError
      With code ``W601`` when mathtext cannot parse the expression.
  """
  import matplotlib as mpl
  from matplotlib import mathtext
  from matplotlib.figure import Figure
  from matplotlib.font_manager import FontProperties

  size = DISPLAY_FONTSIZE if display else INLINE_FONTSIZE
  try:
    with mpl.rc_context(_RC):
      parsed = mathtext.MathTextParser('path').parse(
        f'${latex}$', dpi=_MEASURE_DPI, prop=FontProperties(size=size)
      )
      figure = Figure(figsize=(0.01, 0.01))
      figure.patch.set_alpha(0.0)
      figure.text(0, 0, f'${latex}$', fontsize=size, color=color)
      buffer = io.BytesIO()
      figure.savefig(
        buffer,
        format='svg',
        transparent=True,
        bbox_inches='tight',
        pad_inches=0.02,
        metadata=_SVG_METADATA,
      )
  except (ValueError, RuntimeError, KeyError) as exc:
    raise MathError(latex, str(exc).replace('\n', ' ')) from exc
  depth_pt = parsed.depth * 72.0 / _MEASURE_DPI
  data = base64.b64encode(buffer.getvalue()).decode('ascii')
  return MathSvg(f'data:image/svg+xml;base64,{data}', depth_pt)
