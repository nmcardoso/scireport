"""``astro.snr_magnitude``: signal-to-noise against magnitude, with the 5-sigma depth marked.

Ported from the MOSAICS panel ``plot_snr_magnitude``. The catalogue of one band gives a
magnitude and a signal-to-noise ratio per object; the panel draws their hexagon density
(crowded regions as cells, sparse points individually) with the S/N = 5 line, and, when it is
known or can be estimated, the magnitude where the sample's S/N crosses 5.

Parameters of the step (see :func:`snr_magnitude`):

* ``magnitude_column``, ``snr_column``: the single-band magnitude and the signal-to-noise of
  the same rows. Rows whose S/N is not positive are dropped (the axis is logarithmic).
* ``depth``: the 5-sigma depth to mark; when omitted and ``estimate_depth`` is true, it is
  estimated from the data as the magnitude where the running median S/N falls through 5.
* ``estimate_depth``: estimate the depth when ``depth`` is not given.
* ``gridsize``, ``threshold``: hexagons across the magnitude range, and the occupancy up to
  which a hexagon is drawn as individual points.
* ``x_label``, ``y_label``, ``title``, ``width`` (fraction of the page frame), ``height``
  (inches), ``alt`` and ``caption``.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``kind`` (``hex``, ``point`` or ``depth``), ``x``, ``y`` (magnitude and
log10 S/N of a hexagon centre or point; for ``depth`` the magnitude and null), ``n`` (points in
the hexagon, 1 for a point), ``dx`` and ``dy`` (hexagon pitch, null otherwise).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.astro._density_marks import (
  cells_of,
  density_table,
  marks_of,
  n_points,
)
from scireport.preprocess.context import Context
from scireport.preprocess.plotting import draw_hex_bins, empty_axes, numbers, require_columns
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

_LOG_SNR_5 = float(np.log10(5.0))
_DEPTH_BINS = 20
_DEPTH_MIN_COUNT = 5


def five_sigma_depth(
  magnitude: np.ndarray,
  log_snr: np.ndarray,
  *,
  bins: int = _DEPTH_BINS,
  min_count: int = _DEPTH_MIN_COUNT,
) -> float | None:
  """Estimate the magnitude at which the running median S/N falls through 5.

  The magnitude range is cut into ``bins`` equal bins; each bin with at least ``min_count``
  points gives the median of log10 S/N at the bin centre. Going from bright to faint, the first
  step from a median of 5 or more to one below 5 is interpolated linearly in magnitude.

  Parameters
  ----------
  magnitude : numpy.ndarray
      Finite magnitudes.
  log_snr : numpy.ndarray
      Finite log10 S/N of the same rows.
  bins : int, default=20
      Number of magnitude bins.
  min_count : int, default=5
      Fewest points a bin needs to count.

  Returns
  -------
  float or None
      The depth, or None when the running median never crosses 5 (all above, all below, or too
      few populated bins).
  """
  if magnitude.size == 0 or float(magnitude.max()) == float(magnitude.min()):
    return None
  edges = np.linspace(float(magnitude.min()), float(magnitude.max()), bins + 1)
  which = np.clip(np.digitize(magnitude, edges) - 1, 0, bins - 1)
  centres: list[float] = []
  medians: list[float] = []
  for index in range(bins):
    members = log_snr[which == index]
    if members.size >= min_count:
      centres.append(float((edges[index] + edges[index + 1]) / 2.0))
      medians.append(float(np.median(members)))
  for index in range(len(centres) - 1):
    m0, s0, m1, s1 = centres[index], medians[index], centres[index + 1], medians[index + 1]
    if s0 >= _LOG_SNR_5 > s1:
      return m0 + (s0 - _LOG_SNR_5) / (s0 - s1) * (m1 - m0)
  return None


def compute_snr_magnitude(
  table: pa.Table,
  magnitude_column: str,
  snr_column: str,
  *,
  depth: float | None = None,
  estimate_depth: bool = True,
  gridsize: int = 60,
  threshold: int = 3,
) -> pa.Table:
  """Bin magnitude against log10 S/N and add the depth mark.

  Parameters
  ----------
  table : pyarrow.Table
      The catalogue.
  magnitude_column, snr_column : str
      Magnitude and signal-to-noise columns.
  depth : float or None, default=None
      The 5-sigma depth to mark.
  estimate_depth : bool, default=True
      Estimate the depth with :func:`five_sigma_depth` when ``depth`` is None.
  gridsize : int, default=60
      Hexagons across the magnitude range.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Rows of kind ``hex`` and ``point`` (x = magnitude, y = log10 S/N) and, when there is a
      depth, one row of kind ``depth``. Empty when no row has a finite magnitude and a positive
      S/N.
  """
  require_columns(table, magnitude_column, snr_column)
  x = numbers(table, magnitude_column)
  s = numbers(table, snr_column)
  keep = np.isfinite(x) & np.isfinite(s) & (s > 0)
  x, y = x[keep], np.log10(s[keep])
  marks: list[tuple[str, float, float]] = []
  if x.size:
    value = depth
    if value is None and estimate_depth:
      value = five_sigma_depth(x, y)
    if value is not None and np.isfinite(value):
      marks.append(('depth', float(value), float('nan')))
  return density_table(x, y, gridsize=gridsize, threshold=threshold, marks=marks)


def render_snr_magnitude(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = 'Magnitude',
  y_label: str = r'$\log_{10}$ S/N',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
) -> Figure:
  """Draw the density of :func:`compute_snr_magnitude`, the S/N = 5 line and the depth.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_snr_magnitude` made (or read back from a bundle's sidecar file).
  x_label, y_label, title : str
      Axis labels and title; an empty title draws nothing.
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
    cells = cells_of(data)
    if cells.num_rows == 0:
      empty_axes(ax, 'No data')
      return figure
    draw_hex_bins(ax, cells, ctx.look)
    ax.axhline(
      _LOG_SNR_5, color=ctx.look.color('annotation'), linewidth=1, linestyle='--', label='S/N = 5'
    )
    depth_x, _ = marks_of(data, 'depth')
    if depth_x.size:
      depth = float(depth_x[0])
      ax.axvline(
        depth,
        color=ctx.look.color('warning'),
        linewidth=1,
        linestyle=':',
        label=f'5σ depth {depth:.2f}',
      )
      low, high = ax.get_xlim()
      ax.set_xlim(min(low, depth), max(high, depth))
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
    ax.legend(fontsize=7)
  return figure


@preprocessor(
  'astro.snr_magnitude',
  version=1,
  inputs={
    'table': Port('table', description='Catalogue with a magnitude and a signal-to-noise column')
  },
  outputs={'figure': Port('figure', description='Density of S/N against magnitude')},
  render=render_snr_magnitude,
)
def snr_magnitude(
  ctx: Context,
  *,
  table: pa.Table,
  magnitude_column: str,
  snr_column: str,
  depth: float | None = None,
  estimate_depth: bool = True,
  gridsize: int = 60,
  threshold: int = 3,
  x_label: str = 'Magnitude',
  y_label: str = r'$\log_{10}$ S/N',
  title: str = '',
  width: float = 1.0,
  height: float = 3.4,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Signal-to-noise against magnitude, with the 5-sigma depth marked.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object, with a single-band magnitude and its signal-to-noise.
  magnitude_column : str
      Magnitude column.
  snr_column : str
      Signal-to-noise column; rows with a value of zero or less are dropped.
  depth : float or None, default=None
      The magnitude at which the S/N crosses 5, drawn as a vertical mark.
  estimate_depth : bool, default=True
      When ``depth`` is None, estimate it from the running median S/N; if that never crosses 5
      no depth is drawn.
  gridsize : int, default=60
      Hexagons across the magnitude range.
  threshold : int, default=3
      A hexagon with this many points or fewer is drawn as individual points.
  x_label, y_label : str
      Axis labels.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.4
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the columns, the point count and the depth when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_snr_magnitude(
    table,
    magnitude_column,
    snr_column,
    depth=depth,
    estimate_depth=estimate_depth,
    gridsize=gridsize,
    threshold=threshold,
  )
  figure = render_snr_magnitude(
    ctx, data, x_label=x_label, y_label=y_label, title=title, width=width, height=height
  )
  total = n_points(data)
  marked, _ = marks_of(data, 'depth')
  text = alt or (
    f'Density of log10 signal-to-noise ({snr_column}) against magnitude ({magnitude_column}) '
    f'for {total:,} objects, with the S/N = 5 line'
    + (f' and the 5-sigma depth at magnitude {float(marked[0]):.2f}.' if marked.size else '.')
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
