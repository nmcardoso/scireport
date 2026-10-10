from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.achieved_vs_target import compute_achieved_vs_target
from scireport.spec.kinds import FigureValue

PAIRS = {
  'tier': ['a', 'b', 'c', 'd'],
  'got': [1000.0, 52.0, 3.5, 0.0],
  'want': [None, 50.0, 4.0, 1.0],
}
PARAMS = {'label_column': 'tier', 'achieved_column': 'got', 'target_column': 'want'}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  data = _figure(result).data
  assert data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(data)))


def test_pairs(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.achieved_vs_target',
    {'data': PAIRS},
    params={**PARAMS, 'title': 'Tiers', 'x_label': 'Rows'},
    min_sidecar_rows=4,
  )
  assert 'got' in value.alt and 'want' in value.alt


def test_explicit_height(tmp_path: Path) -> None:
  tall = run_step(
    tmp_path, 'core.achieved_vs_target', {'data': PAIRS}, params={**PARAMS, 'height': 6.0}
  )
  auto = run_step(tmp_path, 'core.achieved_vs_target', {'data': PAIRS}, params=PARAMS, label='auto')
  assert _figure(tall).renditions[0].sha256 != _figure(auto).renditions[0].sha256


def test_compute_keeps_nulls_and_order() -> None:
  data = compute_achieved_vs_target(pa.table(PAIRS), 'tier', 'got', 'want')
  assert data.column_names == ['label', 'achieved', 'target']
  assert data.column('label').to_pylist() == ['a', 'b', 'c', 'd']
  assert data.column('achieved').to_pylist() == [1000.0, 52.0, 3.5, 0.0]
  assert data.column('target').to_pylist() == [None, 50.0, 4.0, 1.0]


def test_all_zero_values_still_draw(tmp_path: Path) -> None:
  table = {'tier': ['a', 'b'], 'got': [0, 0], 'want': [None, None]}
  check_figure_preprocessor(tmp_path, 'core.achieved_vs_target', {'data': table}, params=PARAMS)


def test_empty_table_draws_a_placeholder(tmp_path: Path) -> None:
  table = pa.table(
    {'tier': pa.array([], pa.string()), 'got': pa.array([], pa.float64()),
     'want': pa.array([], pa.float64())}
  )  # fmt: skip
  result = run_step(tmp_path, 'core.achieved_vs_target', {'data': table}, params=PARAMS)
  assert _figure(result).alt.startswith('No rows')
  assert _sidecar(result).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.achieved_vs_target',
      {'data': PAIRS},
      params={**PARAMS, 'target_column': 'wnat'},
    )
  assert caught.value.code == 'E603'
  assert 'want' in str(caught.value)
