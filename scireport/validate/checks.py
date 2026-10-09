"""Checks of a bundle against a template, a layout and the formats being written (ADR-0005).

Everything here runs before any rendering and reports all problems at once: missing or
wrongly-typed values the template needs (``E105``, ``E207``), table columns (``E303`` to
``E305``), figure renditions (``E210``), number formats (``E205``), raw LaTeX without a
replacement (``E209``) and math that mathtext cannot draw (``W601``).
"""

from __future__ import annotations

import difflib
import io
from typing import TYPE_CHECKING

from scireport.bundle.reader import Bundle
from scireport.errors import BundleError, Issue
from scireport.render.definition import Format
from scireport.render.numbers import format_problem
from scireport.render.template import ColumnSpec, FieldSpec, Template
from scireport.spec.kinds import (
  FigureValue,
  MathValue,
  NumberValue,
  TableValue,
  TextValue,
)

if TYPE_CHECKING:
  import pyarrow as pa

_FIGURE_NEEDS = {'md': ('png', 'svg'), 'html': ('png', 'svg'), 'tex': ('pdf', 'png')}


def check_fields(template: Template, bundle: Bundle) -> list[Issue]:
  """Check the bundle's values against the ``fields`` the template declares.

  Parameters
  ----------
  template : Template
      The template.
  bundle : Bundle
      The bundle.

  Returns
  -------
  list of Issue
      ``E105`` for a required field with no value, ``E207`` for a value of the wrong kind,
      ``E303`` and ``E304`` for table columns, ``E210`` for missing figure renditions.
  """
  values = bundle.manifest.values
  issues: list[Issue] = []
  for index, spec in enumerate(template.definition.fields):
    where = f'template.yaml fields[{index}]'
    matches = [key for key in sorted(values) if spec.matches(key)]
    if not matches:
      if spec.required:
        issues.append(_missing_field(spec, list(values), where))
      continue
    for key in matches:
      value = values[key]
      if value.kind not in spec.kinds:
        issues.append(
          Issue(
            'E207',
            f'value {key!r} is a {value.kind}, but the template needs {" or ".join(spec.kinds)}',
            pointer=f'/values/{key}',
            key=key,
            expected=' or '.join(spec.kinds),
            found=value.kind,
            location=where,
          )
        )
        continue
      if isinstance(value, TableValue) and spec.columns:
        issues.extend(_check_columns(bundle, key, value, spec.columns, where))
      if isinstance(value, FigureValue) and spec.renditions:
        have = {r.format for r in value.renditions}
        lacking = [fmt for fmt in spec.renditions if fmt not in have]
        if lacking:
          issues.append(
            Issue(
              'E210',
              f'figure {key!r} lacks the {", ".join(lacking)} rendition the template needs',
              pointer=f'/values/{key}/renditions',
              key=key,
              expected=', '.join(spec.renditions),
              found=', '.join(sorted(have)),
              location=where,
            )
          )
  return issues


def check_values(bundle: Bundle, formats: list[Format]) -> list[Issue]:
  """Check the values for the formats that will be written, whatever the template.

  Parameters
  ----------
  bundle : Bundle
      The bundle.
  formats : list of {'md', 'html', 'tex'}
      The formats about to be rendered.

  Returns
  -------
  list of Issue
      ``E205`` for an unusable number or column format, ``E305`` for a declared column that the
      data file lacks, ``E209`` for raw LaTeX with no replacement, ``W601`` for math mathtext
      cannot draw (when HTML is written).
  """
  issues: list[Issue] = []
  for key, value in sorted(bundle.manifest.values.items()):
    base = f'/values/{key}'
    if isinstance(value, NumberValue):
      issues.extend(_format_issue(value.format, f'{base}/format', key))
    elif isinstance(value, TableValue):
      for position, column in enumerate(value.columns):
        issues.extend(_format_issue(column.format, f'{base}/columns/{position}/format', key))
      issues.extend(_check_declared_columns(bundle, key, value))
    elif isinstance(value, TextValue) and value.format == 'latex':
      for fmt in formats:
        if fmt != 'tex' and fmt not in (value.alt or {}):
          issues.append(
            Issue(
              'E209',
              f'raw LaTeX text {key!r} has no "{fmt}" replacement',
              pointer=f'{base}/alt',
              key=key,
              hint='Add alt: {html: ..., md: ...} to the value.',
            )
          )
    elif isinstance(value, MathValue) and 'html' in formats:
      from scireport.render.math import math_problem

      problem = math_problem(value.latex)
      if problem:
        issues.append(
          Issue(
            'W601',
            f'mathtext cannot draw {value.latex!r}: {problem}',
            pointer=f'{base}/latex',
            key=key,
            hint='The source is shown instead; LaTeX output is not affected.',
          )
        )
    elif isinstance(value, FigureValue):
      for fmt in formats:
        have = {r.format for r in value.renditions}
        if not have & set(_FIGURE_NEEDS[fmt]):
          issues.append(
            Issue(
              'E210',
              f'figure {key!r} has no {" or ".join(_FIGURE_NEEDS[fmt])} rendition for {fmt}',
              pointer=f'{base}/renditions',
              key=key,
              expected=' or '.join(_FIGURE_NEEDS[fmt]),
              found=', '.join(sorted(have)),
            )
          )
  return issues


def table_dtypes(bundle: Bundle, value: TableValue) -> dict[str, str]:
  """Read the column names and abstract types of a table without loading its rows.

  Parameters
  ----------
  bundle : Bundle
      The bundle that holds the table.
  value : TableValue
      The table value.

  Returns
  -------
  dict
      Column name to one of ``int``, ``float``, ``string``, ``bool``, ``date``, ``timestamp`` or
      ``other``, in column order.

  Raises
  ------
  BundleError
      With ``E401`` to ``E403`` when the asset is damaged.
  """
  import pyarrow as pa
  import pyarrow.csv as pacsv
  import pyarrow.parquet as pq

  if value.rows is not None:
    names = [column.name for column in value.columns]
    return {name: _inline_dtype([row[i] for row in value.rows]) for i, name in enumerate(names)}
  assert value.asset is not None
  if value.format == 'parquet':
    with bundle.open_asset(value.asset) as handle:
      source = handle if handle.seekable() else io.BytesIO(handle.read())
      schema = pq.read_schema(source)
  else:
    try:
      schema = pacsv.read_csv(pa.BufferReader(bundle.read_asset(value.asset))).schema
    except pa.ArrowInvalid as exc:
      raise BundleError(
        f'{value.asset.path} is not a readable CSV file: {exc}', code='E302'
      ) from exc
  return {field.name: abstract_dtype(field.type) for field in schema}


def abstract_dtype(arrow_type: pa.DataType) -> str:
  """Map an Arrow type to the abstract type names used by templates.

  Parameters
  ----------
  arrow_type : pyarrow.DataType
      The column type.

  Returns
  -------
  str
      ``int``, ``float``, ``string``, ``bool``, ``date``, ``timestamp`` or ``other``.
  """
  import pyarrow.types as pat

  if pat.is_integer(arrow_type):
    return 'int'
  if pat.is_floating(arrow_type) or pat.is_decimal(arrow_type):
    return 'float'
  if pat.is_string(arrow_type) or pat.is_large_string(arrow_type):
    return 'string'
  if pat.is_boolean(arrow_type):
    return 'bool'
  if pat.is_timestamp(arrow_type):
    return 'timestamp'
  if pat.is_date(arrow_type):
    return 'date'
  return 'other'


def _missing_field(spec: FieldSpec, keys: list[str], where: str) -> Issue:
  """Build ``E105`` for a required field without a value, with the closest key as a hint."""
  kinds = ' or '.join(spec.kinds)
  purpose = f' ({spec.description})' if spec.description else ''
  if spec.is_pattern:
    return Issue(
      'E105',
      f'no value matches the pattern {spec.key!r}, which the template needs as {kinds}{purpose}',
      expected=f'{kinds} at {spec.key}',
      location=where,
    )
  close = difflib.get_close_matches(spec.key, keys, n=1)
  return Issue(
    'E105',
    f'the template needs a {kinds} value at {spec.key!r}{purpose}',
    pointer='/values',
    key=spec.key,
    expected=f'{kinds} at {spec.key}',
    hint=f'Did you mean {close[0]!r}?' if close else None,
    location=where,
  )


def _check_columns(
  bundle: Bundle, key: str, value: TableValue, needed: list[ColumnSpec], where: str
) -> list[Issue]:
  """Compare a table's columns with those the template requires."""
  try:
    have = table_dtypes(bundle, value)
  except BundleError as exc:
    return [Issue(exc.code, exc.message, pointer=f'/values/{key}', key=key, location=where)]
  issues = []
  for column in needed:
    if column.name not in have:
      if column.required:
        close = difflib.get_close_matches(column.name, list(have), n=1)
        issues.append(
          Issue(
            'E303',
            f'table {key!r} lacks the column {column.name!r}',
            pointer=f'/values/{key}',
            key=key,
            expected=column.name,
            found=', '.join(have),
            hint=f'Did you mean {close[0]!r}?' if close else None,
            location=where,
          )
        )
      continue
    if not _dtype_ok(column.dtype, have[column.name]):
      issues.append(
        Issue(
          'E304',
          f'column {column.name!r} of table {key!r} has type {have[column.name]}, '
          f'but the template needs {column.dtype}',
          pointer=f'/values/{key}',
          key=key,
          expected=column.dtype,
          found=have[column.name],
          location=where,
        )
      )
  return issues


def _check_declared_columns(bundle: Bundle, key: str, value: TableValue) -> list[Issue]:
  """Report ``E305`` for columns the manifest declares that the data file does not have."""
  if value.asset is None or not value.columns:
    return []
  try:
    have = table_dtypes(bundle, value)
  except BundleError:
    return []
  return [
    Issue(
      'E305',
      f'table {key!r} declares column {column.name!r}, which the data file does not have',
      pointer=f'/values/{key}/columns/{position}',
      key=key,
      expected=column.name,
      found=', '.join(have),
      hint=(
        f'Did you mean {close[0]!r}?'
        if (close := difflib.get_close_matches(column.name, list(have), n=1))
        else None
      ),
    )
    for position, column in enumerate(value.columns)
    if column.name not in have
  ]


def _format_issue(spec: str | None, pointer: str, key: str) -> list[Issue]:
  """Return ``E205`` when a number or column format cannot be used."""
  problem = format_problem(spec)
  if problem is None:
    return []
  return [Issue('E205', problem, pointer=pointer, key=key, found=str(spec))]


def _dtype_ok(wanted: str, found: str) -> bool:
  """Say whether an actual abstract type satisfies a wanted one."""
  if wanted == 'any':
    return True
  if wanted == 'number':
    return found in ('int', 'float')
  return wanted == found


def _inline_dtype(cells: list[object]) -> str:
  """Guess the abstract type of an inline column from its cells."""
  present = [cell for cell in cells if cell is not None]
  if present and all(isinstance(c, bool) for c in present):
    return 'bool'
  if present and all(isinstance(c, int) and not isinstance(c, bool) for c in present):
    return 'int'
  if present and all(isinstance(c, int | float) and not isinstance(c, bool) for c in present):
    return 'float'
  if present and all(isinstance(c, str) for c in present):
    return 'string'
  return 'other'
