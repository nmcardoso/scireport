"""``astro.number_counts``: differential number counts per magnitude bin, with the Euclidean slope.

Ported from the MOSAICS panel ``plot_number_counts``. A uniform, non-evolving population fills
space fast enough that log10 dN/dm grows linearly with a slope of 0.6 per magnitude, the Euclidean
count-slope relation. A survey follows it while it is complete and falls below it once it starts
missing sources, so this panel is also the completeness turnover for whichever band it is drawn
from. The input is a tally (counts already made per magnitude bin, so a run over hundreds of
millions of rows never carries the catalogue); with ``group_column`` it is a long table with one
series per group, for example one per survey or per band.

The dashed reference is anchored through the fullest bin of each series, where the survey is most
likely still complete, rather than fitted, since a fit would let incompleteness pull its own
reference down. The original does not normalise by area, and neither does this step.

Parameters of the step (see :func:`number_counts`):

* ``center_column``: magnitude bin centres. ``count_column``: sources per bin. Rows with a null,
  non-finite or non-positive value are dropped; repeated centres in a series are summed.
* ``group_column``: optional series label (one row per bin and group).
* ``reference_slope``: the Euclidean slope per magnitude (0.6).
* ``x_label``, ``title``: text. ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``group`` (series label, empty without ``group_column``), ``center``, ``left``
and ``right`` (the bin and its edges, the width being the smallest spacing between the series'
centres, or 1 for a single bin) and ``count``, sorted by group and centre.
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


def compute_number_counts(
  table: pa.Table,
  center_column: str,
  count_column: str,
  *,
  group_column: str | None = None,
) -> pa.Table:
  """Tidy the tally of counts per magnitude bin, one series per group.

  Parameters
  ----------
  table : pyarrow.Table
      The input, one row per bin (and group).
  center_column : str
      Numeric column with the bin centres.
  count_column : str
      Numeric column with the sources per bin.
  group_column : str or None, default=None
      Column with the series label; one unnamed series when None.

  Returns
  -------
  pyarrow.Table
      Columns ``group``, ``center``, ``left``, ``right`` and ``count``, sorted by group and
      centre. Rows that are not finite or have no sources are dropped, repeated centres summed.
  """
  require_columns(table, center_column, count_column, group_column)
  centres = numbers(table, center_column)
  counts = numbers(table, count_column)
  names = labels(table, group_column) if group_column is not None else [''] * table.num_rows
  usable = np.isfinite(centres) & np.isfinite(counts) & (counts > 0)
  group_out: list[str] = []
  centre_out: list[float] = []
  left_out: list[float] = []
  right_out: list[float] = []
  count_out: list[float] = []
  kept = np.asarray(names, dtype=object)[usable]
  for name in sorted(set(kept.tolist())):
    mask = kept == name
    unique, inverse = np.unique(centres[usable][mask], return_inverse=True)
    totals = np.zeros(unique.size)
    np.add.at(totals, np.asarray(inverse).reshape(-1), counts[usable][mask])
    width = float(np.min(np.diff(unique))) if unique.size > 1 else 1.0
    group_out.extend([name] * unique.size)
    centre_out.extend(unique.tolist())
    left_out.extend((unique - width / 2).tolist())
    right_out.extend((unique + width / 2).tolist())
    count_out.extend(totals.tolist())
  return pa.table(
    {
      'group': pa.array(group_out, pa.string()),
      'center': pa.array(centre_out, pa.float64()),
      'left': pa.array(left_out, pa.float64()),
      'right': pa.array(right_out, pa.float64()),
      'count': pa.array(count_out, pa.float64()),
    }
  )


def render_number_counts(
  ctx: Context,
  data: pa.Table,
  *,
  reference_slope: float = 0.6,
  x_label: str = 'Magnitude',
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
) -> Figure:
  """Draw log10 counts per bin with the Euclidean reference of :func:`compute_number_counts`.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_number_counts` made (or read back from a bundle's sidecar file).
  reference_slope : float, default=0.6
      The Euclidean slope per magnitude, drawn dashed through the fullest bin of each series.
  x_label, title : str
      Axis label and title; empty strings draw nothing.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.2
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure; a placeholder when ``data`` has no rows.
  """
  from matplotlib.lines import Line2D

  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height)
    if data.num_rows == 0:
      empty_axes(ax, 'No data')
      return figure
    group = np.asarray(data.column('group').to_pylist(), dtype=object)
    centre, count = values_of(data, 'center'), values_of(data, 'count')
    names = sorted(set(group.tolist()))
    single = names == ['']
    annotation = ctx.look.color('annotation')
    for index, name in enumerate(names):
      mask = group == name
      centres, log_counts = centre[mask], np.log10(count[mask])
      color = ctx.look.series(index)
      ax.step(
        centres,
        log_counts,
        where='mid',
        color=color,
        linewidth=1.3,
        label='Observed' if single else name,
      )
      anchor = int(np.argmax(log_counts))
      reference = reference_slope * (centres - centres[anchor]) + log_counts[anchor]
      ax.plot(
        centres,
        reference,
        color=annotation if single else color,
        linewidth=1,
        linestyle='--',
        label=f'Euclidean slope ({reference_slope:g}/mag)' if single else '_nolegend_',
      )
    handles, texts = ax.get_legend_handles_labels()
    if not single:
      handles.append(Line2D([], [], color=annotation, linewidth=1, linestyle='--'))
      texts.append(f'Euclidean slope ({reference_slope:g}/mag)')
    ax.legend(handles, texts, fontsize=7)
    ax.set_xlabel(x_label)
    ax.set_ylabel(r'$\log_{10}$ counts per bin')
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'astro.number_counts',
  version=1,
  inputs={'table': Port('table', description='Sources per magnitude bin, one row per bin')},
  outputs={'figure': Port('figure', description='The differential number counts')},
  render=render_number_counts,
)
def number_counts(
  ctx: Context,
  *,
  table: pa.Table,
  center_column: str,
  count_column: str,
  group_column: str | None = None,
  reference_slope: float = 0.6,
  x_label: str = 'Magnitude',
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Differential number counts, log-scaled, against the Euclidean reference slope.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per magnitude bin (and group).
  center_column : str
      Column with the magnitude bin centres.
  count_column : str
      Column with the sources per bin.
  group_column : str or None, default=None
      Column with a series label (a survey, a band); one series when None.
  reference_slope : float, default=0.6
      The Euclidean slope per magnitude, anchored through the fullest bin of each series.
  x_label : str, default='Magnitude'
      Label of the x axis.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.2
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the number of series and bins when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_number_counts(table, center_column, count_column, group_column=group_column)
  figure = render_number_counts(
    ctx,
    data,
    reference_slope=reference_slope,
    x_label=x_label,
    title=title,
    width=width,
    height=height,
  )
  series = len(set(data.column('group').to_pylist()))
  total = float(np.nansum(values_of(data, 'count'))) if data.num_rows else 0.0
  text = alt or (
    f'Differential number counts of {count_column} against {center_column}, on a log scale with '
    f'a dashed reference slope of {reference_slope:g} per magnitude: {series} series, '
    f'{data.num_rows} bins, {total:,.0f} sources in all.'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
