"""``core.heatmap``: a matrix of values drawn as coloured cells, from a long table.

New in scireport (MOSAICS had no such panel): the dataset report needs a flags matrix (objects
by flag), a co-occurrence matrix and similar grids. The input is a *long* table, one row per
cell, so that a sparse matrix stays small and a cell that has no row is drawn blank.

Parameters of the step (see :func:`heatmap`):

* ``row_column``, ``column_column``, ``value_column``: the columns that name the row, name the
  column and hold the cell's number. A cell may appear once; a null value is drawn blank too.
* ``row_order``, ``column_order``: the labels in drawing order, which may list labels the data
  lacks (drawn as blank rows or columns) and may leave some out (their cells are not drawn).
  By default the labels come in order of first appearance.
* ``cmap``: ``'sequential'`` or ``'diverging'`` (the layout's colour maps). ``vmin``, ``vmax``:
  the colour limits (the data's range by default). ``symmetric``: limits ``-m`` and ``m`` with
  ``m`` the largest absolute value, so a diverging scale is centred on 0. ``log``: logarithmic
  colour scale (cells that are not positive are drawn blank).
* ``annotate``: write the value in each cell (``'auto'`` does so up to 400 cells), in
  ``value_format`` (a Python format specification), with a text colour that contrasts with
  the cell.
* ``colorbar_label``, ``row_label``, ``column_label``, ``title``: text. ``square``: square cells.
* ``width`` (fraction of the page frame), ``height`` (inches; from the number of rows when
  omitted), ``alt`` and ``caption``.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``row`` and ``column`` (labels), ``value`` (null for a blank cell),
``row_index`` and ``column_index`` (zero-based positions in the drawn order), sorted by row then
column. A label of ``row_order`` or ``column_order`` that has no cell in the data appears once
with a null value, so the sidecar holds every label that is drawn.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np
import pyarrow as pa

from scireport.errors import Issue, PreprocessError
from scireport.preprocess.context import Context
from scireport.preprocess.plotting import (
  empty_axes,
  labels,
  numbers,
  require_columns,
  values_of,
)
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

_AUTO_ANNOTATE_CELLS = 400
_LONG_LABEL = 6
_ROW_HEIGHT = 0.22


def compute_heatmap(
  table: pa.Table,
  row_column: str,
  column_column: str,
  value_column: str,
  *,
  row_order: list[str] | None = None,
  column_order: list[str] | None = None,
) -> pa.Table:
  """Place the cells of a long table on the grid of the drawn order.

  Parameters
  ----------
  table : pyarrow.Table
      One row per cell.
  row_column, column_column : str
      Columns naming the row and the column of each cell (read as text).
  value_column : str
      Numeric column with the cell's value; nulls and NaN are blank cells.
  row_order, column_order : list of str or None, default=None
      Labels in drawing order; first appearance in the table when None. Cells whose label is
      not listed are dropped.

  Returns
  -------
  pyarrow.Table
      Columns ``row``, ``column``, ``value`` (null when blank), ``row_index`` and
      ``column_index``, sorted by row then column; see the module docstring.

  Raises
  ------
  PreprocessError
      With ``E603`` when a cell appears twice or an order lists a label twice.
  """
  require_columns(table, row_column, column_column, value_column)
  row_names = labels(table, row_column)
  column_names = labels(table, column_column)
  values = numbers(table, value_column)
  rows = _axis(row_names, row_order, 'row_order')
  columns = _axis(column_names, column_order, 'column_order')
  row_at = {name: index for index, name in enumerate(rows)}
  column_at = {name: index for index, name in enumerate(columns)}
  cells: dict[tuple[int, int], float] = {}
  for row, column, value in zip(row_names, column_names, values, strict=True):
    if row not in row_at or column not in column_at:
      continue
    slot = (row_at[row], column_at[column])
    if slot in cells:
      raise PreprocessError(
        [
          Issue(
            'E603',
            f'the cell ({row!r}, {column!r}) appears more than once in the table',
            hint='Aggregate the table to one row per cell first.',
          )
        ]
      )
    cells[slot] = float(value)
  seen_rows = {slot[0] for slot in cells}
  seen_columns = {slot[1] for slot in cells}
  for index in range(len(rows)):
    if index not in seen_rows:
      cells[(index, 0)] = float('nan')
  for index in range(len(columns)):
    if index not in seen_columns:
      cells.setdefault((0, index), float('nan'))
  ordered = sorted(cells)
  value_out = [None if np.isnan(cells[slot]) else cells[slot] for slot in ordered]
  return pa.table(
    {
      'row': pa.array([rows[r] for r, _ in ordered], pa.string()),
      'column': pa.array([columns[c] for _, c in ordered], pa.string()),
      'value': pa.array(value_out, pa.float64()),
      'row_index': pa.array([r for r, _ in ordered], pa.int64()),
      'column_index': pa.array([c for _, c in ordered], pa.int64()),
    }
  )


def render_heatmap(
  ctx: Context,
  data: pa.Table,
  *,
  cmap: Literal['sequential', 'diverging'] = 'sequential',
  vmin: float | None = None,
  vmax: float | None = None,
  symmetric: bool = False,
  log: bool = False,
  annotate: bool | Literal['auto'] = 'auto',
  value_format: str = '.2g',
  colorbar_label: str = '',
  row_label: str = '',
  column_label: str = '',
  title: str = '',
  square: bool = False,
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw the grid of :func:`compute_heatmap` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_heatmap` made (or read back from a bundle's sidecar file).
  cmap : {'sequential', 'diverging'}, default='sequential'
      Which colour map of the layout to use.
  vmin, vmax : float or None, default=None
      Colour limits; the range of the drawn values when None.
  symmetric : bool, default=False
      Limits ``-m`` to ``m`` with ``m`` the largest absolute value (or of the given limits).
  log : bool, default=False
      Logarithmic colour scale; cells that are not positive are blank.
  annotate : bool or 'auto', default='auto'
      Write each value in its cell; ``'auto'`` does so for at most 400 cells.
  value_format : str, default='.2g'
      Python format specification of the cell text.
  colorbar_label, row_label, column_label, title : str
      Texts; empty strings draw nothing.
  square : bool, default=False
      Square cells.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; from the number of rows when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  import matplotlib as mpl

  n_rows, n_columns = _shape(data)
  grid_height = height if height is not None else max(2.0, _ROW_HEIGHT * n_rows + 1.0)
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, grid_height)
    # Labels on top and a colour bar: let matplotlib make room for them.
    figure.set_layout_engine('constrained')
    grid = _matrix(data, n_rows, n_columns)
    if log:
      grid = np.where(grid > 0, grid, np.nan)
    if not np.isfinite(grid).any():
      empty_axes(ax, 'No data')
      return figure
    norm = _norm(grid, vmin, vmax, symmetric, log)
    colormap = mpl.colormaps[ctx.look.diverging if cmap == 'diverging' else ctx.look.sequential]
    colormap = colormap.with_extremes(bad=(0.0, 0.0, 0.0, 0.0))
    masked = np.ma.masked_invalid(grid)
    image = ax.imshow(
      masked,
      cmap=colormap,
      norm=norm,
      aspect='auto',
      interpolation='nearest',
    )
    if square:
      ax.set_box_aspect(n_rows / n_columns)
    row_names = _names(data, 'row', 'row_index', n_rows)
    column_names = _names(data, 'column', 'column_index', n_columns)
    font = float(mpl.rcParams['font.size'])
    row_font = max(4.0, min(font, 0.85 * 0.8 * grid_height * 72.0 / n_rows))
    ax.set_yticks(np.arange(n_rows))
    ax.set_yticklabels(row_names, fontsize=row_font)
    rotate = max((len(name) for name in column_names), default=0) > _LONG_LABEL
    ax.set_xticks(np.arange(n_columns))
    ax.set_xticklabels(
      column_names,
      rotation=90 if rotate else 0,
      ha='center',
      fontsize=min(font, row_font + 1.0) if n_columns > 12 else font,
    )
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position('top')
    ax.tick_params(axis='both', length=0)
    ax.grid(False)
    for side in ('top', 'right', 'bottom', 'left'):
      ax.spines[side].set_visible(False)
    if row_label:
      ax.set_ylabel(row_label)
    if column_label:
      ax.set_xlabel(column_label)
    if title:
      ax.set_title(title, pad=14.0 if not rotate else 6.0, loc='left')
    bar = figure.colorbar(image, ax=ax, shrink=0.8, pad=0.02, label=colorbar_label)
    bar.outline.set_visible(False)
    if _annotated(annotate, n_rows * n_columns):
      _write_cells(ax, grid, image, value_format, figure.get_size_inches(), font, square)
  return figure


@preprocessor(
  'core.heatmap',
  version=1,
  inputs={'table': Port('table', description='A long table: one row per cell of the matrix')},
  outputs={'figure': Port('figure', description='The heatmap')},
  render=render_heatmap,
)
def heatmap(
  ctx: Context,
  *,
  table: pa.Table,
  row_column: str,
  column_column: str,
  value_column: str,
  row_order: list[str] | None = None,
  column_order: list[str] | None = None,
  cmap: Literal['sequential', 'diverging'] = 'sequential',
  vmin: float | None = None,
  vmax: float | None = None,
  symmetric: bool = False,
  log: bool = False,
  annotate: bool | Literal['auto'] = 'auto',
  value_format: str = '.2g',
  colorbar_label: str = '',
  row_label: str = '',
  column_label: str = '',
  title: str = '',
  square: bool = False,
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Heatmap of a matrix given as a long table (one row per cell).

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per cell.
  row_column, column_column : str
      Columns naming the row and the column of each cell.
  value_column : str
      Numeric column with the cell's value; null cells are drawn blank.
  row_order, column_order : list of str or None, default=None
      Labels in drawing order (first appearance when None); may list labels the data lacks, and
      leaving one out drops its cells.
  cmap : {'sequential', 'diverging'}, default='sequential'
      Which colour map of the layout to use.
  vmin, vmax : float or None, default=None
      Colour limits; the range of the values when None.
  symmetric : bool, default=False
      Colour limits ``-m`` to ``m``, centring a diverging scale on 0.
  log : bool, default=False
      Logarithmic colour scale (cells that are not positive are blank).
  annotate : bool or 'auto', default='auto'
      Write each value in its cell; ``'auto'`` does so for at most 400 cells.
  value_format : str, default='.2g'
      Python format specification of the cell text.
  colorbar_label : str, default=''
      Label of the colour bar.
  row_label, column_label : str, default=''
      Axis labels (rows on the left, columns on top).
  title : str, default=''
      Title; nothing when empty.
  square : bool, default=False
      Square cells.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; from the number of rows when None.
  alt : str or None, default=None
      Alternative text; built from the column names and the grid size when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_heatmap(
    table,
    row_column,
    column_column,
    value_column,
    row_order=row_order,
    column_order=column_order,
  )
  figure = render_heatmap(
    ctx,
    data,
    cmap=cmap,
    vmin=vmin,
    vmax=vmax,
    symmetric=symmetric,
    log=log,
    annotate=annotate,
    value_format=value_format,
    colorbar_label=colorbar_label,
    row_label=row_label,
    column_label=column_label,
    title=title,
    square=square,
    width=width,
    height=height,
  )
  n_rows, n_columns = _shape(data)
  values = values_of(data, 'value')
  filled = int(np.isfinite(values).sum())
  text = alt or (
    f'Heatmap of {value_column} by {row_column} ({n_rows} rows) and {column_column} '
    f'({n_columns} columns): {filled} of {n_rows * n_columns} cells have a value.'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _axis(found: list[str], order: list[str] | None, name: str) -> list[str]:
  """Return the labels of one axis: the given order, else first appearance."""
  if order is None:
    return list(dict.fromkeys(found))
  if len(set(order)) != len(order):
    raise PreprocessError([Issue('E603', f'{name} lists a label more than once', found=str(order))])
  return list(order)


def _shape(data: pa.Table) -> tuple[int, int]:
  """Return the number of rows and columns of the grid a sidecar table describes."""
  if data.num_rows == 0:
    return 0, 0
  rows = values_of(data, 'row_index')
  columns = values_of(data, 'column_index')
  return int(np.max(rows)) + 1, int(np.max(columns)) + 1


def _matrix(data: pa.Table, n_rows: int, n_columns: int) -> np.ndarray:
  """Return the grid of values, NaN where a cell is blank."""
  grid = np.full((n_rows, n_columns), np.nan)
  if data.num_rows:
    rows = values_of(data, 'row_index').astype(int)
    columns = values_of(data, 'column_index').astype(int)
    grid[rows, columns] = values_of(data, 'value')
  return grid


def _names(data: pa.Table, label: str, index: str, count: int) -> list[str]:
  """Return the labels of one axis in drawn order."""
  names = [''] * count
  for name, position in zip(
    data.column(label).to_pylist(), data.column(index).to_pylist(), strict=True
  ):
    names[int(position)] = str(name)
  return names


def _norm(
  grid: np.ndarray, vmin: float | None, vmax: float | None, symmetric: bool, log: bool
) -> object:
  """Build the colour normalisation from the data and the limits asked for."""
  from matplotlib.colors import LogNorm, Normalize

  finite = grid[np.isfinite(grid)]
  low = float(finite.min()) if vmin is None else float(vmin)
  high = float(finite.max()) if vmax is None else float(vmax)
  if symmetric and not log:
    bound = max(abs(low), abs(high))
    low, high = -bound, bound
  if log:
    low = low if low > 0 else float(finite.min())
    return LogNorm(vmin=low, vmax=max(high, low * (1.0 + 1e-9)))
  if high <= low:
    high = low + 1.0
  return Normalize(vmin=low, vmax=high)


def _annotated(annotate: bool | Literal['auto'], cells: int) -> bool:
  """Whether cell text is drawn."""
  return cells <= _AUTO_ANNOTATE_CELLS if annotate == 'auto' else bool(annotate)


def _write_cells(
  ax: object,
  grid: np.ndarray,
  image: object,
  value_format: str,
  size_inches: np.ndarray,
  font: float,
  square: bool,
) -> None:
  """Write each value in its cell, black or white according to the cell colour.

  Parameters
  ----------
  ax : matplotlib.axes.Axes
      The axes holding the image.
  grid : numpy.ndarray
      The values, NaN for a blank cell.
  image : matplotlib.image.AxesImage
      The drawn image, which knows the colour of every value.
  value_format : str
      Python format specification of the text.
  size_inches : numpy.ndarray
      Width and height of the figure, to size the text to the cells.
  font : float
      Largest font size in points.
  square : bool
      Whether the cells are square, so that their width equals their height.
  """
  from matplotlib.axes import Axes
  from matplotlib.image import AxesImage

  assert isinstance(ax, Axes) and isinstance(image, AxesImage)
  n_rows, n_columns = grid.shape
  texts = {}
  for row in range(n_rows):
    for column in range(n_columns):
      value = grid[row, column]
      if np.isfinite(value):
        texts[(row, column)] = _format(float(value), value_format)
  if not texts:
    return
  longest = max(len(text) for text in texts.values())
  cell_height = 0.8 * float(size_inches[1]) * 72.0 / n_rows
  cell_width = 0.7 * float(size_inches[0]) * 72.0 / n_columns
  if square:
    cell_width = min(cell_width, cell_height)
  size = max(3.0, min(font, 0.6 * cell_height, cell_width / (0.62 * longest)))
  for (row, column), text in texts.items():
    red, green, blue, _ = image.cmap(image.norm(grid[row, column]))
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    ax.text(
      column,
      row,
      text,
      ha='center',
      va='center',
      fontsize=size,
      color='#111111' if luminance > 0.5 else '#ffffff',
    )


def _format(value: float, spec: str) -> str:
  """Format one cell value; the shortest text when the specification does not fit."""
  try:
    return format(value, spec)
  except (ValueError, TypeError):
    return str(value)
