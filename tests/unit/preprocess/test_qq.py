from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess.core.qq import compute_qq

_RNG = np.random.default_rng(3)
SAMPLES = {
  'left': list(_RNG.normal(0.0, 1.0, 300)),
  'right': list(_RNG.normal(0.3, 1.2, 250)) + [None] * 50,
}


def test_against_a_normal_distribution(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.qq',
    {'data': SAMPLES},
    params={'column': 'left', 'x_label': 'Normal quantiles', 'y_label': 'left quantiles'},
    min_sidecar_rows=300,
  )
  assert 'standard normal' in value.alt


def test_against_a_second_sample(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.qq',
    {'data': SAMPLES},
    params={
      'column': 'right',
      'reference_column': 'left',
      'x_label': 'left',
      'y_label': 'right',
      'title': 'Right against left',
    },
  )
  assert 'against left' in value.alt


def test_max_points_caps_the_sidecar(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.qq',
    {'data': SAMPLES},
    params={'column': 'left', 'max_points': 50, 'x_label': 'x', 'y_label': 'y'},
    min_sidecar_rows=50,
  )
  assert value.data is not None
  data = compute_qq(pa.table(SAMPLES), 'left', max_points=50)
  assert data.num_rows == 50


def test_two_sample_quantiles_are_hand_checked() -> None:
  table = pa.table({'a': [1.0, 2.0, 3.0, 4.0], 'b': [2.0, 4.0, 6.0, 8.0]})
  data = compute_qq(table, 'a', reference_column='b')
  assert data.column_names == ['level', 'x', 'y']
  assert data.column('level').to_pylist() == pytest.approx([0.0, 1 / 3, 2 / 3, 1.0])
  assert data.column('x').to_pylist() == pytest.approx([2.0, 4.0, 6.0, 8.0])
  assert data.column('y').to_pylist() == pytest.approx([1.0, 2.0, 3.0, 4.0])


def test_normal_quantiles_are_hand_checked() -> None:
  data = compute_qq(pa.table({'a': [1.0, 2.0, 3.0]}), 'a')
  # Plotting positions 1/6, 1/2, 5/6; the standard normal quantile at 5/6 is 0.9674216.
  assert data.column('x').to_pylist() == pytest.approx([-0.9674216, 0.0, 0.9674216], abs=1e-6)
  # The sample (1, 2, 3) has population standard deviation sqrt(2/3).
  assert data.column('y').to_pylist() == pytest.approx([-1.2247449, 0.0, 1.2247449], abs=1e-6)


def test_constant_sample_does_not_divide_by_zero() -> None:
  data = compute_qq(pa.table({'a': [5.0, 5.0, 5.0]}), 'a')
  assert data.column('y').to_pylist() == [0.0, 0.0, 0.0]


def test_empty_sample_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path, 'core.qq', {'data': {'value': [None, None]}}, params={'column': 'value'}
  )
  fig = result.bundle.manifest.values['fig']
  assert fig.kind == 'figure'
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_empty_reference_draws_a_placeholder() -> None:
  table = pa.table({'a': [1.0, 2.0], 'b': pa.array([None, None], pa.float64())})
  assert compute_qq(table, 'a', reference_column='b').num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.qq', {'data': SAMPLES}, params={'column': 'lef'})
  assert caught.value.code == 'E603'
  assert 'left' in str(caught.value)


def test_missing_reference_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path, 'core.qq', {'data': SAMPLES}, params={'column': 'left', 'reference_column': 'nope'}
    )
  assert caught.value.code == 'E603'
