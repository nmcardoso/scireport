"""``core.histogram``: a histogram of a column of samples, or of counts tallied elsewhere.

Ported from the MOSAICS panels ``plot_pixel_histogram``, ``plot_size_histogram`` and the tallied
branch of ``plot_separation_histogram``. A run over hundreds of millions of rows never carries
the sample into a report, only the histogram it already computed, so the pre-processor takes
either form and draws the same panel.

Parameters of the step (see :func:`histogram`):

* ``column``: the samples, or (with ``counts_column``) the bin centres or labels.
* ``counts_column``: the column of counts when the table is already a tally.
* ``bins``: an integer, or a numpy rule (``'auto'``, ``'fd'``, ``'sturges'``, ``'sqrt'``).
* ``categorical``: draw one bar per distinct label instead of a continuous axis.
* ``log``: logarithmic count axis. ``x_label``, ``y_label``, ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``left``, ``right`` (bin edges, NaN for a categorical bar), ``count`` and
``label`` (the bar's label for a categorical bar, else null).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import numpy as np
import pyarrow as pa

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

BinRule = Literal['auto', 'fd', 'doane', 'scott', 'stone', 'rice', 'sturges', 'sqrt']
_MAX_BARS = 40


def compute_histogram(
  table: pa.Table,
  column_name: str,
  *,
  bins: int | BinRule = 'auto',
  counts_column: str | None = None,
  categorical: bool = False,
) -> pa.Table:
  """Tally a column into bars.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  column_name : str
      Samples, or bin centres / labels when ``counts_column`` is given.
  bins : int or str, default='auto'
      Number of bins or a numpy bin rule; used for samples only.
  counts_column : str or None, default=None
      Column of counts; the table is then taken to be a tally.
  categorical : bool, default=False
      One bar per label (sorted numerically when the labels are numbers).

  Returns
  -------
  pyarrow.Table
      Columns ``left``, ``right``, ``count`` and ``label``.
  """
  require_columns(table, column_name, counts_column)
  if counts_column is None and not categorical:
    values = numbers(table, column_name)
    values = values[np.isfinite(values)]
    if values.size == 0:
      return _bars([], [], [], [])
    counts, edges = np.histogram(values, bins=bins)
    return _bars(edges[:-1], edges[1:], counts, [None] * counts.size)
  weights = numbers(table, counts_column) if counts_column is not None else np.ones(table.num_rows)
  weights = np.nan_to_num(weights, nan=0.0)
  names = labels(table, column_name)
  if categorical or not _is_numeric(table, column_name):
    totals: dict[str, float] = {}
    for name, weight in zip(names, weights, strict=True):
      totals[name] = totals.get(name, 0.0) + float(weight)
    ordered = sorted(totals, key=_sort_key)
    return _bars(
      [np.nan] * len(ordered),
      [np.nan] * len(ordered),
      [totals[name] for name in ordered],
      ordered,
    )
  centres = numbers(table, column_name)
  keep = np.isfinite(centres)
  centres, weights = centres[keep], weights[keep]
  order = np.argsort(centres, kind='stable')
  centres, weights = centres[order], weights[order]
  if centres.size == 0:
    return _bars([], [], [], [])
  width = float(np.min(np.diff(centres))) if centres.size > 1 else float(centres[0] or 1.0)
  width = width if width > 0 else 1.0
  return _bars(centres - width / 2, centres + width / 2, weights, [None] * centres.size)


def render_histogram(
  ctx: Context,
  data: pa.Table,
  *,
  log: bool = False,
  x_label: str = '',
  y_label: str = 'Count',
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
) -> Figure:
  """Draw the bars of :func:`compute_histogram` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_histogram` made (or read back from a bundle's sidecar file).
  log : bool, default=False
      Logarithmic count axis.
  x_label, y_label, title : str
      Axis labels and title; empty strings draw nothing.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.2
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height)
    counts = values_of(data, 'count')
    if counts.size == 0 or not np.nansum(counts) > 0:
      empty_axes(ax, 'No data')
      return figure
    left, right = values_of(data, 'left'), values_of(data, 'right')
    names = data.column('label').to_pylist()
    color = ctx.look.series(0)
    if any(name is not None for name in names):
      if len(names) > _MAX_BARS:
        ax.tick_params(axis='x', labelrotation=90)
      positions = np.arange(len(names))
      ax.bar(positions, counts, color=color)
      ax.set_xticks(positions)
      ax.set_xticklabels([str(name) for name in names])
    else:
      ax.bar(left, counts, width=right - left, align='edge', color=color, linewidth=0)
    if log:
      ax.set_yscale('log')
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'core.histogram',
  version=1,
  inputs={'table': Port('table', description='Samples, or a tally of counts per bin')},
  outputs={'figure': Port('figure', description='The histogram')},
  render=render_histogram,
)
def histogram(
  ctx: Context,
  *,
  table: pa.Table,
  column: str,
  bins: int | BinRule = 'auto',
  counts_column: str | None = None,
  categorical: bool = False,
  log: bool = False,
  x_label: str | None = None,
  y_label: str = 'Count',
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Histogram of a column of samples, or of counts tallied elsewhere.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      Samples, or one row per bin when ``counts_column`` is given.
  column : str
      Column of samples, or of bin centres (numbers) or labels (anything else) for a tally.
  bins : int or str, default='auto'
      Number of bins or a numpy bin rule (``'auto'``, ``'fd'``, ``'sturges'``, ...); ignored for
      a tally.
  counts_column : str or None, default=None
      Column with the count of each row; makes the table a tally.
  categorical : bool, default=False
      One bar per distinct label rather than a continuous axis.
  log : bool, default=False
      Logarithmic count axis.
  x_label : str or None, default=None
      Label of the x axis; the column name when None.
  y_label : str, default='Count'
      Label of the y axis.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.2
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the column name and the number of bars when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_histogram(
    table, column, bins=bins, counts_column=counts_column, categorical=categorical
  )
  label = column if x_label is None else x_label
  figure = render_histogram(
    ctx, data, log=log, x_label=label, y_label=y_label, title=title, width=width, height=height
  )
  total = float(np.nansum(data.column('count').to_numpy())) if data.num_rows else 0.0
  text = alt or f'Histogram of {column}: {data.num_rows} bars, {total:,.0f} rows in all.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _bars(left: Any, right: Any, count: Any, label: list[str | None] | list[Any]) -> pa.Table:
  """Build the tally table with fixed column types, empty or not."""
  return pa.table(
    {
      'left': pa.array(np.asarray(left, dtype=float), pa.float64()),
      'right': pa.array(np.asarray(right, dtype=float), pa.float64()),
      'count': pa.array(np.asarray(count, dtype=float), pa.float64()),
      'label': pa.array(list(label), pa.string()),
    }
  )


def _is_numeric(table: pa.Table, name: str) -> bool:
  """Whether a column holds numbers."""
  kind = table.column(name).type
  return bool(pa.types.is_integer(kind) or pa.types.is_floating(kind))


def _sort_key(label: str) -> tuple[int, float, str]:
  """Sort numeric labels by value, then the others alphabetically."""
  try:
    return (0, float(label), label)
  except ValueError:
    return (1, 0.0, label)
