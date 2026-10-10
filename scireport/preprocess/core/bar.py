"""``core.bar``: one labelled horizontal bar per row of a table of counts.

Ported from the MOSAICS panel ``plot_category_counts``: the generic counting panel (rows per
survey, sources per field, columns dropped per source), where every panel has the same shape, a
label and a number. The bars are horizontal because the labels are long identifiers that would
need rotated ticks. A zero is drawn in the failure colour and still labelled, because a category
that stopped contributing is what the panel exists to make visible.

Parameters of the step (see :func:`bar`):

* ``label_column``: the label of each bar. ``value_column``: its count (null counts as zero).
* ``highlight``: labels to draw in the failure colour whatever their value.
* ``log``: symmetric-logarithmic value axis, for counts that span several decades.
* ``sort``: ``'none'`` keeps the table order, ``'ascending'`` and ``'descending'`` sort by value.
* ``x_label``, ``title``: text. ``width`` (fraction of the page frame) and ``height`` (inches;
  computed from the number of bars when omitted).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``label``, ``value`` (the count, nulls turned into zero) and ``flagged``
(true when the bar is drawn in the failure colour: highlighted, or not above zero), one row per
bar in drawing order, top to bottom.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.plotting import (
  empty_axes,
  labels,
  numbers,
  require_columns,
  thin_count_axis,
  values_of,
)
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

SortOrder = Literal['none', 'ascending', 'descending']
_INCHES_PER_BAR = 0.26
_MARGIN_INCHES = 0.9


def compute_bar(
  table: pa.Table,
  label_column: str,
  value_column: str,
  *,
  highlight: list[str] | None = None,
  sort: SortOrder = 'none',
) -> pa.Table:
  """Turn a table of labels and counts into one row per bar.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  label_column : str
      Column with the label of each bar.
  value_column : str
      Numeric column with the count of each bar; null or NaN counts as zero.
  highlight : list of str or None, default=None
      Labels flagged whatever their value.
  sort : {'none', 'ascending', 'descending'}, default='none'
      Order of the bars; ties keep the table order.

  Returns
  -------
  pyarrow.Table
      Columns ``label`` (string), ``value`` (float64) and ``flagged`` (bool).
  """
  require_columns(table, label_column, value_column)
  names = labels(table, label_column)
  values = np.nan_to_num(numbers(table, value_column), nan=0.0)
  if sort != 'none' and values.size:
    keys = values if sort == 'ascending' else -values
    order = np.argsort(keys, kind='stable')
    names = [names[i] for i in order]
    values = values[order]
  marked = set(highlight or [])
  flagged = [name in marked or value <= 0 for name, value in zip(names, values, strict=True)]
  return pa.table(
    {
      'label': pa.array(names, pa.string()),
      'value': pa.array(values, pa.float64()),
      'flagged': pa.array(flagged, pa.bool_()),
    }
  )


def default_height(n_bars: int) -> float:
  """Return a figure height in inches that gives each bar room.

  Parameters
  ----------
  n_bars : int
      Number of bars.

  Returns
  -------
  float
      Height in inches, at least 1.6.
  """
  return max(1.6, _INCHES_PER_BAR * n_bars + _MARGIN_INCHES)


def render_bar(
  ctx: Context,
  data: pa.Table,
  *,
  log: bool = False,
  x_label: str = 'Rows',
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw the bars of :func:`compute_bar` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_bar` made (or read back from a bundle's sidecar file).
  log : bool, default=False
      Symmetric-logarithmic value axis.
  x_label : str, default='Rows'
      Label of the value axis.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; computed from the number of bars when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, default_height(data.num_rows) if height is None else height)
    figure.set_layout_engine('constrained')
    if data.num_rows == 0:
      empty_axes(ax, 'Nothing recorded')
      return figure
    names = [str(name) for name in data.column('label').to_pylist()]
    values = values_of(data, 'value')
    flagged = np.asarray(data.column('flagged').to_pylist(), dtype=bool)
    failed = ctx.look.color('failed')
    colors = [failed if is_flagged else ctx.look.series(0) for is_flagged in flagged]
    positions = np.arange(len(names))
    ax.barh(positions, values, color=colors)
    ax.set_yticks(positions)
    ax.set_yticklabels(names, fontsize=7, family='monospace')
    ax.invert_yaxis()
    ax.set_xlabel(x_label)
    if title:
      ax.set_title(title)
    span = float(values.max()) if np.any(values) else 1.0
    for position, (value, is_flagged) in enumerate(zip(values, flagged, strict=True)):
      # An offset in points, so the text clears the bar end on a linear and a symlog axis alike.
      ax.annotate(
        f'{value:,.0f}',
        (value, position),
        xytext=(3, 0),
        textcoords='offset points',
        va='center',
        fontsize=7,
        color=failed if is_flagged else ctx.look.color('annotation'),
      )
    if log:
      ax.set_xscale('symlog')
      ax.set_xlim(0, span * 4)
    else:
      ax.set_xlim(0, span * 1.18)
      thin_count_axis(ax)
  return figure


@preprocessor(
  'core.bar',
  version=1,
  inputs={'table': Port('table', description='One row per bar: a label and a count')},
  outputs={'figure': Port('figure', description='The horizontal bar chart')},
  render=render_bar,
)
def bar(
  ctx: Context,
  *,
  table: pa.Table,
  label_column: str,
  value_column: str,
  highlight: list[str] | None = None,
  log: bool = False,
  x_label: str = 'Rows',
  sort: SortOrder = 'none',
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Horizontal bars of a table of labelled counts.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per bar.
  label_column : str
      Column with the label of each bar.
  value_column : str
      Numeric column with the count of each bar; null counts as zero.
  highlight : list of str or None, default=None
      Labels to draw in the failure colour whatever their value.
  log : bool, default=False
      Symmetric-logarithmic value axis.
  x_label : str, default='Rows'
      Label of the value axis.
  sort : {'none', 'ascending', 'descending'}, default='none'
      Order of the bars; 'none' keeps the table order.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; computed from the number of bars when None.
  alt : str or None, default=None
      Alternative text; built from the column names and the counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_bar(table, label_column, value_column, highlight=highlight, sort=sort)
  figure = render_bar(ctx, data, log=log, x_label=x_label, title=title, width=width, height=height)
  if alt is None:
    flagged = int(np.sum(np.asarray(data.column('flagged').to_pylist(), dtype=bool)))
    total = float(np.sum(values_of(data, 'value'))) if data.num_rows else 0.0
    alt = (
      f'Horizontal bars of {value_column} for each {label_column}: {data.num_rows} bars, '
      f'{total:,.0f} in all, {flagged} drawn as flagged.'
    )
  return {'figure': ctx.save_figure(figure, data=data, alt=alt, caption=caption, width=width)}
