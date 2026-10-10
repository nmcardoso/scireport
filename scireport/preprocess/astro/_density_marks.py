"""Private helpers of the density panels with reference marks (``astro.snr_magnitude`` and kin).

Three photometric panels draw a hexagon-binned density of one quantity against another, with
reference marks over it (a depth, a fitted line). The sidecar table they store is the table of
:func:`scireport.preprocess.plotting.hex_bins` (rows of kind ``hex`` and ``point``) followed by
one row per reference mark, of kind ``depth`` or ``fit``, so that the figure is drawn again from
that one table. This module builds the table and takes it apart again; the leading underscore
keeps it out of the registry.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from scireport.preprocess.plotting import hex_bins, values_of

CELL_KINDS = ('hex', 'point')
_COLUMNS = ('x', 'y', 'n', 'dx', 'dy')


def density_table(
  x: np.ndarray,
  y: np.ndarray,
  *,
  gridsize: int,
  threshold: int,
  marks: Sequence[tuple[str, float, float]] = (),
) -> pa.Table:
  """Bin a scatter into hexagons and sparse points, and append the reference marks.

  Parameters
  ----------
  x, y : numpy.ndarray
      Aligned 1D arrays; pairs that are not both finite are dropped.
  gridsize : int
      Hexagons across the x range.
  threshold : int
      A hexagon with this many points or fewer is kept as individual points.
  marks : sequence of tuple, default=()
      Reference marks as ``(kind, x, y)``, stored after the cells (``y`` may be NaN).

  Returns
  -------
  pyarrow.Table
      Columns ``kind`` (string) and ``x``, ``y``, ``n``, ``dx``, ``dy`` (float64); the cells
      come first, hexagons then points, each sorted by ``x`` and then ``y``.
  """
  cells = hex_bins(x, y, gridsize, threshold)
  kinds = np.asarray(cells['kind'], dtype=object)
  columns = {name: np.asarray(cells[name], dtype=float) for name in _COLUMNS}
  rank = np.where(kinds == 'hex', 0, 1) if kinds.size else np.empty(0, dtype=int)
  order = np.lexsort((columns['y'], columns['x'], rank)) if kinds.size else np.empty(0, dtype=int)
  kind_list = [str(kinds[i]) for i in order]
  out = {name: values[order] for name, values in columns.items()}
  for kind, mark_x, mark_y in marks:
    kind_list.append(kind)
    out['x'] = np.append(out['x'], mark_x)
    out['y'] = np.append(out['y'], mark_y)
    for name in ('n', 'dx', 'dy'):
      out[name] = np.append(out[name], np.nan)
  return pa.table(
    {
      'kind': pa.array(kind_list, pa.string()),
      **{name: pa.array(out[name], pa.float64()) for name in _COLUMNS},
    }
  )


def cells_of(data: pa.Table) -> pa.Table:
  """Return the hexagon and point rows of a table made by :func:`density_table`.

  Parameters
  ----------
  data : pyarrow.Table
      The sidecar table.

  Returns
  -------
  pyarrow.Table
      Only the rows :func:`~scireport.preprocess.plotting.draw_hex_bins` draws.
  """
  keep = pc.is_in(data.column('kind'), value_set=pa.array(CELL_KINDS, pa.string()))
  return data.filter(keep)


def marks_of(data: pa.Table, kind: str) -> tuple[np.ndarray, np.ndarray]:
  """Return the ``x`` and ``y`` of the reference marks of one kind.

  Parameters
  ----------
  data : pyarrow.Table
      The sidecar table.
  kind : str
      ``'depth'`` or ``'fit'``.

  Returns
  -------
  tuple of numpy.ndarray
      ``x`` and ``y`` of each row of that kind, in stored order.
  """
  picked = data.filter(pc.equal(data.column('kind'), kind))
  return values_of(picked, 'x'), values_of(picked, 'y')


def n_points(data: pa.Table) -> int:
  """Count the points the cells of a table stand for.

  Parameters
  ----------
  data : pyarrow.Table
      The sidecar table.

  Returns
  -------
  int
      The sum of ``n`` over hexagons and points.
  """
  counts = values_of(cells_of(data), 'n')
  return int(np.nansum(counts))
