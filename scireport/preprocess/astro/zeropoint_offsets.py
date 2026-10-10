"""``astro.zeropoint_offsets``: one band's cross-survey magnitude offset against colour.

Ported from the MOSAICS panel ``plot_zeropoint_offsets``. A slope of the offset against colour
is a colour term (the two surveys' passbands differ enough that the offset depends on the
source's spectral shape); a flat cloud with a non-zero median and no slope is a pure zero-point
offset. The panel draws the hexagon density of the offset (crowded regions as cells, sparse
points individually), a dashed zero line and, optionally, a least-squares line.

Parameters of the step (see :func:`zeropoint_offsets`):

* ``color_column``: the reference colour, on the x axis.
* ``delta_column``: the offset ``m_a - m_b`` between the two surveys, on the y axis.
* ``fit``: fit a straight line (ordinary least squares, ``numpy.polyfit`` of degree 1) over the
  finite pairs and draw it over their colour range; skipped when fewer than two pairs or a
  single colour value.
* ``gridsize``, ``threshold``: hexagons across the colour range, and the occupancy up to which a
  hexagon is drawn as individual points.
* ``x_label``, ``y_label``, ``title``, ``width`` (fraction of the page frame), ``height``
  (inches), ``alt`` and ``caption``.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``kind`` (``hex``, ``point`` or ``fit``), ``x``, ``y`` (colour and offset of a
hexagon centre or point; for ``fit`` the two end points of the line, lowest colour first),
``n`` (points in the hexagon, 1 for a point), ``dx`` and ``dy`` (hexagon pitch, null otherwise).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.astro._density_marks import cells_of, density_table, marks_of, n_points
from scireport.preprocess.context import Context
from scireport.preprocess.plotting import draw_hex_bins, empty_axes, numbers, require_columns
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_zeropoint_offsets(
  table: pa.Table,
  color_column: str,
  delta_column: str,
  *,
  fit: bool = True,
  gridsize: int = 60,
  threshold: int = 3,
) -> pa.Table:
  """Bin an offset against colour and add the fitted colour term.

  Parameters
  ----------
  table : pyarrow.Table
      The catalogue.
  color_column, delta_column : str
      Colour and offset columns.
  fit : bool, default=True
      Fit a line (degree-1 least squares) to the finite pairs.
  gridsize : int, default=60
      Hexagons across the colour range.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Rows of kind ``hex`` and ``point`` and, when fitted, two rows of kind ``fit`` (the line at
      the lowest and highest colour). Empty when no row has both values finite.
  """
  require_columns(table, color_column, delta_column)
  x = numbers(table, color_column)
  y = numbers(table, delta_column)
  keep = np.isfinite(x) & np.isfinite(y)
  x, y = x[keep], y[keep]
  marks: list[tuple[str, float, float]] = []
  if fit and x.size >= 2 and float(x.max()) > float(x.min()):
    slope, intercept = (float(value) for value in np.polyfit(x, y, 1))
    low, high = float(x.min()), float(x.max())
    marks = [('fit', low, slope * low + intercept), ('fit', high, slope * high + intercept)]
  return density_table(x, y, gridsize=gridsize, threshold=threshold, marks=marks)


def render_zeropoint_offsets(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = 'Colour (mag)',
  y_label: str = 'Δm (mag)',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
) -> Figure:
  """Draw the density of :func:`compute_zeropoint_offsets`, a zero line and the fitted line.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_zeropoint_offsets` made (or read back from a bundle's sidecar).
  x_label, y_label, title : str
      Axis labels and title; an empty title draws nothing.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.4
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height)
    cells = cells_of(data)
    if cells.num_rows == 0:
      empty_axes(ax, 'No data')
      return figure
    draw_hex_bins(ax, cells, ctx.look)
    ax.axhline(0.0, color=ctx.look.color('annotation'), linewidth=1, linestyle='--')
    line_x, line_y = marks_of(data, 'fit')
    if line_x.size == 2:
      slope = float((line_y[1] - line_y[0]) / (line_x[1] - line_x[0]))
      intercept = float(line_y[0] - slope * line_x[0])
      ax.plot(
        line_x,
        line_y,
        color=ctx.look.color('warning'),
        linewidth=1.4,
        label=f'fit: {slope:.3f}x + {intercept:.3f}',
      )
      ax.legend(fontsize=7)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'astro.zeropoint_offsets',
  version=1,
  inputs={'table': Port('table', description='Catalogue with a colour and a magnitude offset')},
  outputs={'figure': Port('figure', description='Density of the offset against colour')},
  render=render_zeropoint_offsets,
)
def zeropoint_offsets(
  ctx: Context,
  *,
  table: pa.Table,
  color_column: str,
  delta_column: str,
  fit: bool = True,
  gridsize: int = 60,
  threshold: int = 3,
  x_label: str = 'Colour (mag)',
  y_label: str = 'Δm (mag)',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """One band's cross-survey magnitude offset against colour, as a hexagon density.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per matched object, with a reference colour and the offset ``m_a - m_b``.
  color_column : str
      Colour column (x axis).
  delta_column : str
      Offset column (y axis).
  fit : bool, default=True
      Draw a least-squares line over the colour range; its slope is the colour term.
  gridsize : int, default=60
      Hexagons across the colour range.
  threshold : int, default=3
      A hexagon with this many points or fewer is drawn as individual points.
  x_label, y_label : str
      Axis labels.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.4
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the columns, the point count and the fit when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_zeropoint_offsets(
    table, color_column, delta_column, fit=fit, gridsize=gridsize, threshold=threshold
  )
  figure = render_zeropoint_offsets(
    ctx, data, x_label=x_label, y_label=y_label, title=title, width=width, height=height
  )
  line_x, line_y = marks_of(data, 'fit')
  slope_text = ''
  if line_x.size == 2:
    slope = float((line_y[1] - line_y[0]) / (line_x[1] - line_x[0]))
    slope_text = f' A fitted line has slope {slope:.3f} mag per mag of colour.'
  text = alt or (
    f'Density of the magnitude offset ({delta_column}) against colour ({color_column}) '
    f'for {n_points(data):,} objects, with a dashed line at zero.{slope_text}'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
