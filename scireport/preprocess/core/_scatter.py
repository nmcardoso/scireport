"""Private helpers the hybrid-density pre-processors share.

Used by ``core.density_scatter``, ``core.metric_scatter`` and ``core.corner``. The hexagon binning
itself lives in :func:`scireport.preprocess.plotting.hex_bins`; this module only gives its output a
fixed column type, so that an empty scatter and a full one have the same sidecar schema, and finds
the paired finite values of two columns.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from scireport.preprocess.plotting import hex_bins, numbers, require_columns

HEX_SCHEMA = pa.schema(
  [
    pa.field('kind', pa.string()),
    pa.field('x', pa.float64()),
    pa.field('y', pa.float64()),
    pa.field('n', pa.float64()),
    pa.field('dx', pa.float64()),
    pa.field('dy', pa.float64()),
  ]
)


def finite_pairs(table: pa.Table, x_column: str, y_column: str) -> tuple[np.ndarray, np.ndarray]:
  """Read two columns and keep the rows where both are finite.

  Parameters
  ----------
  table : pyarrow.Table
      The input.
  x_column, y_column : str
      Numeric columns.

  Returns
  -------
  tuple of numpy.ndarray
      The finite x and y values, aligned.

  Raises
  ------
  PreprocessError
      With ``E603`` when a column is missing or not numeric.
  """
  require_columns(table, x_column, y_column)
  x, y = numbers(table, x_column), numbers(table, y_column)
  keep = np.isfinite(x) & np.isfinite(y)
  return x[keep], y[keep]


def hex_table(x: np.ndarray, y: np.ndarray, gridsize: int, threshold: int) -> pa.Table:
  """Bin a scatter into the sidecar table of a hybrid density panel.

  Parameters
  ----------
  x, y : numpy.ndarray
      Aligned values; pairs that are not both finite are dropped.
  gridsize : int
      Hexagons across the x range.
  threshold : int
      A hexagon with this many points or fewer is kept as individual points.

  Returns
  -------
  pyarrow.Table
      Columns ``kind`` (``'hex'`` or ``'point'``), ``x``, ``y``, ``n``, ``dx``, ``dy`` with fixed
      types, no rows when nothing is finite.
  """
  return typed(hex_bins(x, y, gridsize, threshold))


def typed(columns: Mapping[str, Any]) -> pa.Table:
  """Build a table whose columns have the :data:`HEX_SCHEMA` types.

  Parameters
  ----------
  columns : mapping
      Column name to values; names outside :data:`HEX_SCHEMA` are made float64, except ``panel``
      which is a string.

  Returns
  -------
  pyarrow.Table
      The table.
  """
  strings = {'kind', 'panel'}
  arrays = {
    name: pa.array(list(values), pa.string())
    if name in strings
    else pa.array(np.asarray(values, dtype=float), pa.float64())
    for name, values in columns.items()
  }
  return pa.table(arrays)


def without_kind(data: pa.Table, kind: str) -> pa.Table:
  """Drop the rows of one ``kind`` from a table.

  Parameters
  ----------
  data : pyarrow.Table
      A table with a ``kind`` column.
  kind : str
      The kind to remove.

  Returns
  -------
  pyarrow.Table
      The remaining rows.
  """
  return data.filter(pc.not_equal(data.column('kind'), kind))
