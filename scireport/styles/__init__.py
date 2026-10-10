"""The matplotlib style API: figures that look like the report (ADR-0007).

``mplstyle()`` is a context manager that applies the style of a layout and restores matplotlib's
parameters on exit, so a report can share a process with code that reads ``rcParams``.
``mplstyle_path()`` and ``palette()`` give the style file and the palette of a layout, and
``figure()`` makes a figure at its final size as a fraction of the page frame. ``save_figure()``
and ``figure_bytes()`` write PNG, PDF and SVG without a date, a version or a random id inside.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scireport.errors import TemplateError
from scireport.logging_utils import get_logger
from scireport.styles import fonts
from scireport.styles.figures import (
  DEFAULT_DPI,
  figure_bytes,
  new_figure,
  save_figure,
)
from scireport.styles.palette import Palette, load_palette

if TYPE_CHECKING:
  from matplotlib.figure import Figure

log = get_logger(__name__)

STYLES_DIR = Path(__file__).resolve().parent
"""Where the shipped ``<name>.mplstyle`` files are."""
PAPER_MM = {'a4': (210.0, 297.0), 'letter': (215.9, 279.4)}
"""Paper name to width and height in millimetres."""

__all__ = [
  'DEFAULT_DPI',
  'Palette',
  'figure',
  'figure_bytes',
  'fonts',
  'mplstyle',
  'mplstyle_path',
  'palette',
  'save_figure',
]


def mplstyle_path(layout: str = 'default') -> Path:
  """Return the matplotlib style file of a layout.

  Parameters
  ----------
  layout : str, default='default'
      A layout reference (``name``, ``name@version`` or a directory), as in ``scireport render``.

  Returns
  -------
  pathlib.Path
      The ``.mplstyle`` file. ``layout.yaml`` names it either by a shipped style (``default``,
      found in ``scireport/styles/``) or by a path relative to the layout directory.

  Raises
  ------
  TemplateError
      With ``E701`` when the layout does not exist, and ``E703`` when it has no style or names a
      file that is not there.
  """
  from scireport.render.registry import load_layout

  loaded = load_layout(layout)
  name = loaded.definition.mplstyle
  if not name:
    raise TemplateError(f'layout {loaded.ref} has no matplotlib style', code='E703')
  if '/' in name or name.endswith('.mplstyle'):
    path = (loaded.root / name).resolve()
    if not path.is_relative_to(loaded.root.resolve()):
      raise TemplateError(f'the style {name!r} leaves the layout directory', code='E703')
  else:
    path = STYLES_DIR / f'{name}.mplstyle'
  if not path.is_file():
    raise TemplateError(
      f'layout {loaded.ref} names the style {name!r}, which is missing', code='E703'
    )
  return path


def palette(layout: str = 'default') -> Palette:
  """Return the palette of a layout: colours, chart roles, fonts and page geometry.

  Parameters
  ----------
  layout : str, default='default'
      A layout reference (``name``, ``name@version`` or a directory).

  Returns
  -------
  Palette
      The parsed ``palette.yaml`` of the layout.

  Raises
  ------
  TemplateError
      With ``E701`` when the layout does not exist, ``E703`` when it has no palette file and
      ``E702`` when the file is invalid.
  """
  from scireport.render.registry import load_layout

  loaded = load_layout(layout)
  name = loaded.definition.palette
  if not name:
    raise TemplateError(f'layout {loaded.ref} has no palette', code='E703')
  return load_palette(loaded.root / name)


@contextmanager
def mplstyle(layout: str = 'default', *, rc: dict[str, Any] | None = None) -> Iterator[None]:
  """Apply the matplotlib style of a layout for the duration of a ``with`` block.

  Registers the vendored fonts first. matplotlib's parameters are restored on exit, so the style
  never leaks into code that has nothing to do with the report. Draw everything of a figure
  (axes, labels, legends) inside the block: most parameters are read when an artist is created.

  Parameters
  ----------
  layout : str, default='default'
      A layout reference.
  rc : dict or None, default=None
      matplotlib parameters applied on top of the style, for one-off changes.

  Yields
  ------
  None
      Nothing; the parameters are set while the block runs.

  Raises
  ------
  TemplateError
      When the layout or its style cannot be found (see :func:`mplstyle_path`).
  """
  import matplotlib as mpl
  import matplotlib.style

  path = mplstyle_path(layout)
  fonts.register()
  _probe_once()
  extra: dict[Any, Any] = dict(rc or {})
  with matplotlib.style.context(str(path)), mpl.rc_context(extra):
    yield


def figure(
  width: float = 1.0,
  height: float = 3.6,
  nrows: int = 1,
  ncols: int = 1,
  *,
  layout: str = 'default',
  paper: str = 'a4',
  subplot_kw: dict[str, Any] | None = None,
) -> tuple[Figure, Any]:
  """Create a figure at its final size, as a fraction of the page frame, in the style of a layout.

  The size is physical: a figure of ``width=0.5`` is half the usable page width, so a font size
  of 8 pt is 8 pt on paper. The figure is made inside :func:`mplstyle`; draw on it inside a
  ``with scireport.mplstyle(layout):`` block too, so that later artists get the same style.

  Parameters
  ----------
  width : float, default=1.0
      Width as a fraction of the frame (clamped to 1).
  height : float, default=3.6
      Height in inches (clamped to the frame height).
  nrows, ncols : int, default=1
      The grid of axes.
  layout : str, default='default'
      The layout whose style and page margins apply.
  paper : {'a4', 'letter'}, default='a4'
      The paper size of the report.
  subplot_kw : dict or None, default=None
      Passed to every subplot.

  Returns
  -------
  tuple
      The figure and its axes (a single ``Axes`` for a 1x1 grid, an array otherwise).

  Raises
  ------
  ValueError
      When ``paper`` is unknown or a size is not positive.
  """
  if paper not in PAPER_MM:
    raise ValueError(f'paper must be one of {", ".join(PAPER_MM)}, got {paper!r}')
  page = palette(layout).page.model_copy(
    update={'width_mm': PAPER_MM[paper][0], 'height_mm': PAPER_MM[paper][1]}
  )
  with mplstyle(layout):
    return new_figure(
      width,
      height,
      nrows,
      ncols,
      frame_width_in=page.frame_width_in,
      frame_height_in=page.frame_height_in,
      subplot_kw=subplot_kw,
    )


_probed = {'done': False}


def _probe_once() -> None:
  """Run the font probe the first time a style is applied; it logs a warning per fallback."""
  if _probed['done']:
    return
  _probed['done'] = True
  fonts.probe()
