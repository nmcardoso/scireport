"""``core.density_scatter``: a scatter of two columns, dense regions as hexagons, rare points kept.

Ported from the MOSAICS panel ``plot_density_scatter``. A plain scatter of a few hundred thousand
points piles ink into one blob and hides the rare points. The plane is binned into hexagons; a
hexagon holding more than ``threshold`` points is drawn as one cell coloured by its count, and
the points of a sparser hexagon stay individual, small and semi-transparent. The bundle holds the
hexagons and the sparse points only, never the full sample.

Parameters of the step (see :func:`density_scatter`):

* ``x_column``, ``y_column``: the two numeric columns; rows where either is null or not finite
  are dropped.
* ``gridsize``: hexagons across the x range. ``threshold``: a hexagon with this many points or
  fewer is not drawn as a cell.
* ``x_label``, ``y_label`` (the column names when omitted) and ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``kind`` (``'hex'`` or ``'point'``), ``x`` and ``y`` (hexagon centre or point),
``n`` (points in the hexagon, 1 for a point) and ``dx``, ``dy`` (the cell's horizontal and
vertical pitch, NaN for a point). No rows when nothing is finite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.core._scatter import finite_pairs, hex_table
from scireport.preprocess.plotting import draw_hex_bins, empty_axes, values_of
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_density_scatter(
  table: pa.Table, x_column: str, y_column: str, *, gridsize: int = 50, threshold: int = 3
) -> pa.Table:
  """Bin two columns into hexagons and sparse points.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  x_column, y_column : str
      Numeric columns; rows where either is not finite are dropped.
  gridsize : int, default=50
      Number of hexagons across the x range.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Columns ``kind``, ``x``, ``y``, ``n``, ``dx`` and ``dy``; see the module docstring.
  """
  x, y = finite_pairs(table, x_column, y_column)
  return hex_table(x, y, gridsize, threshold)


def render_density_scatter(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = '',
  y_label: str = '',
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
) -> Figure:
  """Draw the hexagons and points of :func:`compute_density_scatter`.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_density_scatter` made (or read back from a bundle's sidecar file).
  x_label, y_label, title : str
      Axis labels and title; empty strings draw nothing.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.6
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height)
    if data.num_rows == 0:
      empty_axes(ax, 'No data')
      return figure
    draw_hex_bins(ax, data, ctx.look)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'core.density_scatter',
  version=1,
  inputs={'table': Port('table', description='One row per object, two numeric columns')},
  outputs={'figure': Port('figure', description='The hybrid density scatter')},
  render=render_density_scatter,
)
def density_scatter(
  ctx: Context,
  *,
  table: pa.Table,
  x_column: str,
  y_column: str,
  gridsize: int = 50,
  threshold: int = 3,
  x_label: str | None = None,
  y_label: str | None = None,
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Scatter of two columns: hexagons where it is crowded, individual points where it is not.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object.
  x_column, y_column : str
      Numeric columns for the two axes.
  gridsize : int, default=50
      Number of hexagons across the x range.
  threshold : int, default=3
      A hexagon with this many points or fewer is drawn as individual points.
  x_label, y_label : str or None, default=None
      Axis labels; the column names when None.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.6
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the column names and counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_density_scatter(table, x_column, y_column, gridsize=gridsize, threshold=threshold)
  figure = render_density_scatter(
    ctx,
    data,
    x_label=x_column if x_label is None else x_label,
    y_label=y_column if y_label is None else y_label,
    title=title,
    width=width,
    height=height,
  )
  text = alt or _alt(data, x_column, y_column)
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _alt(data: pa.Table, x_column: str, y_column: str) -> str:
  """Describe the figure from its data, with no number that is not counted."""
  if data.num_rows == 0:
    return f'Density scatter of {y_column} against {x_column}: no finite pairs.'
  kinds = data.column('kind').to_pylist()
  cells = kinds.count('hex')
  points = kinds.count('point')
  counts = values_of(data, 'n')
  total = int(np.nansum(counts))
  return (
    f'Density scatter of {y_column} against {x_column}: {total:,} pairs, drawn as {cells:,} '
    f'hexagons and {points:,} individual points.'
  )
