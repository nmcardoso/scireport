"""The context a pre-processor runs in: its inputs, the style, the seed, and where results go.

A pre-processor never touches the bundle or the file system. It asks the context for values and
tables, draws inside the layout's style, and hands figures and tables back through
``save_figure`` and ``save_table``, which return the value envelopes to put in the result. The
runner collects the asset files the context holds and decides where they are stored.
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal

from scireport.errors import Issue, PreprocessError
from scireport.hashing import sha256_bytes
from scireport.logging_utils import get_logger
from scireport.preprocess.look import Look
from scireport.report import serialise_table, to_arrow_table
from scireport.spec.assets import ASSET_ROOT, AssetRef, asset_path_problem
from scireport.spec.kinds import Column, Envelope, FigureValue, Rendition, TableValue

if TYPE_CHECKING:
  import numpy as np
  import pyarrow as pa
  from matplotlib.figure import Figure

  from scireport.bundle.reader import Bundle

_FIGURE_DPI = 200


def derive_seed(base: int, label: str) -> int:
  """Derive the seed of one step from the run's base seed and the step's label.

  Parameters
  ----------
  base : int
      The seed of the whole run.
  label : str
      The step's id, or its name and position when it has no id.

  Returns
  -------
  int
      A 63-bit non-negative integer, the same for the same inputs on every machine.
  """
  digest = hashlib.sha256(f'{base}:{label}'.encode()).digest()
  return int.from_bytes(digest[:8], 'big') >> 1


class Context:
  """What a pre-processor sees of the run.

  Parameters
  ----------
  bundle : Bundle
      The input bundle (read only).
  produced : dict
      Values made by earlier steps of this run, by key; they are visible to later steps.
  outputs : dict
      Port name to the value key this step's results are stored under.
  layout : str
      The layout whose matplotlib style and colours apply.
  seed : int
      The step's seed; see :func:`derive_seed`.
  name : str
      The pre-processor's name, for the logger.
  """

  def __init__(
    self,
    *,
    bundle: Bundle,
    produced: Mapping[str, Envelope],
    outputs: Mapping[str, str],
    layout: str,
    seed: int,
    name: str,
  ) -> None:
    self._bundle = bundle
    self._produced = produced
    self._outputs = outputs
    self._assets: dict[str, bytes] = {}
    self._tables: dict[str, pa.Table] = {}
    self.layout = layout
    self.seed = seed
    self.log: logging.Logger = get_logger(f'scireport.preprocess.{name}')

  @cached_property
  def look(self) -> Look:
    """The chart colours of the layout, to hand to a drawing function."""
    return Look.of_layout(self.layout)

  def rng(self) -> np.random.Generator:
    """Return a random generator seeded with :attr:`seed`.

    Returns
    -------
    numpy.random.Generator
        A fresh generator; two calls give the same stream.
    """
    import numpy as np

    return np.random.default_rng(self.seed)

  def value(self, key: str) -> Envelope:
    """Return the value stored under ``key``, including values made by earlier steps.

    Parameters
    ----------
    key : str
        A value key.

    Returns
    -------
    Envelope
        The value model.

    Raises
    ------
    PreprocessError
        With ``E603`` when there is no such value.
    """
    if key in self._produced:
      return self._produced[key]
    try:
      return self._bundle.manifest.values[key]
    except KeyError:
      raise PreprocessError([Issue('E603', f'no value with key {key!r}', key=key)]) from None

  def load_table(self, key: str) -> pa.Table:
    """Return a table value as a pyarrow table.

    Parameters
    ----------
    key : str
        Key of a ``table`` value.

    Returns
    -------
    pyarrow.Table
        The data, read from the bundle or from an earlier step of this run.

    Raises
    ------
    PreprocessError
        With ``E603`` when the key is missing or the value is not a table.
    """
    value = self.value(key)
    if not isinstance(value, TableValue):
      raise PreprocessError(
        [Issue('E603', f'{key!r} is a {value.kind}, not a table', key=key, expected='table')]
      )
    if key in self._tables:
      return self._tables[key]
    return self._bundle.read_table(key)

  @contextmanager
  def mplstyle(self) -> Iterator[None]:
    """Apply the matplotlib style of the layout while a ``with`` block runs.

    Yields
    ------
    None
        Draw inside the block; the parameters are restored on exit.
    """
    from scireport.styles import mplstyle

    with mplstyle(self.layout):
      yield

  def figure(
    self,
    width: float = 1.0,
    height: float = 3.6,
    nrows: int = 1,
    ncols: int = 1,
    *,
    subplot_kw: dict[str, Any] | None = None,
  ) -> tuple[Figure, Any]:
    """Create a figure at its final size, as a fraction of the page frame.

    Parameters
    ----------
    width : float, default=1.0
        Width as a fraction of the frame (clamped to 1).
    height : float, default=3.6
        Height in inches.
    nrows, ncols : int, default=1
        The grid of axes.
    subplot_kw : dict or None, default=None
        Passed to every subplot, for example ``{'projection': 'mollweide'}``.

    Returns
    -------
    tuple
        The figure and its axes (an array for a grid).
    """
    from scireport.styles import figure

    return figure(width, height, nrows, ncols, layout=self.layout, subplot_kw=subplot_kw)

  def save_figure(
    self,
    figure: Figure,
    *,
    data: Any,
    alt: str,
    caption: str | None = None,
    width: float = 1.0,
    port: str = 'figure',
    formats: Sequence[Literal['png', 'pdf', 'svg']] = ('png', 'pdf'),
  ) -> FigureValue:
    """Store a figure with the data it was drawn from.

    The data is required: a figure in a bundle must be rebuildable from its sidecar file.

    Parameters
    ----------
    figure : matplotlib.figure.Figure
        The drawn figure.
    data : Any
        What :func:`~scireport.report.to_arrow_table` takes: a table, a mapping of columns, or
        a list of row dicts.
    alt : str
        Alternative text; required and not blank.
    caption : str or None, default=None
        Caption below the figure.
    width : float, default=1.0
        Width as a fraction of the frame, as it was drawn.
    port : str, default='figure'
        The output port this figure belongs to; its key comes from the step's ``outputs``.
    formats : sequence of {'png', 'pdf', 'svg'}, default=('png', 'pdf')
        The renditions to store.

    Returns
    -------
    FigureValue
        The value to return under ``port``.

    Raises
    ------
    PreprocessError
        With ``E603`` when the step has no key for ``port``.
    """
    from scireport.styles.figures import figure_bytes

    key = self._key(port)
    renditions: list[Rendition] = []
    for fmt in formats:
      with self.mplstyle():
        content = figure_bytes(figure, fmt, dpi=_FIGURE_DPI, tight=False)
      ref = self._put('figures', f'{key}.{fmt}', content)
      renditions.append(Rendition.model_validate({**ref.model_dump(), 'format': fmt}))
    sidecar = self._put(
      'figures', f'{key}.data.parquet', serialise_table(to_arrow_table(data), 'parquet')
    )
    return FigureValue(
      kind='figure', renditions=renditions, alt=alt, caption=caption, width=width, data=sidecar
    )

  def save_table(
    self,
    data: Any,
    *,
    port: str = 'table',
    columns: Sequence[str | Mapping[str, Any] | Column] | None = None,
    caption: str | None = None,
    format: Literal['parquet', 'csv'] = 'parquet',
  ) -> TableValue:
    """Store a table.

    Parameters
    ----------
    data : Any
        What :func:`~scireport.report.to_arrow_table` takes.
    port : str, default='table'
        The output port this table belongs to.
    columns : sequence or None, default=None
        Column presentation; defaults to the data's columns in order.
    caption : str or None, default=None
        Caption below the table.
    format : {'parquet', 'csv'}, default='parquet'
        File format.

    Returns
    -------
    TableValue
        The value to return under ``port``.
    """
    table = to_arrow_table(data)
    key = self._key(port)
    cols = [
      column
      if isinstance(column, Column)
      else Column.model_validate({'name': column})
      if isinstance(column, str)
      else Column.model_validate(column)
      for column in (columns if columns is not None else table.column_names)
    ]
    ref = self._put('tables', f'{key}.{format}', serialise_table(table, format))
    self._tables[key] = table
    return TableValue(kind='table', columns=cols, asset=ref, caption=caption, n_rows=table.num_rows)

  def take_assets(self) -> dict[str, bytes]:
    """Return the asset files stored so far and forget them; the runner calls this.

    Returns
    -------
    dict
        Bundle-relative path to content.
    """
    assets, self._assets = self._assets, {}
    return assets

  def _key(self, port: str) -> str:
    """Return the value key of an output port or raise ``E603``."""
    try:
      return self._outputs[port]
    except KeyError:
      raise PreprocessError(
        [
          Issue(
            'E603',
            f'the step has no output key for port {port!r}',
            expected=f'one of {sorted(self._outputs)}',
            found=port,
          )
        ]
      ) from None

  def _put(self, folder: str, name: str, data: bytes) -> AssetRef:
    """Hold an asset file and return its reference."""
    path = f'{ASSET_ROOT}/{folder}/{name}'
    problem = asset_path_problem(path)
    if problem is not None:
      raise PreprocessError([Issue('E603', f'invalid asset path {path!r}: {problem}')])
    self._assets[path] = data
    return AssetRef(path=path, sha256=sha256_bytes(data), bytes=len(data))
