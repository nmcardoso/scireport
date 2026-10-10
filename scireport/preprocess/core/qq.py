"""``core.qq``: a Q-Q plot of a sample against a normal distribution or a second sample.

Ported from the MOSAICS panel ``plot_qq``, which plotted the quantiles of the right-hand pixel
sample against those of the left-hand one with the line ``y = x``. Here the two samples are two
columns of the input table, or the second is the standard normal distribution.

Parameters of the step (see :func:`qq`):

* ``column``: the sample on the y axis.
* ``reference_column``: a second sample for the x axis. Without it the x axis holds quantiles of
  the standard normal distribution and the sample is standardised (mean 0, standard deviation 1)
  first, so that ``y = x`` is the line of a perfect normal sample.
* ``max_points``: the most points drawn. The quantiles are taken on a deterministic grid of at
  most this many levels, never at every row, so the sidecar stays small.
* ``x_label``, ``y_label``, ``title``: text (axis labels come from the columns when omitted).
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``level`` (the probability of the quantile), ``x`` (reference quantile) and
``y`` (sample quantile).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.core._distribution import (
  finite_sample,
  hazen_levels,
  normal_ppf,
  standardise,
)
from scireport.preprocess.plotting import empty_axes, frame, require_columns, values_of
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_qq(
  table: pa.Table,
  column: str,
  *,
  reference_column: str | None = None,
  max_points: int = 2000,
) -> pa.Table:
  """Pair the quantiles of a sample with those of the reference.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  column : str
      The sample (y axis); nulls, NaN and infinities are dropped.
  reference_column : str or None, default=None
      A second sample (x axis); the standard normal distribution when None.
  max_points : int, default=2000
      The most quantile pairs. Against a normal distribution the levels are the plotting
      positions ``(i + 0.5) / n``, so a sample of at most ``max_points`` rows is compared
      order statistic by order statistic. Between two samples the levels are ``n`` evenly spaced
      probabilities from 0 to 1 (extremes included), ``n`` being the larger sample size capped
      at ``max_points``.

  Returns
  -------
  pyarrow.Table
      Columns ``level``, ``x`` and ``y`` (all float64); no rows when a sample is empty.
  """
  require_columns(table, column, reference_column)
  sample = finite_sample(table, column)
  empty = frame(level=np.empty(0), x=np.empty(0), y=np.empty(0))
  if sample.size == 0:
    return empty
  limit = max(int(max_points), 2)
  if reference_column is None:
    levels = hazen_levels(min(sample.size, limit))
    y = np.quantile(standardise(sample), levels, method='hazen')
    return frame(level=levels, x=normal_ppf(levels), y=y)
  reference = finite_sample(table, reference_column)
  if reference.size == 0:
    return empty
  levels = np.linspace(0.0, 1.0, min(max(sample.size, reference.size), limit))
  return frame(level=levels, x=np.quantile(reference, levels), y=np.quantile(sample, levels))


def render_qq(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = 'Theoretical quantiles',
  y_label: str = 'Sample quantiles',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
) -> Figure:
  """Draw the quantile pairs of :func:`compute_qq` with the line ``y = x``.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_qq` made (or read back from a bundle's sidecar file).
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
    ax.scatter(x, y, s=10, alpha=0.7, color=ctx.look.series(0), linewidths=0)
    low, high = float(x.min()), float(x.max())
    ax.plot(
      [low, high],
      [low, high],
      color=ctx.look.color('annotation'),
      linewidth=1,
      linestyle='--',
      label='y = x',
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
    ax.legend()
  return figure


@preprocessor(
  'core.qq',
  version=1,
  inputs={'table': Port('table', description='A table with the sample column (and the reference)')},
  outputs={'figure': Port('figure', description='The Q-Q plot')},
  render=render_qq,
)
def qq(
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
  """Q-Q plot of a sample against a normal distribution or a second sample.

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
      The most points drawn (a deterministic quantile grid, not every row).
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
  data = compute_qq(table, column, reference_column=reference_column, max_points=max_points)
  if reference_column is None:
    x_text, y_text = 'Normal quantiles', f'{column} quantiles (standardised)'
    against = 'the standard normal distribution'
  else:
    x_text, y_text = f'{reference_column} quantiles', f'{column} quantiles'
    against = reference_column
  figure = render_qq(
    ctx,
    data,
    x_label=x_text if x_label is None else x_label,
    y_label=y_text if y_label is None else y_label,
    title=title,
    width=width,
    height=height,
  )
  text = alt or f'Q-Q plot of {column} against {against}: {data.num_rows} quantile pairs.'
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
