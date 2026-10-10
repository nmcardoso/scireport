"""Helpers the drawing functions of the catalogue share.

Every figure pre-processor is split in two so that a figure can always be rebuilt from the data
stored beside it: a *compute* function turns the input table into a small tidy table (counts per
bin, points per hexagon, one row per bar), and a *draw* function turns that table into a figure.
These helpers hold what several of them need: checking columns, reading a column as numbers,
the placeholder for an empty axes, thousands separators on count axes, and the hexagon binning
behind the density scatter (numpy only, so the base install needs no scipy).
"""

from __future__ import annotations

import difflib
from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from scireport.errors import Issue, PreprocessError

if TYPE_CHECKING:
  from matplotlib.axes import Axes

  from scireport.preprocess.look import Look

SQRT3 = float(np.sqrt(3.0))


def require_columns(table: pa.Table, *names: str | None) -> None:
  """Raise ``E603`` unless the table has every named column.

  Parameters
  ----------
  table : pyarrow.Table
      The input table.
  *names : str or None
      Column names a parameter refers to; None entries (an unset optional parameter) are skipped.

  Raises
  ------
  PreprocessError
      With one ``E603`` issue per missing column, each with a "did you mean" hint.
  """
  have = list(table.column_names)
  issues = []
  for name in names:
    if name is None or name in have:
      continue
    close = difflib.get_close_matches(name, have, n=1)
    issues.append(
      Issue(
        'E603',
        f'the table has no column {name!r}',
        expected=f'one of {have}',
        found=name,
        hint=f'Did you mean {close[0]!r}?' if close else None,
      )
    )
  if issues:
    raise PreprocessError(issues)


def numbers(table: pa.Table, column: str) -> np.ndarray:
  """Return a column as float64, with nulls as NaN.

  Parameters
  ----------
  table : pyarrow.Table
      The input table.
  column : str
      A numeric column.

  Returns
  -------
  numpy.ndarray
      One float per row.

  Raises
  ------
  PreprocessError
      With ``E603`` when the column is missing or is not numeric.
  """
  require_columns(table, column)
  data = table.column(column)
  if not (
    pa.types.is_integer(data.type) or pa.types.is_floating(data.type) or pa.types.is_null(data.type)
  ):
    raise PreprocessError(
      [
        Issue(
          'E603',
          f'column {column!r} is {data.type}, not a number',
          expected='an integer or floating-point column',
          found=str(data.type),
        )
      ]
    )
  return np.asarray(pc.cast(data, pa.float64()).fill_null(float('nan')).to_numpy(), dtype=float)


def labels(table: pa.Table, column: str) -> list[str]:
  """Return a column as strings (nulls become the empty string).

  Parameters
  ----------
  table : pyarrow.Table
      The input table.
  column : str
      Any column.

  Returns
  -------
  list of str
      One string per row.
  """
  require_columns(table, column)
  return ['' if item is None else str(item) for item in table.column(column).to_pylist()]


def frame(**columns: Sequence[Any] | np.ndarray) -> pa.Table:
  """Build the sidecar table of a figure from named columns.

  Parameters
  ----------
  **columns : sequence or numpy.ndarray
      Column name to values, all of one length.

  Returns
  -------
  pyarrow.Table
      The table, without schema metadata.
  """
  return pa.table({name: _as_list(values) for name, values in columns.items()})


def values_of(table: pa.Table, name: str) -> np.ndarray:
  """Return one column of a sidecar table as a numpy array (floats stay floats).

  Parameters
  ----------
  table : pyarrow.Table
      A table made by :func:`frame`.
  name : str
      Column name.

  Returns
  -------
  numpy.ndarray
      The values; nulls in a numeric column are NaN.
  """
  data = table.column(name)
  if pa.types.is_floating(data.type) or pa.types.is_integer(data.type):
    return np.asarray(data.cast(pa.float64()).fill_null(float('nan')).to_numpy(), dtype=float)
  return np.asarray(data.to_pylist(), dtype=object)


def empty_axes(ax: Axes, message: str = 'No data') -> Axes:
  """Write a placeholder on an axes instead of leaving it blank.

  Parameters
  ----------
  ax : matplotlib.axes.Axes
      The axes.
  message : str, default='No data'
      The text, centred.

  Returns
  -------
  matplotlib.axes.Axes
      ``ax``.
  """
  ax.text(0.5, 0.5, message, ha='center', va='center', transform=ax.transAxes)
  ax.set_xticks([])
  ax.set_yticks([])
  return ax


def thin_count_axis(ax: Axes) -> None:
  """Keep a count axis readable: few ticks and thousands separators.

  Parameters
  ----------
  ax : matplotlib.axes.Axes
      The axes whose x axis holds counts.
  """
  from matplotlib.ticker import FuncFormatter, MaxNLocator

  ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
  ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{int(value):,}'))


def hex_bins(
  x: np.ndarray, y: np.ndarray, gridsize: int, threshold: int
) -> dict[str, np.ndarray | list[Any]]:
  """Split a scatter into dense hexagons and the sparse points that stay individual.

  A hexagon that holds more than ``threshold`` points is drawn as one cell; the points of a
  hexagon with ``threshold`` or fewer are kept one by one, so a rare point is never hidden under
  a crowd. The lattice is matplotlib's: ``gridsize`` hexagons across the x range and two
  interleaved rectangular lattices, the nearest centre winning.

  Parameters
  ----------
  x, y : numpy.ndarray
      Aligned 1D arrays; pairs that are not both finite are dropped.
  gridsize : int
      Number of hexagons across the x range.
  threshold : int
      A hexagon with this many points or fewer is not drawn as a cell.

  Returns
  -------
  dict
      Columns of a tidy table: ``kind`` (``'hex'`` or ``'point'``), ``x`` and ``y`` (hexagon
      centre or point), ``n`` (points in the hexagon, 1 for a point) and ``dx`` and ``dy`` (the
      cell's horizontal and vertical pitch, NaN for a point). Empty when there is nothing finite.
  """
  x = np.asarray(x, dtype=float)
  y = np.asarray(y, dtype=float)
  finite = np.isfinite(x) & np.isfinite(y)
  x, y = x[finite], y[finite]
  if x.size == 0:
    return {
      'kind': [],
      'x': np.empty(0),
      'y': np.empty(0),
      'n': np.empty(0),
      'dx': np.empty(0),
      'dy': np.empty(0),
    }
  x_min, x_max = float(x.min()), float(x.max())
  y_min, y_max = float(y.min()), float(y.max())
  if x_max == x_min:
    x_min, x_max = x_min - 0.5, x_max + 0.5
  if y_max == y_min:
    y_min, y_max = y_min - 0.5, y_max + 0.5
  columns = max(int(gridsize), 1)
  rows = max(int(columns / SQRT3), 1)
  step_x = (x_max - x_min) / columns
  step_y = (y_max - y_min) / rows
  u = (x - x_min) / step_x
  v = (y - y_min) / step_y
  i1, j1 = np.round(u).astype(np.int64), np.round(v).astype(np.int64)
  i2, j2 = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
  first = (u - i1) ** 2 + 3.0 * (v - j1) ** 2 < (u - i2 - 0.5) ** 2 + 3.0 * (v - j2 - 0.5) ** 2
  lattice = np.where(first, 0, 1).astype(np.int64)
  col = np.where(first, i1, i2)
  row = np.where(first, j1, j2)
  cells = np.stack([lattice, col, row], axis=1)
  unique, inverse, counts = np.unique(cells, axis=0, return_inverse=True, return_counts=True)
  inverse = np.asarray(inverse).reshape(-1)
  dense = counts > threshold
  offset = np.where(unique[:, 0] == 0, 0.0, 0.5)
  centre_x = x_min + (unique[:, 1] + offset) * step_x
  centre_y = y_min + (unique[:, 2] + offset) * step_y
  sparse_point = ~dense[inverse]
  kinds = ['hex'] * int(dense.sum()) + ['point'] * int(sparse_point.sum())
  return {
    'kind': kinds,
    'x': np.concatenate([centre_x[dense], x[sparse_point]]),
    'y': np.concatenate([centre_y[dense], y[sparse_point]]),
    'n': np.concatenate([counts[dense].astype(float), np.ones(int(sparse_point.sum()))]),
    'dx': np.concatenate(
      [np.full(int(dense.sum()), step_x), np.full(int(sparse_point.sum()), np.nan)]
    ),
    'dy': np.concatenate(
      [np.full(int(dense.sum()), step_y), np.full(int(sparse_point.sum()), np.nan)]
    ),
  }


def draw_hex_bins(
  ax: Axes, data: pa.Table, look: Look, *, colorbar: bool = True, label: str = 'Count'
) -> None:
  """Draw the table made by :func:`hex_bins`: hexagon cells coloured by count, sparse points.

  Parameters
  ----------
  ax : matplotlib.axes.Axes
      The axes to draw on.
  data : pyarrow.Table
      Columns ``kind``, ``x``, ``y``, ``n``, ``dx`` and ``dy``.
  look : Look
      Colour map and the annotation colour for the sparse points.
  colorbar : bool, default=True
      Add a colour bar for the cells; off for a panel too small to hold one.
  label : str, default='Count'
      Colour bar label.
  """
  from matplotlib.collections import PolyCollection

  kinds = np.asarray(data.column('kind').to_pylist(), dtype=object)
  x, y, n = values_of(data, 'x'), values_of(data, 'y'), values_of(data, 'n')
  dx, dy = values_of(data, 'dx'), values_of(data, 'dy')
  hexes = kinds == 'hex'
  if hexes.any():
    pitch_x, pitch_y = dx[hexes][0], dy[hexes][0]
    shape = np.array(
      [[0.5, -0.5], [0.5, 0.5], [0.0, 1.0], [-0.5, 0.5], [-0.5, -0.5], [0.0, -1.0]]
    ) * np.array([pitch_x, pitch_y / 3.0])
    polygons = [shape + np.array([cx, cy]) for cx, cy in zip(x[hexes], y[hexes], strict=True)]
    cells = PolyCollection(
      polygons, array=n[hexes], cmap=look.sequential, edgecolors='face', linewidths=0.2
    )
    ax.add_collection(cells)
    ax.autoscale_view()
    if colorbar:
      ax.figure.colorbar(cells, ax=ax, label=label)
  points = ~hexes
  if points.any():
    ax.scatter(x[points], y[points], s=4, alpha=0.4, color=look.color('annotation'), linewidths=0)
  lo_x = float(np.nanmin(x - np.where(hexes, np.nan_to_num(dx) / 2.0, 0.0))) if x.size else 0.0
  hi_x = float(np.nanmax(x + np.where(hexes, np.nan_to_num(dx) / 2.0, 0.0))) if x.size else 1.0
  lo_y = (
    float(np.nanmin(y - np.where(hexes, np.nan_to_num(dy) * 2.0 / 3.0, 0.0))) if y.size else 0.0
  )
  hi_y = (
    float(np.nanmax(y + np.where(hexes, np.nan_to_num(dy) * 2.0 / 3.0, 0.0))) if y.size else 1.0
  )
  if hi_x <= lo_x:
    lo_x, hi_x = lo_x - 0.5, hi_x + 0.5
  if hi_y <= lo_y:
    lo_y, hi_y = lo_y - 0.5, hi_y + 0.5
  ax.set_xlim(lo_x, hi_x)
  ax.set_ylim(lo_y, hi_y)


def table_columns(table: pa.Table) -> dict[str, list[Any]]:
  """Return a table as a mapping of column name to Python values.

  Parameters
  ----------
  table : pyarrow.Table
      Any table.

  Returns
  -------
  dict
      Column name to list.
  """
  return {name: table.column(name).to_pylist() for name in table.column_names}


def _as_list(values: Iterable[Any] | np.ndarray) -> Any:
  """Hand numpy arrays to pyarrow as they are and everything else as a list."""
  if isinstance(values, np.ndarray):
    return values
  return list(values) if not isinstance(values, Mapping) else values
