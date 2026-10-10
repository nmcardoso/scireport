"""``core.separation_histogram``: how far each matched object sits from the position it matched.

Ported from the MOSAICS panel ``plot_separation_histogram``. The distribution is the main
evidence that a match radius was the right one. A histogram that rises towards the radius and is
cut off by it belongs to a radius too small to have found every counterpart; one that falls to
zero well inside it is a radius with room to spare, and the rows out at the edge are the ones
most likely to be chance alignments. The match radius is drawn as a dashed vertical rule so the
tail can be read against the limit that produced it.

The pre-processor takes either the separations themselves or a tally of them (a column of bin
centres and a column of counts), because a run over a hundred million rows never carries the
sample into its report, only the histogram it already computed. Both forms draw the same panel.

Parameters of the step (see :func:`separation_histogram`):

* ``column``: the separations in arcseconds, or (with ``counts_column``) the bin centres.
* ``counts_column``: the column of counts when the table is already a tally.
* ``radius``: the match radius in arcseconds, drawn as a rule; nothing when null.
* ``bins``: number of bins, for samples only.
* ``x_label``, ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``left`` and ``right`` (bin edges in arcseconds) and ``count`` (matches in the
bin). The match radius is a drawing parameter, not data, and is not in the sidecar.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.plotting import empty_axes, numbers, require_columns, values_of
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

_DEFAULT_X_LABEL = 'Angular separation (arcsec)'


def compute_separation_histogram(
  table: pa.Table,
  column: str,
  *,
  counts_column: str | None = None,
  bins: int = 40,
) -> pa.Table:
  """Tally separations into bars.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  column : str
      Separations in arcseconds, or bin centres when ``counts_column`` is given.
  counts_column : str or None, default=None
      Column of counts; the table is then taken to be a tally (one row per bin).
  bins : int, default=40
      Number of equal-width bins between the smallest and the largest separation; used for
      samples only.

  Returns
  -------
  pyarrow.Table
      Columns ``left``, ``right`` and ``count``; no rows when there is nothing finite to count.
  """
  require_columns(table, column, counts_column)
  values = numbers(table, column)
  if counts_column is None:
    values = values[np.isfinite(values)]
    if values.size == 0:
      return _bars(np.empty(0), np.empty(0), np.empty(0))
    counts, edges = np.histogram(values, bins=max(int(bins), 1))
    return _bars(edges[:-1], edges[1:], counts)
  weights = np.nan_to_num(numbers(table, counts_column), nan=0.0)
  keep = np.isfinite(values)
  centres, weights = values[keep], weights[keep]
  if centres.size == 0:
    return _bars(np.empty(0), np.empty(0), np.empty(0))
  order = np.argsort(centres, kind='stable')
  centres, weights = centres[order], weights[order]
  width = float(np.min(np.diff(centres))) if centres.size > 1 else float(centres[0] or 1.0)
  width = width if width > 0 else 1.0
  return _bars(centres - width / 2, centres + width / 2, weights)


def render_separation_histogram(
  ctx: Context,
  data: pa.Table,
  *,
  radius: float | None = None,
  x_label: str = _DEFAULT_X_LABEL,
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
) -> Figure:
  """Draw the bars of :func:`compute_separation_histogram` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_separation_histogram` made (or read back from a sidecar file).
  radius : float or None, default=None
      The match radius in arcseconds, drawn as a dashed vertical rule; nothing when None or 0.
  x_label : str, default='Angular separation (arcsec)'
      Label of the separation axis.
  title : str, default=''
      Title; nothing when empty.
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
      empty_axes(ax, 'No separations recorded')
      return figure
    left, right = values_of(data, 'left'), values_of(data, 'right')
    ax.bar(left, counts, width=right - left, align='edge', color=ctx.look.series(0), linewidth=0)
    if radius:
      ax.axvline(
        float(radius),
        color=ctx.look.color('warning'),
        linestyle='--',
        linewidth=1.0,
        label=f'match radius ({radius:g}")',
      )
      ax.legend(fontsize=7)
    ax.set_xlabel(x_label)
    ax.set_ylabel('Matches')
    ax.set_xlim(left=0)
    if title:
      ax.set_title(title, fontsize=11)
  return figure


@preprocessor(
  'core.separation_histogram',
  version=1,
  inputs={'table': Port('table', description='Separations, or a tally of matches per bin')},
  outputs={'figure': Port('figure', description='The histogram of match separations')},
  render=render_separation_histogram,
)
def separation_histogram(
  ctx: Context,
  *,
  table: pa.Table,
  column: str,
  counts_column: str | None = None,
  radius: float | None = None,
  bins: int = 40,
  x_label: str = _DEFAULT_X_LABEL,
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Histogram of match separations, with the match radius marked.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      Separations, or one row per bin when ``counts_column`` is given.
  column : str
      Column of separations in arcseconds, or of bin centres (arcseconds) for a tally.
  counts_column : str or None, default=None
      Column with the number of matches in each bin; makes the table a tally.
  radius : float or None, default=None
      Match radius in arcseconds, drawn as a vertical rule; nothing when None.
  bins : int, default=40
      Number of bins for a sample; ignored for a tally.
  x_label : str, default='Angular separation (arcsec)'
      Label of the separation axis.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.2
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the column name, the number of matches and the radius when
      None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_separation_histogram(table, column, counts_column=counts_column, bins=bins)
  figure = render_separation_histogram(
    ctx, data, radius=radius, x_label=x_label, title=title, width=width, height=height
  )
  total = float(np.nansum(values_of(data, 'count'))) if data.num_rows else 0.0
  if alt:
    text = alt
  elif total > 0:
    text = f'Histogram of {column}: {data.num_rows} bars, {total:,.0f} matches in all.'
    if radius:
      text += f' A dashed rule marks the match radius at {radius:g} arcsec.'
  else:
    text = f'No separations were recorded in {column}.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _bars(left: np.ndarray, right: np.ndarray, count: np.ndarray) -> pa.Table:
  """Build the tally table with fixed column types, empty or not."""
  return pa.table(
    {
      'left': pa.array(np.asarray(left, dtype=float), pa.float64()),
      'right': pa.array(np.asarray(right, dtype=float), pa.float64()),
      'count': pa.array(np.asarray(count, dtype=float), pa.float64()),
    }
  )
