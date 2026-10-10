"""``astro.footprint``: the sky a catalogue covers, as filled HEALPix pixels on a Mollweide map.

Ported from the MOSAICS panel ``plot_footprint``, the complement of ``astro.sky_density``: a
density map colours a quantity per pixel, a footprint has none, so every pixel that holds at
least ``min_count`` objects is drawn in one fill and the rest of the sky stays blank. That is
what lets a reader see how much of a target's sky a catalogue does and does not cover. With
``group_column`` several catalogues (surveys) are overlaid, one colour each, with a legend.
Positions are binned at a coarse level (default 5: 12,288 pixels of about 3.4 square degrees)
with ``astropy_healpix`` in the NESTED ordering. The map is matplotlib's own Mollweide projection
with right ascension increasing to the left (east left) and the meridians labelled with right
ascension in degrees; see :mod:`scireport.preprocess.astro._sky` for the convention.

Parameters of the step (see :func:`footprint`):

* ``order``: HEALPix level of the coverage mask (default 5).
* ``ra_column``, ``dec_column``: positions in degrees (the point form).
* ``ipix_column``, ``counts_column``: nested pixel indices at ``order`` and their counts (the
  tally form). ``counts_column`` is optional and weights the rows.
* ``group_column``: one colour and one legend entry per distinct value (at most 12).
* ``min_count``: a pixel is covered when it holds at least this many objects (default 1).
* ``title``, ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``group`` (empty without a group column), ``ipix`` (nested pixel index of a
covered pixel), ``count`` (objects in it) and ``order`` (constant: the HEALPix level).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa

from scireport.errors import Issue, PreprocessError
from scireport.preprocess.astro._sky import (
  MOLLWEIDE,
  SKY_AREA_DEG2,
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

_MAX_GROUPS = 12


def compute_footprint(
  table: pa.Table,
  *,
  order: int = 5,
  ra_column: str = 'ra',
  dec_column: str = 'dec',
  ipix_column: str | None = None,
  counts_column: str | None = None,
  group_column: str | None = None,
  min_count: float = 1.0,
) -> pa.Table:
  """Find the covered HEALPix pixels (NESTED), per group.

  Parameters
  ----------
  table : pyarrow.Table
      Positions, or one row per pixel when ``ipix_column`` is given.
  order : int, default=5
      HEALPix level of the mask (points) or of the indices (pixels); 0 to 10.
  ra_column, dec_column : str, default='ra', 'dec'
      Positions in degrees; ignored when ``ipix_column`` is given.
  ipix_column : str or None, default=None
      Column of nested pixel indices; makes the table a tally.
  counts_column : str or None, default=None
      Weight (count) of each row; one per row when None.
  group_column : str or None, default=None
      Column whose distinct values are separate footprints.
  min_count : float, default=1.0
      A pixel is covered when its total is at least this.

  Returns
  -------
  pyarrow.Table
      Columns ``group``, ``ipix``, ``count`` and ``order``, sorted by group then pixel.

  Raises
  ------
  PreprocessError
      With ``E602`` when there are more than 12 groups (use ``astro.sky_grid`` instead).
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
  groups = sorted(set(found.group))
  if len(groups) > _MAX_GROUPS:
    raise PreprocessError(
      [
        Issue(
          'E602',
          f'{len(groups)} groups cannot be told apart on one map',
          expected=f'at most {_MAX_GROUPS} values in {group_column!r}',
          found=str(len(groups)),
          hint='Use astro.sky_grid for one panel per group.',
        )
      ]
    )
  return tally_table(found)


def render_footprint(
  ctx: Context,
  data: pa.Table,
  *,
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
) -> Figure:
  """Draw the covered pixels of :func:`compute_footprint`, one colour per group.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_footprint` made (or read back from a bundle's sidecar file).
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
  from matplotlib.colors import ListedColormap
  from matplotlib.patches import Patch

  with ctx.mplstyle():
    figure, ax = ctx.figure(width, height, subplot_kw=MOLLWEIDE)
    if data.num_rows == 0:
      empty_axes(ax, 'No footprint to draw')
      return figure
    order = order_of(data)
    names = np.asarray(data.column('group').to_pylist(), dtype=object)
    ipix = values_of(data, 'ipix').astype(np.int64)
    groups = sorted(set(names.tolist()))
    labelled = groups != ['']
    single = ctx.look.color('success')
    handles = []
    for index, group in enumerate(groups):
      colour = ctx.look.series(index) if labelled else single
      covered = names == group
      grid = pixel_grid(ipix[covered], np.ones(int(covered.sum())), order)
      opacity = 0.7 if len(groups) > 1 else 1.0
      draw_grid(ax, grid, cmap=ListedColormap([colour]), alpha=opacity, zorder=1.0 + index / 100.0)
      handles.append(
        Patch(facecolor=colour, alpha=opacity, edgecolor='none', label=group or 'footprint')
      )
    style_sky_axes(ax, grid_color=ctx.look.color('annotation'))
    if labelled:
      ax.legend(handles=handles, loc='lower left', fontsize=7, frameon=False)
    if title:
      ax.set_title(title)
  return figure


@preprocessor(
  'astro.footprint',
  version=1,
  inputs={'table': Port('table', description='Positions in degrees, or counts per HEALPix pixel')},
  outputs={'figure': Port('figure', description='The Mollweide coverage map')},
  render=render_footprint,
  requires='astro',
)
def footprint(
  ctx: Context,
  *,
  table: pa.Table,
  order: int = 5,
  ra_column: str = 'ra',
  dec_column: str = 'dec',
  ipix_column: str | None = None,
  counts_column: str | None = None,
  group_column: str | None = None,
  min_count: float = 1.0,
  title: str = '',
  width: float = 1.0,
  height: float = 3.2,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Coverage footprint of one or several catalogues on a Mollweide sky map.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object (``ra_column``, ``dec_column``), or one row per pixel when
      ``ipix_column`` is given.
  order : int, default=5
      HEALPix level of the coverage mask, nested ordering; 0 to 10.
  ra_column, dec_column : str, default='ra', 'dec'
      Right ascension and declination in degrees; ignored when ``ipix_column`` is given.
  ipix_column : str or None, default=None
      Column of nested pixel indices at ``order``; makes the table a tally.
  counts_column : str or None, default=None
      Column with the count (weight) of each row; one per row when None.
  group_column : str or None, default=None
      One colour and legend entry per distinct value (at most 12).
  min_count : float, default=1.0
      A pixel is covered when it holds at least this many objects.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.2
      Figure height in inches.
  alt : str or None, default=None
      Alternative text; built from the covered pixel counts and areas when None.
  caption : str or None, default=None
      Caption below the figure.

  Returns
  -------
  dict
      ``{'figure': FigureValue}``.
  """
  data = compute_footprint(
    table,
    order=order,
    ra_column=ra_column,
    dec_column=dec_column,
    ipix_column=ipix_column,
    counts_column=counts_column,
    group_column=group_column,
    min_count=min_count,
  )
  figure = render_footprint(ctx, data, title=title, width=width, height=height)
  text = alt or _describe(data, order)
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}


def _describe(data: pa.Table, order: int) -> str:
  """Factual alt text: covered pixels and sky area per group, from the sidecar table."""
  if data.num_rows == 0:
    return 'Mollweide sky map of a coverage footprint: nothing to draw.'
  area = pixel_area_deg2(order)
  names = data.column('group').to_pylist()
  parts = []
  for group in sorted(set(names)):
    pixels = names.count(group)
    parts.append(
      f'{group or "the footprint"}: {pixels:,} pixels, {pixels * area:,.0f} square degrees '
      f'({100.0 * pixels * area / SKY_AREA_DEG2:.1f}% of the sky)'
    )
  return (
    f'Mollweide sky map of coverage at HEALPix order {order} (nested), pixels of '
    f'{area:.2f} square degrees. ' + '; '.join(parts) + '.'
  )
