"""``core.split_marginals``: each split's marginal on one stratifier, normalised and overlaid.

Ported from the MOSAICS panel ``plot_split_marginals``. The input is a long table with one row
per split and bin. Each split's counts are divided by its own total and drawn as a step curve,
all on one axis. They are normalised because splits can differ by orders of magnitude in size
and the question is about *shape*: plotted as counts, most of the curves would be flat on the
axis. One split can be named the reference and is drawn heavier, so the eye has a baseline.

Parameters of the step (see :func:`split_marginals`):

* ``split_column``: the split of each row (for example ``train``, ``validation``, ``test``).
* ``bin_column``: the bin of the stratifier: numbers are ordered by value, other labels in the
  order they appear.
* ``count_column``: the count of the split in that bin.
* ``stratifier``: name of the stratified quantity, for the axis label and the title.
* ``reference``: the split drawn heavier; none when empty.
* ``y_label``, ``title``: text; ``title`` is ``Split marginals: <stratifier>`` when omitted and
  nothing when an empty string.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``split``, ``position`` (the bin's place on the axis, from 0), ``bin`` (its
label), ``count`` and ``share`` (the count over the split's total).
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


def compute_split_marginals(
  table: pa.Table, split_column: str, bin_column: str, count_column: str
) -> pa.Table:
  """Turn a long table of counts into the share of each split in each bin.

  Parameters
  ----------
  table : pyarrow.Table
      One row per split and bin; repeated pairs are summed.
  split_column : str
      Column with the split of each row.
  bin_column : str
      Column with the bin of the stratifier.
  count_column : str
      Column with the count of the split in that bin.

  Returns
  -------
  pyarrow.Table
      Columns ``split``, ``position``, ``bin``, ``count`` and ``share``; every split has a row
      for every bin (a bin it never lists has count 0).
  """
  return compute_shares(table, split_column, bin_column, count_column, group_name='split')


def render_split_marginals(
  ctx: Context,
  data: pa.Table,
  *,
  stratifier: str = '',
  reference: str = '',
  y_label: str = 'Share of split',
  title: str | None = None,
  width: float = 1.0,
  height: float = 3.2,
) -> Figure:
  """Draw the share curves of :func:`compute_split_marginals`.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_split_marginals` made (or read back from a sidecar file).
  stratifier : str, default=''
      Name of the stratified quantity, for the axis label and the title.
  reference : str, default=''
      The split drawn heavier; none when empty or not among the splits.
  y_label : str, default='Share of split'
      Label of the share axis.
  title : str or None, default=None
      Title; ``Split marginals: <stratifier>`` when None, nothing when empty.
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
      title = f'Split marginals: {stratifier}' if stratifier else 'Split marginals'
    draw_shares(
      ax,
      data,
      ctx.look,
      group_name='split',
      stratifier=stratifier,
      empty_message='No marginals',
      y_label=y_label,
      title=title,
      reference=reference,
    )
  return figure


@preprocessor(
  'core.split_marginals',
  version=1,
  inputs={'table': Port('table', description='One row per split and bin: split, bin, count')},
  outputs={'figure': Port('figure', description='Overlaid, normalised marginals of the splits')},
  render=render_split_marginals,
)
def split_marginals(
  ctx: Context,
  *,
  table: pa.Table,
  split_column: str,
  bin_column: str,
  count_column: str,
  stratifier: str = '',
  reference: str = '',
  y_label: str = 'Share of split',
  title: str | None = None,
  width: float = 1.0,
  height: float = 3.2,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Each split's marginal on one stratifier, normalised and overlaid.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per split and bin.
  split_column : str
      Column with the split of each row.
  bin_column : str
      Column with the bin of the stratifier (numbers are ordered by value).
  count_column : str
      Column with the count of the split in that bin.
  stratifier : str, default=''
      Name of the stratified quantity, for the axis label and the title.
  reference : str, default=''
      The split drawn heavier so the eye has a baseline; none when empty.
  y_label : str, default='Share of split'
      Label of the share axis.
  title : str or None, default=None
      Title; ``Split marginals: <stratifier>`` when None, nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.2
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the split names and the number of bins when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_split_marginals(table, split_column, bin_column, count_column)
  figure = render_split_marginals(
    ctx,
    data,
    stratifier=stratifier,
    reference=reference,
    y_label=y_label,
    title=title,
    width=width,
    height=height,
  )
  if alt:
    text = alt
  elif data.num_rows:
    splits = list(dict.fromkeys(data.column('split').to_pylist()))
    n_bins = data.num_rows // len(splits)
    what = f' of {stratifier}' if stratifier else ''
    text = (
      f'Step curves of the share of each split ({", ".join(splits)}) in {n_bins} '
      f'bin{"s" if n_bins != 1 else ""}{what}.'
    )
  else:
    text = 'No split marginals were recorded.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
