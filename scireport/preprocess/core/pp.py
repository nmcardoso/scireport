"""``core.pp``: a P-P plot of a sample against a normal distribution or a second sample.

Ported from the MOSAICS panel ``plot_pp``, which compared the empirical distribution functions
of two pixel samples on a common grid of values. Here the two samples are two columns of the
input table, or the second is the standard normal distribution.

Parameters of the step (see :func:`pp`):

* ``column``: the sample (y axis).
* ``reference_column``: a second sample (x axis). Without it the x axis holds the standard
  normal distribution function and the sample is standardised (mean 0, standard deviation 1)
  first, so that ``y = x`` is the line of a perfect normal sample.
* ``max_points``: the most points drawn. The distribution functions are evaluated on a
  deterministic grid of at most this many points, never at every row.
* ``x_label``, ``y_label``, ``title``: text (axis labels come from the columns when omitted).
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``value`` (where the distribution functions were evaluated; standardised units
against a normal distribution), ``x`` (reference distribution function) and ``y`` (sample
distribution function).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.core._distribution import (
  finite_sample,
  hazen_levels,
  normal_cdf,
  standardise,
)
from scireport.preprocess.plotting import empty_axes, frame, require_columns, values_of
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_pp(
  table: pa.Table,
  column: str,
  *,
  reference_column: str | None = None,
  max_points: int = 2000,
) -> pa.Table:
  """Pair the distribution function of a sample with that of the reference.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  column : str
      The sample (y axis); nulls, NaN and infinities are dropped.
  reference_column : str or None, default=None
      A second sample (x axis); the standard normal distribution when None.
  max_points : int, default=2000
      The most points. Between two samples the functions are evaluated on ``n`` evenly spaced
      values from the smallest to the largest of both samples, ``n`` being the larger sample size
      capped at ``max_points``. Against a normal distribution they are evaluated at the
      standardised sample values that sit at ``n`` evenly spaced plotting positions.

  Returns
  -------
  pyarrow.Table
      Columns ``value``, ``x`` and ``y`` (all float64); no rows when a sample is empty.
  """
  require_columns(table, column, reference_column)
  sample = finite_sample(table, column)
  empty = frame(value=np.empty(0), x=np.empty(0), y=np.empty(0))
  if sample.size == 0:
    return empty
  limit = max(int(max_points), 2)
  if reference_column is None:
    scaled = standardise(sample)
    count = min(sample.size, limit)
    picks = np.minimum((hazen_levels(count) * sample.size).astype(np.int64), sample.size - 1)
    grid = scaled[picks]
    sample_cdf = np.searchsorted(scaled, grid, side='right') / sample.size
    return frame(value=grid, x=normal_cdf(grid), y=sample_cdf)
  reference = finite_sample(table, reference_column)
  if reference.size == 0:
    return empty
  count = min(max(sample.size, reference.size), limit)
  grid = np.linspace(min(sample[0], reference[0]), max(sample[-1], reference[-1]), count)
  return frame(
    value=grid,
    x=np.searchsorted(reference, grid, side='right') / reference.size,
    y=np.searchsorted(sample, grid, side='right') / sample.size,
  )


def render_pp(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = 'Reference CDF',
  y_label: str = 'Sample CDF',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
) -> Figure:
  """Draw the points of :func:`compute_pp` with the line ``y = x`` on the unit square.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_pp` made (or read back from a bundle's sidecar file).
  x_label, y_label, title : str
      Axis labels and title; empty strings draw nothing.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.4
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height)
    x, y = values_of(data, 'x'), values_of(data, 'y')
    if x.size == 0:
      empty_axes(ax, 'No data')
      return figure
    ax.plot(x, y, color=ctx.look.series(0))
    ax.plot(
      [0, 1],
      [0, 1],
      color=ctx.look.color('annotation'),
      linewidth=1,
      linestyle='--',
      label='y = x',
    )
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.set_box_aspect(1)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
    ax.legend()
  return figure


@preprocessor(
  'core.pp',
  version=1,
  inputs={'table': Port('table', description='A table with the sample column (and the reference)')},
  outputs={'figure': Port('figure', description='The P-P plot')},
  render=render_pp,
)
def pp(
  ctx: Context,
  *,
  table: pa.Table,
  column: str,
  reference_column: str | None = None,
  max_points: int = 2000,
  x_label: str | None = None,
  y_label: str | None = None,
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """P-P plot of a sample against a normal distribution or a second sample.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      The input table.
  column : str
      The sample, drawn on the y axis.
  reference_column : str or None, default=None
      A second sample for the x axis; without it the standard normal distribution, against
      which the standardised sample is drawn.
  max_points : int, default=2000
      The most points drawn (a deterministic grid, not every row).
  x_label, y_label : str or None, default=None
      Axis labels; made from the column names when None.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.4
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the column names and the number of points when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_pp(table, column, reference_column=reference_column, max_points=max_points)
  if reference_column is None:
    x_text, y_text = 'Normal CDF', f'{column} CDF (standardised)'
    against = 'the standard normal distribution'
  else:
    x_text, y_text = f'{reference_column} CDF', f'{column} CDF'
    against = reference_column
  figure = render_pp(
    ctx,
    data,
    x_label=x_text if x_label is None else x_label,
    y_label=y_text if y_label is None else y_label,
    title=title,
    width=width,
    height=height,
  )
  text = alt or f'P-P plot of {column} against {against}: {data.num_rows} points.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
