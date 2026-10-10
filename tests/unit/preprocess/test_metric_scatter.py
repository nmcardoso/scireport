from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.metric_scatter import compute_metric_scatter
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(5)
_LEFT = _RNG.uniform(0.2, 1.0, 300)
_RIGHT = _LEFT + _RNG.normal(0.0, 0.03, 300)
METRIC = {'left': list(_LEFT), 'right': list(_RIGHT)}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  value = _figure(result)
  assert value.data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def test_figure(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.metric_scatter',
    {'data': METRIC},
    params={'x_column': 'left', 'y_column': 'right', 'gridsize': 12, 'title': 'SSIM'},
    min_sidecar_rows=5,
  )


def test_line_rows_hold_the_end_points() -> None:
  table = pa.table({'l': [1.0, 2.0, 3.0, None], 'r': [0.5, 2.5, 3.0, 9.0]})
  data = compute_metric_scatter(table, 'l', 'r', gridsize=4, threshold=3)
  kinds = data.column('kind').to_pylist()
  assert kinds.count('line') == 2
  line = data.filter(pa.array([kind == 'line' for kind in kinds]))
  # lowest value of either column is 0.5, highest is 3.0 (the row with a null is dropped)
  assert line.column('x').to_pylist() == [0.5, 3.0]
  assert line.column('y').to_pylist() == [0.5, 3.0]
  assert data.column('n').to_pylist()[:3] == [1.0, 1.0, 1.0]
  assert kinds[:3] == ['point', 'point', 'point']


def test_the_line_is_drawn(tmp_path: Path) -> None:
  without = run_step(
    tmp_path,
    'core.metric_scatter',
    {'data': METRIC},
    params={'x_column': 'left', 'y_column': 'right'},
    label='with',
  )
  sidecar = _sidecar(without)
  assert sidecar.column('kind').to_pylist().count('line') == 2


def test_all_null_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'core.metric_scatter',
    {'data': {'left': [None], 'right': [None]}},
    params={'x_column': 'left', 'y_column': 'right'},
  )
  sidecar = _sidecar(result)
  assert sidecar.num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.metric_scatter',
      {'data': METRIC},
      params={'x_column': 'lefft', 'y_column': 'right'},
    )
  assert caught.value.code == 'E603'
  assert 'left' in str(caught.value)
