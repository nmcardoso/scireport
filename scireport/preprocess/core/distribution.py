"""``core.distribution``: a box or a violin of one value column, per group.

Ported from the MOSAICS panel ``plot_metric_distribution`` (the spread of a per-object metric
such as SSIM, PSNR or a KS statistic across the sample, one box or violin per metric). A bundle
never holds the sample, so the step stores summaries and the figure is drawn from them alone:

* a box needs the five-number summary, the whisker ends (the most extreme values within 1.5
  interquartile ranges of the box, as matplotlib draws them) and the outlying values, of which at
  most ``max_outliers`` per group are kept, spread evenly over the sorted outliers so that the
  smallest and the largest are always among them;
* a violin needs a density curve: ``n_grid`` points per group, from the smallest to the largest
  value, computed with a Gaussian kernel density estimate with Scott's bandwidth
  (``std * n**(-1/5)``, sample standard deviation).

Parameters of the step (see :func:`distribution`):

* ``value_column``: the numeric column. ``group_column``: one box or violin per distinct value
  of this column, in order of first appearance; when omitted there is one group named after the
  value column. Nulls and non-finite values are dropped.
* ``kind``: ``'box'`` or ``'violin'``. ``max_outliers`` and ``n_grid`` as above.
* ``y_label`` (the value column name when omitted) and ``title``.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns, one tidy table for both kinds:

* ``group``: the group's label (rows of one group are contiguous, groups in drawing order).
* ``part``: ``'summary'`` (one row per statistic), ``'outlier'`` (box only, one row per kept
  outlier) or ``'density'`` (violin only, one row per grid point).
* ``name``: for a summary row ``n`` (finite values), ``n_outliers`` (box only: all outliers,
  kept or not), ``min``, ``q1``, ``median``, ``q3``, ``max``, ``whisker_low``,
  ``whisker_high``; null otherwise.
* ``value``: the statistic, the outlier, or the grid point.
* ``density``: the density at the grid point (integrates to one); NaN for other rows.

A group without finite values has the single row ``n = 0`` and draws as an empty slot.
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
  values_of,
)
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

_KDE_CHUNK = 20_000
_STATS = ('min', 'q1', 'median', 'q3', 'max', 'whisker_low', 'whisker_high')


def gaussian_kde_curve(values: np.ndarray, n_grid: int = 100) -> tuple[np.ndarray, np.ndarray]:
  """Evaluate a Gaussian kernel density estimate on an even grid over the data range.

  The bandwidth is Scott's rule, ``std * n**(-1/5)`` with the sample standard deviation
  (``ddof=1``). When it is zero (one value, or all values equal) the bandwidth is 0.1 and the grid
  covers the value plus and minus 0.5, so the curve is a narrow bump rather than an error.

  Parameters
  ----------
  values : numpy.ndarray
      Finite samples, at least one.
  n_grid : int, default=100
      Number of grid points.

  Returns
  -------
  tuple of numpy.ndarray
      The grid and the density on it (it integrates to about one over the real line).
  """
  values = np.asarray(values, dtype=float)
  count = values.size
  low, high = float(values.min()), float(values.max())
  spread = float(np.std(values, ddof=1)) if count > 1 else 0.0
  bandwidth = spread * count ** (-1.0 / 5.0)
  if not bandwidth > 0.0:
    bandwidth = 0.1
    low, high = low - 0.5, high + 0.5
  grid = np.linspace(low, high, n_grid)
  total = np.zeros(n_grid)
  for start in range(0, count, _KDE_CHUNK):
    scaled = (grid[:, None] - values[None, start : start + _KDE_CHUNK]) / bandwidth
    total += np.exp(-0.5 * scaled * scaled).sum(axis=1)
  return grid, total / (count * bandwidth * np.sqrt(2.0 * np.pi))


def box_statistics(values: np.ndarray, max_outliers: int = 200) -> dict[str, Any]:
  """Summarise a sample as a box: quartiles, whisker ends and outliers.

  Parameters
  ----------
  values : numpy.ndarray
      Finite samples, at least one.
  max_outliers : int, default=200
      The most outliers to keep; more are thinned evenly over the sorted outliers.

  Returns
  -------
  dict
      ``n``, ``min``, ``q1``, ``median``, ``q3``, ``max``, ``whisker_low``, ``whisker_high``,
      ``n_outliers`` (floats) and ``outliers`` (a sorted array of at most ``max_outliers``).
  """
  values = np.sort(np.asarray(values, dtype=float))
  q1, median, q3 = (float(item) for item in np.percentile(values, [25, 50, 75]))
  reach = 1.5 * (q3 - q1)
  inside = values[(values >= q1 - reach) & (values <= q3 + reach)]
  outside = values[(values < q1 - reach) | (values > q3 + reach)]
  if outside.size > max_outliers:
    keep = np.unique(np.round(np.linspace(0, outside.size - 1, max_outliers)).astype(np.int64))
    kept = outside[keep]
  else:
    kept = outside
  return {
    'n': float(values.size),
    'min': float(values[0]),
    'q1': q1,
    'median': median,
    'q3': q3,
    'max': float(values[-1]),
    'whisker_low': float(inside[0]),
    'whisker_high': float(inside[-1]),
    'n_outliers': float(outside.size),
    'outliers': kept,
  }


def compute_distribution(
  table: pa.Table,
  value_column: str,
  *,
  group_column: str | None = None,
  kind: Literal['box', 'violin'] = 'box',
  max_outliers: int = 200,
  n_grid: int = 100,
) -> pa.Table:
  """Summarise each group of a value column for a box or a violin.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  value_column : str
      Numeric column.
  group_column : str or None, default=None
      Column naming each row's group; one group named ``value_column`` when None.
  kind : {'box', 'violin'}, default='box'
      Which summaries to store: outliers for a box, a density curve for a violin.
  max_outliers : int, default=200
      The most outliers kept per group (box).
  n_grid : int, default=100
      Grid points per group (violin).

  Returns
  -------
  pyarrow.Table
      Columns ``group``, ``part``, ``name``, ``value`` and ``density``; see the module
      docstring. No rows when the table has none.
  """
  require_columns(table, value_column, group_column)
  values = numbers(table, value_column)
  groups = labels(table, group_column) if group_column is not None else None
  order: list[str] = (
    list(dict.fromkeys(groups)) if groups is not None else ([value_column] if values.size else [])
  )
  names = np.asarray(groups if groups is not None else [value_column] * values.size, dtype=object)
  rows: list[tuple[str, str, str | None, float, float]] = []
  nan = float('nan')
  for group in order:
    sample = values[names == group]
    sample = sample[np.isfinite(sample)]
    if sample.size == 0:
      rows.append((group, 'summary', 'n', 0.0, nan))
      continue
    stats = box_statistics(sample, max_outliers)
    rows.append((group, 'summary', 'n', stats['n'], nan))
    if kind == 'box':
      rows.append((group, 'summary', 'n_outliers', stats['n_outliers'], nan))
    rows.extend((group, 'summary', name, stats[name], nan) for name in _STATS)
    if kind == 'box':
      rows.extend((group, 'outlier', None, float(item), nan) for item in stats['outliers'])
    else:
      grid, density = gaussian_kde_curve(sample, n_grid)
      rows.extend(
        (group, 'density', None, float(point), float(height))
        for point, height in zip(grid, density, strict=True)
      )
  return pa.table(
    {
      'group': pa.array([row[0] for row in rows], pa.string()),
      'part': pa.array([row[1] for row in rows], pa.string()),
      'name': pa.array([row[2] for row in rows], pa.string()),
      'value': pa.array([row[3] for row in rows], pa.float64()),
      'density': pa.array([row[4] for row in rows], pa.float64()),
    }
  )


def render_distribution(
  ctx: Context,
  data: pa.Table,
  *,
  y_label: str = '',
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
) -> Figure:
  """Draw the boxes or violins of :func:`compute_distribution` from its summaries only.

  The kind is read from the table: a density curve makes a violin, otherwise a box. A box is drawn
  with ``Axes.bxp`` from the stored statistics, a violin as a filled curve of constant maximum
  width with the range and the median marked.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_distribution` made (or read back from a bundle's sidecar file).
  y_label, title : str
      Axis label and title; empty strings draw nothing.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.6
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height)
    groups = list(dict.fromkeys(str(item) for item in data.column('group').to_pylist()))
    group_of = np.asarray(data.column('group').to_pylist(), dtype=object)
    part_of = np.asarray(data.column('part').to_pylist(), dtype=object)
    name_of = np.asarray(data.column('name').to_pylist(), dtype=object)
    value, density = values_of(data, 'value'), values_of(data, 'density')
    summaries: list[dict[str, float] | None] = []
    for group in groups:
      mine = (group_of == group) & (part_of == 'summary')
      stats = {
        str(name): float(item) for name, item in zip(name_of[mine], value[mine], strict=True)
      }
      summaries.append(stats if stats.get('n', 0.0) > 0 else None)
    if not any(item is not None for item in summaries):
      empty_axes(ax, 'No data')
      return figure
    positions = np.arange(1, len(groups) + 1)
    color = ctx.look.series(0)
    if bool((part_of == 'density').any()):
      _draw_violins(ax, groups, summaries, group_of, part_of, value, density, color)
    else:
      _draw_boxes(ax, ctx, groups, summaries, group_of, part_of, value, color)
    ax.set_xticks(positions)
    if len(groups) > 1:
      ax.set_xticklabels(groups, rotation=30, ha='right')
    else:
      ax.set_xticklabels(groups)
    ax.set_xlim(0.5, len(groups) + 0.5)
    if y_label:
      ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'core.distribution',
  version=1,
  inputs={'table': Port('table', description='One row per object, a value and optionally a group')},
  outputs={'figure': Port('figure', description='A box or violin per group')},
  render=render_distribution,
)
def distribution(
  ctx: Context,
  *,
  table: pa.Table,
  value_column: str,
  group_column: str | None = None,
  kind: Literal['box', 'violin'] = 'box',
  max_outliers: int = 200,
  n_grid: int = 100,
  y_label: str | None = None,
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Box or violin plot of a per-object value, one per group.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object.
  value_column : str
      Numeric column to summarise.
  group_column : str or None, default=None
      Column naming the group of each row; a single group when None.
  kind : {'box', 'violin'}, default='box'
      Box and whiskers, or a kernel density estimate.
  max_outliers : int, default=200
      The most outlying values stored per group (box).
  n_grid : int, default=100
      Points of the density curve per group (violin).
  y_label : str or None, default=None
      Label of the value axis; the column name when None.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.6
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the column name and counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_distribution(
    table,
    value_column,
    group_column=group_column,
    kind=kind,
    max_outliers=max_outliers,
    n_grid=n_grid,
  )
  figure = render_distribution(
    ctx,
    data,
    y_label=value_column if y_label is None else y_label,
    title=title,
    width=width,
    height=height,
  )
  text = alt or _alt(data, value_column, kind)
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _draw_boxes(
  ax: Any,
  ctx: Context,
  groups: list[str],
  summaries: list[dict[str, float] | None],
  group_of: np.ndarray,
  part_of: np.ndarray,
  value: np.ndarray,
  color: str,
) -> None:
  """Draw the stored statistics as boxes with ``Axes.bxp``."""
  stats: list[dict[str, Any]] = []
  positions: list[int] = []
  for index, (group, summary) in enumerate(zip(groups, summaries, strict=True), start=1):
    if summary is None:
      continue
    fliers = value[(group_of == group) & (part_of == 'outlier')]
    stats.append(
      {
        'label': group,
        'med': summary['median'],
        'q1': summary['q1'],
        'q3': summary['q3'],
        'whislo': summary['whisker_low'],
        'whishi': summary['whisker_high'],
        'fliers': fliers,
      }
    )
    positions.append(index)
  ax.bxp(
    stats,
    positions=positions,
    patch_artist=True,
    boxprops={'facecolor': color, 'alpha': 0.5},
    medianprops={'color': ctx.look.color('annotation'), 'linewidth': 1.5},
    flierprops={'marker': 'o', 'markersize': 3, 'markerfacecolor': 'none'},
  )


def _draw_violins(
  ax: Any,
  groups: list[str],
  summaries: list[dict[str, float] | None],
  group_of: np.ndarray,
  part_of: np.ndarray,
  value: np.ndarray,
  density: np.ndarray,
  color: str,
) -> None:
  """Draw each stored density curve as a filled violin of half-width 0.25 at its peak."""
  for index, (group, summary) in enumerate(zip(groups, summaries, strict=True), start=1):
    if summary is None:
      continue
    mine = (group_of == group) & (part_of == 'density')
    grid, curve = value[mine], density[mine]
    half = 0.25 * curve / float(curve.max())
    ax.fill_betweenx(grid, index - half, index + half, color=color, alpha=0.5, linewidth=0)
    ax.plot(
      np.concatenate([index + half, (index - half)[::-1]]),
      np.concatenate([grid, grid[::-1]]),
      color=color,
      linewidth=0.8,
    )
    ax.vlines(index, summary['min'], summary['max'], color=color, linewidth=0.8)
    for end in (summary['min'], summary['max']):
      ax.hlines(end, index - 0.1, index + 0.1, color=color, linewidth=0.8)
    ax.hlines(summary['median'], index - 0.25, index + 0.25, color=color, linewidth=1.5)


def _alt(data: pa.Table, value_column: str, kind: str) -> str:
  """Describe the figure from its data, with no number that is not counted."""
  part = data.column('part').to_pylist()
  name = data.column('name').to_pylist()
  value = values_of(data, 'value')
  sizes = [
    int(item)
    for item, part_name, stat in zip(value, part, name, strict=True)
    if part_name == 'summary' and stat == 'n'
  ]
  if not sizes or sum(sizes) == 0:
    return f'{kind.capitalize()} plot of {value_column}: no finite values.'
  groups = len(sizes)
  return (
    f'{kind.capitalize()} plot of {value_column}: {groups:,} '
    f'{"group" if groups == 1 else "groups"}, {sum(sizes):,} values in all.'
  )
