"""``core.corner``: a corner (pairs) plot of several numeric columns.

Ported from the MOSAICS panel ``plot_corner``. The diagonal holds the histogram of each column,
the lower triangle holds the hybrid density of each pair (hexagons where crowded, individual
points where sparse, no colour bar: the point of a corner plot is the shape of each pair, not
its exact counts), and the upper triangle is left blank.

Parameters of the step (see :func:`corner`):

* ``columns``: two to eight numeric columns, in the order of the grid (the first is the top row
  and the left column). More than eight is an ``E602`` parameter error: the grid would be too small
  to read.
* ``bins``: bins of each diagonal histogram. ``gridsize``: hexagons across the x range of each
  pair. ``threshold``: a hexagon with this many points or fewer is not drawn as a cell.
* ``title`` (default ``'Corner plot'``), ``width`` (fraction of the page frame) and ``height``
  (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar: one long table with these columns.

* ``panel``: ``'hist:<col>'`` for the diagonal panel of a column, ``'pair:<colx>:<coly>'`` for the
  lower-triangle panel with ``colx`` on the x axis and ``coly`` on the y axis. The ``hist`` panels
  come first, in the order of ``columns``; that order is the order of the grid.
* ``kind``: ``'bar'`` (a histogram bar), ``'hex'`` or ``'point'`` (as in ``core.density_scatter``),
  or ``'empty'`` (one row that marks a panel with nothing finite to draw).
* ``left``, ``right``, ``count``: the bar's edges and count (``'bar'`` rows; NaN otherwise).
* ``x``, ``y``, ``n``, ``dx``, ``dy``: the hexagon centre or point, the points in it and the
  cell's pitch (``'hex'`` and ``'point'`` rows; NaN otherwise).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from pydantic import Field

from scireport.errors import Issue, PreprocessError
from scireport.preprocess.context import Context
from scireport.preprocess.core._scatter import typed
from scireport.preprocess.plotting import (
  draw_hex_bins,
  empty_axes,
  hex_bins,
  numbers,
  require_columns,
  values_of,
)
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

MAX_COLUMNS = 8
_NAN = float('nan')
_FIELDS = ('x', 'y', 'n', 'dx', 'dy', 'left', 'right', 'count')


def compute_corner(
  table: pa.Table,
  columns: list[str],
  *,
  bins: int = 20,
  gridsize: int = 12,
  threshold: int = 3,
) -> pa.Table:
  """Tally the diagonal histograms and bin each pair of a corner plot.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  columns : list of str
      Numeric columns, in grid order; names must be distinct.
  bins : int, default=20
      Bins of each histogram.
  gridsize : int, default=12
      Hexagons across the x range of each pair.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      The long table described in the module docstring.

  Raises
  ------
  PreprocessError
      With ``E603`` when a column is missing or not numeric, and ``E602`` when a name repeats.
  """
  require_columns(table, *columns)
  if len(set(columns)) != len(columns):
    raise PreprocessError(
      [Issue('E602', 'core.corner: columns must be distinct', found=repr(columns))]
    )
  data = {name: numbers(table, name) for name in columns}
  panels: list[str] = []
  kinds: list[str] = []
  fields: dict[str, list[float]] = {name: [] for name in _FIELDS}

  def add(panel: str, kind: str, **values: Any) -> None:
    """Append rows of one panel; fields not given are NaN."""
    size = len(next(iter(values.values()))) if values else 1
    panels.extend([panel] * size)
    kinds.extend([kind] * size)
    for name in _FIELDS:
      fields[name].extend(
        np.asarray(values[name], dtype=float).tolist() if name in values else [_NAN] * size
      )

  for name in columns:
    values = data[name][np.isfinite(data[name])]
    if values.size == 0:
      add(f'hist:{name}', 'empty')
      continue
    counts, edges = np.histogram(values, bins=bins)
    add(f'hist:{name}', 'bar', left=edges[:-1], right=edges[1:], count=counts)
  for row, y_name in enumerate(columns):
    for col in range(row):
      x_name = columns[col]
      cells = hex_bins(data[x_name], data[y_name], gridsize, threshold)
      panel = f'pair:{x_name}:{y_name}'
      size = len(cells['kind'])
      if size == 0:
        add(panel, 'empty')
        continue
      panels.extend([panel] * size)
      kinds.extend(str(item) for item in cells['kind'])
      for name in _FIELDS:
        fields[name].extend(
          np.asarray(cells[name], dtype=float).tolist() if name in cells else [_NAN] * size
        )
  return typed({'panel': panels, 'kind': kinds, **fields})


def render_corner(
  ctx: Context,
  data: pa.Table,
  *,
  title: str = 'Corner plot',
  width: float = 1.0,
  height: float = 6.0,
) -> Figure:
  """Draw the grid of :func:`compute_corner` from its table.

  The columns, and so the grid size, are read from the ``hist:`` panels of the table.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_corner` made (or read back from a bundle's sidecar file).
  title : str, default='Corner plot'
      Title above the grid; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=6.0
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    panel_names = [str(item) for item in data.column('panel').to_pylist()]
    names = [
      panel[len('hist:') :] for panel in dict.fromkeys(panel_names) if panel.startswith('hist:')
    ]
    kind_names = np.asarray(data.column('kind').to_pylist(), dtype=object)
    if len(names) < 2 or not (kind_names != 'empty').any():
      figure, ax = ctx.figure(width, height)
      empty_axes(ax, 'No data')
      return figure
    size = len(names)
    figure, axes = ctx.figure(width, height, size, size)
    panel_array = np.asarray(panel_names, dtype=object)
    for row, row_name in enumerate(names):
      for col, col_name in enumerate(names):
        ax = axes[row][col]
        if col > row:
          ax.set_axis_off()
          continue
        key = f'hist:{row_name}' if row == col else f'pair:{col_name}:{row_name}'
        mine = panel_array == key
        sub = data.filter(pa.array(mine))
        if row == col:
          _draw_bars(ax, ctx, sub)
        else:
          _draw_pair(ax, ctx, sub)
        ax.set_xticks([])
        ax.set_yticks([])
        if col == 0:
          ax.set_ylabel(row_name, fontsize=8)
        if row == size - 1:
          ax.set_xlabel(col_name, fontsize=8)
    if title:
      figure.suptitle(title)
  return figure


@preprocessor(
  'core.corner',
  version=1,
  inputs={'table': Port('table', description='One row per object, several numeric columns')},
  outputs={'figure': Port('figure', description='The corner plot')},
  render=render_corner,
)
def corner(
  ctx: Context,
  *,
  table: pa.Table,
  columns: Annotated[list[str], Field(min_length=2, max_length=MAX_COLUMNS)],
  bins: int = 20,
  gridsize: int = 12,
  threshold: int = 3,
  title: str = 'Corner plot',
  width: float = 1.0,
  height: float = 6.0,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Corner plot of two to eight numeric columns.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object.
  columns : list of str
      Two to eight distinct numeric columns, in grid order.
  bins : int, default=20
      Bins of each diagonal histogram.
  gridsize : int, default=12
      Hexagons across the x range of each pair.
  threshold : int, default=3
      A hexagon with this many points or fewer is drawn as individual points.
  title : str, default='Corner plot'
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=6.0
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the column names when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_corner(table, columns, bins=bins, gridsize=gridsize, threshold=threshold)
  figure = render_corner(ctx, data, title=title, width=width, height=height)
  text = alt or (
    f'Corner plot of {len(columns)} columns ({", ".join(columns)}): a histogram of each on the '
    'diagonal and the density of each pair below it.'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _draw_bars(ax: Any, ctx: Context, sub: pa.Table) -> None:
  """Draw the histogram bars of one diagonal panel, or grey the panel when it has none."""
  bars = sub.filter(pc.equal(sub.column('kind'), 'bar'))
  if bars.num_rows == 0:
    _grey(ax, ctx)
    return
  left, right = values_of(bars, 'left'), values_of(bars, 'right')
  ax.bar(
    left,
    values_of(bars, 'count'),
    width=right - left,
    align='edge',
    color=ctx.look.series(0),
    linewidth=0,
  )


def _draw_pair(ax: Any, ctx: Context, sub: pa.Table) -> None:
  """Draw the hexagons and points of one lower-triangle panel, or grey it when it has none."""
  cells = sub.filter(pc.not_equal(sub.column('kind'), 'empty'))
  if cells.num_rows == 0:
    _grey(ax, ctx)
    return
  draw_hex_bins(ax, cells, ctx.look, colorbar=False)


def _grey(ax: Any, ctx: Context) -> None:
  """Mark a panel with nothing to draw by a light neutral fill."""
  ax.set_facecolor(ctx.look.color('neutral'))
  ax.patch.set_alpha(0.15)
