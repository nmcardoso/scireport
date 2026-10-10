"""The ``Report`` builder: collect values, tables, figures and attachments, then write a bundle.

Typical use::

    report = Report('Cross-match report', authors=['N. Cardoso'], version='1.1.0')
    report.add_number('crossmatch.n_pairs', 3061, format='int')
    report.add_table('crossmatch.pairs', table, caption='Matched pairs')
    report.add_figure('crossmatch.separations', fig, alt='Histogram of pair separations')
    report.write('out/crossmatch.scireport.zip')

Nothing here reads the clock or the environment: the same calls always produce the same bytes.
"""

from __future__ import annotations

import datetime as dt
import functools
import io
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, ParamSpec, TypeVar

from pydantic import ValidationError

from scireport._version import __version__
from scireport.bundle.backends import MANIFEST_NAME, MemoryBackend
from scireport.bundle.reader import Bundle
from scireport.bundle.writer import WriteForm, write_bundle
from scireport.errors import Issue, KeyConflictError, SpecError
from scireport.hashing import sha256_bytes
from scireport.spec.assets import ASSET_ROOT, AssetRef, asset_path_problem
from scireport.spec.keys import find_prefix_conflicts, is_valid_key, suggest_key
from scireport.spec.kinds import (
  AlertValue,
  AttachmentValue,
  BoolValue,
  CellEmphasis,
  CodeValue,
  Column,
  DateValue,
  Envelope,
  FigureValue,
  FlowStage,
  FlowValue,
  ImageValue,
  ListValue,
  MappingEntry,
  MappingValue,
  MathValue,
  MetricItem,
  MetricsValue,
  NumberValue,
  Rendition,
  StatusValue,
  TableValue,
  TextValue,
  value_adapter,
)
from scireport.spec.manifest import (
  Author,
  Generator,
  InputRef,
  Manifest,
  Meta,
  OutlineNode,
  PreprocessStep,
  Provenance,
  Render,
  check_manifest,
  issues_from_validation_error,
  manifest_to_json,
)
from scireport.spec.version import SPEC_VERSION

if TYPE_CHECKING:
  import pyarrow as pa

INLINE_TEXT_BYTES = 4096
"""Text longer than this many UTF-8 bytes is stored as an asset unless the caller says otherwise."""

_MEDIA_TYPES = {
  'csv': 'text/csv',
  'json': 'application/json',
  'md': 'text/markdown',
  'txt': 'text/plain',
  'parquet': 'application/vnd.apache.parquet',
  'pdf': 'application/pdf',
  'png': 'image/png',
  'zip': 'application/zip',
}
_TEXT_SUFFIX = {'plain': 'txt', 'markdown': 'md', 'latex': 'tex'}
_ZSTD_LEVEL = 9

_P = ParamSpec('_P')
_R = TypeVar('_R')


def _coded(*, values: bool) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
  """Decorate a ``Report`` method so pydantic errors surface as coded ``SpecError``.

  Parameters
  ----------
  values : bool
      True for ``add_*`` methods whose first argument is the value key; the key then prefixes
      the JSON pointer of each issue.

  Returns
  -------
  callable
      The decorator.
  """

  def decorator(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @functools.wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
      try:
        return func(*args, **kwargs)
      except ValidationError as exc:
        key = args[1] if values and len(args) > 1 and isinstance(args[1], str) else None
        issues = issues_from_validation_error(exc, None)
        if key is not None:
          prefix = '/values/' + key.replace('~', '~0').replace('/', '~1')
          issues = [replace(issue, pointer=prefix + issue.pointer, key=key) for issue in issues]
        raise SpecError(issues) from None

    return wrapper

  return decorator


class Report:
  """Builds a report bundle in memory.

  Parameters
  ----------
  title : str
      Report title.
  subtitle, version, pipeline, footer, abstract : str or None, default=None
      Document metadata, as in :class:`~scireport.spec.manifest.Meta`.
  authors : iterable of str or dict or Author, default=()
      Authors in order; a string is a name.
  date : str or datetime.date or None, default=None
      Report date. Never filled in automatically.
  keywords : iterable of str, default=()
      Keywords.
  language : str, default='en'
      BCP 47 language tag.
  generator : tuple of (str, str) or None, default=None
      Name and version of the program that produced the content, for the provenance block.
  """

  def __init__(
    self,
    title: str,
    *,
    subtitle: str | None = None,
    authors: Iterable[str | Mapping[str, Any] | Author] = (),
    date: str | dt.date | None = None,
    version: str | None = None,
    pipeline: str | None = None,
    footer: str | None = None,
    abstract: str | None = None,
    keywords: Iterable[str] = (),
    language: str = 'en',
    generator: tuple[str, str] | None = None,
  ) -> None:
    self._meta: dict[str, Any] = {
      'title': title,
      'subtitle': subtitle,
      'authors': list(authors),
      'date': date.isoformat() if isinstance(date, dt.date) else date,
      'version': version,
      'pipeline': pipeline,
      'footer': footer,
      'abstract': abstract,
      'keywords': list(keywords),
      'language': language,
    }
    self._generator = generator
    self._render = Render()
    self._outline: list[OutlineNode] | None = None
    self._preprocess: list[PreprocessStep] = []
    self._inputs: list[InputRef] = []
    self._values: dict[str, Envelope] = {}
    self._assets: dict[str, bytes] = {}

  @property
  def keys(self) -> list[str]:
    """The keys added so far, sorted."""
    return sorted(self._values)

  @_coded(values=False)
  def set_render(self, **options: Any) -> Report:
    """Set fields of the ``render`` block (template, layout, formats, engines, options).

    Parameters
    ----------
    **options : Any
        Fields of :class:`~scireport.spec.manifest.Render`; unspecified fields are kept.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    self._render = Render.model_validate({**self._render.model_dump(), **options})
    return self

  @_coded(values=False)
  def set_outline(self, nodes: Sequence[str | Mapping[str, Any] | OutlineNode]) -> Report:
    """Set the outline used by the ``generic`` template.

    Parameters
    ----------
    nodes : sequence
        Keys (leaves) and ``{'title': ..., 'children': [...]}`` headings.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    self._outline = [OutlineNode.model_validate(node) for node in nodes]
    return self

  @_coded(values=False)
  def add_preprocess(
    self,
    name: str,
    *,
    inputs: Mapping[str, str] | None = None,
    outputs: Mapping[str, str] | None = None,
    params: Mapping[str, Any] | None = None,
    version: int | None = None,
    id: str | None = None,
  ) -> Report:
    """Declare a pre-processing step to run when the report is rendered.

    Parameters
    ----------
    name : str
        Registered pre-processor name.
    inputs, outputs : mapping or None
        Port name to value key.
    params : mapping or None
        JSON parameters.
    version : int or None
        Pre-processor version the step was written for.
    id : str or None
        Identifier for the step.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    self._preprocess.append(
      PreprocessStep.model_validate(
        {
          'name': name,
          'version': version,
          'id': id,
          'inputs': dict(inputs or {}),
          'outputs': dict(outputs or {}),
          'params': dict(params or {}),
        }
      )
    )
    return self

  @_coded(values=False)
  def add_input(self, name: str, *, sha256: str | None = None, uri: str | None = None) -> Report:
    """Record an input of the computation in the provenance block.

    Parameters
    ----------
    name : str
        A label such as a file name.
    sha256 : str or None
        SHA-256 of the input file.
    uri : str or None
        Where the input came from.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    self._inputs.append(InputRef(name=name, sha256=sha256, uri=uri))
    return self

  @_coded(values=True)
  def add(self, key: str, value: Any) -> Report:
    """Add any value: a bare JSON shorthand, an envelope dict or a value model.

    Parameters
    ----------
    key : str
        The value's key.
    value : Any
        What :func:`~scireport.spec.kinds.canonicalise` accepts. A value that refers to asset
        files cannot be added this way; use the typed ``add_*`` methods.

    Returns
    -------
    Report
        ``self``, for chaining.

    Raises
    ------
    KeyConflictError
        When the key is already used or is a prefix of another key (``E104``, ``E102``).
    SpecError
        When the key is malformed or the value invalid.
    """
    return self._put(key, value_adapter.validate_python(value))

  @_coded(values=True)
  def add_text(
    self,
    key: str,
    text: str,
    *,
    format: Literal['plain', 'markdown', 'latex'] = 'plain',
    alt: Mapping[Literal['html', 'md'], str] | None = None,
    as_asset: bool | None = None,
  ) -> Report:
    """Add prose or a short string.

    Parameters
    ----------
    key : str
        The value's key.
    text : str
        The content.
    format : {'plain', 'markdown', 'latex'}, default='plain'
        How the content is marked up.
    alt : mapping or None
        For ``latex``, the replacement for HTML and Markdown output.
    as_asset : bool or None, default=None
        Store as a file in ``assets/text/``. None stores texts over ``INLINE_TEXT_BYTES`` bytes as
        files and shorter ones inline.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    data = text.encode('utf-8')
    if as_asset or (as_asset is None and len(data) > INLINE_TEXT_BYTES):
      ref = self._put_asset('text', f'{key}.{_TEXT_SUFFIX[format]}', data)
      return self._put(
        key, TextValue(kind='text', asset=ref, format=format, alt=dict(alt or {}) or None)
      )
    return self._put(
      key, TextValue(kind='text', text=text, format=format, alt=dict(alt or {}) or None)
    )

  @_coded(values=True)
  def add_number(
    self,
    key: str,
    value: int | float | None,
    *,
    unit: str | None = None,
    format: str | None = None,
    uncertainty: float | None = None,
    interval: tuple[float, float] | None = None,
    missing: str | None = None,
  ) -> Report:
    """Add a number. NaN is stored as a missing number; infinities are an error.

    Parameters
    ----------
    key : str
        The value's key.
    value : int or float or None
        The number; None or NaN means missing.
    unit, format, missing : str or None
        As in :class:`~scireport.spec.kinds.NumberValue`.
    uncertainty : float or None
        Symmetric uncertainty.
    interval : tuple of (float, float) or None
        Asymmetric interval.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    return self._put(
      key,
      NumberValue(
        kind='number',
        value=_finite_or_none(value),
        unit=unit,
        format=format,
        uncertainty=uncertainty,
        interval=interval,
        missing=missing,
      ),
    )

  @_coded(values=True)
  def add_bool(self, key: str, value: bool) -> Report:
    """Add a boolean.

    Parameters
    ----------
    key : str
        The value's key.
    value : bool
        The truth value.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    return self._put(key, BoolValue(kind='bool', value=value))

  @_coded(values=True)
  def add_date(self, key: str, value: str | dt.date) -> Report:
    """Add a date or date-time.

    Parameters
    ----------
    key : str
        The value's key.
    value : str or datetime.date
        An ISO 8601 string, a date or a datetime.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    text = value.isoformat() if isinstance(value, dt.date) else value
    return self._put(key, DateValue(kind='date', value=text))

  @_coded(values=True)
  def add_list(self, key: str, items: Iterable[Any], *, ordered: bool = False) -> Report:
    """Add a list; items may be bare JSON, envelopes or value models.

    Parameters
    ----------
    key : str
        The value's key.
    items : iterable
        The members.
    ordered : bool, default=False
        Number the items when rendered.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    return self._put(
      key,
      ListValue.model_validate({'kind': 'list', 'items': list(items), 'ordered': ordered}),
    )

  @_coded(values=True)
  def add_mapping(self, key: str, entries: Mapping[str, Any] | Iterable[tuple[str, Any]]) -> Report:
    """Add labelled entries (a description list), in the order given.

    Parameters
    ----------
    key : str
        The value's key.
    entries : mapping or iterable of (label, value)
        Display labels with their values (bare JSON, envelopes or models).

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    pairs = entries.items() if isinstance(entries, Mapping) else entries
    return self._put(
      key,
      MappingValue.model_validate(
        {
          'kind': 'mapping',
          'entries': [MappingEntry.model_validate({'key': k, 'value': v}) for k, v in pairs],
        }
      ),
    )

  @_coded(values=True)
  def add_table(
    self,
    key: str,
    data: Any,
    *,
    columns: Iterable[str | Mapping[str, Any] | Column] | None = None,
    caption: str | None = None,
    format: Literal['parquet', 'csv'] = 'parquet',
    inline: bool = False,
    row_status: Sequence[Literal['pass', 'warn', 'fail'] | None] | None = None,
    row_status_column: str | None = None,
    emphasis: Iterable[CellEmphasis | Mapping[str, Any]] = (),
    max_rows: int | None = None,
    overflow_attachment: str | None = None,
  ) -> Report:
    """Add a table.

    Parameters
    ----------
    key : str
        The value's key.
    data : Any
        A pyarrow ``Table``, a pandas or other DataFrame (anything with an Arrow interface), a
        mapping of column name to values, or a list of row dicts.
    columns : iterable or None, default=None
        Column presentation (names, dicts or :class:`~scireport.spec.kinds.Column`); defaults to
        the data's columns, in order.
    caption : str or None
        Caption below the table.
    format : {'parquet', 'csv'}, default='parquet'
        File format when the table is stored as an asset (Parquet uses zstd).
    inline : bool, default=False
        Store the rows in the manifest instead; only for small tables of JSON scalars.
    row_status : sequence or None
        Per-row verdicts for an inline table.
    row_status_column : str or None
        Data column holding the verdicts.
    emphasis : iterable
        Cells to emphasise.
    max_rows : int or None
        Show at most this many rows.
    overflow_attachment : str or None
        Key of the attachment with the full table.

    Returns
    -------
    Report
        ``self``, for chaining.

    Raises
    ------
    SpecError
        With ``E301`` when an inline table holds a value that is not a JSON scalar.
    """
    table = to_arrow_table(data)
    cols = (
      [_column(column) for column in columns]
      if columns is not None
      else [Column(name=name) for name in table.column_names]
    )
    common: dict[str, Any] = {
      'kind': 'table',
      'columns': cols,
      'caption': caption,
      'n_rows': table.num_rows,
      'row_status': list(row_status) if row_status is not None else None,
      'row_status_column': row_status_column,
      'emphasis': [CellEmphasis.model_validate(cue) for cue in emphasis],
      'max_rows': max_rows,
      'overflow_attachment': overflow_attachment,
    }
    if inline:
      names = [column.name for column in cols]
      return self._put(
        key, TableValue.model_validate({**common, 'rows': _inline_rows(table, names)})
      )
    ref = self._put_asset('tables', f'{key}.{format}', serialise_table(table, format))
    return self._put(key, TableValue.model_validate({**common, 'asset': ref}))

  @_coded(values=True)
  def add_figure(
    self,
    key: str,
    figure: Any,
    *,
    alt: str,
    caption: str | None = None,
    width: float = 1.0,
    data: Any = None,
    formats: Sequence[Literal['png', 'pdf', 'svg']] = ('png', 'pdf'),
    dpi: float = 200,
  ) -> Report:
    """Add a figure with its sidecar data.

    Parameters
    ----------
    key : str
        The value's key.
    figure : Any
        A matplotlib ``Figure`` (rendered to ``formats`` with metadata stripped, so the bytes do
        not depend on the clock), a mapping of format to ``bytes`` or ``Path``, or one ``Path``
        whose suffix gives the format.
    alt : str
        Alternative text; required and not blank.
    caption : str or None
        Caption below the figure.
    width : float, default=1.0
        Width as a fraction of the frame.
    data : Any, optional
        The data the figure was drawn from, anything :meth:`add_table` takes; stored as a
        sidecar Parquet file.
    formats : sequence of {'png', 'pdf', 'svg'}, default=('png', 'pdf')
        Formats to render a matplotlib figure to.
    dpi : float, default=200
        Resolution of the PNG rendition.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    renditions: list[Rendition] = []
    for fmt, content in _figure_files(figure, formats, dpi).items():
      ref = self._put_asset('figures', f'{key}.{fmt}', content)
      renditions.append(Rendition.model_validate({**ref.model_dump(), 'format': fmt}))
    sidecar = None
    if data is not None:
      sidecar = self._put_asset(
        'figures', f'{key}.data.parquet', serialise_table(to_arrow_table(data), 'parquet')
      )
    return self._put(
      key,
      FigureValue(
        kind='figure',
        renditions=renditions,
        alt=alt,
        caption=caption,
        width=width,
        data=sidecar,
      ),
    )

  @_coded(values=True)
  def add_image(
    self,
    key: str,
    source: Path | str | bytes,
    *,
    suffix: str | None = None,
    alt: str | None = None,
    caption: str | None = None,
    width: float = 1.0,
  ) -> Report:
    """Add a picture that is not generated from data.

    Parameters
    ----------
    key : str
        The value's key.
    source : pathlib.Path or str or bytes
        An image file, or its bytes together with ``suffix``.
    suffix : str or None
        ``png``, ``jpg``, ``jpeg``, ``svg`` or ``pdf``; taken from the file name when None.
    alt : str or None
        Alternative text; None marks a decorative image.
    caption : str or None
        Caption below the image.
    width : float, default=1.0
        Width as a fraction of the frame.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    data, ext = _file_content(source, suffix)
    ref = self._put_asset('images', f'{key}.{ext}', data)
    return self._put(
      key, ImageValue(kind='image', asset=ref, alt=alt, caption=caption, width=width)
    )

  @_coded(values=True)
  def add_math(
    self,
    key: str,
    latex: str,
    *,
    display: bool = True,
    numbered: bool = False,
    caption: str | None = None,
  ) -> Report:
    """Add a LaTeX expression.

    Parameters
    ----------
    key : str
        The value's key.
    latex : str
        The expression, without ``$`` delimiters.
    display : bool, default=True
        Display style on its own line.
    numbered : bool, default=False
        Number a display equation.
    caption : str or None
        Text below the equation.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    return self._put(
      key,
      MathValue(kind='math', latex=latex, display=display, numbered=numbered, caption=caption),
    )

  @_coded(values=True)
  def add_code(
    self,
    key: str,
    source: str,
    *,
    language: str | None = None,
    caption: str | None = None,
    as_asset: bool | None = None,
  ) -> Report:
    """Add source code or preformatted text.

    Parameters
    ----------
    key : str
        The value's key.
    source : str
        The code.
    language : str or None
        Language name for highlighting.
    caption : str or None
        Text below the block.
    as_asset : bool or None, default=None
        As for :meth:`add_text`.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    data = source.encode('utf-8')
    if as_asset or (as_asset is None and len(data) > INLINE_TEXT_BYTES):
      ref = self._put_asset('text', f'{key}.txt', data)
      return self._put(key, CodeValue(kind='code', asset=ref, language=language, caption=caption))
    return self._put(key, CodeValue(kind='code', source=source, language=language, caption=caption))

  @_coded(values=True)
  def add_metrics(
    self, key: str, items: Iterable[MetricItem | Mapping[str, Any] | tuple[Any, ...]]
  ) -> Report:
    """Add a grid of headline numbers.

    Parameters
    ----------
    key : str
        The value's key.
    items : iterable
        :class:`~scireport.spec.kinds.MetricItem`, dicts with ``label``, ``value`` and
        ``detail``, or tuples ``(label, value)`` / ``(label, value, detail)``.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    tiles = [
      MetricItem.model_validate(
        dict(zip(('label', 'value', 'detail'), item, strict=False))
        if isinstance(item, tuple)
        else item
      )
      for item in items
    ]
    return self._put(key, MetricsValue(kind='metrics', items=tiles))

  @_coded(values=True)
  def add_status(
    self,
    key: str,
    level: Literal['success', 'warning', 'partial', 'failed', 'running'],
    headline: str,
    detail: str | None = None,
  ) -> Report:
    """Add an overall verdict banner.

    Parameters
    ----------
    key : str
        The value's key.
    level : {'success', 'warning', 'partial', 'failed', 'running'}
        The verdict.
    headline : str
        One line.
    detail : str or None
        Explanation under the headline.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    return self._put(key, StatusValue(kind='status', level=level, headline=headline, detail=detail))

  @_coded(values=True)
  def add_alert(self, key: str, level: Literal['info', 'warning', 'error'], text: str) -> Report:
    """Add a one-line call-out.

    Parameters
    ----------
    key : str
        The value's key.
    level : {'info', 'warning', 'error'}
        Severity.
    text : str
        The message.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    return self._put(key, AlertValue(kind='alert', level=level, text=text))

  @_coded(values=True)
  def add_flow(self, key: str, stages: Iterable[FlowStage | Mapping[str, Any] | str]) -> Report:
    """Add a pipeline drawn as numbered stages.

    Parameters
    ----------
    key : str
        The value's key.
    stages : iterable
        :class:`~scireport.spec.kinds.FlowStage`, dicts, or a bare string for a stage label.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    built = [
      FlowStage.model_validate({'label': stage} if isinstance(stage, str) else stage)
      for stage in stages
    ]
    return self._put(key, FlowValue(kind='flow', stages=built))

  @_coded(values=True)
  def add_attachment(
    self,
    key: str,
    source: Path | str | bytes,
    *,
    filename: str | None = None,
    media_type: str | None = None,
    description: str | None = None,
  ) -> Report:
    """Add a file offered alongside the report.

    Parameters
    ----------
    key : str
        The value's key.
    source : pathlib.Path or str or bytes
        The file, or its bytes together with ``filename``.
    filename : str or None
        Name shown to the reader; the file's own name when ``source`` is a path.
    media_type : str or None
        MIME type; a fixed table for common suffixes is used when None (never the system's).
    description : str or None
        What the file contains.

    Returns
    -------
    Report
        ``self``, for chaining.
    """
    if isinstance(source, bytes):
      if filename is None:
        raise ValueError('add_attachment needs filename= when given bytes')
      data = source
    else:
      data = Path(source).read_bytes()
      filename = filename or Path(source).name
    ext = filename.rpartition('.')[2].lower() if '.' in filename else ''
    name = f'{key}.{ext}' if ext.isalnum() and len(ext) <= 10 else key
    ref = self._put_asset('attachments', name, data)
    return self._put(
      key,
      AttachmentValue(
        kind='attachment',
        asset=ref,
        filename=filename,
        media_type=media_type or _MEDIA_TYPES.get(ext),
        description=description,
      ),
    )

  def manifest(self) -> Manifest:
    """Assemble and fully check the manifest.

    Returns
    -------
    Manifest
        The manifest as it would be written.

    Raises
    ------
    SpecError
        Carrying every cross-reference problem (``E102``, ``E103``, ``E202``, ``E411``).
    """
    manifest = Manifest(
      scireport=SPEC_VERSION,
      meta=Meta.model_validate(self._meta),
      render=self._render,
      outline=self._outline,
      values=dict(self._values),
      preprocess=list(self._preprocess),
      provenance=Provenance(
        generator=Generator(name=self._generator[0], version=self._generator[1])
        if self._generator
        else None,
        writer=f'scireport {__version__}',
        inputs=list(self._inputs),
      ),
    )
    problems = check_manifest(manifest)
    if problems:
      raise SpecError(problems)
    return manifest

  def build(self) -> Bundle:
    """Assemble the report into an in-memory bundle.

    Returns
    -------
    Bundle
        A bundle over memory; write it with :func:`~scireport.bundle.writer.write_bundle`.
    """
    manifest = self.manifest()
    files = {MANIFEST_NAME: manifest_to_json(manifest).encode('utf-8'), **self._assets}
    return Bundle(manifest, MemoryBackend(files), form='directory')

  def write(
    self, dest: Path | str, *, form: WriteForm | None = None, overwrite: bool = False
  ) -> Path:
    """Build the report and write it.

    Parameters
    ----------
    dest : pathlib.Path or str
        ``*.scireport.zip`` for a ZIP, anything else for a directory, ``*.json`` for a
        single-file manifest (a report without assets).
    form : {'directory', 'zip', 'file'} or None
        Overrides the form inferred from ``dest``.
    overwrite : bool, default=False
        Replace an existing destination.

    Returns
    -------
    pathlib.Path
        ``dest``.
    """
    return write_bundle(self.build(), dest, form=form, overwrite=overwrite)

  def _put(self, key: str, value: Envelope) -> Report:
    """Register a value under a checked key."""
    if not is_valid_key(key):
      hint = suggest_key(key) if isinstance(key, str) else None
      raise SpecError(
        [
          Issue(
            'E101',
            f'invalid key {key!r}: segments must match [a-z0-9_-]+ and be joined by single dots',
            key=str(key),
            hint=f'Did you mean {hint!r}?' if hint else None,
          )
        ]
      )
    if key in self._values:
      raise KeyConflictError(f'key {key!r} is already in use', code='E104')
    clash = find_prefix_conflicts([*self._values, key])
    if clash:
      prefix, longer = clash[0]
      raise KeyConflictError(
        f'key {prefix!r} would hold a value and also be the prefix of {longer!r}', code='E102'
      )
    self._values[key] = value
    return self

  def _put_asset(self, folder: str, name: str, data: bytes) -> AssetRef:
    """Store asset bytes under ``assets/<folder>/<name>`` and return the reference."""
    path = f'{ASSET_ROOT}/{folder}/{name}'
    problem = asset_path_problem(path)
    if problem is not None:
      raise SpecError([Issue('E404', f'invalid asset path {path!r}: {problem}')])
    self._assets[path] = data
    return AssetRef(path=path, sha256=sha256_bytes(data), bytes=len(data))


def to_arrow_table(data: Any) -> pa.Table:
  """Convert tabular input to a pyarrow table with no schema metadata.

  Parameters
  ----------
  data : Any
      A pyarrow ``Table``; a pandas DataFrame (the index is dropped); any object with an Arrow
      stream interface (polars, ...); a mapping of column name to values; or a list of row dicts.

  Returns
  -------
  pyarrow.Table
      The data, without the pandas or other metadata that would make the bytes depend on the
      library that produced it.

  Raises
  ------
  TypeError
      When ``data`` is none of these.
  """
  import pyarrow as pa

  if isinstance(data, pa.Table):
    table = data
  elif type(data).__module__.partition('.')[0] == 'pandas':
    table = pa.Table.from_pandas(data, preserve_index=False)
  elif hasattr(data, '__arrow_c_stream__'):
    table = pa.table(data)
  elif isinstance(data, Mapping):
    table = pa.table({str(name): list(values) for name, values in data.items()})
  elif isinstance(data, Sequence) and not isinstance(data, str | bytes):
    table = pa.Table.from_pylist(list(data))
  else:
    raise TypeError(f'cannot make a table from {type(data).__name__}')
  return table.replace_schema_metadata(None)


def serialise_table(table: pa.Table, format: Literal['parquet', 'csv']) -> bytes:
  """Write a pyarrow table to Parquet (zstd) or CSV bytes.

  Parameters
  ----------
  table : pyarrow.Table
      The table.
  format : {'parquet', 'csv'}
      Target format.

  Returns
  -------
  bytes
      The file content; identical for identical input and library versions.
  """
  import pyarrow.csv as pacsv
  import pyarrow.parquet as pq

  sink = io.BytesIO()
  if format == 'parquet':
    pq.write_table(table, sink, compression='zstd', compression_level=_ZSTD_LEVEL)
  else:
    pacsv.write_csv(table, sink)
  return sink.getvalue()


def _column(column: str | Mapping[str, Any] | Column) -> Column:
  """Build a ``Column`` from a name, a dict or a ``Column``."""
  if isinstance(column, str):
    return Column(name=column)
  return Column.model_validate(column)


def _finite_or_none(value: int | float | None) -> int | float | None:
  """Map NaN to None; reject infinities."""
  if isinstance(value, float):
    if math.isnan(value):
      return None
    if math.isinf(value):
      raise ValueError('infinite numbers cannot be stored; use None for a missing number')
  return value


def _inline_rows(table: pa.Table, names: list[str]) -> list[list[Any]]:
  """Convert a table to JSON-scalar rows in the order of ``names``."""
  columns = table.to_pydict()
  missing = [name for name in names if name not in columns]
  if missing:
    raise SpecError([Issue('E302', f'columns {missing} are not in the data')])
  rows: list[list[Any]] = []
  for index in range(table.num_rows):
    row: list[Any] = []
    for name in names:
      cell = columns[name][index]
      if isinstance(cell, float) and math.isnan(cell):
        cell = None
      if cell is not None and not isinstance(cell, str | int | float | bool):
        raise SpecError(
          [
            Issue(
              'E301',
              f'column {name!r} holds {type(cell).__name__} values; an inline table takes JSON '
              'scalars only',
              hint='Store the table as Parquet (inline=False).',
            )
          ]
        )
      row.append(cell)
    rows.append(row)
  return rows


def _file_content(source: Path | str | bytes, suffix: str | None) -> tuple[bytes, str]:
  """Return the bytes and lower-case suffix of an image source."""
  if isinstance(source, bytes):
    if suffix is None:
      raise ValueError('bytes need suffix= to say what kind of image they are')
    return source, suffix.lstrip('.').lower()
  path = Path(source)
  return path.read_bytes(), (suffix or path.suffix).lstrip('.').lower()


def _figure_files(figure: Any, formats: Sequence[str], dpi: float) -> dict[str, bytes]:
  """Produce the renditions of a figure as bytes, keyed by format."""
  if hasattr(figure, 'savefig'):
    return {fmt: _render_figure(figure, fmt, dpi) for fmt in formats}
  if isinstance(figure, Mapping):
    files = {fmt: _read(content) for fmt, content in figure.items()}
  else:
    path = Path(figure)
    files = {path.suffix.lstrip('.').lower(): path.read_bytes()}
  return files


def _read(content: bytes | Path | str) -> bytes:
  """Return bytes as they are, or read a file."""
  return content if isinstance(content, bytes) else Path(content).read_bytes()


def _render_figure(figure: Any, fmt: str, dpi: float) -> bytes:
  """Render a matplotlib figure with the metadata that would make the bytes vary removed."""
  from scireport.styles.figures import figure_bytes

  return figure_bytes(figure, fmt, dpi=round(dpi), tight=False)  # type: ignore[arg-type]
