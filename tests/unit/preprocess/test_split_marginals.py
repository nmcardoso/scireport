from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.split_marginals import compute_split_marginals
from scireport.spec.kinds import FigureValue

LONG = {
  'tier': ['full', 'full', 'full', 'dev', 'dev', 'dev'],
  'bin': [0, 1, 2, 0, 1, 2],
  'n': [6000, 3000, 1000, 60, 30, 10],
}
PARAMS = {'split_column': 'tier', 'bin_column': 'bin', 'count_column': 'n'}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  data = _figure(result).data
  assert data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(data)))


def test_marginals(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.split_marginals',
    {'data': LONG},
    params={**PARAMS, 'stratifier': 'redshift', 'reference': 'full'},
    min_sidecar_rows=6,
  )
  assert 'full, dev' in value.alt and '3 bins' in value.alt


def test_reference_changes_the_drawing(tmp_path: Path) -> None:
  plain = run_step(tmp_path, 'core.split_marginals', {'data': LONG}, params=PARAMS)
  highlighted = run_step(
    tmp_path,
    'core.split_marginals',
    {'data': LONG},
    params={**PARAMS, 'reference': 'full'},
    label='highlighted',
  )
  assert _figure(plain).renditions[0].sha256 != _figure(highlighted).renditions[0].sha256


def test_compute_hand_checked() -> None:
  data = compute_split_marginals(pa.table(LONG), 'tier', 'bin', 'n')
  assert data.column_names == ['split', 'position', 'bin', 'count', 'share']
  assert data.column('split').to_pylist() == ['full'] * 3 + ['dev'] * 3
  assert data.column('position').to_pylist() == [0, 1, 2, 0, 1, 2]
  assert data.column('share').to_pylist() == pytest.approx([0.6, 0.3, 0.1, 0.6, 0.3, 0.1])


def test_compute_fills_missing_bins_and_sorts_numbers() -> None:
  table = pa.table({'s': ['a', 'a', 'b', 'a'], 'b': [10, 2, 10, 2], 'n': [1, 2, 4, 1]})
  data = compute_split_marginals(table, 's', 'b', 'n')
  assert data.column('bin').to_pylist() == ['2', '10', '2', '10']
  assert data.column('count').to_pylist() == [3.0, 1.0, 0.0, 4.0]
  assert data.column('share').to_pylist() == [0.75, 0.25, 0.0, 1.0]


def test_compute_keeps_label_order_and_an_empty_split() -> None:
  table = pa.table({'s': ['a', 'a', 'b', 'b'], 'b': ['lo', 'hi', 'lo', 'hi'], 'n': [1, 3, 0, 0]})
  data = compute_split_marginals(table, 's', 'b', 'n')
  assert data.column('bin').to_pylist() == ['lo', 'hi', 'lo', 'hi']
  assert data.column('share').to_pylist() == [0.25, 0.75, 0.0, 0.0]


def test_one_bin_draws_a_placeholder(tmp_path: Path) -> None:
  table = {'tier': ['full', 'dev'], 'bin': [0, 0], 'n': [10, 1]}
  result = run_step(
    tmp_path, 'core.split_marginals', {'data': table}, params={**PARAMS, 'stratifier': 'mag'}
  )
  assert _figure(result).kind == 'figure'
  assert _sidecar(result).num_rows == 2


def test_empty_table_draws_a_placeholder(tmp_path: Path) -> None:
  table = pa.table(
    {
      'tier': pa.array([], pa.string()),
      'bin': pa.array([], pa.int64()),
      'n': pa.array([], pa.int64()),
    }
  )
  result = run_step(tmp_path, 'core.split_marginals', {'data': table}, params=PARAMS)
  assert _figure(result).alt == 'No split marginals were recorded.'
  assert _sidecar(result).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path, 'core.split_marginals', {'data': LONG}, params={**PARAMS, 'split_column': 'tir'}
    )
  assert caught.value.code == 'E603'
  assert 'tier' in str(caught.value)
