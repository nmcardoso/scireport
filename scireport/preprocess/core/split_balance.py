"""``core.split_balance``: one split's train, validation and test marginals on one stratifier.

Ported from the MOSAICS panel ``plot_split_balance``. The input is a long table with one row per
arm (for example the training, validation and test part of one split) and bin. Each arm's counts
are divided by its own total and drawn as a step curve; if the arms are balanced the curves lie
on top of each other.

Parameters of the step (see :func:`split_balance`):

* ``arm_column``: the arm of each row.
* ``bin_column``: the bin of the stratifier: numbers are ordered by value, other labels in the
  order they appear.
* ``count_column``: the count of the arm in that bin.
* ``stratifier``: name of the stratified quantity, for the axis label and the title.
* ``split``: name of the split the arms belong to, for the title.
* ``y_label``, ``title``: text; ``title`` is ``<split>: label balance on <stratifier>`` when
  omitted and nothing when an empty string.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``arm``, ``position`` (the bin's place on the axis, from 0), ``bin`` (its
label), ``count`` and ``share`` (the count over the arm's total).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.core._split_shares import compute_shares, draw_shares
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_split_balance(
  table: pa.Table, arm_column: str, bin_column: str, count_column: str
) -> pa.Table:
  """Turn a long table of counts into the share of each arm in each bin.

  Parameters
  ----------
  table : pyarrow.Table
      One row per arm and bin; repeated pairs are summed.
  arm_column : str
      Column with the arm of each row.
  bin_column : str
      Column with the bin of the stratifier.
  count_column : str
      Column with the count of the arm in that bin.

  Returns
  -------
  pyarrow.Table
      Columns ``arm``, ``position``, ``bin``, ``count`` and ``share``; every arm has a row for
      every bin (a bin it never lists has count 0).
  """
  return compute_shares(table, arm_column, bin_column, count_column, group_name='arm')


def render_split_balance(
  ctx: Context,
  data: pa.Table,
  *,
  stratifier: str = '',
  split: str = '',
  y_label: str = 'Share of arm',
  title: str | None = None,
  width: float = 1.0,
  height: float = 3.2,
) -> Figure:
  """Draw the share curves of :func:`compute_split_balance`.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_split_balance` made (or read back from a sidecar file).
  stratifier : str, default=''
      Name of the stratified quantity, for the axis label and the title.
  split : str, default=''
      Name of the split the arms belong to, for the title.
  y_label : str, default='Share of arm'
      Label of the share axis.
  title : str or None, default=None
      Title; ``<split>: label balance on <stratifier>`` when None, nothing when empty.
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
    if title is None:
      title = f'{split}: label balance on {stratifier}'.strip(': ')
    draw_shares(
      ax,
      data,
      ctx.look,
      group_name='arm',
      stratifier=stratifier,
      empty_message='No arms',
      y_label=y_label,
      title=title,
    )
  return figure


@preprocessor(
  'core.split_balance',
  version=1,
  inputs={'table': Port('table', description='One row per arm and bin: arm, bin, count')},
  outputs={'figure': Port('figure', description='Overlaid, normalised marginals of the arms')},
  render=render_split_balance,
)
def split_balance(
  ctx: Context,
  *,
  table: pa.Table,
  arm_column: str,
  bin_column: str,
  count_column: str,
  stratifier: str = '',
  split: str = '',
  y_label: str = 'Share of arm',
  title: str | None = None,
  width: float = 1.0,
  height: float = 3.2,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """One split's arms (train, validation, test) on one stratifier, normalised and overlaid.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per arm and bin.
  arm_column : str
      Column with the arm of each row.
  bin_column : str
      Column with the bin of the stratifier (numbers are ordered by value).
  count_column : str
      Column with the count of the arm in that bin.
  stratifier : str, default=''
      Name of the stratified quantity, for the axis label and the title.
  split : str, default=''
      Name of the split the arms belong to, for the title.
  y_label : str, default='Share of arm'
      Label of the share axis.
  title : str or None, default=None
      Title; ``<split>: label balance on <stratifier>`` when None, nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.2
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the arm names and the number of bins when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_split_balance(table, arm_column, bin_column, count_column)
  figure = render_split_balance(
    ctx,
    data,
    stratifier=stratifier,
    split=split,
    y_label=y_label,
    title=title,
    width=width,
    height=height,
  )
  if alt:
    text = alt
  elif data.num_rows:
    arms = list(dict.fromkeys(data.column('arm').to_pylist()))
    n_bins = data.num_rows // len(arms)
    what = f' of {stratifier}' if stratifier else ''
    text = (
      f'Step curves of the share of each arm ({", ".join(arms)}) in {n_bins} '
      f'bin{"s" if n_bins != 1 else ""}{what}.'
    )
  else:
    text = 'No arms were recorded.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
