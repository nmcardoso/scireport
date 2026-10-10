from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.density_scatter import compute_density_scatter

_RNG = np.random.default_rng(3)
_CORE = _RNG.normal(0.0, 1.0, (400, 2))
_OUTLIERS = np.array([[8.0, 8.0], [-8.0, 7.5], [7.0, -8.0]])
_XY = np.vstack([_CORE, _OUTLIERS])
SCATTER = {'a': list(_XY[:, 0]), 'b': list(_XY[:, 1])}


def _sidecar(result: PreprocessResult, key: str = 'fig') -> pa.Table:
  value = result.bundle.manifest.values[key]
  assert value.kind == 'figure' and value.data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def test_figure(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.density_scatter',
    {'data': SCATTER},
    params={'x_column': 'a', 'y_column': 'b', 'gridsize': 15, 'x_label': 'a', 'y_label': 'b'},
    min_sidecar_rows=5,
  )


def test_labels_default_to_the_column_names(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.density_scatter',
    {'data': SCATTER},
    params={'x_column': 'a', 'y_column': 'b', 'title': 'Density'},
    render_params={'x_label': 'a', 'y_label': 'b', 'title': 'Density'},
  )


def test_dense_cells_and_sparse_points_are_both_kept() -> None:
  data = compute_density_scatter(pa.table(SCATTER), 'a', 'b', gridsize=10, threshold=3)
  kinds = data.column('kind').to_pylist()
  assert 'hex' in kinds and 'point' in kinds
  # every pair is counted once, either in a cell or as a point
  assert sum(data.column('n').to_pylist()) == _XY.shape[0]
  points = [
    (x, y)
    for kind, x, y in zip(
      kinds, data.column('x').to_pylist(), data.column('y').to_pylist(), strict=True
    )
    if kind == 'point'
  ]
  for outlier in _OUTLIERS:
    assert any(np.allclose(outlier, point) for point in points)


def test_compute_on_a_hand_checked_example() -> None:
  # one dense corner (4 points, above the threshold of 3) and one lone point
  table = pa.table(
    {
      'x': [0.0, 0.0, 0.0, 0.0, 10.0, float('nan'), 5.0],
      'y': [0.0, 0.0, 0.0, 0.0, 10.0, 3.0, None],
    }
  )
  data = compute_density_scatter(table, 'x', 'y', gridsize=4, threshold=3)
  assert data.column('kind').to_pylist() == ['hex', 'point']
  assert data.column('n').to_pylist() == [4.0, 1.0]
  assert data.column('x').to_pylist()[1] == 10.0
  assert data.column('y').to_pylist()[1] == 10.0


def test_threshold_moves_points_into_cells() -> None:
  table = pa.table(SCATTER)
  loose = compute_density_scatter(table, 'a', 'b', gridsize=10, threshold=0)
  assert set(loose.column('kind').to_pylist()) == {'hex'}
  strict = compute_density_scatter(table, 'a', 'b', gridsize=10, threshold=10_000)
  assert set(strict.column('kind').to_pylist()) == {'point'}


def test_all_null_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'core.density_scatter',
    {'data': {'a': [None, None], 'b': [None, None]}},
    params={'x_column': 'a', 'y_column': 'b'},
  )
  assert result.bundle.manifest.values['fig'].kind == 'figure'
  sidecar = _sidecar(result)
  assert sidecar.num_rows == 0
  assert sidecar.column_names == ['kind', 'x', 'y', 'n', 'dx', 'dy']


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.density_scatter',
      {'data': SCATTER},
      params={'x_column': 'a', 'y_column': 'c'},
    )
  assert caught.value.code == 'E603'
