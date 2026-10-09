"""Read a ``table`` value and turn it into a :class:`~scireport.render.specs.TableSpec`.

Large tables are not loaded whole: a Parquet file is read through its footer and only the first
``max_rows`` rows are decoded, so cutting a 10,000-row table to 25 rows costs 25 rows. Cells are
formatted by the column's ``format`` (see :mod:`scireport.render.numbers`) and always fit on one
line.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from scireport.bundle.reader import Bundle
from scireport.errors import BundleError
from scireport.render.numbers import Target, format_cell, typeset_unit
from scireport.render.safe import Safe
from scireport.render.specs import ColSpec, LinkSpec, RowSpec, TableSpec
from scireport.spec.kinds import Column, TableValue

if TYPE_CHECKING:
  import pyarrow as pa

IssueSink = Callable[..., None]
"""Records a problem: ``sink(code, message, key=..., hint=...)``."""

MISSING_CELL = '--'
"""Shown for a cell that holds no value."""


def read_rows(
  bundle: Bundle, value: TableValue, names: list[str] | None, limit: int | None
) -> tuple[list[str], list[list[Any]], int, set[str]]:
  """Read the leading rows of a table without loading the rest.

  Parameters
  ----------
  bundle : Bundle
      The bundle that holds the table's asset.
  value : TableValue
      The table value.
  names : list of str or None
      Columns to read, in order; None reads every column.
  limit : int or None
      Read at most this many rows; None reads all.

  Returns
  -------
  tuple
      The column names found (in the order read), the rows, the total number of rows in the
      data and the names of the numeric columns.

  Raises
  ------
  BundleError
      With ``E401`` to ``E403`` when the asset is damaged.
  """
  if value.rows is not None:
    inline = [column.name for column in value.columns]
    wanted = [name for name in (names or inline) if name in inline]
    index = [inline.index(name) for name in wanted]
    rows = [[row[i] for i in index] for row in value.rows[:limit]]
    numeric = {
      name
      for name, i in zip(wanted, index, strict=True)
      if _numeric_cells(r[i] for r in value.rows)
    }
    return wanted, rows, len(value.rows), numeric
  assert value.asset is not None
  if value.format == 'parquet':
    table, total = _read_parquet(bundle, value, names, limit)
  else:
    table = _read_csv(bundle, value)
    total = table.num_rows
    if names is not None:
      table = table.select([name for name in names if name in table.column_names])
    if limit is not None:
      table = table.slice(0, limit)
  import pyarrow.types as pat

  numeric = {
    field.name
    for field in table.schema
    if pat.is_integer(field.type) or pat.is_floating(field.type) or pat.is_decimal(field.type)
  }
  return (
    table.column_names,
    [list(row) for row in zip(*table.to_pydict().values(), strict=True)],
    total,
    numeric,
  )


def build_table(
  bundle: Bundle,
  value: TableValue,
  *,
  target: Target,
  number: int,
  caption: str | None,
  max_rows: int | None,
  report: IssueSink,
  key: str,
  overflow: Callable[[str], LinkSpec | None],
) -> TableSpec:
  """Build the spec of a table.

  Parameters
  ----------
  bundle : Bundle
      The bundle that holds the table.
  value : TableValue
      The table value.
  target : {'md', 'html', 'tex'}
      The output format.
  number : int
      The table number.
  caption : str or None
      Caption override; the value's own caption when None.
  max_rows : int or None
      Row cap override; the value's ``max_rows`` when None. None means no cap.
  report : callable
      Receives problems (``E305``).
  key : str
      The value's key, for messages.
  overflow : callable
      Given the key of an attachment, returns the link to offer for the full table.

  Returns
  -------
  TableSpec
      The table, ready for a layout macro.
  """
  limit = max_rows if max_rows is not None else value.max_rows
  defined = {column.name: column for column in value.columns}
  status_name = value.row_status_column
  shown_names = [name for name in defined if name != status_name] or None
  read_names = None if shown_names is None else shown_names + ([status_name] if status_name else [])
  names, rows, total, numeric = read_rows(bundle, value, read_names, limit)
  for name in defined:
    if name not in names:
      report(
        'E305',
        f'table {key!r} declares column {name!r}, which the data file does not have',
        key=key,
      )
  shown = [name for name in names if name != status_name]
  columns = tuple(_column(defined.get(name), name, name in numeric, target) for name in shown)
  widths = _normalise([defined[n].width if n in defined else None for n in shown])
  columns = tuple(
    ColSpec(c.label, c.unit, c.align, w, defined[n].width is not None if n in defined else False)
    for c, w, n in zip(columns, widths, shown, strict=True)
  )
  formats = [defined[n].format if n in defined else None for n in shown]
  emphasis = {(cue.row, cue.column): cue.style for cue in value.emphasis}
  status_index = names.index(status_name) if status_name in names else None
  out_rows = []
  for r, row in enumerate(rows):
    cells = tuple(
      _cell(row[names.index(name)], fmt, target) for name, fmt in zip(shown, formats, strict=True)
    )
    if status_index is not None:
      verdict = row[status_index]
    else:
      verdict = value.row_status[r] if value.row_status and r < len(value.row_status) else None
    out_rows.append(
      RowSpec(
        cells,
        verdict if verdict in ('pass', 'warn', 'fail') else None,
        tuple(emphasis.get((r, name)) for name in shown),
      )
    )
  truncated = total > len(out_rows)
  link = overflow(value.overflow_attachment) if truncated and value.overflow_attachment else None
  return TableSpec(
    columns=columns,
    rows=tuple(out_rows),
    caption=caption if caption is not None else (value.caption or ''),
    number=number,
    total=total,
    truncated=truncated,
    overflow=link,
    headed=any(c.label.strip() for c in columns),
    has_verdicts=any(r.verdict for r in out_rows),
  )


def _read_parquet(
  bundle: Bundle, value: TableValue, names: list[str] | None, limit: int | None
) -> tuple[pa.Table, int]:
  """Read the leading rows of a Parquet table through its footer."""
  import pyarrow as pa
  import pyarrow.parquet as pq

  assert value.asset is not None
  with bundle.open_asset(value.asset) as handle:
    source = io.BytesIO(handle.read()) if not handle.seekable() else handle
    parquet = pq.ParquetFile(source)
    total = int(parquet.metadata.num_rows)
    present = [n for n in (names or parquet.schema_arrow.names) if n in parquet.schema_arrow.names]
    if limit is None:
      return parquet.read(columns=present), total
    for batch in parquet.iter_batches(batch_size=max(limit, 1), columns=present):
      return pa.Table.from_batches([batch.slice(0, limit)]), total
    return parquet.schema_arrow.empty_table().select(present), total


def _read_csv(bundle: Bundle, value: TableValue) -> pa.Table:
  """Read a whole CSV table."""
  import pyarrow as pa
  import pyarrow.csv as pacsv

  assert value.asset is not None
  try:
    return pacsv.read_csv(pa.BufferReader(bundle.read_asset(value.asset)))
  except pa.ArrowInvalid as exc:
    raise BundleError(f'{value.asset.path} is not a readable CSV file: {exc}', code='E302') from exc


def _column(definition: Column | None, name: str, is_numeric: bool, target: Target) -> ColSpec:
  """Build the presentation of one column from its definition and the data type."""
  align = (definition.align if definition else None) or ('right' if is_numeric else 'left')
  unit = typeset_unit(definition.unit, target) if definition and definition.unit else ''
  label = (definition.label if definition and definition.label else name) or ''
  return ColSpec(label=label, unit=Safe(unit) if unit else '', align=align)


def _normalise(given: list[float | None]) -> list[float]:
  """Turn column widths into shares that sum to 1; columns without a width get the mean."""
  known = [w for w in given if w]
  fill = sum(known) / len(known) if known else 1.0
  weights = [w if w else fill for w in given]
  total = sum(weights) or 1.0
  return [w / total for w in weights]


def _cell(value: Any, spec: str | None, target: Target) -> str:
  """Format one cell as a single line."""
  if value is None:
    return MISSING_CELL
  text = format_cell(value, spec, target)
  if isinstance(text, Safe):
    return text
  return ' '.join(str(text).split())


def _numeric_cells(cells: Any) -> bool:
  """Say whether every non-null cell of an inline column is a number."""
  values = [cell for cell in cells if cell is not None]
  return bool(values) and all(
    isinstance(c, int | float) and not isinstance(c, bool) for c in values
  )
