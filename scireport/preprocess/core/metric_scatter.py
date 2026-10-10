"""``core.metric_scatter``: one metric of the left dataset against the same metric of the right.

Ported from the MOSAICS panel ``plot_metric_scatter`` (for example the maximum pixel value of
each stamp in one dataset against the other, or an astrophysical property). It is the hybrid
density of ``core.density_scatter`` (hexagons where crowded, individual points where sparse) with
the dashed ``y = x`` line that shows where perfect agreement lies.

Parameters of the step (see :func:`metric_scatter`):

* ``x_column`` (left metric) and ``y_column`` (right metric): numeric columns, one row per
  object; rows where either is null or not finite are dropped.
* ``x_label``, ``y_label`` (default ``'left'`` and ``'right'``) and ``title``.
* ``gridsize``: hexagons across the x range. ``threshold``: a hexagon with this many points or
  fewer is not drawn as a cell.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: those of ``core.density_scatter`` (``kind`` of ``'hex'`` or ``'point'``, ``x``,
``y``, ``n``, ``dx``, ``dy``) plus two rows of ``kind = 'line'`` that hold the end points of the
``y = x`` line, from ``(lo, lo)`` to ``(hi, hi)`` where ``lo`` and ``hi`` are the smallest and
largest value of either column (``n``, ``dx`` and ``dy`` are NaN in them). No rows at all when
nothing is finite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.core._scatter import finite_pairs, hex_table, typed, without_kind
from scireport.preprocess.plotting import draw_hex_bins, empty_axes, values_of
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_metric_scatter(
  table: pa.Table, x_column: str, y_column: str, *, gridsize: int = 50, threshold: int = 3
) -> pa.Table:
  """Bin the two metrics and add the end points of the ``y = x`` line.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  x_column, y_column : str
      Numeric columns (left and right metric); rows where either is not finite are dropped.
  gridsize : int, default=50
      Number of hexagons across the x range.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      The hexagon table of :func:`~scireport.preprocess.core._scatter.hex_table` followed by two
      ``'line'`` rows, ``(lo, lo)`` and ``(hi, hi)``; empty when nothing is finite.
  """
  x, y = finite_pairs(table, x_column, y_column)
  cells = hex_table(x, y, gridsize, threshold)
  if x.size == 0:
    return cells
  lo = float(min(x.min(), y.min()))
  hi = float(max(x.max(), y.max()))
  nan = float('nan')
  line = typed(
    {
      'kind': ['line', 'line'],
      'x': [lo, hi],
      'y': [lo, hi],
      'n': [nan, nan],
      'dx': [nan, nan],
      'dy': [nan, nan],
    }
  )
  return pa.concat_tables([cells, line])


def render_metric_scatter(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = 'left',
  y_label: str = 'right',
  title: str = 'Metric comparison',
  width: float = 1.0,
  height: float = 3.6,
) -> Figure:
  """Draw the hybrid density and the ``y = x`` line of :func:`compute_metric_scatter`.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_metric_scatter` made (or read back from a bundle's sidecar file).
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
    cells = without_kind(data, 'line')
    if cells.num_rows:
      draw_hex_bins(ax, cells, ctx.look)
    is_line = np.asarray(data.column('kind').to_pylist(), dtype=object) == 'line'
    line_x, line_y = values_of(data, 'x')[is_line], values_of(data, 'y')[is_line]
    if line_x.size:
      ax.plot(
        line_x,
        line_y,
        color=ctx.look.color('annotation'),
        linewidth=1,
        linestyle='--',
        label='y = x',
      )
      ax.legend()
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'core.metric_scatter',
  version=1,
  inputs={'table': Port('table', description='One row per object, a left and a right metric')},
  outputs={'figure': Port('figure', description='Left metric against right metric')},
  render=render_metric_scatter,
)
def metric_scatter(
  ctx: Context,
  *,
  table: pa.Table,
  x_column: str,
  y_column: str,
  x_label: str = 'left',
  y_label: str = 'right',
  title: str = 'Metric comparison',
  gridsize: int = 50,
  threshold: int = 3,
  width: float = 1.0,
  height: float = 3.6,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Compare a per-object metric of the left dataset with the right one, against ``y = x``.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object.
  x_column, y_column : str
      Numeric columns: the left metric (x axis) and the right metric (y axis).
  x_label, y_label : str, default='left', 'right'
      Axis labels.
  title : str, default='Metric comparison'
      Title; nothing when empty.
  gridsize : int, default=50
      Number of hexagons across the x range.
  threshold : int, default=3
      A hexagon with this many points or fewer is drawn as individual points.
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
  data = compute_metric_scatter(table, x_column, y_column, gridsize=gridsize, threshold=threshold)
  figure = render_metric_scatter(
    ctx, data, x_label=x_label, y_label=y_label, title=title, width=width, height=height
  )
  text = alt or _alt(data, x_column, y_column)
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _alt(data: pa.Table, x_column: str, y_column: str) -> str:
  """Describe the figure from its data, with no number that is not counted."""
  if data.num_rows == 0:
    return f'Metric comparison of {y_column} against {x_column}: no finite pairs.'
  kinds = data.column('kind').to_pylist()
  counts = values_of(data, 'n')
  total = int(np.nansum(counts))
  return (
    f'Metric comparison of {y_column} against {x_column} with the y = x line: {total:,} pairs, '
    f'drawn as {kinds.count("hex"):,} hexagons and {kinds.count("point"):,} individual points.'
  )
