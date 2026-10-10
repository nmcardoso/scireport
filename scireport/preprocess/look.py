"""The colours a chart takes from a layout, as plain data (ADR-0007).

A drawing function never reads a layout itself: it is handed a :class:`Look`, so that the same
function draws the same figure from a bundle's sidecar data long after the layout has moved on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

from scireport.styles.palette import Palette


@dataclass(frozen=True)
class Look:
  """Chart colours of one layout.

  Parameters
  ----------
  role : dict
      Colour with a fixed meaning (``failed``, ``success``, ``warning``, ``neutral``,
      ``annotation``) to ``#rrggbb``.
  cycle : tuple of str
      Series colours in order, as ``#rrggbb``.
  sequential, diverging : str
      matplotlib colour map names.
  """

  role: dict[str, str] = field(default_factory=dict)
  cycle: tuple[str, ...] = ()
  sequential: str = 'cividis'
  diverging: str = 'RdBu_r'

  @classmethod
  def from_palette(cls, palette: Palette) -> Look:
    """Take the chart colours of a resolved palette.

    Parameters
    ----------
    palette : Palette
        The palette of a layout.

    Returns
    -------
    Look
        Roles, cycle and colour maps of ``palette``.
    """
    return cls(
      role=palette.role_colors,
      cycle=tuple(palette.cycle_colors),
      sequential=palette.cmap.sequential,
      diverging=palette.cmap.diverging,
    )

  @classmethod
  def of_layout(cls, layout: str = 'default') -> Look:
    """Read the look of a layout.

    Parameters
    ----------
    layout : str, default='default'
        A layout reference (``name``, ``name@version`` or a directory).

    Returns
    -------
    Look
        The layout's chart colours.
    """
    from scireport.styles import palette

    return cls.from_palette(palette(layout))

  def color(self, role: str) -> str:
    """Return the colour of a chart role.

    Parameters
    ----------
    role : str
        For example ``'failed'`` or ``'annotation'``.

    Returns
    -------
    str
        ``#rrggbb``; a mid grey when the layout does not define the role.
    """
    return self.role.get(role, '#78838c')

  def series(self, index: int) -> str:
    """Return the colour of the ``index``-th series, wrapping around the cycle.

    Parameters
    ----------
    index : int
        Zero-based series index.

    Returns
    -------
    str
        ``#rrggbb``.
    """
    return self.cycle[index % len(self.cycle)] if self.cycle else self.color('neutral')


@cache
def default_look() -> Look:
  """Return the look of the default layout, read once.

  Returns
  -------
  Look
      What a drawing function uses when it is called without a look.
  """
  return Look.of_layout('default')
