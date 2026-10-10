"""Shared checks for the pre-processor catalogue (``tests`` is on ``sys.path``).

Every figure pre-processor gets the same three tests through :func:`check_figure_preprocessor`:

* smoke: the step runs on a small fixture and stores a PNG, a PDF and sidecar data;
* determinism: a second run, in another work directory with an empty cache, gives byte-identical
  PNG, PDF and sidecar files;
* sidecar data: the figure drawn again from nothing but the stored sidecar data (through the
  pre-processor's ``render`` function) is byte-identical to the stored PNG.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from scireport import Report
from scireport.preprocess import Context, PreprocessResult, get_preprocessor, preprocess_bundle
from scireport.spec.kinds import FigureValue
from scireport.styles.figures import figure_bytes

PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def run_step(
  tmp_path: Path,
  name: str,
  tables: Mapping[str, Any],
  *,
  params: Mapping[str, Any] | None = None,
  inputs: Mapping[str, str] | None = None,
  outputs: Mapping[str, str] | None = None,
  label: str = 'run',
  cache: bool = True,
) -> PreprocessResult:
  """Build a bundle holding ``tables``, declare one step on it and run it.

  Parameters
  ----------
  tmp_path : pathlib.Path
      Scratch directory; the work directory and the cache go under ``<label>/``.
  name : str
      Pre-processor name.
  tables : dict
      Value key to table data (anything ``Report.add_table`` takes).
  params : dict or None
      The step's parameters.
  inputs : dict or None
      Port to key; by default the port ``table`` reads the first key of ``tables``.
  outputs : dict or None
      Port to key; by default ``figure`` is stored under ``fig``.
  label : str, default='run'
      Names the work and cache directories, so two runs do not share them.
  cache : bool, default=True
      Use the cache.

  Returns
  -------
  PreprocessResult
      The result of :func:`~scireport.preprocess.preprocess_bundle`.
  """
  report = Report(title='Fixture')
  for key, data in tables.items():
    report.add_table(key, data)
  report.add_preprocess(
    name,
    inputs=dict(inputs) if inputs is not None else {'table': next(iter(tables))},
    outputs=dict(outputs) if outputs is not None else {'figure': 'fig'},
    params=dict(params or {}),
  )
  return preprocess_bundle(
    report.build(),
    work_dir=tmp_path / label / 'work',
    cache_dir=tmp_path / label / 'cache',
    use_cache=cache,
  )


def check_figure_preprocessor(
  tmp_path: Path,
  name: str,
  tables: Mapping[str, Any],
  *,
  params: Mapping[str, Any] | None = None,
  inputs: Mapping[str, str] | None = None,
  outputs: Mapping[str, str] | None = None,
  key: str = 'fig',
  render_params: Mapping[str, Any] | None = None,
  min_sidecar_rows: int = 1,
) -> FigureValue:
  """Run the smoke, determinism and sidecar-data checks of one figure pre-processor.

  Parameters
  ----------
  tmp_path : pathlib.Path
      Scratch directory.
  name : str
      Pre-processor name.
  tables : dict
      Fixture tables by value key.
  params, inputs, outputs : dict or None
      As for :func:`run_step`.
  key : str, default='fig'
      The key the figure is stored under.
  render_params : dict or None
      The keyword arguments of the ``render`` function when they differ from the step's
      parameters (a default the step fills in, such as an axis label taken from a column name).
      By default the step's parameters that ``render`` accepts.
  min_sidecar_rows : int, default=1
      The least number of rows the sidecar table must have.

  Returns
  -------
  FigureValue
      The stored figure, for further assertions.
  """
  first = run_step(tmp_path, name, tables, params=params, inputs=inputs, outputs=outputs)
  value = first.bundle.manifest.values[key]
  assert isinstance(value, FigureValue)
  png_ref = next(item for item in value.renditions if item.format == 'png')
  pdf_ref = next(item for item in value.renditions if item.format == 'pdf')
  png = first.bundle.read_asset(png_ref)
  assert png.startswith(PNG_MAGIC)
  assert first.bundle.read_asset(pdf_ref).startswith(b'%PDF')
  assert value.alt.strip()
  assert value.data is not None
  sidecar_bytes = first.bundle.read_asset(value.data)
  sidecar = pq.read_table(pa.BufferReader(sidecar_bytes))
  assert sidecar.num_rows >= min_sidecar_rows

  second = run_step(
    tmp_path, name, tables, params=params, inputs=inputs, outputs=outputs, label='again'
  )
  again = second.bundle.manifest.values[key]
  assert isinstance(again, FigureValue)
  assert [r.sha256 for r in again.renditions] == [r.sha256 for r in value.renditions]
  assert again.data is not None and again.data.sha256 == value.data.sha256
  assert second.bundle.read_asset(png_ref) == png

  entry = get_preprocessor(name)
  assert entry.render is not None, f'{name} must register its render function'
  style = (
    dict(render_params)
    if render_params is not None
    else {
      param: value
      for param, value in (params or {}).items()
      if param in inspect.signature(entry.render).parameters
    }
  )
  ctx = Context(bundle=first.bundle, produced={}, outputs={}, layout='default', seed=0, name=name)
  rebuilt = entry.render(ctx, sidecar, **style)
  with ctx.mplstyle():
    assert figure_bytes(rebuilt, 'png', dpi=200, tight=False) == png
  return value
