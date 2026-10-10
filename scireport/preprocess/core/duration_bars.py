"""``core.duration_bars``: wall-clock seconds per artifact, with the reused ones marked.

Ported from the MOSAICS panel ``plot_duration_bars``. A reused artifact costs no time and is
drawn hatched and labelled ``reused`` rather than left out: the panel is meant to show what a
re-run skipped as much as what it spent. Each built artifact is labelled with its duration in
the notation ``43 s``, ``2 min 05 s`` or ``1 h 02 min``.

Parameters of the step (see :func:`duration_bars`):

* ``label_column``: the artifact's name.
* ``seconds_column``: seconds spent; a null is drawn as an empty bar labelled ``--``.
* ``reused_column``: true where the artifact was reused; optional, a missing column or a null
  means the artifact was built.
* ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches; from the number of bars when
  omitted).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``label``, ``seconds`` (null kept as null) and ``reused`` (boolean), one row per
artifact in the order of the input.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.plotting import empty_axes, labels, numbers, require_columns, values_of
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_duration_bars(
  table: pa.Table,
  label_column: str,
  seconds_column: str,
  *,
  reused_column: str | None = None,
) -> pa.Table:
  """Pick the columns of the bars, in the order of the input.

  Parameters
  ----------
  table : pyarrow.Table
      One row per artifact.
  label_column : str
      Artifact name.
  seconds_column : str
      Seconds spent (a number).
  reused_column : str or None, default=None
      Column telling whether the artifact was reused; every artifact counts as built when None.

  Returns
  -------
  pyarrow.Table
      Columns ``label`` (string), ``seconds`` (float64, null kept) and ``reused`` (boolean,
      null counted as false).
  """
  require_columns(table, label_column, seconds_column, reused_column)
  seconds = numbers(table, seconds_column)
  if reused_column is None:
    reused = [False] * table.num_rows
  else:
    reused = [bool(flag) for flag in table.column(reused_column).to_pylist()]
  return pa.table(
    {
      'label': pa.array(labels(table, label_column), pa.string()),
      'seconds': pa.array([None if np.isnan(s) else float(s) for s in seconds], pa.float64()),
      'reused': pa.array(reused, pa.bool_()),
    }
  )


def render_duration_bars(
  ctx: Context,
  data: pa.Table,
  *,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw the bars of :func:`compute_duration_bars`.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_duration_bars` made (or read back from a sidecar file).
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; from the number of bars when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  rows = data.num_rows
  with ctx.mplstyle():
    figure, ax = ctx.figure(
      width, float(height) if height is not None else max(1.8, 0.3 * rows + 1.0)
    )
    if rows == 0:
      empty_axes(ax, 'No artifacts')
      return figure
    names = [str(name) for name in data.column('label').to_pylist()]
    raw = values_of(data, 'seconds')
    values = np.nan_to_num(raw, nan=0.0)
    flags = [bool(flag) for flag in data.column('reused').to_pylist()]
    positions = np.arange(rows)
    bars = ax.barh(
      positions,
      values,
      color=[ctx.look.color('neutral' if flag else 'success') for flag in flags],
    )
    for bar, flag in zip(bars, flags, strict=True):
      if flag:
        bar.set_hatch('//')
    ax.set_yticks(positions)
    ax.set_yticklabels(names, fontsize=7, family='monospace')
    ax.invert_yaxis()
    ax.set_xlabel('Wall clock')
    if title:
      ax.set_title(title, fontsize=11)
    span = float(values.max()) if values.any() else 1.0
    for position, (value, seconds, flag) in enumerate(zip(values, raw, flags, strict=True)):
      ax.text(
        value + span * 0.01,
        position,
        'reused' if flag else _format_duration(float(seconds)),
        va='center',
        fontsize=7,
        color=ctx.look.color('neutral' if flag else 'annotation'),
      )
    ax.set_xlim(0, span * 1.22)
  return figure


@preprocessor(
  'core.duration_bars',
  version=1,
  inputs={'table': Port('table', description='One row per artifact: label, seconds, reused')},
  outputs={'figure': Port('figure', description='Horizontal bars of wall-clock seconds')},
  render=render_duration_bars,
)
def duration_bars(
  ctx: Context,
  *,
  table: pa.Table,
  label_column: str,
  seconds_column: str,
  reused_column: str | None = None,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Wall-clock seconds per artifact, with the reused ones hatched.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per artifact.
  label_column : str
      Column with the artifact's name.
  seconds_column : str
      Column with the seconds spent.
  reused_column : str or None, default=None
      Boolean column that is true where the artifact was reused; all built when None.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; from the number of bars when None.
  alt : str or None, default=None
      Alternative text; built from the number of artifacts and the total time when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_duration_bars(table, label_column, seconds_column, reused_column=reused_column)
  figure = render_duration_bars(ctx, data, title=title, width=width, height=height)
  if alt:
    text = alt
  elif data.num_rows:
    seconds = np.nan_to_num(values_of(data, 'seconds'), nan=0.0)
    n_reused = sum(bool(flag) for flag in data.column('reused').to_pylist())
    text = (
      f'Horizontal bars of the wall-clock time of {data.num_rows} artifacts, '
      f'{_format_duration(float(seconds.sum()))} in all; {n_reused} reused.'
    )
  else:
    text = 'No artifacts were recorded.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _format_duration(seconds: float | None) -> str:
  """Write a duration in seconds as ``0.3 s``, ``43 s``, ``2 min 05 s`` or ``1 h 02 min``.

  Parameters
  ----------
  seconds : float or None
      Duration in seconds. None, NaN and infinity are no duration to show.

  Returns
  -------
  str
      ``'--'`` for a missing or non-finite input. Below one second, one decimal place
      (``'0.3 s'``): a measured duration never reads ``'0 s'``. From one second the value is
      rounded to the whole second and written with the two largest units that apply, the
      smaller one padded to two digits: ``'43 s'``, ``'2 min 05 s'``, ``'1 h 02 min'``,
      ``'1 h 00 min'``. A negative input gets a leading ``'-'``.
  """
  if seconds is None or not math.isfinite(seconds):
    return '--'
  if seconds < 0:
    return f'-{_format_duration(-seconds)}'
  if seconds < 1:
    return f'{seconds:.1f} s'
  total = round(seconds)
  hours, remainder = divmod(total, 3600)
  minutes, secs = divmod(remainder, 60)
  if hours:
    return f'{hours} h {minutes:02d} min'
  if minutes:
    return f'{minutes} min {secs:02d} s'
  return f'{secs} s'
