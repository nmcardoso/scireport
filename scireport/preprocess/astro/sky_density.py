"""``astro.sky_density``: a Mollweide sky map of source density on a HEALPix grid.

Ported from the MOSAICS panel ``plot_sky_density``. HEALPix pixels have equal area, so the count in
a pixel is a density up to one constant; the map is stored as counts and converted to objects per
square degree when drawn. A run over hundreds of millions of rows never carries the catalogue into
a report, only the pixel counts, so the pre-processor takes either form: a table of positions, or
a table of pixels already counted. The sky is binned with ``astropy_healpix`` in the NESTED
ordering. The map is matplotlib's own Mollweide projection with right ascension increasing to the
left (east left) and the meridians labelled with right ascension in degrees; see
:mod:`scireport.preprocess.astro._sky` for the convention.

Parameters of the step (see :func:`sky_density`):

* ``order``: HEALPix level of the bins (default 7: 196,608 pixels of about 0.21 square degrees).
* ``ra_column``, ``dec_column``: positions in degrees (the point form).
* ``ipix_column``, ``counts_column``: nested pixel indices and their counts (the tally form; the
  indices are then taken to be at ``order``). ``counts_column`` is optional and weights the rows.
* ``log``: logarithmic colour scale. ``per_area``: objects per square degree (else per pixel).
* ``min_count``: pixels with fewer objects are left blank. ``colorbar_label`` and ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``ipix`` (nested pixel index), ``count``, ``order`` and ``area_deg2`` (the last
two constant: the level and the area of one pixel in square degrees).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.preprocess.astro._sky import (
  MOLLWEIDE,
  draw_grid,
  order_of,
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


def compute_sky_density(
  table: pa.Table,
  *,
  order: int = 7,
  ra_column: str = 'ra',
  dec_column: str = 'dec',
  ipix_column: str | None = None,
  counts_column: str | None = None,
  min_count: float = 1.0,
) -> pa.Table:
  """Count objects per HEALPix pixel (NESTED).

  Parameters
  ----------
  table : pyarrow.Table
      Positions, or one row per pixel when ``ipix_column`` is given.
  order : int, default=7
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
      Columns ``ipix``, ``count``, ``order`` and ``area_deg2``, sorted by ``ipix``.
  """
  found = tally(
    table,
    order=order,
    ra_column=ra_column,
    dec_column=dec_column,
    ipix_column=ipix_column,
    counts_column=counts_column,
    min_count=min_count,
  )
  return tally_table(found, groups=False, area=True)


def render_sky_density(
  ctx: Context,
  data: pa.Table,
  *,
  log: bool = True,
  per_area: bool = True,
  colorbar_label: str | None = None,
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
) -> Figure:
  """Draw the pixel counts of :func:`compute_sky_density` as a Mollweide map.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_sky_density` made (or read back from a bundle's sidecar file).
  log : bool, default=True
      Logarithmic colour scale, from the smallest positive value to the largest.
  per_area : bool, default=True
      Objects per square degree (the count divided by the pixel area) rather than per pixel.
  colorbar_label : str or None, default=None
      Colour bar label; ``'objects / deg$^2$'`` or ``'objects / pixel'`` when None.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.6
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  from matplotlib.colors import LogNorm, Normalize

  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height, subplot_kw=MOLLWEIDE)
    ipix, count = values_of(data, 'ipix'), values_of(data, 'count')
    if ipix.size == 0 or not np.nansum(count) > 0:
      empty_axes(ax, 'No positions to map')
      return figure
    values = count / float(values_of(data, 'area_deg2')[0]) if per_area else count
    positive = values[values > 0]
    low, high = float(positive.min()), float(positive.max())
    norm = LogNorm(vmin=low, vmax=max(high, low * 10.0)) if log else Normalize(vmin=0.0, vmax=high)
    grid = pixel_grid(ipix.astype(np.int64), values, order_of(data))
    mesh = draw_grid(ax, grid, cmap=ctx.look.sequential, norm=norm)
    style_sky_axes(ax, grid_color=ctx.look.color('annotation'))
    default = 'objects / deg$^2$' if per_area else 'objects / pixel'
    figure.colorbar(mesh, ax=ax, label=colorbar_label or default, shrink=0.7, pad=0.03)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'astro.sky_density',
  version=1,
  inputs={'table': Port('table', description='Positions in degrees, or counts per HEALPix pixel')},
  outputs={'figure': Port('figure', description='The Mollweide density map')},
  render=render_sky_density,
  requires='astro',
)
def sky_density(
  ctx: Context,
  *,
  table: pa.Table,
  order: int = 7,
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
  height: float = 3.6,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Mollweide sky map of source density on a HEALPix grid.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object (``ra_column``, ``dec_column``), or one row per pixel when
      ``ipix_column`` is given.
  order : int, default=7
      HEALPix level of the bins, or of the indices of a tally; 0 to 10. The sky has
      ``12 * 4**order`` pixels, nested ordering.
  ra_column, dec_column : str, default='ra', 'dec'
      Right ascension and declination in degrees; ignored when ``ipix_column`` is given.
  ipix_column : str or None, default=None
      Column of nested pixel indices at ``order``; makes the table a tally.
  counts_column : str or None, default=None
      Column with the count (weight) of each row; one per row when None.
  log : bool, default=True
      Logarithmic colour scale.
  per_area : bool, default=True
      Colour by objects per square degree instead of objects per pixel.
  colorbar_label : str or None, default=None
      Colour bar label; the unit when None.
  min_count : float, default=1.0
      Pixels with fewer objects stay blank.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.6
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the pixel and object counts when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_sky_density(
    table,
    order=order,
    ra_column=ra_column,
    dec_column=dec_column,
    ipix_column=ipix_column,
    counts_column=counts_column,
    min_count=min_count,
  )
  figure = render_sky_density(
    ctx,
    data,
    log=log,
    per_area=per_area,
    colorbar_label=colorbar_label,
    title=title,
    width=width,
    height=height,
  )
  total = float(np.nansum(data.column('count').to_numpy())) if data.num_rows else 0.0
  text = alt or (
    f'Mollweide sky map of source density at HEALPix order {order} (nested): '
    f'{data.num_rows:,} occupied pixels holding {total:,.0f} objects.'
    if data.num_rows
    else 'Mollweide sky map of source density: no positions to map.'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
