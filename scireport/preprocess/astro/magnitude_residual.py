"""``astro.magnitude_residual``: a magnitude residual against magnitude.

Ported from the MOSAICS panel ``plot_magnitude_residual``. Used for the closure check (a derived
flux density inverted back to a magnitude and compared with the survey's published one) and for
any other residual that needs plotting against magnitude: the panel draws the hexagon density
of the residual (crowded regions as cells, sparse points individually) with a dashed zero line.

Parameters of the step (see :func:`magnitude_residual`):

* ``magnitude_column``: the reference magnitude, on the x axis.
* ``residual_column``: the residual (for example recovered minus published), on the y axis.
* ``gridsize``, ``threshold``: hexagons across the magnitude range, and the occupancy up to
  which a hexagon is drawn as individual points.
* ``x_label``, ``y_label``, ``title``, ``width`` (fraction of the page frame), ``height``
  (inches), ``alt`` and ``caption``.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``kind`` (``hex`` or ``point``), ``x``, ``y`` (magnitude and residual of a
hexagon centre or point), ``n`` (points in the hexagon, 1 for a point), ``dx`` and ``dy``
(hexagon pitch, null for a point).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.astro._density_marks import cells_of, density_table, n_points
from scireport.preprocess.context import Context
from scireport.preprocess.plotting import draw_hex_bins, empty_axes, numbers, require_columns
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_magnitude_residual(
  table: pa.Table,
  magnitude_column: str,
  residual_column: str,
  *,
  gridsize: int = 60,
  threshold: int = 3,
) -> pa.Table:
  """Bin a residual against magnitude into hexagons and sparse points.

  Parameters
  ----------
  table : pyarrow.Table
      The catalogue.
  magnitude_column, residual_column : str
      Reference magnitude and residual columns.
  gridsize : int, default=60
      Hexagons across the magnitude range.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Rows of kind ``hex`` and ``point``; empty when no row has both values finite.
  """
  require_columns(table, magnitude_column, residual_column)
  x = numbers(table, magnitude_column)
  y = numbers(table, residual_column)
  keep = np.isfinite(x) & np.isfinite(y)
  return density_table(x[keep], y[keep], gridsize=gridsize, threshold=threshold)


def render_magnitude_residual(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = 'Published magnitude',
  y_label: str = 'Recovered - published (mag)',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
) -> Figure:
  """Draw the density of :func:`compute_magnitude_residual` with a dashed zero line.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_magnitude_residual` made (or read back from a bundle's sidecar).
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
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'astro.magnitude_residual',
  version=1,
  inputs={'table': Port('table', description='Catalogue with a magnitude and a residual column')},
  outputs={'figure': Port('figure', description='Density of the residual against magnitude')},
  render=render_magnitude_residual,
)
def magnitude_residual(
  ctx: Context,
  *,
  table: pa.Table,
  magnitude_column: str,
  residual_column: str,
  gridsize: int = 60,
  threshold: int = 3,
  x_label: str = 'Published magnitude',
  y_label: str = 'Recovered - published (mag)',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Draw a magnitude residual against magnitude as a hexagon density.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object, with a reference magnitude and a residual.
  magnitude_column : str
      Reference magnitude column (x axis).
  residual_column : str
      Residual column (y axis); the sign and meaning are the caller's.
  gridsize : int, default=60
      Hexagons across the magnitude range.
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
      Alternative text; built from the columns and the point count when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_magnitude_residual(
    table, magnitude_column, residual_column, gridsize=gridsize, threshold=threshold
  )
  figure = render_magnitude_residual(
    ctx, data, x_label=x_label, y_label=y_label, title=title, width=width, height=height
  )
  text = alt or (
    f'Density of the residual ({residual_column}) against magnitude ({magnitude_column}) '
    f'for {n_points(data):,} objects, with a dashed line at zero.'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
