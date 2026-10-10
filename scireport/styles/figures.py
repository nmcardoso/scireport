"""Frame-aware figure sizes and deterministic saving (ADR-0007).

A figure is made at its final physical size, as a fraction of the usable width of the page, so
that its text is as large in the report as it was on screen. Saving strips everything that varies
between runs (the matplotlib version, creation dates, random ids), so that the same drawing gives
the same bytes.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
  from matplotlib.figure import Figure

DEFAULT_DPI = 200
"""Resolution of PNG files; true 200 dpi."""
PNG_METADATA: dict[str, str | None] = {'Software': None}
PDF_METADATA: dict[str, Any] = {
  'Creator': None,
  'Producer': None,
  'CreationDate': None,
  'ModDate': None,
}
SVG_METADATA: dict[str, str | None] = {'Creator': None, 'Date': None}
FigureFormat = Literal['png', 'pdf', 'svg']
_SVG_RC: dict[str, Any] = {'svg.fonttype': 'path', 'svg.hashsalt': 'scireport'}
_PDF_RC: dict[str, Any] = {'pdf.fonttype': 42}


def new_figure(
  width: float = 1.0,
  height: float = 3.6,
  nrows: int = 1,
  ncols: int = 1,
  *,
  frame_width_in: float,
  frame_height_in: float,
  subplot_kw: dict[str, Any] | None = None,
) -> tuple[Figure, Any]:
  """Create a figure at its final size, with a grid of axes.

  Prefer :func:`scireport.figure`, which knows the frame of a layout and applies its style.

  Parameters
  ----------
  width : float, default=1.0
      Width as a fraction of the frame; larger values are clamped to 1.
  height : float, default=3.6
      Height in inches; larger than the frame is clamped to the frame height.
  nrows, ncols : int, default=1
      The grid of axes.
  frame_width_in, frame_height_in : float
      The usable page area in inches.
  subplot_kw : dict or None, default=None
      Passed to every subplot, for example ``{'projection': 'mollweide'}``.

  Returns
  -------
  tuple
      The figure and its axes: one ``Axes`` for a 1x1 grid, an array otherwise.

  Raises
  ------
  ValueError
      When ``width``, ``height`` or the grid is not positive.
  """
  from matplotlib.figure import Figure

  if width <= 0 or height <= 0:
    raise ValueError(f'width and height must be positive, got {width} and {height}')
  if nrows < 1 or ncols < 1:
    raise ValueError(f'the grid must have at least one row and one column, got {nrows}x{ncols}')
  figure = Figure(figsize=(frame_width_in * min(width, 1.0), min(height, frame_height_in)))
  axes = figure.subplots(nrows, ncols, subplot_kw=subplot_kw)
  return figure, axes


def figure_bytes(
  figure: Figure,
  format: FigureFormat = 'png',
  *,
  dpi: int = DEFAULT_DPI,
  tight: bool = True,
) -> bytes:
  """Draw a figure to bytes that do not vary between runs.

  Parameters
  ----------
  figure : matplotlib.figure.Figure
      The figure, already drawn on.
  format : {'png', 'pdf', 'svg'}, default='png'
      The file type. PDF embeds TrueType (type 42) fonts; SVG draws text as paths.
  dpi : int, default=200
      Resolution of a PNG; ignored by the vector formats.
  tight : bool, default=True
      Crop to the content (``bbox_inches='tight'``), as the report figures are.

  Returns
  -------
  bytes
      The file: no matplotlib version, no date and no random id inside.

  Raises
  ------
  ValueError
      When ``format`` is not one of ``png``, ``pdf`` or ``svg``.
  """
  import matplotlib as mpl

  if format not in ('png', 'pdf', 'svg'):
    raise ValueError(f'figure format must be png, pdf or svg, got {format!r}')
  metadata: dict[str, Any] = {'png': PNG_METADATA, 'pdf': PDF_METADATA, 'svg': SVG_METADATA}[format]
  rc: dict[Any, Any] = {'png': {}, 'pdf': dict(_PDF_RC), 'svg': dict(_SVG_RC)}[format]
  buffer = io.BytesIO()
  with mpl.rc_context(rc):
    figure.savefig(
      buffer,
      format=format,
      dpi=dpi,
      bbox_inches='tight' if tight else None,
      metadata=metadata,
    )
  return buffer.getvalue()


def save_figure(
  figure: Figure,
  path: str | Path,
  *,
  dpi: int = DEFAULT_DPI,
  tight: bool = True,
  close: bool = False,
) -> Path:
  """Save a figure to a PNG, PDF or SVG file, chosen by the suffix, without run-varying bytes.

  Parameters
  ----------
  figure : matplotlib.figure.Figure
      The figure, already drawn on.
  path : str or pathlib.Path
      Destination; the suffix (``.png``, ``.pdf`` or ``.svg``) selects the format. Parent
      directories are created.
  dpi : int, default=200
      Resolution of a PNG.
  tight : bool, default=True
      Crop to the content.
  close : bool, default=False
      Close the figure afterwards, which frees it when it was made with pyplot.

  Returns
  -------
  pathlib.Path
      ``path``.

  Raises
  ------
  ValueError
      When the suffix is not ``.png``, ``.pdf`` or ``.svg``.
  """
  target = Path(path)
  suffix = target.suffix.lower().lstrip('.')
  if suffix not in ('png', 'pdf', 'svg'):
    raise ValueError(f'cannot save a figure as {target.suffix!r}: use .png, .pdf or .svg')
  data = figure_bytes(figure, suffix, dpi=dpi, tight=tight)  # type: ignore[arg-type]
  target.parent.mkdir(parents=True, exist_ok=True)
  target.write_bytes(data)
  if close:
    import matplotlib.pyplot as plt

    plt.close(figure)
  return target
