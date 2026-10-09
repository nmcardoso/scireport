"""The v1.0 value kinds and the canonicalisation of bare JSON into typed envelopes (ADR-0002).

A value in ``values`` is an *envelope*: an object with a ``kind`` and the fields of that kind.
Bare JSON is shorthand and is canonicalised on load by :func:`canonicalise`:

========================  =========================================================
Bare JSON                 Canonical envelope
========================  =========================================================
string                    ``text`` with ``format: plain``
``true`` / ``false``      ``bool``
integer or float          ``number``
``null``                  ``number`` with ``value: null`` (a missing number)
array                     ``list`` whose items are canonicalised in turn
object without ``kind``   ``mapping`` with one entry per member, in order
========================  =========================================================

An object that has a ``kind`` member is always an envelope, so a mapping with an entry called
``kind`` has to be written in full. Strings that look like dates stay ``text``; write a ``date``
envelope when a date is meant.

Frozen: once phase S7 releases spec 1.0, a field, default or rule here changes only through a new
minor version (ADR-0008).
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import (
  AfterValidator,
  BaseModel,
  BeforeValidator,
  ConfigDict,
  Field,
  StrictBool,
  StrictFloat,
  StrictInt,
  StrictStr,
  TypeAdapter,
  ValidationInfo,
  model_validator,
)
from pydantic_core import PydanticCustomError

from scireport.spec.assets import RESOLVER_CONTEXT_KEY, AssetRef
from scireport.spec.keys import Key

Verdict = Literal['pass', 'warn', 'fail']
StatusLevel = Literal['success', 'warning', 'partial', 'failed', 'running']
AlertLevel = Literal['info', 'warning', 'error']
FlowState = Literal['done', 'reused', 'skipped', 'failed', 'running', 'pending']
Align = Literal['left', 'right', 'center', 'path']
Emphasis = Literal['strong', 'muted', 'pass', 'warn', 'fail']
TextFormat = Literal['plain', 'markdown', 'latex']
FigureFormat = Literal['png', 'pdf', 'svg']
ImageSuffix = ('png', 'jpg', 'jpeg', 'svg', 'pdf')

Fraction = Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
Finite = Annotated[StrictFloat, Field(allow_inf_nan=False)]
Num = StrictInt | Finite
Cell = StrictStr | StrictInt | Finite | StrictBool | None

_FILENAME_RE = re.compile(r'[^/\\\x00-\x1f]+')


class Model(BaseModel):
  """Base of every spec model: unknown fields are errors and instances are immutable."""

  model_config = ConfigDict(extra='forbid', frozen=True)


def _one_of(label: str, **fields: object) -> None:
  """Raise ``E206`` unless exactly one of ``fields`` is set (not None).

  Parameters
  ----------
  label : str
      Names the kind in the message.
  **fields : object
      Field name to value.
  """
  given = [name for name, value in fields.items() if value is not None]
  if len(given) != 1:
    raise PydanticCustomError(
      'E206',
      '{label} needs exactly one of {names}, got {given}',
      {'label': label, 'names': ', '.join(fields), 'given': ', '.join(given) or 'none'},
    )


def canonical_date(text: str) -> str:
  """Normalise an ISO 8601 date or date-time string.

  Parameters
  ----------
  text : str
      For example ``'2026-10-09'``, ``'20261009'`` or ``'2026-10-09T10:30:00Z'``.

  Returns
  -------
  str
      ``YYYY-MM-DD`` for a date, otherwise the ISO 8601 date-time with its offset if it has one.

  Raises
  ------
  pydantic_core.PydanticCustomError
      With code ``E205`` when ``text`` is not an ISO 8601 date or date-time.
  """
  try:
    return dt.date.fromisoformat(text).isoformat()
  except (ValueError, TypeError):
    pass
  try:
    return dt.datetime.fromisoformat(text).isoformat()
  except (ValueError, TypeError):
    raise PydanticCustomError(
      'E205', 'not an ISO 8601 date or date-time: {text}', {'text': repr(text)}
    ) from None


IsoDate = Annotated[str, AfterValidator(canonical_date)]


class TextValue(Model):
  """Prose or a short string: inline ``text`` or a file in ``assets/text/``.

  Parameters
  ----------
  kind : {'text'}
      The kind tag.
  text : str or None
      The content, inline. Exactly one of ``text`` and ``asset`` is given.
  asset : AssetRef or None
      A Markdown, plain-text or LaTeX file, for long content.
  format : {'plain', 'markdown', 'latex'}, default='plain'
      How the content is marked up. ``latex`` is emitted verbatim in TeX output.
  alt : dict or None
      For ``latex`` text, the replacement used by other outputs: keys ``html`` and ``md``.
  """

  kind: Literal['text']
  text: str | None = None
  asset: AssetRef | None = None
  format: TextFormat = 'plain'
  alt: dict[Literal['html', 'md'], str] | None = None

  @model_validator(mode='after')
  def _check(self) -> TextValue:
    """Enforce one source, and ``alt`` only for LaTeX."""
    _one_of('text', text=self.text, asset=self.asset)
    if self.alt is not None and self.format != 'latex':
      raise PydanticCustomError('E205', 'alt is only meaningful for format "latex"')
    return self


class NumberValue(Model):
  """A number with its presentation and uncertainty.

  Parameters
  ----------
  kind : {'number'}
      The kind tag.
  value : int or float or None, default=None
      The number; None means missing. Never NaN or infinite.
  unit : str or None
      Unit, free text (``'arcsec'``, ``'deg^2'``).
  format : str or None
      A name from the number filters (``'int'``, ``'pct'``, ``'sci'``, ...) or a Python format
      specification (``',.2f'``). Resolved by the renderer.
  uncertainty : float or None
      Symmetric uncertainty, at least 0. Excludes ``interval``.
  interval : tuple of two numbers or None
      Lower and upper bound of an asymmetric interval. Excludes ``uncertainty``.
  missing : str or None
      Text shown when ``value`` is None; the renderer's placeholder when None.
  """

  kind: Literal['number']
  value: Num | None = None
  unit: str | None = None
  format: str | None = None
  uncertainty: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
  interval: tuple[Num, Num] | None = None
  missing: str | None = None

  @model_validator(mode='after')
  def _check(self) -> NumberValue:
    """Enforce the exclusions between value, uncertainty and interval."""
    if self.uncertainty is not None and self.interval is not None:
      raise PydanticCustomError('E206', 'give either uncertainty or interval, not both')
    if self.value is None and (self.uncertainty is not None or self.interval is not None):
      raise PydanticCustomError('E205', 'a missing number cannot have an uncertainty or interval')
    if self.interval is not None and self.interval[0] > self.interval[1]:
      raise PydanticCustomError('E205', 'interval lower bound is above the upper bound')
    return self


class BoolValue(Model):
  """A boolean.

  Parameters
  ----------
  kind : {'bool'}
      The kind tag.
  value : bool
      The truth value.
  """

  kind: Literal['bool']
  value: StrictBool


class DateValue(Model):
  """A calendar date or date-time, stored in canonical ISO 8601 form.

  Parameters
  ----------
  kind : {'date'}
      The kind tag.
  value : str
      ``YYYY-MM-DD`` or an ISO 8601 date-time. Normalised on load by :func:`canonical_date`.
  """

  kind: Literal['date']
  value: IsoDate


class ListValue(Model):
  """An ordered list of values (any kind, nested).

  Parameters
  ----------
  kind : {'list'}
      The kind tag.
  items : list of Value
      The members. Bare JSON members are canonicalised.
  ordered : bool, default=False
      Whether the list is numbered when rendered.
  """

  kind: Literal['list']
  items: list[Value]
  ordered: bool = False


class MappingEntry(Model):
  """One labelled entry of a :class:`MappingValue`.

  Parameters
  ----------
  key : str
      The display label. Free text, not a value key.
  value : Value
      The entry's value.
  """

  key: Annotated[str, Field(min_length=1)]
  value: Value


class MappingValue(Model):
  """Labelled metadata entries in a fixed order (a description list).

  Parameters
  ----------
  kind : {'mapping'}
      The kind tag.
  entries : list of MappingEntry
      The entries, in display order.
  """

  kind: Literal['mapping']
  entries: list[MappingEntry]

  @model_validator(mode='after')
  def _check(self) -> MappingValue:
    """Reject repeated labels."""
    labels = [entry.key for entry in self.entries]
    if len(set(labels)) != len(labels):
      raise PydanticCustomError('E205', 'mapping entry labels must be unique')
    return self


class Column(Model):
  """Presentation of one table column.

  Parameters
  ----------
  name : str
      The column's name in the data.
  label : str or None
      Header text; the name when None.
  unit : str or None
      Unit shown in the header.
  format : str or None
      Cell number format, as for :class:`NumberValue`.
  align : {'left', 'right', 'center', 'path'} or None
      Cell alignment; ``path`` is left-aligned monospace that may break anywhere.
  width : float or None
      Share of the frame width in (0, 1]; widths are normalised by the renderer.
  description : str or None
      What the column holds, for the data-model appendix.
  """

  name: Annotated[str, Field(min_length=1)]
  label: str | None = None
  unit: str | None = None
  format: str | None = None
  align: Align | None = None
  width: Fraction | None = None
  description: str | None = None


class CellEmphasis(Model):
  """Emphasis of one cell of a table.

  Parameters
  ----------
  row : int
      Zero-based row index in the table's data.
  column : str
      Column name.
  style : {'strong', 'muted', 'pass', 'warn', 'fail'}
      The emphasis.
  """

  row: Annotated[int, Field(ge=0)]
  column: Annotated[str, Field(min_length=1)]
  style: Emphasis


class TableValue(Model):
  """A table: a Parquet or CSV file in ``assets/tables/``, or a small inline table.

  Parameters
  ----------
  kind : {'table'}
      The kind tag.
  columns : list of Column
      Column presentation. For an inline table it also names the columns and fixes their order;
      for a file it is optional and selects and orders the columns shown.
  asset : AssetRef or None
      A ``.parquet`` or ``.csv`` file. Exactly one of ``asset`` and ``rows`` is given.
  rows : list of list or None
      Inline rows of JSON scalars, one cell per column.
  caption : str or None
      Caption below the table.
  n_rows : int or None
      Number of rows in the data, recorded by the writer.
  row_status : list or None
      Per row ``pass``, ``warn``, ``fail`` or None (inline tables). Excludes ``row_status_column``.
  row_status_column : str or None
      Name of a data column that holds the per-row verdicts.
  emphasis : list of CellEmphasis
      Cells to emphasise.
  max_rows : int or None
      Show at most this many rows; the rest is available through ``overflow_attachment``.
  overflow_attachment : str or None
      Key of an ``attachment`` value with the full table, linked when rows are cut.
  """

  kind: Literal['table']
  columns: list[Column] = []
  asset: AssetRef | None = None
  rows: list[list[Cell]] | None = None
  caption: str | None = None
  n_rows: Annotated[int, Field(ge=0)] | None = None
  row_status: list[Verdict | None] | None = None
  row_status_column: str | None = None
  emphasis: list[CellEmphasis] = []
  max_rows: Annotated[int, Field(ge=1)] | None = None
  overflow_attachment: Key | None = None

  @property
  def format(self) -> Literal['parquet', 'csv', 'inline']:
    """The storage format: ``parquet`` or ``csv`` from the file suffix, else ``inline``."""
    if self.asset is None:
      return 'inline'
    return 'csv' if self.asset.path.endswith('.csv') else 'parquet'

  @model_validator(mode='after')
  def _check(self) -> TableValue:
    """Enforce one data source and the consistency of columns, rows and verdicts."""
    _one_of('table', asset=self.asset, rows=self.rows)
    names = [column.name for column in self.columns]
    if len(set(names)) != len(names):
      raise PydanticCustomError('E302', 'column names must be unique')
    if self.asset is not None and not self.asset.path.endswith(('.parquet', '.csv')):
      raise PydanticCustomError('E205', 'a table asset must be a .parquet or .csv file')
    if self.row_status is not None and self.row_status_column is not None:
      raise PydanticCustomError('E206', 'give either row_status or row_status_column, not both')
    if self.rows is not None:
      if not self.columns:
        raise PydanticCustomError('E301', 'an inline table needs its columns')
      if any(len(row) != len(self.columns) for row in self.rows):
        raise PydanticCustomError('E301', 'every inline row needs one cell per column')
      if self.n_rows is not None and self.n_rows != len(self.rows):
        raise PydanticCustomError('E301', 'n_rows does not match the number of inline rows')
      if self.row_status is not None and len(self.row_status) != len(self.rows):
        raise PydanticCustomError('E301', 'row_status needs one entry per inline row')
    if names:
      for cue in self.emphasis:
        if cue.column not in names:
          raise PydanticCustomError(
            'E302', 'emphasis refers to unknown column {name}', {'name': repr(cue.column)}
          )
      if self.row_status_column is not None and self.row_status_column not in names:
        raise PydanticCustomError(
          'E302', 'row_status_column {name} is not a column', {'name': repr(self.row_status_column)}
        )
    return self


class Rendition(AssetRef):
  """One file format of a figure.

  Parameters
  ----------
  format : {'png', 'pdf', 'svg'}
      The format; must match the file suffix, and is taken from it when left out.
  """

  format: FigureFormat

  @model_validator(mode='before')
  @classmethod
  def _suffix(cls, data: Any, info: ValidationInfo) -> Any:
    """Fill ``format`` from the suffix of ``path`` when it is not given."""
    if isinstance(data, str) and RESOLVER_CONTEXT_KEY in (info.context or {}):
      data = {'path': data}
    if isinstance(data, dict) and 'format' not in data and isinstance(data.get('path'), str):
      data = {**data, 'format': data['path'].rpartition('.')[2]}
    return data

  @model_validator(mode='after')
  def _check_suffix(self) -> Rendition:
    """Require the path suffix to equal the declared format."""
    if not self.path.endswith(f'.{self.format}'):
      raise PydanticCustomError(
        'E205', 'rendition path {path} does not end with .{format}', self.model_dump()
      )
    return self


class FigureValue(Model):
  """A figure with one or more renditions, required alt text and optional sidecar data.

  Parameters
  ----------
  kind : {'figure'}
      The kind tag.
  renditions : list of Rendition
      At least one, at most one per format. LaTeX output prefers PDF, then PNG; SVG is never
      used in LaTeX.
  alt : str
      Alternative text. Required and not blank.
  caption : str or None
      Caption below the figure.
  width : float, default=1.0
      Width as a fraction of the frame, in (0, 1].
  data : AssetRef or None
      A ``.parquet`` or ``.csv`` sidecar with the data the figure was drawn from.
  """

  kind: Literal['figure']
  renditions: Annotated[list[Rendition], Field(min_length=1)]
  alt: Annotated[str, Field(min_length=1)]
  caption: str | None = None
  width: Fraction = 1.0
  data: AssetRef | None = None

  @model_validator(mode='after')
  def _check(self) -> FigureValue:
    """Reject blank alt text, repeated formats and a sidecar that is not tabular."""
    if not self.alt.strip():
      raise PydanticCustomError('E205', 'alt text must not be blank')
    formats = [rendition.format for rendition in self.renditions]
    if len(set(formats)) != len(formats):
      raise PydanticCustomError('E205', 'each figure format may appear only once')
    if self.data is not None and not self.data.path.endswith(('.parquet', '.csv')):
      raise PydanticCustomError('E205', 'figure sidecar data must be a .parquet or .csv file')
    return self


class ImageValue(Model):
  """A picture that is not generated from data (a logo, a photo, a diagram).

  Parameters
  ----------
  kind : {'image'}
      The kind tag.
  asset : AssetRef
      A ``.png``, ``.jpg``, ``.jpeg``, ``.svg`` or ``.pdf`` file in ``assets/images/``.
  alt : str or None
      Alternative text; None marks a decorative image.
  caption : str or None
      Caption below the image.
  width : float, default=1.0
      Width as a fraction of the frame, in (0, 1].
  """

  kind: Literal['image']
  asset: AssetRef
  alt: str | None = None
  caption: str | None = None
  width: Fraction = 1.0

  @model_validator(mode='after')
  def _check(self) -> ImageValue:
    """Require a known image suffix."""
    if self.asset.path.rpartition('.')[2].lower() not in ImageSuffix:
      raise PydanticCustomError(
        'E205', 'image asset must end with one of {suffixes}', {'suffixes': ', '.join(ImageSuffix)}
      )
    return self


class MathValue(Model):
  """A mathematical expression in LaTeX.

  Parameters
  ----------
  kind : {'math'}
      The kind tag.
  latex : str
      The expression, without ``$`` delimiters.
  display : bool, default=True
      Display (own line) rather than inline style.
  numbered : bool, default=False
      Whether a display equation gets a number.
  caption : str or None
      Text below the equation.
  """

  kind: Literal['math']
  latex: Annotated[str, Field(min_length=1)]
  display: bool = True
  numbered: bool = False
  caption: str | None = None


class CodeValue(Model):
  """Source code or preformatted text: inline ``source`` or a file in ``assets/text/``.

  Parameters
  ----------
  kind : {'code'}
      The kind tag.
  source : str or None
      The code, inline. Exactly one of ``source`` and ``asset`` is given.
  asset : AssetRef or None
      A text file.
  language : str or None
      Language name for highlighting (``'python'``, ``'sql'``); none means preformatted text.
  caption : str or None
      Text below the block.
  """

  kind: Literal['code']
  source: str | None = None
  asset: AssetRef | None = None
  language: str | None = None
  caption: str | None = None

  @model_validator(mode='after')
  def _check(self) -> CodeValue:
    """Enforce one source."""
    _one_of('code', source=self.source, asset=self.asset)
    return self


def canonicalise(raw: Any) -> Any:
  """Turn bare JSON into a typed envelope; leave envelopes and models alone.

  Idempotent: canonicalising an envelope returns it unchanged. Values that match no rule are
  returned as they are and fail validation with an error that names the problem.

  Parameters
  ----------
  raw : Any
      A bare JSON scalar, list or object, a date, a model or an envelope dict.

  Returns
  -------
  Any
      An envelope dict (or the model or unrecognised input, unchanged).
  """
  if raw is None:
    return {'kind': 'number', 'value': None}
  if isinstance(raw, BaseModel):
    return raw
  if isinstance(raw, bool):
    return {'kind': 'bool', 'value': raw}
  if isinstance(raw, int | float):
    return {'kind': 'number', 'value': raw}
  if isinstance(raw, str):
    return {'kind': 'text', 'text': raw, 'format': 'plain'}
  if isinstance(raw, dt.date):
    return {'kind': 'date', 'value': raw.isoformat()}
  if isinstance(raw, list | tuple):
    return {'kind': 'list', 'items': list(raw)}
  if isinstance(raw, Mapping):
    if 'kind' in raw:
      return raw
    return {
      'kind': 'mapping',
      'entries': [{'key': key, 'value': value} for key, value in raw.items()],
    }
  return raw


class MetricItem(Model):
  """One tile of a :class:`MetricsValue`.

  Parameters
  ----------
  label : str
      What the tile measures.
  value : NumberValue or TextValue
      The headline value; a bare number or string is canonicalised.
  detail : str or None
      A line of context under the value.
  """

  label: Annotated[str, Field(min_length=1)]
  value: Annotated[
    NumberValue | TextValue, Field(discriminator='kind'), BeforeValidator(canonicalise)
  ]
  detail: str | None = None


class MetricsValue(Model):
  """A grid of headline numbers.

  Parameters
  ----------
  kind : {'metrics'}
      The kind tag.
  items : list of MetricItem
      At least one tile, in display order.
  """

  kind: Literal['metrics']
  items: Annotated[list[MetricItem], Field(min_length=1)]


class StatusValue(Model):
  """An overall verdict banner.

  Parameters
  ----------
  kind : {'status'}
      The kind tag.
  level : {'success', 'warning', 'partial', 'failed', 'running'}
      The verdict.
  headline : str
      One line, for example ``COMPLETED SUCCESSFULLY``.
  detail : str or None
      Explanation under the headline.
  """

  kind: Literal['status']
  level: StatusLevel
  headline: Annotated[str, Field(min_length=1)]
  detail: str | None = None


class AlertValue(Model):
  """A one-line call-out.

  Parameters
  ----------
  kind : {'alert'}
      The kind tag.
  level : {'info', 'warning', 'error'}
      Severity.
  text : str
      The message.
  """

  kind: Literal['alert']
  level: AlertLevel
  text: Annotated[str, Field(min_length=1)]


class FlowStage(Model):
  """One stage of a :class:`FlowValue`.

  Parameters
  ----------
  label : str
      Stage name.
  detail : list of str
      Lines of detail under the name.
  state : {'done', 'reused', 'skipped', 'failed', 'running', 'pending'}, default='done'
      How the stage ended.
  """

  label: Annotated[str, Field(min_length=1)]
  detail: list[str] = []
  state: FlowState = 'done'


class FlowValue(Model):
  """A pipeline drawn as numbered stages.

  Parameters
  ----------
  kind : {'flow'}
      The kind tag.
  stages : list of FlowStage
      At least one stage, numbered from 1 in order.
  """

  kind: Literal['flow']
  stages: Annotated[list[FlowStage], Field(min_length=1)]


class AttachmentValue(Model):
  """A file offered alongside the report (for example the full table behind a cut one).

  Parameters
  ----------
  kind : {'attachment'}
      The kind tag.
  asset : AssetRef
      The file in ``assets/attachments/``.
  filename : str
      Name shown to the reader and used on download: no path separators.
  media_type : str or None
      MIME type, for example ``text/csv``.
  description : str or None
      What the file contains.
  """

  kind: Literal['attachment']
  asset: AssetRef
  filename: Annotated[str, Field(min_length=1)]
  media_type: str | None = None
  description: str | None = None

  @model_validator(mode='after')
  def _check(self) -> AttachmentValue:
    """Require a plain file name."""
    if _FILENAME_RE.fullmatch(self.filename) is None or self.filename in ('.', '..'):
      raise PydanticCustomError('E205', 'filename must not contain path separators')
    return self


Envelope = (
  TextValue
  | NumberValue
  | BoolValue
  | DateValue
  | ListValue
  | MappingValue
  | TableValue
  | FigureValue
  | ImageValue
  | MathValue
  | CodeValue
  | MetricsValue
  | StatusValue
  | AlertValue
  | FlowValue
  | AttachmentValue
)

type Value = Annotated[Envelope, Field(discriminator='kind'), BeforeValidator(canonicalise)]
"""A report value: any v1.0 kind, accepting bare JSON as shorthand."""

KINDS: tuple[str, ...] = (
  'text',
  'number',
  'bool',
  'date',
  'list',
  'mapping',
  'table',
  'figure',
  'image',
  'math',
  'code',
  'metrics',
  'status',
  'alert',
  'flow',
  'attachment',
)
"""Every v1.0 kind tag, in the order of the specification."""

value_adapter: TypeAdapter[Any] = TypeAdapter(Value)
"""Validates one value, bare or enveloped: ``value_adapter.validate_python(raw)``."""
