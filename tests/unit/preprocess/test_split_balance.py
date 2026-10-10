from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.split_balance import compute_split_balance
from scireport.spec.kinds import FigureValue

LONG = {
  'arm': ['train'] * 4 + ['val'] * 4 + ['test'] * 4,
  'label': ['q1', 'q2', 'q3', 'q4'] * 3,
  'n': [70, 20, 8, 2, 10, 3, 1, 1, 12, 5, 2, 1],
}
PARAMS = {'arm_column': 'arm', 'bin_column': 'label', 'count_column': 'n'}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  data = _figure(result).data
  assert data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(data)))


def test_balance(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.split_balance',
    {'data': LONG},
    params={**PARAMS, 'stratifier': 'class', 'split': 'dev'},
    min_sidecar_rows=12,
  )
  assert 'train, val, test' in value.alt and '4 bins' in value.alt


def test_title_changes_the_drawing(tmp_path: Path) -> None:
  titled = run_step(
    tmp_path, 'core.split_balance', {'data': LONG}, params={**PARAMS, 'split': 'dev'}
  )
  untitled = run_step(
    tmp_path,
    'core.split_balance',
    {'data': LONG},
    params={**PARAMS, 'split': 'dev', 'title': ''},
    label='untitled',
  )
  assert _figure(titled).renditions[0].sha256 != _figure(untitled).renditions[0].sha256


def test_compute_hand_checked() -> None:
  data = compute_split_balance(pa.table(LONG), 'arm', 'label', 'n')
  assert data.column_names == ['arm', 'position', 'bin', 'count', 'share']
  assert data.column('arm').to_pylist() == ['train'] * 4 + ['val'] * 4 + ['test'] * 4
  assert data.column('bin').to_pylist() == ['q1', 'q2', 'q3', 'q4'] * 3
  assert data.column('share').to_pylist()[:4] == pytest.approx([0.7, 0.2, 0.08, 0.02])
  assert data.column('share').to_pylist()[4:8] == pytest.approx([10 / 15, 3 / 15, 1 / 15, 1 / 15])


def test_compute_sums_repeated_rows_and_nulls() -> None:
  table = pa.table({'a': ['x', 'x', 'x', 'y'], 'b': [0, 0, 1, 1], 'n': [1, 2, None, 5]})
  data = compute_split_balance(table, 'a', 'b', 'n')
  assert data.column('count').to_pylist() == [3.0, 0.0, 0.0, 5.0]
  assert data.column('share').to_pylist() == [1.0, 0.0, 0.0, 1.0]


def test_one_bin_draws_a_placeholder(tmp_path: Path) -> None:
  table = {'arm': ['train', 'val'], 'label': ['q1', 'q1'], 'n': [10, 1]}
  result = run_step(tmp_path, 'core.split_balance', {'data': table}, params=PARAMS)
  assert _figure(result).kind == 'figure'
  assert _sidecar(result).num_rows == 2


def test_empty_table_draws_a_placeholder(tmp_path: Path) -> None:
  table = pa.table(
    {
      'arm': pa.array([], pa.string()),
      'label': pa.array([], pa.string()),
      'n': pa.array([], pa.int64()),
    }
  )
  result = run_step(tmp_path, 'core.split_balance', {'data': table}, params=PARAMS)
  assert _figure(result).alt == 'No arms were recorded.'
  assert _sidecar(result).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.split_balance', {'data': LONG}, params={**PARAMS, 'count_column': 'm'})
  assert caught.value.code == 'E603'
