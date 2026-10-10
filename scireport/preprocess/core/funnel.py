"""``core.funnel``: how many rows survive each step of a cascade of cuts, and what each cut removed.

Ported from the MOSAICS panels ``plot_constraint_counts`` and ``plot_constraint_drop``. Read top
to bottom: the first bar is the unconstrained count and each one below adds a cut. A bar as long
as the one above removed nothing, which is the pattern worth noticing: a cut that costs a query
nothing is either redundant or not matching what its author meant. The left panel shows the
running count, the right panel the marginal cost, where a cut doing nothing becomes obvious
rather than merely inferable. The bars are horizontal because the labels are long (query
predicates), and a step that did not return (a null count) is drawn as a zero-length bar written
out as ``failed`` rather than hidden.

Parameters of the step (see :func:`funnel`):

* ``label_column``: the name of each step, in the order the cuts are applied.
* ``count_column``: rows surviving the step; null marks a step that failed.
* ``panels``: ``'both'`` (running count on the left, rows removed on the right), ``'counts'``
  or ``'drops'``.
* ``title``: text above the figure. ``width`` (fraction of the page frame) and ``height``
  (inches; computed from the number of steps when omitted).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``label``, ``count`` (null for a failed step) and ``removed`` (the previous
step's count minus this one's; null for the first step, for a failed step and for a step that
follows a failed one), one row per step in table order.
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
  thin_count_axis,
  values_of,
)
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.axes import Axes
  from matplotlib.figure import Figure

Panels = Literal['both', 'counts', 'drops']
_INCHES_PER_STEP = 0.26
_MARGIN_INCHES = 1.0


def compute_funnel(table: pa.Table, label_column: str, count_column: str) -> pa.Table:
  """Turn a table of steps and surviving counts into counts and rows removed per step.

  Parameters
  ----------
  table : pyarrow.Table
      The input, one row per step in the order the cuts are applied.
  label_column : str
      Column with the name of each step.
  count_column : str
      Numeric column with the rows surviving the step; null marks a failed step.

  Returns
  -------
  pyarrow.Table
      Columns ``label`` (string), ``count`` and ``removed`` (float64, null where unknown).
  """
  require_columns(table, label_column, count_column)
  names = labels(table, label_column)
  counts = numbers(table, count_column)
  removed = np.full(counts.shape, np.nan)
  removed[1:] = counts[:-1] - counts[1:]
  return pa.table(
    {
      'label': pa.array(names, pa.string()),
      'count': pa.array(_nullable(counts), pa.float64()),
      'removed': pa.array(_nullable(removed), pa.float64()),
    }
  )


def default_height(n_steps: int) -> float:
  """Return a figure height in inches that gives each step room.

  Parameters
  ----------
  n_steps : int
      Number of steps.

  Returns
  -------
  float
      Height in inches, at least 1.6.
  """
  return max(1.6, _INCHES_PER_STEP * n_steps + _MARGIN_INCHES)


def render_funnel(
  ctx: Context,
  data: pa.Table,
  *,
  panels: Panels = 'both',
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw the panels of :func:`compute_funnel` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_funnel` made (or read back from a bundle's sidecar file).
  panels : {'both', 'counts', 'drops'}, default='both'
      Which panels to draw; two panels sit side by side.
  title : str, default=''
      Title above the figure; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; computed from the number of steps when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  drawn = ['counts', 'drops'] if panels == 'both' else [panels]
  with ctx.mplstyle():
    figure, axes = ctx.figure(
      width, default_height(data.num_rows) if height is None else height, 1, len(drawn)
    )
    figure.set_layout_engine('constrained')
    for panel, ax in zip(drawn, [axes] if len(drawn) == 1 else list(axes), strict=True):
      if panel == 'counts':
        _draw_counts(ctx, ax, data, compact=len(drawn) > 1)
      else:
        _draw_drops(ctx, ax, data, compact=len(drawn) > 1)
    if title:
      figure.suptitle(title)
  return figure


def _draw_counts(ctx: Context, ax: Axes, data: pa.Table, *, compact: bool) -> None:
  """Draw the running count of each step; a failed step is a zero-length bar."""
  if data.num_rows == 0:
    empty_axes(ax, 'No constraints')
    return
  names = [str(name) for name in data.column('label').to_pylist()]
  counts = values_of(data, 'count')
  failed = np.isnan(counts)
  values = np.where(failed, 0.0, counts)
  colors = [ctx.look.color('failed') if bad else ctx.look.series(0) for bad in failed]
  _draw_bars(ax, names, values, colors, 'Rows')
  ax.set_title('Rows surviving each constraint')
  span = float(values.max()) if np.any(values) else 1.0
  for position, (value, bad) in enumerate(zip(values, failed, strict=True)):
    _annotate(
      ax,
      position,
      value,
      'failed' if bad else f'{value:,.0f}',
      ctx.look.color('failed') if bad else ctx.look.color('annotation'),
    )
  _finish_axis(ax, span, compact=compact)


def _draw_drops(ctx: Context, ax: Axes, data: pa.Table, *, compact: bool) -> None:
  """Draw the rows each step removed; steps with no measurable drop are left out."""
  removed = values_of(data, 'removed')
  keep = np.isfinite(removed)
  if not keep.any():
    empty_axes(ax, 'Nothing measurable')
    return
  names = [
    str(name) for name, kept in zip(data.column('label').to_pylist(), keep, strict=True) if kept
  ]
  values = removed[keep]
  _draw_bars(ax, names, values, [ctx.look.series(1)] * len(names), 'Rows removed')
  ax.set_title('Rows removed by each constraint')
  span = float(values.max()) if np.any(values) else 1.0
  for position, value in enumerate(values):
    _annotate(ax, position, value, f'{value:,.0f}', None)
  _finish_axis(ax, span, compact=compact)


def _draw_bars(
  ax: Axes, names: list[str], values: np.ndarray, colors: list[str], label: str
) -> None:
  """Horizontal bars read top to bottom in the order the cuts are applied."""
  positions = np.arange(len(names))
  ax.barh(positions, values, color=colors)
  ax.set_yticks(positions)
  ax.set_yticklabels(names, fontsize=7, family='monospace')
  ax.invert_yaxis()
  ax.set_xlabel(label)


def _annotate(ax: Axes, position: int, value: float, text: str, color: str | None) -> None:
  """Write a number just past the end of a bar (an offset in points)."""
  extra: dict[str, Any] = {} if color is None else {'color': color}
  ax.annotate(
    text,
    (value, position),
    xytext=(3, 0),
    textcoords='offset points',
    va='center',
    fontsize=7,
    **extra,
  )


def _finish_axis(ax: Axes, span: float, *, compact: bool) -> None:
  """Leave room for the numbers past the longest bar and thin the count axis.

  A panel sharing the figure with another is half as wide, so it gets fewer ticks and more room.
  """
  ax.set_xlim(0, span * (1.3 if compact else 1.18))
  thin_count_axis(ax)
  if compact:
    from matplotlib.ticker import MaxNLocator

    ax.xaxis.set_major_locator(MaxNLocator(nbins=3))


def _nullable(values: np.ndarray) -> list[float | None]:
  """Turn NaN into None so that pyarrow stores a null."""
  return [None if np.isnan(value) else float(value) for value in values]


@preprocessor(
  'core.funnel',
  version=1,
  inputs={'table': Port('table', description='One row per step: its name and rows surviving')},
  outputs={'figure': Port('figure', description='Rows surviving and rows removed by each step')},
  render=render_funnel,
)
def funnel(
  ctx: Context,
  *,
  table: pa.Table,
  label_column: str,
  count_column: str,
  panels: Panels = 'both',
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Rows surviving each cumulative step, and rows removed by each step.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per step, in the order the cuts are applied.
  label_column : str
      Column with the name of each step.
  count_column : str
      Numeric column with the rows surviving the step; null marks a step that failed.
  panels : {'both', 'counts', 'drops'}, default='both'
      Running count on the left and rows removed on the right, or one of them alone.
  title : str, default=''
      Title above the figure; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; computed from the number of steps when None.
  alt : str or None, default=None
      Alternative text; built from the counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_funnel(table, label_column, count_column)
  figure = render_funnel(ctx, data, panels=panels, title=title, width=width, height=height)
  if alt is None:
    counts = values_of(data, 'count') if data.num_rows else np.empty(0)
    n_failed = int(np.isnan(counts).sum())
    known = counts[np.isfinite(counts)]
    shown = {
      'both': 'Two panels: rows surviving and rows removed',
      'counts': 'Rows surviving',
      'drops': 'Rows removed',
    }[panels]
    alt = f'{shown} at each of {data.num_rows} steps ({label_column}).'
    if known.size:
      alt += f' The count goes from {known[0]:,.0f} to {known[-1]:,.0f}.'
    if n_failed:
      alt += f' Failed steps: {n_failed}.'
  return {'figure': ctx.save_figure(figure, data=data, alt=alt, caption=caption, width=width)}
