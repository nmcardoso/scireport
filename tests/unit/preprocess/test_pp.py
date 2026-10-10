from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess.core.pp import compute_pp

_RNG = np.random.default_rng(4)
SAMPLES = {
  'left': list(_RNG.normal(0.0, 1.0, 300)),
  'right': list(_RNG.normal(0.3, 1.2, 250)) + [None] * 50,
}


def test_against_a_normal_distribution(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.pp',
    {'data': SAMPLES},
    params={'column': 'left', 'x_label': 'Normal CDF', 'y_label': 'left CDF'},
    min_sidecar_rows=300,
  )
  assert 'standard normal' in value.alt


def test_against_a_second_sample(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.pp',
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


def test_max_points_caps_the_sidecar() -> None:
  table = pa.table(SAMPLES)
  assert compute_pp(table, 'left', max_points=40).num_rows == 40
  assert compute_pp(table, 'left', reference_column='right', max_points=40).num_rows == 40


def test_two_sample_cdfs_are_hand_checked() -> None:
  table = pa.table({'a': [1.0, 2.0, 3.0, 4.0], 'b': [2.0, 4.0, 6.0, 8.0]})
  data = compute_pp(table, 'a', reference_column='b')
  assert data.column_names == ['value', 'x', 'y']
  assert data.column('value').to_pylist() == pytest.approx([1.0, 10 / 3, 17 / 3, 8.0])
  assert data.column('x').to_pylist() == pytest.approx([0.0, 0.25, 0.5, 1.0])
  assert data.column('y').to_pylist() == pytest.approx([0.25, 0.75, 1.0, 1.0])


def test_normal_cdfs_are_hand_checked() -> None:
  data = compute_pp(pa.table({'a': [-1.0, 0.0, 1.0]}), 'a')
  # Standardised values are +-sqrt(3/2) = 1.2247449 and 0; Phi(1.2247449) = 0.8896.
  assert data.column('x').to_pylist() == pytest.approx([0.1104, 0.5, 0.8896], abs=1e-4)
  assert data.column('y').to_pylist() == pytest.approx([1 / 3, 2 / 3, 1.0])


def test_identical_samples_lie_on_the_diagonal() -> None:
  table = pa.table({'a': [1.0, 2.0, 3.0, 4.0], 'b': [1.0, 2.0, 3.0, 4.0]})
  data = compute_pp(table, 'a', reference_column='b')
  assert data.column('x').to_pylist() == data.column('y').to_pylist()


def test_empty_sample_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path, 'core.pp', {'data': {'value': [None, None]}}, params={'column': 'value'}
  )
  fig = result.bundle.manifest.values['fig']
  assert fig.kind == 'figure'
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.pp', {'data': SAMPLES}, params={'column': 'rigth'})
  assert caught.value.code == 'E603'
  assert 'right' in str(caught.value)
