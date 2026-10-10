"""``core.achieved_vs_target``: paired horizontal bars of what was asked for and what came out.

Ported from the MOSAICS panel ``plot_achieved_vs_target``. Each row of the input table is one
pair: a label, the value that was measured and the value that was requested. The achieved bar is
drawn above the requested bar, in a logarithmic axis (the pairs can span several orders of
magnitude and the small ones would be indistinguishable from zero on a linear axis), and each
achieved bar is annotated with its value and with the ratio achieved over requested.

Parameters of the step (see :func:`achieved_vs_target`):

* ``label_column``: the name of each pair.
* ``achieved_column``: what was measured.
* ``target_column``: what was requested; null where nothing was requested, in which case only
  the achieved bar is drawn.
* ``x_label``, ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches; from the number of pairs when
  omitted).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``label``, ``achieved`` and ``target``, one row per pair in the order of the
input; a null is kept as null (and drawn as zero).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

_DEFAULT_X_LABEL = 'Parts per million'
_BAR = 0.38


def compute_achieved_vs_target(
  table: pa.Table, label_column: str, achieved_column: str, target_column: str
) -> pa.Table:
  """Pick the three columns of the pairs, in the order of the input.

  Parameters
  ----------
  table : pyarrow.Table
      One row per pair.
  label_column : str
      Name of each pair.
  achieved_column : str
      What was measured (a number).
  target_column : str
      What was requested (a number; null where nothing was requested).

  Returns
  -------
  pyarrow.Table
      Columns ``label`` (string), ``achieved`` and ``target`` (float64, null kept as null).
  """
  require_columns(table, label_column, achieved_column, target_column)
  names = labels(table, label_column)
  achieved = numbers(table, achieved_column)
  target = numbers(table, target_column)
  return pa.table(
    {
      'label': pa.array(names, pa.string()),
      'achieved': pa.array([_or_none(value) for value in achieved], pa.float64()),
      'target': pa.array([_or_none(value) for value in target], pa.float64()),
    }
  )


def render_achieved_vs_target(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = _DEFAULT_X_LABEL,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw the pairs of :func:`compute_achieved_vs_target` as horizontal bars.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_achieved_vs_target` made (or read back from a sidecar file).
  x_label : str, default='Parts per million'
      Label of the value axis.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; from the number of pairs when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, _height(height, data.num_rows))
    if data.num_rows == 0:
      empty_axes(ax, 'Nothing recorded')
      return figure
    names = [str(name) for name in data.column('label').to_pylist()]
    got = np.nan_to_num(values_of(data, 'achieved'), nan=0.0)
    want = np.nan_to_num(values_of(data, 'target'), nan=0.0)
    positions = np.arange(len(names))
    ax.barh(positions - _BAR / 2, got, height=_BAR, color=ctx.look.series(0), label='achieved')
    ax.barh(
      positions + _BAR / 2, want, height=_BAR, color=ctx.look.color('neutral'), label='requested'
    )
    ax.set_yticks(positions)
    ax.set_yticklabels(names, fontsize=8, family='monospace')
    ax.invert_yaxis()
    # Log because the pairs can span one per mille to the whole catalogue; on a linear axis
    # the small ones are indistinguishable from zero. With nothing positive there is nothing
    # to put on a log axis, so it stays linear.
    if bool((got > 0).any() or (want > 0).any()):
      ax.set_xscale('log')
    ax.set_xlabel(x_label)
    if title:
      ax.set_title(title, fontsize=11)
    ax.legend(fontsize=7, loc='lower right')
    left = float(ax.get_xlim()[0])
    for position, (value, wanted) in enumerate(zip(got, want, strict=True)):
      ratio = f'  x{value / wanted:.3f}' if wanted else ''
      # A zero cannot sit on a log axis: its label starts at the left edge instead.
      ax.text(
        max(float(value), left),
        position - _BAR / 2,
        f' {value:,.0f}{ratio}',
        va='center',
        fontsize=7,
        clip_on=True,
      )
  return figure


@preprocessor(
  'core.achieved_vs_target',
  version=1,
  inputs={'table': Port('table', description='One row per pair: label, achieved and target')},
  outputs={'figure': Port('figure', description='Paired horizontal bars, achieved and requested')},
  render=render_achieved_vs_target,
)
def achieved_vs_target(
  ctx: Context,
  *,
  table: pa.Table,
  label_column: str,
  achieved_column: str,
  target_column: str,
  x_label: str = _DEFAULT_X_LABEL,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Paired horizontal bars of what was asked for and what came out.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per pair.
  label_column : str
      Column with the name of each pair.
  achieved_column : str
      Column with what was measured.
  target_column : str
      Column with what was requested; null where nothing was requested.
  x_label : str, default='Parts per million'
      Label of the value axis.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; from the number of pairs when None.
  alt : str or None, default=None
      Alternative text; built from the column names and the number of pairs when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_achieved_vs_target(table, label_column, achieved_column, target_column)
  figure = render_achieved_vs_target(
    ctx, data, x_label=x_label, title=title, width=width, height=height
  )
  if alt:
    text = alt
  elif data.num_rows:
    text = (
      f'Horizontal bars of {achieved_column} (achieved) and {target_column} (requested) for '
      f'{data.num_rows} items named by {label_column}, on a logarithmic axis.'
    )
  else:
    text = f'No rows to compare {achieved_column} with {target_column}.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _height(height: float | None, rows: int) -> float:
  """Figure height in inches: the given one, else room for the pairs."""
  return float(height) if height is not None else max(1.8, 0.55 * rows + 1.0)


def _or_none(value: float) -> float | None:
  """Turn NaN back into a null."""
  return None if np.isnan(value) else float(value)
