"""Sky-map helpers shared by ``astro.sky_density``, ``astro.footprint`` and ``astro.sky_grid``.

Private module (leading underscore): the astro package does not import it by itself, and it never
imports astropy at module level, so the registry can list the sky maps without the ``astro``
extra.

Conventions, all of them fixed here so that the three maps agree:

* **HEALPix**: ``astropy_healpix`` with the **NESTED** ordering throughout. ``order`` is the
  HEALPix level, ``nside = 2**order`` and the sky has ``12 * 4**order`` equal-area pixels, so a
  count per pixel is a density up to one constant (the pixel area).
* **Projection**: matplotlib's own ``projection='mollweide'`` axes (equal area), whose data
  coordinates are longitude and latitude in radians.
* **Orientation**: the astronomy sky-map convention, right ascension increasing to the LEFT (east
  left). The longitude drawn is ``x = -(RA wrapped to [-180, 180) degrees)`` in radians and the
  latitude is the declination. The x ticks are labelled with the right ascension in degrees
  (0 to 360) accordingly: 0 at the centre, 90 at the left of the centre, 270 at the right.
* **Rendering**: the pixel map is sampled on a regular grid of cell centres in the Mollweide
  projection plane (:data:`GRID_COLUMNS` by :data:`GRID_ROWS`, two columns per row), each centre
  is inverse-projected to longitude and latitude and looked up in the pixel table, and the
  result is drawn with ``pcolormesh`` (rasterised, in axes coordinates): no per-pixel polygons,
  deterministic output, and no moire near the poles as a longitude/latitude grid would give.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import numpy as np
import pyarrow as pa

from scireport.errors import Issue, PreprocessError
from scireport.preprocess.plotting import labels, numbers, require_columns, values_of

if TYPE_CHECKING:
  from matplotlib.axes import Axes
  from matplotlib.collections import QuadMesh

GRID_COLUMNS = 720
"""Cells of the sampling grid across the map (the projection plane is twice as wide as tall)."""
GRID_ROWS = 360
"""Cells of the sampling grid down the map."""
MAX_ORDER = 10
"""Deepest HEALPix level accepted: ``12 * 4**10`` = 12.6 million pixels, nside 1024."""
SKY_AREA_DEG2 = 4.0 * 180.0**2 / np.pi
"""Whole sky in square degrees (4 pi steradians), about 41,253."""
MOLLWEIDE: dict[str, Any] = {'projection': 'mollweide'}
"""The ``subplot_kw`` of a sky-map axes."""

_TICKS_DEG = np.arange(-150, 151, 30)


@dataclass(frozen=True)
class Tally:
  """Occupied HEALPix pixels (NESTED) per group, sorted by group then pixel.

  Parameters
  ----------
  order : int
      HEALPix level the indices belong to.
  group : list of str
      The group of each row (the empty string when the table has no group column).
  ipix : numpy.ndarray
      Nested pixel index, int64, one per row.
  count : numpy.ndarray
      Objects (or summed weights) in the pixel, float64, one per row.
  """

  order: int
  group: list[str]
  ipix: np.ndarray
  count: np.ndarray


def check_order(order: int) -> int:
  """Validate a HEALPix level.

  Parameters
  ----------
  order : int
      The level.

  Returns
  -------
  int
      ``order``.

  Raises
  ------
  PreprocessError
      With ``E602`` when ``order`` is not between 0 and :data:`MAX_ORDER`.
  """
  if not 0 <= order <= MAX_ORDER:
    raise PreprocessError(
      [
        Issue(
          'E602',
          f'order must be between 0 and {MAX_ORDER}',
          expected=f'an integer from 0 to {MAX_ORDER}',
          found=str(order),
        )
      ]
    )
  return order


def pixel_area_deg2(order: int) -> float:
  """Return the area of one HEALPix pixel in square degrees.

  Parameters
  ----------
  order : int
      HEALPix level.

  Returns
  -------
  float
      ``41252.96 / (12 * 4**order)``, computed by ``astropy_healpix``.
  """
  import astropy.units as u
  from astropy_healpix import level_to_nside, nside_to_pixel_area

  return float(nside_to_pixel_area(level_to_nside(order)).to_value(u.deg**2))


def tally(
  table: pa.Table,
  *,
  order: int,
  ra_column: str = 'ra',
  dec_column: str = 'dec',
  ipix_column: str | None = None,
  counts_column: str | None = None,
  group_column: str | None = None,
  min_count: float = 1.0,
) -> Tally:
  """Count objects per HEALPix pixel (NESTED), per group.

  Two input forms: points (``ra_column`` and ``dec_column`` in degrees, binned at ``order``) or,
  when ``ipix_column`` is given, pixels already counted at ``order``. Rows with a null or
  non-finite position or index, or a non-positive weight, are skipped; rows of one pixel are
  summed.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  order : int
      HEALPix level of the bins (points) or of the given indices (pixels).
  ra_column, dec_column : str, default='ra', 'dec'
      Position columns in degrees; ignored when ``ipix_column`` is given.
  ipix_column : str or None, default=None
      Column of nested pixel indices, making the table a tally.
  counts_column : str or None, default=None
      Weight of each row (the count of a pixel row); one per row when None.
  group_column : str or None, default=None
      Column whose distinct values are tallied separately.
  min_count : float, default=1.0
      Pixels with a smaller total are dropped.

  Returns
  -------
  Tally
      The occupied pixels, sorted by group and pixel.

  Raises
  ------
  PreprocessError
      With ``E603`` for a missing or non-numeric column or an index outside the sky, and
      ``E602`` for an invalid ``order``.
  """
  check_order(order)
  npix = 12 * 4**order
  require_columns(table, counts_column, group_column)
  if ipix_column is not None:
    require_columns(table, ipix_column)
    raw = numbers(table, ipix_column)
    ok = np.isfinite(raw)
    bad = ok & ((raw < 0) | (raw >= npix) | (raw != np.floor(raw)))
    if bad.any():
      raise PreprocessError(
        [
          Issue(
            'E603',
            f'{int(bad.sum())} values of {ipix_column!r} are not nested HEALPix indices at '
            f'order {order}',
            expected=f'integers from 0 to {npix - 1}',
            found=str(float(raw[bad][0])),
            hint='Check the order, and that the indices are NESTED, not RING.',
          )
        ]
      )
    pixels = np.where(ok, raw, 0).astype(np.int64)
  else:
    require_columns(table, ra_column, dec_column)
    ra, dec = numbers(table, ra_column), numbers(table, dec_column)
    ok = np.isfinite(ra) & np.isfinite(dec) & (np.abs(np.where(np.isfinite(dec), dec, 0)) <= 90)
    pixels = _points_to_pixels(ra[ok], dec[ok], order)
    pixels = _scatter(ok, pixels)
  weights = numbers(table, counts_column) if counts_column else np.ones(table.num_rows)
  keep = ok & (np.nan_to_num(weights, nan=0.0) > 0)
  names = np.asarray(labels(table, group_column) if group_column else [''] * table.num_rows)
  if not keep.any():
    return Tally(order, [], np.empty(0, np.int64), np.empty(0))
  groups, code = np.unique(names[keep], return_inverse=True)
  key = np.asarray(code).reshape(-1).astype(np.int64) * npix + pixels[keep]
  unique, inverse = np.unique(key, return_inverse=True)
  totals = np.bincount(np.asarray(inverse).reshape(-1), weights=weights[keep])
  big = totals >= min_count
  return Tally(
    order,
    [str(name) for name in groups[unique[big] // npix]],
    (unique[big] % npix).astype(np.int64),
    totals[big].astype(float),
  )


def tally_table(found: Tally, *, groups: bool = True, area: bool = False) -> pa.Table:
  """Make the sidecar table of a tally.

  Parameters
  ----------
  found : Tally
      The tally.
  groups : bool, default=True
      Include the ``group`` column.
  area : bool, default=False
      Include the constant ``area_deg2`` column (pixel area in square degrees).

  Returns
  -------
  pyarrow.Table
      Columns ``[group,] ipix, count, order[, area_deg2]``; typed even when empty.
  """
  columns: dict[str, pa.Array] = {}
  if groups:
    columns['group'] = pa.array(found.group, pa.string())
  columns['ipix'] = pa.array(found.ipix, pa.int64())
  columns['count'] = pa.array(found.count, pa.float64())
  columns['order'] = pa.array(np.full(found.ipix.size, found.order), pa.int64())
  if area:
    area_value = pixel_area_deg2(found.order) if found.ipix.size else float('nan')
    columns['area_deg2'] = pa.array(np.full(found.ipix.size, area_value), pa.float64())
  return pa.table(columns)


def order_of(data: pa.Table) -> int:
  """Read the HEALPix level back from a sidecar table (its constant ``order`` column).

  Parameters
  ----------
  data : pyarrow.Table
      A table made by :func:`tally_table`, not empty.

  Returns
  -------
  int
      The level.
  """
  return int(values_of(data, 'order')[0])


@lru_cache(maxsize=4)
def _cell_pixels(order: int, columns: int, rows: int) -> np.ndarray:
  """Nested HEALPix index under every cell centre of the sampling grid; -1 off the ellipse.

  The grid is regular in the Mollweide projection plane, ``u`` and ``v`` running over [-1, 1]
  across the ellipse. With ``theta = arcsin(v)`` the inverse projection is
  ``lat = arcsin((2 theta + sin 2 theta) / pi)`` and ``lon = pi u / cos(theta)``, valid when
  ``|u| <= cos(theta)``. The plotted longitude is ``-RA``, so ``RA = -lon`` modulo 2 pi.
  """
  import astropy.units as u
  from astropy_healpix import level_to_nside, lonlat_to_healpix

  u_axis = -1.0 + (np.arange(columns) + 0.5) * (2.0 / columns)
  v_axis = -1.0 + (np.arange(rows) + 0.5) * (2.0 / rows)
  grid_u, grid_v = np.meshgrid(u_axis, v_axis)
  theta = np.arcsin(grid_v)
  inside = np.abs(grid_u) <= np.cos(theta)
  lat = np.arcsin(np.clip((2.0 * theta + np.sin(2.0 * theta)) / np.pi, -1.0, 1.0))
  lon = np.where(inside, np.pi * grid_u / np.where(inside, np.cos(theta), 1.0), 0.0)
  ra = np.mod(-lon, 2.0 * np.pi)
  pixels = lonlat_to_healpix(
    ra.ravel() * u.rad, lat.ravel() * u.rad, level_to_nside(order), order='nested'
  )
  cells = np.where(inside, np.asarray(pixels, dtype=np.int64).reshape(rows, columns), -1)
  cells.setflags(write=False)
  return cells


def pixel_grid(
  ipix: np.ndarray,
  values: np.ndarray,
  order: int,
  *,
  columns: int = GRID_COLUMNS,
  rows: int = GRID_ROWS,
) -> np.ndarray:
  """Sample a pixel map on the grid of cell centres in the projection plane.

  Parameters
  ----------
  ipix : numpy.ndarray
      Occupied nested indices at ``order``, unique.
  values : numpy.ndarray
      One value per pixel.
  order : int
      HEALPix level.
  columns, rows : int
      The size of the sampling grid.

  Returns
  -------
  numpy.ndarray
      Float array ``(rows, columns)``, row 0 at the south; NaN where no pixel has data and
      outside the ellipse.
  """
  cells = _cell_pixels(order, columns, rows)
  if ipix.size == 0:
    return np.full(cells.shape, np.nan)
  sort = np.argsort(ipix, kind='stable')
  sorted_ipix, sorted_values = ipix[sort], np.asarray(values, dtype=float)[sort]
  at = np.clip(np.searchsorted(sorted_ipix, cells), 0, sorted_ipix.size - 1)
  hit = sorted_ipix[at] == cells
  return np.where(hit, sorted_values[at], np.nan)


def draw_grid(
  ax: Axes,
  grid: np.ndarray,
  *,
  cmap: Any,
  norm: Any = None,
  alpha: float = 1.0,
  zorder: float = 1.0,
) -> QuadMesh:
  """Draw a sampled pixel map on a Mollweide axes; NaN cells stay blank.

  The mesh is placed in axes coordinates: the ellipse fills the axes box, so the projection-plane
  grid of :func:`pixel_grid` maps onto it directly.

  Parameters
  ----------
  ax : matplotlib.axes.Axes
      A Mollweide axes.
  grid : numpy.ndarray
      The array :func:`pixel_grid` made.
  cmap : str or matplotlib.colors.Colormap
      Colour map.
  norm : matplotlib.colors.Normalize or None, default=None
      Colour scale.
  alpha : float, default=1.0
      Opacity.
  zorder : float, default=1.0
      Drawing order.

  Returns
  -------
  matplotlib.collections.QuadMesh
      The mesh, for a colour bar.
  """
  rows, columns = grid.shape
  return ax.pcolormesh(
    np.linspace(0.0, 1.0, columns + 1),
    np.linspace(0.0, 1.0, rows + 1),
    np.ma.masked_invalid(grid),
    cmap=cmap,
    norm=norm,
    alpha=alpha,
    zorder=zorder,
    shading='flat',
    transform=ax.transAxes,
    rasterized=True,
    linewidth=0,
    antialiased=False,
  )


def style_sky_axes(
  ax: Axes, *, grid_color: str, tick_labels: bool = True, size: float = 6.0
) -> None:
  """Add the graticule and the right-ascension labels of the east-left convention.

  Parameters
  ----------
  ax : matplotlib.axes.Axes
      A Mollweide axes.
  grid_color : str
      Colour of the graticule.
  tick_labels : bool, default=True
      Label the meridians with right ascension (degrees) and the parallels with declination;
      small panels pass False and keep only the graticule.
  size : float, default=6.0
      Tick label size in points.
  """
  ax.set_xticks(np.radians(_TICKS_DEG))
  ax.set_yticks(np.radians(np.arange(-60, 61, 30)))
  ax.grid(True, color=grid_color, linewidth=0.4, alpha=0.45)
  ax.set_axisbelow(False)
  if tick_labels:
    ax.set_xticklabels([f'{int(-tick) % 360}\N{DEGREE SIGN}' for tick in _TICKS_DEG])
    ax.tick_params(labelsize=size)
    for label in ax.get_xticklabels():
      label.set_bbox({'facecolor': 'white', 'alpha': 0.6, 'edgecolor': 'none', 'pad': 0.6})
  else:
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.tick_params(length=0)


def _points_to_pixels(ra: np.ndarray, dec: np.ndarray, order: int) -> np.ndarray:
  """Bin positions in degrees at a HEALPix level (nested)."""
  import astropy.units as u
  from astropy_healpix import level_to_nside, lonlat_to_healpix

  if ra.size == 0:
    return np.empty(0, np.int64)
  return np.asarray(
    lonlat_to_healpix(ra * u.deg, dec * u.deg, level_to_nside(order), order='nested'),
    dtype=np.int64,
  )


def _scatter(mask: np.ndarray, values: np.ndarray) -> np.ndarray:
  """Spread ``values`` (one per True of ``mask``) back to the full row length, zero elsewhere."""
  out = np.zeros(mask.size, np.int64)
  out[mask] = values
  return out
