from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.corner import compute_corner
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(7)
_BASE = _RNG.normal(0.0, 1.0, 300)
TABLE = {
  'a': list(_BASE),
  'b': list(_BASE + _RNG.normal(0.0, 0.5, 300)),
  'c': list(_RNG.normal(2.0, 1.0, 300)),
}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  value = _figure(result)
  assert value.data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def _panels(data: pa.Table) -> list[str]:
  return list(dict.fromkeys(data.column('panel').to_pylist()))


def test_figure(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.corner',
    {'data': TABLE},
    params={'columns': ['a', 'b', 'c'], 'bins': 10, 'gridsize': 8, 'height': 4.0},
    min_sidecar_rows=10,
  )


def test_panel_layout_of_the_sidecar() -> None:
  data = compute_corner(pa.table(TABLE), ['a', 'b', 'c'], bins=5)
  assert _panels(data) == [
    'hist:a',
    'hist:b',
    'hist:c',
    'pair:a:b',
    'pair:a:c',
    'pair:b:c',
  ]
  assert data.column_names == [
    'panel', 'kind', 'x', 'y', 'n', 'dx', 'dy', 'left', 'right', 'count'
  ]  # fmt: skip
  panel, kind = data.column('panel').to_pylist(), data.column('kind').to_pylist()
  bars = [k == 'bar' for p, k in zip(panel, kind, strict=True) if p == 'hist:a']
  assert len(bars) == 5 and all(bars)
  assert set(kind) == {'bar', 'hex', 'point'}


def test_histogram_counts_on_a_hand_checked_example() -> None:
  table = pa.table({'u': [0.0, 1.0, 1.0, 2.0, None], 'v': [0.0, 0.0, 1.0, 1.0, 5.0]})
  data = compute_corner(table, ['u', 'v'], bins=2, threshold=10)
  panel = data.column('panel').to_pylist()
  hist = data.filter(pa.array([p == 'hist:u' for p in panel]))
  assert hist.column('left').to_pylist() == [0.0, 1.0]
  assert hist.column('right').to_pylist() == [1.0, 2.0]
  assert hist.column('count').to_pylist() == [1.0, 3.0]
  pair = data.filter(pa.array([p == 'pair:u:v' for p in panel]))
  # the row with a null u is dropped; the four other pairs remain as points (threshold 10)
  assert pair.num_rows == 4
  assert set(pair.column('kind').to_pylist()) == {'point'}


def test_an_empty_pair_is_marked() -> None:
  table = pa.table({'u': [1.0, 2.0, None], 'v': [None, None, 3.0], 'w': [1.0, 2.0, 3.0]})
  data = compute_corner(table, ['u', 'v', 'w'])
  panel, kind = data.column('panel').to_pylist(), data.column('kind').to_pylist()
  assert [k for p, k in zip(panel, kind, strict=True) if p == 'pair:u:v'] == ['empty']


def test_nine_columns_is_a_parameter_error(tmp_path: Path) -> None:
  names = [f'c{i}' for i in range(9)]
  table = {name: list(_BASE[:20]) for name in names}
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.corner', {'data': table}, params={'columns': names})
  assert caught.value.code == 'E602'
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.corner', {'data': TABLE}, params={'columns': ['a']})
  assert caught.value.code == 'E602'


def test_eight_columns_are_accepted(tmp_path: Path) -> None:
  names = [f'c{i}' for i in range(8)]
  rng = np.random.default_rng(1)
  table = {name: list(rng.normal(0.0, 1.0, 60)) for name in names}
  check_figure_preprocessor(
    tmp_path, 'core.corner', {'data': table}, params={'columns': names, 'gridsize': 5}
  )


def test_repeated_column_is_an_error(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.corner', {'data': TABLE}, params={'columns': ['a', 'a']})
  assert caught.value.code == 'E602'


def test_all_null_input_draws_a_placeholder(tmp_path: Path) -> None:
  table = {'a': [None, None], 'b': [None, None]}
  result = run_step(tmp_path, 'core.corner', {'data': table}, params={'columns': ['a', 'b']})
  sidecar = _sidecar(result)
  assert set(sidecar.column('kind').to_pylist()) == {'empty'}


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.corner', {'data': TABLE}, params={'columns': ['a', 'bb']})
  assert caught.value.code == 'E603'
  assert "'b'" in str(caught.value)
