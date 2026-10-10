from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess.core.heatmap import compute_heatmap

_RNG = np.random.default_rng(5)
_ROWS = [f'object-{i}' for i in range(5)]
_COLUMNS = ['f1', 'f2', 'f3', 'f4']
LONG = {
  'row': [r for r in _ROWS for _ in _COLUMNS],
  'flag': [c for _ in _ROWS for c in _COLUMNS],
  'value': list(_RNG.normal(0.0, 1.0, 20)),
}
PARAMS: dict[str, Any] = {'row_column': 'row', 'column_column': 'flag', 'value_column': 'value'}
SMALL = pa.table({'r': ['b', 'a', 'b'], 'c': ['y', 'x', 'x'], 'v': [3.0, 1.0, None]})


def test_sequential(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.heatmap',
    {'data': LONG},
    params={**PARAMS, 'colorbar_label': 'value', 'row_label': 'Object', 'column_label': 'Flag'},
    min_sidecar_rows=20,
  )


def test_diverging_symmetric_with_annotations(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.heatmap',
    {'data': LONG},
    params={
      **PARAMS,
      'cmap': 'diverging',
      'symmetric': True,
      'annotate': True,
      'value_format': '.1f',
      'square': True,
      'title': 'Matrix',
    },
    min_sidecar_rows=20,
  )


def test_log_scale_with_blank_cells(tmp_path: Path) -> None:
  table = {
    'r': ['a', 'a', 'b', 'c'],
    'c': ['x', 'y', 'y', 'x'],
    'v': [1.0, 100.0, 0.0, None],
  }
  check_figure_preprocessor(
    tmp_path,
    'core.heatmap',
    {'data': table},
    params={
      'row_column': 'r',
      'column_column': 'c',
      'value_column': 'v',
      'log': True,
      'vmin': 1.0,
      'vmax': 100.0,
      'annotate': False,
    },
    min_sidecar_rows=4,
  )


def test_long_labels_and_fixed_height(tmp_path: Path) -> None:
  table = {
    'r': ['first row', 'second row'],
    'c': ['a very long column name', 'another long column name'],
    'v': [1.0, 2.0],
  }
  check_figure_preprocessor(
    tmp_path,
    'core.heatmap',
    {'data': table},
    params={
      'row_column': 'r',
      'column_column': 'c',
      'value_column': 'v',
      'height': 2.5,
      'width': 0.6,
    },
  )


def test_orders_and_blank_cells_are_in_the_sidecar() -> None:
  data = compute_heatmap(SMALL, 'r', 'c', 'v', row_order=['a', 'b', 'z'], column_order=['x', 'y'])
  rows = data.to_pylist()
  assert data.column_names == ['row', 'column', 'value', 'row_index', 'column_index']
  # (a,x)=1, (b,x)=null, (b,y)=3 from the data, then the empty row z at column 0.
  assert [(r['row'], r['column'], r['value']) for r in rows] == [
    ('a', 'x', 1.0),
    ('b', 'x', None),
    ('b', 'y', 3.0),
    ('z', 'x', None),
  ]
  assert [(r['row_index'], r['column_index']) for r in rows] == [(0, 0), (1, 0), (1, 1), (2, 0)]


def test_first_appearance_order_is_the_default() -> None:
  data = compute_heatmap(SMALL, 'r', 'c', 'v')
  rows = data.to_pylist()
  assert [(r['row'], r['row_index']) for r in rows if r['column'] == 'y'] == [('b', 0)]
  assert {r['column']: r['column_index'] for r in rows} == {'y': 0, 'x': 1}
  assert {r['row']: r['row_index'] for r in rows} == {'b': 0, 'a': 1}


def test_labels_missing_from_an_order_are_dropped() -> None:
  data = compute_heatmap(SMALL, 'r', 'c', 'v', row_order=['a'])
  # Only (a, x) = 1 is kept; column y (first column by appearance) has no cell left.
  assert data.column('row').to_pylist() == ['a', 'a']
  assert data.column('column').to_pylist() == ['y', 'x']
  assert data.column('value').to_pylist() == [None, 1.0]


def test_a_repeated_cell_is_an_error() -> None:
  table = pa.table({'r': ['a', 'a'], 'c': ['x', 'x'], 'v': [1.0, 2.0]})
  with pytest.raises(PreprocessError) as caught:
    compute_heatmap(table, 'r', 'c', 'v')
  assert caught.value.code == 'E603'


def test_a_repeated_label_in_an_order_is_an_error() -> None:
  with pytest.raises(PreprocessError) as caught:
    compute_heatmap(SMALL, 'r', 'c', 'v', row_order=['a', 'a'])
  assert caught.value.code == 'E603'


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  table = {'r': ['a'], 'c': ['x'], 'v': [None]}
  result = run_step(
    tmp_path,
    'core.heatmap',
    {'data': table},
    params={'row_column': 'r', 'column_column': 'c', 'value_column': 'v'},
  )
  assert result.bundle.manifest.values['fig'].kind == 'figure'
  empty = run_step(
    tmp_path,
    'core.heatmap',
    {
      'data': {
        'r': pa.array([], pa.string()),
        'c': pa.array([], pa.string()),
        'v': pa.array([], pa.float64()),
      }
    },
    params={'row_column': 'r', 'column_column': 'c', 'value_column': 'v'},
    label='empty',
  )
  assert empty.bundle.manifest.values['fig'].kind == 'figure'


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.heatmap',
      {'data': LONG},
      params={**PARAMS, 'value_column': 'valeu'},
    )
  assert caught.value.code == 'E603'
  assert 'value' in str(caught.value)
