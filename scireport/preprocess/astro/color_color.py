"""``astro.color_color``: hybrid density colour-colour diagram, to read the stellar locus off.

Ported from the MOSAICS panel ``plot_color_color``. A tight, sky-invariant band in this plane is
the standard test of zero-point accuracy in a survey data release: its scatter is dominated by
calibration error, not astrophysics, so a locus that is broad, offset or doubled is a photometry
problem before it is anything else. The crowded regions are drawn as hexagons coloured by count
and the sparse regions as individual points, so a rare source is never hidden under a crowd.

Parameters of the step (see :func:`color_color`):

* ``color_x_column``, ``color_y_column``: two columns of colours (magnitude differences, for
  example g - r and r - i), already formed. Rows where either is null or not finite are dropped.
* ``gridsize``: hexagons across the x range. ``threshold``: a hexagon with this many points or
  fewer is drawn as points.
* ``x_label``, ``y_label`` (the column names when omitted), ``title``: text.
* ``width`` (fraction of the page frame) and ``height`` (inches).
* ``alt`` and ``caption``: text of the figure value; ``alt`` is made from the data when omitted.

Outputs: ``figure`` (a ``figure`` value with PNG and PDF renditions and its sidecar data).
Sidecar columns: ``kind`` (``hex`` or ``point``), ``x``, ``y`` (hexagon centre or point), ``n``
(points in the hexagon, 1 for a point), ``dx`` and ``dy`` (the hexagon's horizontal and vertical
pitch, NaN for a point). The catalogue itself is never stored.
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


def compute_color_color(
  table: pa.Table,
  color_x_column: str,
  color_y_column: str,
  *,
  gridsize: int = 60,
  threshold: int = 3,
) -> pa.Table:
  """Bin two colour columns into hexagons and sparse points.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  color_x_column, color_y_column : str
      Numeric columns holding the two colours.
  gridsize : int, default=60
      Hexagons across the x range.
  threshold : int, default=3
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Columns ``kind``, ``x``, ``y``, ``n``, ``dx`` and ``dy``; zero rows when no pair is finite.
  """
  require_columns(table, color_x_column, color_y_column)
  return density_table(
    numbers(table, color_x_column), numbers(table, color_y_column), gridsize, threshold
  )


def render_color_color(
  ctx: Context,
  data: pa.Table,
  *,
  x_label: str = '',
  y_label: str = '',
  title: str = '',
  width: float = 1.0,
  height: float = 3.6,
) -> Figure:
  """Draw the cells of :func:`compute_color_color` in the layout's style.

  Parameters
  ----------
  ctx : Context
      Supplies the figure size, style and colours.
  data : pyarrow.Table
      The table :func:`compute_color_color` made (or read back from a bundle's sidecar file).
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
    ctx, data, x_label=x_label, y_label=y_label, title=title, width=width, height=height
  )


@preprocessor(
  'astro.color_color',
  version=1,
  inputs={'table': Port('table', description='One row per object, with two colour columns')},
  outputs={'figure': Port('figure', description='The colour-colour density diagram')},
  render=render_color_color,
)
def color_color(
  ctx: Context,
  *,
  table: pa.Table,
  color_x_column: str,
  color_y_column: str,
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
  """Hybrid density colour-colour diagram.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      One row per object.
  color_x_column, color_y_column : str
      Columns with the two colours (magnitude differences such as g - r and r - i).
  gridsize : int, default=60
      Hexagons across the x range.
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
  data = compute_color_color(
    table, color_x_column, color_y_column, gridsize=gridsize, threshold=threshold
  )
  figure = render_color_color(
    ctx,
    data,
    x_label=color_x_column if x_label is None else x_label,
    y_label=color_y_column if y_label is None else y_label,
    title=title,
    width=width,
    height=height,
  )
  total = density_total(data)
  text = alt or (
    f'Density diagram of {color_y_column} against {color_x_column}: {total:,} objects with both '
    f'colours finite, drawn as hexagons where crowded and as points elsewhere.'
  )
  return {'figure': ctx.save_figure(figure, data=data, alt=text, caption=caption, width=width)}
