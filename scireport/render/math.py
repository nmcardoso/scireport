"""LaTeX math to a themed SVG, the equation renderer for HTML and WeasyPrint (ADR-0010).

WeasyPrint runs no JavaScript, so KaTeX cannot be used; matplotlib draws the equation as vector
paths instead, with one of two renderers (``render.math_renderer``). ``mathtext`` is matplotlib's
own parser: pure Python, no TeX needed. ``usetex`` sends the expression through a real LaTeX
(matplotlib's ``text.usetex``) and draws the glyph paths of the resulting DVI: full LaTeX math,
but it needs ``latex`` on the path. ``svg.fonttype: path`` makes the SVG self-contained (no font
is referenced by name) and ``svg.hashsalt`` makes the generated ids, and so the bytes,
deterministic. Mathtext implements a large subset of LaTeX math, not all of it; a construct it
cannot draw gives warning ``W601`` and the renderer shows the source instead; under ``usetex`` an
expression LaTeX rejects gives ``W602`` and the same fallback.
"""

from __future__ import annotations

import base64
import functools
import io
import shutil
from dataclasses import dataclass
from typing import Any

from scireport.errors import MissingDependencyError, ScireportError

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
  """The math cannot be drawn: ``W601`` for mathtext, ``W602`` for ``usetex``."""

  def __init__(self, latex: str, reason: str, *, renderer: str = 'mathtext') -> None:
    super().__init__(
      f'cannot draw {latex!r}: {reason}',
      code='W602' if renderer == 'usetex' else 'W601',
      hint=(
        'LaTeX rejected the expression; the source is shown instead.'
        if renderer == 'usetex'
        else 'Mathtext draws a subset of LaTeX math; the source is shown instead.'
      ),
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
def render_math(
  latex: str, *, display: bool, color: str = DEFAULT_COLOR, renderer: str = 'mathtext'
) -> MathSvg:
  """Draw an expression with mathtext.

  Parameters
  ----------
  latex : str
      The expression, without ``$`` delimiters.
  display : bool
      Draw at the display size (a standalone equation) rather than the inline size.
  color : str, default=DEFAULT_COLOR
      Glyph colour, any matplotlib colour.
  renderer : {'mathtext', 'usetex'}, default='mathtext'
      Matplotlib's own parser, or a real LaTeX run.

  Returns
  -------
  MathSvg
      The SVG and its descent.

  Raises
  ------
  MathError
      With code ``W601`` when mathtext cannot parse the expression, ``W602`` when LaTeX rejects
      it under ``usetex``.
  MissingDependencyError
      With ``E901`` when ``usetex`` is chosen and ``latex`` is not installed.
  """
  import matplotlib as mpl
  from matplotlib import mathtext
  from matplotlib.figure import Figure
  from matplotlib.font_manager import FontProperties

  size = DISPLAY_FONTSIZE if display else INLINE_FONTSIZE
  usetex = renderer == 'usetex'
  if usetex and shutil.which('latex') is None:
    raise MissingDependencyError(
      'the usetex math renderer needs latex, which is not installed or not on the path',
      code='E901',
      hint='Install TeX Live, or use the default mathtext renderer (--math-renderer mathtext).',
    )
  rc = (
    {**_RC, 'text.usetex': True, 'text.latex.preamble': r'\usepackage{amsmath,amssymb}'}
    if usetex
    else _RC
  )
  try:
    with mpl.rc_context(rc):
      depth_pt = (
        _usetex_depth(latex, size)
        if usetex
        else mathtext.MathTextParser('path')
        .parse(f'${latex}$', dpi=_MEASURE_DPI, prop=FontProperties(size=size))
        .depth
        * 72.0
        / _MEASURE_DPI
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
  except (ValueError, RuntimeError, KeyError, OSError) as exc:
    raise MathError(latex, str(exc).replace('\n', ' ')[:300], renderer=renderer) from exc
  data = base64.b64encode(buffer.getvalue()).decode('ascii')
  return MathSvg(f'data:image/svg+xml;base64,{data}', depth_pt)


def _usetex_depth(latex: str, size: float) -> float:
  """Measure how far a LaTeX expression descends below its baseline, in points."""
  from matplotlib.texmanager import TexManager

  _, _, descent = TexManager().get_text_width_height_descent(f'${latex}$', size)
  return float(descent)
