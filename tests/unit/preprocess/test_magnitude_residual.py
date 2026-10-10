from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import Context, PreprocessResult
from scireport.preprocess.astro.magnitude_residual import (
  compute_magnitude_residual,
  render_magnitude_residual,
)
from scireport.spec.kinds import FigureValue


def _catalogue() -> dict[str, list[float]]:
  rng = np.random.default_rng(5)
  mag = rng.uniform(15.0, 22.0, 300)
  return {'published': list(mag), 'delta': list(rng.normal(0.0, 0.03, mag.size))}


CATALOGUE = _catalogue()
PARAMS = {'magnitude_column': 'published', 'residual_column': 'delta', 'gridsize': 15}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  value = _figure(result)
  assert value.data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def _png(result: PreprocessResult) -> bytes:
  ref = next(item for item in _figure(result).renditions if item.format == 'png')
  return bytes(result.bundle.read_asset(ref))


def _context(result: PreprocessResult) -> Context:
  return Context(
    bundle=result.bundle,
    produced={},
    produced_assets={},
    outputs={},
    layout='default',
    seed=0,
    name='astro.magnitude_residual',
  )


def test_figure(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path, 'astro.magnitude_residual', {'cat': CATALOGUE}, params=PARAMS
  )
  assert 'published' in value.alt and 'delta' in value.alt and '300 objects' in value.alt


def test_compute_on_a_hand_checked_example() -> None:
  # Ten identical points make one hexagon; two far-away points stay individual.
  table = pa.table(
    {'m': [0.0] * 10 + [10.0, 10.0], 'r': [0.0] * 10 + [5.0, 5.0], 'extra': [1.0] * 12}
  )
  data = compute_magnitude_residual(table, 'm', 'r', gridsize=10, threshold=3)
  assert data.column_names == ['kind', 'x', 'y', 'n', 'dx', 'dy']
  assert data.column('kind').to_pylist() == ['hex', 'point', 'point']
  assert data.column('n').to_pylist() == [10.0, 1.0, 1.0]
  assert data.column('x').to_pylist()[1:] == [10.0, 10.0]
  assert data.column('y').to_pylist()[1:] == [5.0, 5.0]


def test_non_finite_pairs_are_dropped() -> None:
  table = pa.table({'m': [1.0, None, 3.0, float('nan')], 'r': [0.1, 0.2, float('inf'), 0.4]})
  data = compute_magnitude_residual(table, 'm', 'r')
  assert data.num_rows == 1
  assert data.column('x').to_pylist() == [1.0]


def test_sparse_points_are_bounded() -> None:
  rng = np.random.default_rng(1)
  table = pa.table({'m': rng.uniform(0, 1, 20000), 'r': rng.normal(0, 1, 20000)})
  data = compute_magnitude_residual(table, 'm', 'r', gridsize=30, threshold=3)
  assert data.num_rows < 3000
  assert float(np.sum(data.column('n').to_numpy())) == 20000.0


def test_gridsize_and_title_change_the_drawing(tmp_path: Path) -> None:
  base = run_step(tmp_path, 'astro.magnitude_residual', {'cat': CATALOGUE}, params=PARAMS)
  coarse = run_step(
    tmp_path,
    'astro.magnitude_residual',
    {'cat': CATALOGUE},
    params={**PARAMS, 'gridsize': 6},
    label='coarse',
  )
  titled = run_step(
    tmp_path,
    'astro.magnitude_residual',
    {'cat': CATALOGUE},
    params={**PARAMS, 'title': 'Closure'},
    label='titled',
  )
  assert _sidecar(base).num_rows != _sidecar(coarse).num_rows
  assert _png(base) != _png(coarse)
  assert _png(base) != _png(titled)


def test_zero_line_and_labels_are_drawn(tmp_path: Path) -> None:
  result = run_step(tmp_path, 'astro.magnitude_residual', {'cat': CATALOGUE}, params=PARAMS)
  ax = render_magnitude_residual(_context(result), _sidecar(result), x_label='X').axes[0]
  assert ax.get_xlabel() == 'X'
  assert ax.get_ylabel() == 'Recovered - published (mag)'
  assert any(np.allclose(line.get_ydata(), 0.0) for line in ax.get_lines())


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'astro.magnitude_residual',
    {'cat': {'published': [None, None], 'delta': [None, None]}},
    params=PARAMS,
  )
  assert _sidecar(result).num_rows == 0
  figure = render_magnitude_residual(_context(result), _sidecar(result))
  assert [text.get_text() for text in figure.axes[0].texts] == ['No data']


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'astro.magnitude_residual',
      {'cat': CATALOGUE},
      params={'magnitude_column': 'publshed', 'residual_column': 'delta'},
    )
  assert caught.value.code == 'E603'
  assert 'published' in str(caught.value)
