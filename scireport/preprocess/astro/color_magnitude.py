"""``astro.color_magnitude``: hybrid density colour-magnitude diagram.

Ported from the MOSAICS panel ``plot_color_magnitude``. The magnitude axis (y) is inverted, the
usual astronomical convention of brighter (lower magnitude) drawn upward, so a reader used to the
colour-magnitude diagrams of a survey's own data-release papers sees the same orientation. The
crowded regions are drawn as hexagons coloured by count and the sparse regions as individual
points.

Parameters of the step (see :func:`color_magnitude`):

* ``color_column``: a colour (magnitude difference, for example g - r), already formed.
* ``magnitude_column``: a single-band magnitude. Rows where either is null or not finite are
  dropped.
* ``gridsize``: hexagons across the colour range. ``threshold``: a hexagon with this many points
  or fewer is drawn as points.
* ``x_label``, ``y_label`` (the column names when omitted), ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``kind`` (``hex`` or ``point``), ``x`` (colour) and ``y`` (magnitude) of the
hexagon centre or point, ``n`` (points in the hexagon, 1 for a point), ``dx`` and ``dy`` (the
hexagon's horizontal and vertical pitch, NaN for a point). The catalogue itself is never stored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pyarrow as pa

from scireport.preprocess.astro._density import density_table, density_total, draw_density
from scireport.preprocess.context import Context
from scireport.preprocess.plotting import numbers, require_columns
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope

if TYPE_CHECKING:
  from matplotlib.figure import Figure


def compute_color_magnitude(
  table: pa.Table,
  color_column: str,
  magnitude_column: str,
  *,
  gridsize: int = 60,
  threshold: int = 3,
) -> pa.Table:
  """Bin a colour column and a magnitude column into hexagons and sparse points.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  color_column, magnitude_column : str
      Numeric columns holding the colour (x) and the magnitude (y).
  gridsize : int, default=60
      Hexagons across the colour range.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Columns ``kind``, ``x``, ``y``, ``n``, ``dx`` and ``dy``; zero rows when no pair is finite.
  """
  require_columns(table, color_column, magnitude_column)
  return density_table(
    numbers(table, color_column), numbers(table, magnitude_column), gridsize, threshold
  )


def render_color_magnitude(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = '',
  y_label: str = '',
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
) -> Figure:
  """Draw the cells of :func:`compute_color_magnitude`, magnitude axis inverted.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_color_magnitude` made (or read back from a bundle's sidecar file).
  x_label, y_label, title : str
      Axis labels and title; empty strings draw nothing.
  width : float, default=1.0
      Width as a fraction of the page frame.
  height : float, default=3.6
      Height in inches.

  Returns
  -------
  matplotlib.figure.Figure
      The drawn figure.
  """
  return draw_density(
    ctx,
    data,
    x_label=x_label,
    y_label=y_label,
    title=title,
    width=width,
    height=height,
    invert_y=True,
  )


@preprocessor(
  'astro.color_magnitude',
  version=1,
  inputs={'table': Port('table', description='One row per object, with a colour and a magnitude')},
  outputs={'figure': Port('figure', description='The colour-magnitude density diagram')},
  render=render_color_magnitude,
)
def color_magnitude(
  ctx: Context,
  *,
  table: pa.Table,
  color_column: str,
  magnitude_column: str,
  gridsize: int = 60,
  threshold: int = 3,
  x_label: str | None = None,
  y_label: str | None = None,
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
  alt: str | None = None,
  caption: str | None = None,
) -> dict[str, Envelope]:
  """Hybrid density colour-magnitude diagram.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object.
  color_column : str
      Column with a colour (a magnitude difference such as g - r), on the x axis.
  magnitude_column : str
      Column with a single-band magnitude, on the inverted y axis.
  gridsize : int, default=60
      Hexagons across the colour range.
  threshold : int, default=3
      A hexagon with this many points or fewer is drawn as individual points.
  x_label, y_label : str or None, default=None
      Axis labels; the column names when None.
  title : str, default=''
      Title; nothing when empty.
  width : float, default=1.0
      Figure width as a fraction of the page frame.
  height : float, default=3.6
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
  data = compute_color_magnitude(
    table, color_column, magnitude_column, gridsize=gridsize, threshold=threshold
  )
  figure = render_color_magnitude(
    ctx,
    data,
    x_label=color_column if x_label is None else x_label,
    y_label=magnitude_column if y_label is None else y_label,
    title=title,
    width=width,
    height=height,
  )
  total = density_total(data)
  text = alt or (
    f'Colour-magnitude density diagram of {magnitude_column} against {color_column}, magnitude '
    f'increasing downward: {total:,} objects with both values finite, drawn as hexagons where '
    f'crowded and as points elsewhere.'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
