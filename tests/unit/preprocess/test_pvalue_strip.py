from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.pvalue_strip import compute_pvalue_strip
from scireport.spec.kinds import FigureValue

TESTS = {
  'test': ['train mag', 'val mag', 'test mag', 'tiny tier', 'extreme'],
  'p': [0.40, 1e-5, 0.03, None, 1e-30],
}
PARAMS = {'label_column': 'test', 'pvalue_column': 'p'}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _png_sha(tmp_path: Path, label: str, params: Mapping[str, object]) -> str:
  result = run_step(tmp_path, 'core.pvalue_strip', {'data': TESTS}, params=params, label=label)
  return str(_figure(result).renditions[0].sha256)


def test_strip(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path, 'core.pvalue_strip', {'data': TESTS}, params={**PARAMS, 'title': 'Chi-square'}
  )
  assert '5 tests' in value.alt
  assert '3 below it, 1 not computable' in value.alt


def test_alpha_parameter(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path, 'core.pvalue_strip', {'data': TESTS}, params={**PARAMS, 'alpha': 0.5}
  )
  assert 'alpha = 0.5' in value.alt


def test_compute_on_a_hand_checked_example() -> None:
  data = compute_pvalue_strip(pa.table(TESTS), 'test', 'p', alpha=0.05)
  assert data.column('label').to_pylist()[3] == 'tiny tier'
  assert data.column('pvalue').to_pylist() == [0.40, 1e-5, 0.03, None, 1e-30]
  assert data.column('significant').to_pylist() == [False, True, True, None, True]
  stricter = compute_pvalue_strip(pa.table(TESTS), 'test', 'p', alpha=0.01)
  assert stricter.column('significant').to_pylist() == [False, True, False, None, True]


def test_nan_is_not_computable() -> None:
  data = compute_pvalue_strip(pa.table({'t': ['a', 'b'], 'p': [float('nan'), 0.2]}), 't', 'p')
  assert data.column('pvalue').to_pylist() == [None, 0.2]
  assert data.column('significant').to_pylist() == [None, False]


def test_alpha_changes_the_drawing(tmp_path: Path) -> None:
  assert _png_sha(tmp_path, 'a', PARAMS) != _png_sha(tmp_path, 'b', {**PARAMS, 'alpha': 0.001})


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  empty = {'test': pa.array([], pa.string()), 'p': pa.array([], pa.float64())}
  result = run_step(tmp_path, 'core.pvalue_strip', {'data': empty}, params=PARAMS)
  fig = _figure(result)
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_all_null_still_draws(tmp_path: Path) -> None:
  nulls = {'test': ['a', 'b'], 'p': pa.array([None, None], pa.float64())}
  result = run_step(tmp_path, 'core.pvalue_strip', {'data': nulls}, params=PARAMS)
  assert _figure(result).data is not None


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path, 'core.pvalue_strip', {'data': TESTS}, params={**PARAMS, 'pvalue_column': 'pv'}
    )
  assert caught.value.code == 'E603'
  assert "'p'" in str(caught.value)
