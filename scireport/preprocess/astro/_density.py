"""Shared by the density diagrams ``astro.color_color`` and ``astro.color_magnitude``.

Both draw the hybrid density of the MOSAICS report engine: hexagons for the crowded regions and
the individual points of the sparse ones. This module holds the part they have in common, the
sidecar table (one row per hexagon or sparse point) and the drawing of it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.context import Context
from scireport.preprocess.plotting import draw_hex_bins, empty_axes, hex_bins, values_of

if TYPE_CHECKING:
  from matplotlib.figure import Figure

SIDECAR_SCHEMA = pa.schema(
  [
    ('kind', pa.string()),
    ('x', pa.float64()),
    ('y', pa.float64()),
    ('n', pa.float64()),
    ('dx', pa.float64()),
    ('dy', pa.float64()),
  ]
)


def density_table(x: np.ndarray, y: np.ndarray, gridsize: int, threshold: int) -> pa.Table:
  """Bin two aligned columns into hexagons and sparse points.

  Parameters
  ----------
  x, y : numpy.ndarray
      Aligned arrays; pairs that are not both finite are dropped.
  gridsize : int
      Hexagons across the x range.
  threshold : int
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Columns ``kind`` (``'hex'`` or ``'point'``), ``x``, ``y``, ``n``, ``dx`` and ``dy`` (see
      :func:`~scireport.preprocess.plotting.hex_bins`), hexagons first. Zero rows when nothing is
      finite.
  """
  cells = hex_bins(x, y, gridsize, threshold)
  return pa.table(
    {
      'kind': pa.array(list(cells['kind']), pa.string()),
      'x': pa.array(np.asarray(cells['x'], dtype=float), pa.float64()),
      'y': pa.array(np.asarray(cells['y'], dtype=float), pa.float64()),
      'n': pa.array(np.asarray(cells['n'], dtype=float), pa.float64()),
      'dx': pa.array(np.asarray(cells['dx'], dtype=float), pa.float64()),
      'dy': pa.array(np.asarray(cells['dy'], dtype=float), pa.float64()),
    },
    schema=SIDECAR_SCHEMA,
  )


def density_total(data: pa.Table) -> int:
  """Count the points a density table stands for.

  Parameters
  ----------
  data : pyarrow.Table
      The table :func:`density_table` made.

  Returns
  -------
  int
      The sum of ``n``: points inside hexagons plus the sparse points.
  """
  return int(np.nansum(values_of(data, 'n'))) if data.num_rows else 0


def draw_density(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str,
  y_label: str,
  title: str,
  width: float,
  height: float,
  invert_y: bool = False,
) -> Figure:
  """Draw the hybrid density of :func:`density_table` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`density_table` made, or read back from a sidecar file.
  x_label, y_label, title : str
      Axis labels and title; empty strings draw nothing.
  width : float
      Width as a fraction of the page frame.
  height : float
      Height in inches.
  invert_y : bool, default=False
      Put the smallest y at the top, the convention for a magnitude axis.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure; a placeholder when ``data`` has no rows.
  """
  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height)
    if data.num_rows == 0:
      empty_axes(ax, 'No data')
      return figure
    draw_hex_bins(ax, data, ctx.look)
    if invert_y:
      ax.invert_yaxis()
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    if title:
      ax.set_title(title)
  return figure
