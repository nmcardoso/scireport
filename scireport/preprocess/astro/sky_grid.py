"""``astro.sky_grid``: small multiples of sky density, one Mollweide panel per group.

New in scireport (the MOSAICS report drew one footprint at a time). Built on the pieces of
``astro.sky_density``: each group (for example each source catalogue of a dataset) gets a small
Mollweide panel of its object density at a coarse HEALPix level, all panels sharing one colour
scale and one colour bar, so the panels can be compared by eye. Positions are binned with
``astropy_healpix`` in the NESTED ordering. The panels are matplotlib's own Mollweide projection
with right ascension increasing to the left (east left); they keep the graticule but not the tick
labels, which would not fit. See :mod:`scireport.preprocess.astro._sky` for the convention.

Parameters of the step (see :func:`sky_grid`):

* ``group_column``: one panel per distinct value, in sorted order (at most 30).
* ``order``: HEALPix level of the bins (default 5: 12,288 pixels of about 3.4 square degrees).
* ``ncols``: panels per row (default 3).
* ``ra_column``, ``dec_column``: positions in degrees (the point form).
* ``ipix_column``, ``counts_column``: nested pixel indices at ``order`` and their counts (the
  tally form). ``counts_column`` is optional and weights the rows.
* ``log``: logarithmic shared colour scale. ``per_area``: objects per square degree.
* ``min_count``: pixels with fewer objects are left blank. ``colorbar_label`` and ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches; made from the number of rows
  when omitted).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``group``, ``ipix`` (nested pixel index), ``count`` (objects in it) and ``order``
(constant: the HEALPix level).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.errors import Issue, PreprocessError
from scireport.preprocess.astro._sky import (
  MOLLWEIDE,
  draw_grid,
  order_of,
  pixel_area_deg2,
  pixel_grid,
  style_sky_axes,
  tally,
  tally_table,
)
from scireport.preprocess.context import Context
from scireport.preprocess.plotting import empty_axes, values_of
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure

MAX_PANELS = 30
_FRAME_INCHES = 6.5
"""Rough width of the page frame, only to choose a default height from the panel shape."""


def compute_sky_grid(
  table: pa.Table,
  group_column: str,
  *,
  order: int = 5,
  ra_column: str = 'ra',
  dec_column: str = 'dec',
  ipix_column: str | None = None,
  counts_column: str | None = None,
  min_count: float = 1.0,
) -> pa.Table:
  """Count objects per HEALPix pixel (NESTED) for every group.

  Parameters
  ----------
  table : pyarrow.Table
      Positions, or one row per pixel when ``ipix_column`` is given.
  group_column : str
      Column whose distinct values become panels.
  order : int, default=5
      HEALPix level of the bins (points) or of the indices (pixels); 0 to 10.
  ra_column, dec_column : str, default='ra', 'dec'
      Positions in degrees; ignored when ``ipix_column`` is given.
  ipix_column : str or None, default=None
      Column of nested pixel indices; makes the table a tally.
  counts_column : str or None, default=None
      Weight (count) of each row; one per row when None.
  min_count : float, default=1.0
      Pixels with a smaller total are dropped.

  Returns
  -------
  pyarrow.Table
      Columns ``group``, ``ipix``, ``count`` and ``order``, sorted by group then pixel.

  Raises
  ------
  PreprocessError
      With ``E602`` when there are more than :data:`MAX_PANELS` groups.
  """
  found = tally(
    table,
    order=order,
    ra_column=ra_column,
    dec_column=dec_column,
    ipix_column=ipix_column,
    counts_column=counts_column,
    group_column=group_column,
    min_count=min_count,
  )
  panels = len(set(found.group))
  if panels > MAX_PANELS:
    raise PreprocessError(
      [
        Issue(
          'E602',
          f'{panels} groups make too many panels',
          expected=f'at most {MAX_PANELS} values in {group_column!r}',
          found=str(panels),
          hint='Keep the groups that matter (filter the table) or merge the small ones.',
        )
      ]
    )
  return tally_table(found)


def default_height(groups: int, ncols: int, width: float) -> float:
  """Choose a figure height from the shape of the grid.

  Parameters
  ----------
  groups : int
      Number of panels.
  ncols : int
      Panels per row.
  width : float
      Figure width as a fraction of the page frame.

  Returns
  -------
  float
      Inches: a 2:1 Mollweide panel plus its title per row, and room for the colour bar.
  """
  rows = max(math.ceil(max(groups, 1) / max(ncols, 1)), 1)
  return rows * (0.5 * _FRAME_INCHES * min(width, 1.0) / max(ncols, 1) + 0.3) + 0.3


def render_sky_grid(
  ctx: Context,
  data: pa.Table,
  *,
  ncols: int = 3,
  log: bool = True,
  per_area: bool = True,
  colorbar_label: str | None = None,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
) -> Figure:
  """Draw one Mollweide panel per group of :func:`compute_sky_grid`, with one colour scale.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_sky_grid` made (or read back from a bundle's sidecar file).
  ncols : int, default=3
      Panels per row.
  log : bool, default=True
      Logarithmic shared colour scale, from the smallest positive value to the largest of all
      groups.
  per_area : bool, default=True
      Objects per square degree (the count divided by the pixel area) rather than per pixel.
  colorbar_label : str or None, default=None
      Colour bar label; ``'objects / deg$^2$'`` or ``'objects / pixel'`` when None.
  title : str, default=''
      Title of the whole figure; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float or None, default=None
      Height in inches; :func:`default_height` when None.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  from matplotlib.colors import LogNorm, Normalize

  names = data.column('group').to_pylist()
  groups = sorted(set(names))
  columns = max(1, min(ncols, len(groups))) if groups else 1
  rows = max(1, math.ceil(len(groups) / columns))
  tall = default_height(len(groups), columns, width) if height is None else height
  with ctx.mplstyle():
    figure, axes = ctx.figure(width, tall, rows, columns, subplot_kw=MOLLWEIDE)
    panels = np.atleast_1d(axes).ravel()
    if not groups or not np.nansum(values_of(data, 'count')) > 0:
      for spare in panels[1:]:
        spare.remove()
      empty_axes(panels[0], 'No positions to map')
      return figure
    order = order_of(data)
    ipix, count = values_of(data, 'ipix').astype(np.int64), values_of(data, 'count')
    values = count / pixel_area_deg2(order) if per_area else count
    positive = values[values > 0]
    low, high = float(positive.min()), float(positive.max())
    norm = LogNorm(vmin=low, vmax=max(high, low * 10.0)) if log else Normalize(vmin=0.0, vmax=high)
    members = np.asarray(names, dtype=object)
    meshes = []
    for panel, group in zip(panels, groups, strict=False):
      chosen = members == group
      grid = pixel_grid(ipix[chosen], values[chosen], order)
      meshes.append(draw_grid(panel, grid, cmap=ctx.look.sequential, norm=norm))
      style_sky_axes(panel, grid_color=ctx.look.color('annotation'), tick_labels=False)
      panel.set_title(group or '(no label)', fontsize=7, pad=3)
    for spare in panels[len(groups) :]:
      spare.remove()
    default = 'objects / deg$^2$' if per_area else 'objects / pixel'
    figure.colorbar(
      meshes[-1],
      ax=list(panels[: len(groups)]),
      label=colorbar_label or default,
      shrink=0.7,
      pad=0.03,
    )
    if title:
      figure.suptitle(title)
  return figure


@preprocessor(
  'astro.sky_grid',
  version=1,
  inputs={'table': Port('table', description='Positions in degrees, or counts per HEALPix pixel')},
  outputs={'figure': Port('figure', description='One Mollweide density map per group')},
  render=render_sky_grid,
  requires='astro',
)
def sky_grid(
  ctx: Context,
  *,
  table: pa.Table,
  group_column: str,
  order: int = 5,
  ncols: int = 3,
  ra_column: str = 'ra',
  dec_column: str = 'dec',
  ipix_column: str | None = None,
  counts_column: str | None = None,
  log: bool = True,
  per_area: bool = True,
  colorbar_label: str | None = None,
  min_count: float = 1.0,
  title: str = '',
  width: float = 1.0,
  height: float | None = None,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Small multiples: one Mollweide sky-density panel per group, on one shared colour scale.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object (``ra_column``, ``dec_column``), or one row per pixel when
      ``ipix_column`` is given.
  group_column : str
      Column whose distinct values become panels (at most 30), in sorted order.
  order : int, default=5
      HEALPix level of the bins, or of the indices of a tally; 0 to 10; nested ordering.
  ncols : int, default=3
      Panels per row; at least 1.
  ra_column, dec_column : str, default='ra', 'dec'
      Right ascension and declination in degrees; ignored when ``ipix_column`` is given.
  ipix_column : str or None, default=None
      Column of nested pixel indices at ``order``; makes the table a tally.
  counts_column : str or None, default=None
      Column with the count (weight) of each row; one per row when None.
  log : bool, default=True
      Logarithmic shared colour scale.
  per_area : bool, default=True
      Colour by objects per square degree instead of objects per pixel.
  colorbar_label : str or None, default=None
      Colour bar label; the unit when None.
  min_count : float, default=1.0
      Pixels with fewer objects stay blank.
  title : str, default=''
      Title of the whole figure; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float or None, default=None
      Figure height in inches; made from the number of rows when None.
  alt : str or None, default=None
      Alternative text; built from the group names and object counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.

  Raises
  ------
  PreprocessError
      With ``E602`` when ``ncols`` is below 1 or there are more than 30 groups.
  """
  if ncols < 1:
    raise PreprocessError(
      [Issue('E602', 'ncols must be at least 1', expected='an integer >= 1', found=str(ncols))]
    )
  data = compute_sky_grid(
    table,
    group_column,
    order=order,
    ra_column=ra_column,
    dec_column=dec_column,
    ipix_column=ipix_column,
    counts_column=counts_column,
    min_count=min_count,
  )
  figure = render_sky_grid(
    ctx,
    data,
    ncols=ncols,
    log=log,
    per_area=per_area,
    colorbar_label=colorbar_label,
    title=title,
    width=width,
    height=height,
  )
  text = alt or _describe(data, group_column, order)
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _describe(data: pa.Table, group_column: str, order: int) -> str:
  """Factual alt text: the panels and the objects in each, from the sidecar table."""
  if data.num_rows == 0:
    return f'Small multiples of Mollweide sky maps by {group_column}: no positions to map.'
  names = data.column('group').to_pylist()
  counts = values_of(data, 'count')
  parts = [
    f'{group or "(no label)"}: {counts[[n == group for n in names]].sum():,.0f} objects'
    for group in sorted(set(names))
  ]
  return (
    f'Small multiples of Mollweide sky maps by {group_column} at HEALPix order {order} '
    f'(nested), one shared colour scale. ' + '; '.join(parts) + '.'
  )
