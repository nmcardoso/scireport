"""``core.table_profile``: one row per column of a table, and the table's size.

Ported from the MOSAICS report engine's table description (``PROFILE_COLUMNS``, ``_columns_data``,
``_headline_data``): a header of the headline numbers and a row per column with its type and the
shape of its values. MOSAICS read the numbers from a database; here they are computed with
pyarrow from the input table itself. The sky map of the original is a separate step
(``astro.sky_density``). This step draws no figure.

Parameters of the step (see :func:`table_profile`):

* ``caption``: caption of the profile table; a plain description of the columns when omitted.

Outputs:

* ``profile``, a ``table`` value with one row per column of the input, in the input's order:
  ``name``, ``type`` (the Arrow type, for example ``int64`` or ``string``), ``nulls`` (null cells,
  and NaN in a floating-point column), ``zeros``, ``negatives``, ``distinct`` (distinct non-null
  values), ``outliers`` (values outside the Tukey fences, 1.5 times the interquartile range
  beyond the quartiles), ``min``, ``max`` and ``mean``. A statistic that does not apply is null,
  which the layout shows blank, never as a zero: ``zeros``, ``negatives``, ``outliers``, ``min``,
  ``max`` and ``mean`` apply to numeric columns only, ``distinct`` to columns that are not
  floating point, and ``outliers`` needs a non-zero interquartile range. Infinities count in
  ``negatives``, ``outliers``, ``min`` and ``max``; the quartiles and the mean use finite values
  only.
* ``summary``, a ``metrics`` value with ``Rows``, ``Columns`` and ``In memory`` (the Arrow
  table's ``nbytes``).
"""

from __future__ import annotations

from typing import Any

import pyarrow as pa
import pyarrow.compute as pc

from scireport.preprocess.context import Context
from scireport.preprocess.ports import Port
from scireport.preprocess.registry import preprocessor
from scireport.spec.kinds import Envelope, MetricsValue

OUTLIER_FENCE = 1.5
"""Distance of a Tukey fence from the quartile, in interquartile ranges."""

PROFILE_COLUMNS: tuple[tuple[str, str, float, str, str | None], ...] = (
  ('name', 'Column', 0.26, 'left', None),
  ('type', 'Type', 0.10, 'left', None),
  ('nulls', 'Nulls', 0.075, 'right', 'int'),
  ('zeros', 'Zeros', 0.075, 'right', 'int'),
  ('negatives', 'Negative', 0.075, 'right', 'int'),
  ('distinct', 'Distinct', 0.075, 'right', 'int'),
  ('outliers', 'Outliers', 0.075, 'right', 'int'),
  ('min', 'Min', 0.10, 'right', ',.8g'),
  ('max', 'Max', 0.10, 'right', ',.8g'),
  ('mean', 'Mean', 0.09, 'right', ',.8g'),
)
"""Key, heading, share of the frame, alignment and number format of each profile column."""

_SCHEMA = pa.schema(
  [
    ('name', pa.string()),
    ('type', pa.string()),
    ('nulls', pa.int64()),
    ('zeros', pa.int64()),
    ('negatives', pa.int64()),
    ('distinct', pa.int64()),
    ('outliers', pa.int64()),
    ('min', pa.float64()),
    ('max', pa.float64()),
    ('mean', pa.float64()),
  ]
)

_CAPTION = (
  'Profile of the input table, one row per column. Nulls count null cells and NaN. Zeros, '
  'negatives, outliers (beyond 1.5 interquartile ranges from the quartiles), min, max and mean '
  'apply to numeric columns only, and distinct values to columns that are not floating point; a '
  'blank cell means the statistic does not apply.'
)


def compute_table_profile(table: pa.Table) -> pa.Table:
  """Describe every column of a table.

  Parameters
  ----------
  table : pyarrow.Table
      The table to profile.

  Returns
  -------
  pyarrow.Table
      One row per column with the columns listed in the module docstring.
  """
  rows = [_profile_column(name, table.column(name)) for name in table.column_names]
  return pa.table(
    {field.name: pa.array([row[field.name] for row in rows], field.type) for field in _SCHEMA},
    schema=_SCHEMA,
  )


@preprocessor(
  'core.table_profile',
  version=1,
  inputs={'table': Port('table', description='The table to profile')},
  outputs={
    'profile': Port('table', description='One row per column: type, nulls, zeros and shape'),
    'summary': Port('metrics', description='Rows, columns and size in memory'),
  },
)
def table_profile(
  ctx: Context, *, table: pa.Table, caption: str | None = None
) -> dict[str, Envelope]:
  """Per-column profile of a table, with its size.

  Parameters
  ----------
  ctx : Context
      The run context.
  table : pyarrow.Table
      The table to profile.
  caption : str or None, default=None
      Caption below the profile table; a description of the columns when None.

  Returns
  -------
  dict
      ``{'profile': TableValue, 'summary': MetricsValue}``.
  """
  profile = compute_table_profile(table)
  ctx.log.info('profiled %d columns of %d rows', table.num_columns, table.num_rows)
  columns = [
    {
      'name': key,
      'label': heading,
      'align': align,
      'width': width,
      **({'format': number_format} if number_format is not None else {}),
    }
    for key, heading, width, align, number_format in PROFILE_COLUMNS
  ]
  summary = MetricsValue.model_validate(
    {
      'kind': 'metrics',
      'items': [
        {'label': 'Rows', 'value': {'kind': 'number', 'value': table.num_rows, 'format': 'int'}},
        {
          'label': 'Columns',
          'value': {'kind': 'number', 'value': table.num_columns, 'format': 'int'},
        },
        {'label': 'In memory', 'value': {'kind': 'text', 'text': _bytes(table.nbytes)}},
      ],
    }
  )
  return {
    'profile': ctx.save_table(
      profile, port='profile', columns=columns, caption=caption if caption is not None else _CAPTION
    ),
    'summary': summary,
  }


def _profile_column(name: str, column: pa.ChunkedArray) -> dict[str, Any]:
  """Compute the statistics of one column; ``None`` where a statistic does not apply."""
  kind = column.type
  numeric = pa.types.is_integer(kind) or pa.types.is_floating(kind) or pa.types.is_decimal(kind)
  row: dict[str, Any] = dict.fromkeys(_SCHEMA.names)
  row['name'] = name
  row['type'] = str(kind)
  row['nulls'] = column.null_count
  if pa.types.is_floating(kind):
    row['nulls'] += int(pc.sum(pc.is_nan(column)).as_py() or 0)
  if not pa.types.is_floating(kind):
    try:
      row['distinct'] = int(pc.count_distinct(column).as_py())
    except (pa.ArrowNotImplementedError, pa.ArrowInvalid):
      row['distinct'] = None
  if numeric:
    row.update(_numeric_statistics(column))
  return row


def _numeric_statistics(column: pa.ChunkedArray) -> dict[str, Any]:
  """Zeros, negatives, outliers, min, max and mean of a numeric column."""
  values = pc.cast(column, pa.float64())
  valid = values.filter(pc.invert(pc.is_nan(values)))
  result: dict[str, Any] = {
    'zeros': int(pc.sum(pc.equal(valid, 0.0)).as_py() or 0),
    'negatives': int(pc.sum(pc.less(valid, 0.0)).as_py() or 0),
  }
  if len(valid) == 0:
    return result
  extremes = pc.min_max(valid)
  result['min'] = extremes['min'].as_py()
  result['max'] = extremes['max'].as_py()
  finite = valid.filter(pc.is_finite(valid))
  if len(finite) == 0:
    return result
  result['mean'] = pc.mean(finite).as_py()
  first, third = pc.quantile(finite, [0.25, 0.75]).to_pylist()
  spread = third - first
  if spread > 0.0:
    low, high = first - OUTLIER_FENCE * spread, third + OUTLIER_FENCE * spread
    outside = pc.or_(pc.less(valid, low), pc.greater(valid, high))
    result['outliers'] = int(pc.sum(outside).as_py() or 0)
  return result


def _bytes(value: Any) -> str:
  """Format a byte count in the largest unit that keeps it above one.

  Parameters
  ----------
  value : Any
      Bytes.

  Returns
  -------
  str
      For example ``'4.5 MB'`` (units of 1024), or ``'--'`` when it is not a number.
  """
  try:
    size = float(value)
  except (TypeError, ValueError):
    return '--'
  for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
    if size < 1024.0 or unit == 'TB':
      return f'{size:,.1f} {unit}' if unit != 'B' else f'{size:,.0f} B'
    size /= 1024.0
  return f'{size:,.1f} TB'
