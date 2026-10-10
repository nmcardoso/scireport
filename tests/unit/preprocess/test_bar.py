from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.bar import compute_bar
from scireport.spec.kinds import FigureValue

COUNTS = {
  'survey': ['des', 'ps1', 'unwise', 'gaia'],
  'rows': [120_000, 35_000, None, 900],
}
PARAMS = {'label_column': 'survey', 'value_column': 'rows'}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _png_sha(tmp_path: Path, label: str, params: Mapping[str, object]) -> str:
  result = run_step(tmp_path, 'core.bar', {'data': COUNTS}, params=params, label=label)
  return str(_figure(result).renditions[0].sha256)


def test_bars(tmp_path: Path) -> None:
  value = check_figure_preprocessor(tmp_path, 'core.bar', {'data': COUNTS}, params=PARAMS)
  assert value.alt.startswith('Horizontal bars of rows')


def test_log_highlight_and_sort(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.bar',
    {'data': COUNTS},
    params={
      **PARAMS,
      'log': True,
      'highlight': ['ps1'],
      'sort': 'descending',
      'x_label': 'Rows kept',
      'title': 'Rows by survey',
    },
  )


def test_compute_on_a_hand_checked_example() -> None:
  data = compute_bar(pa.table(COUNTS), 'survey', 'rows', highlight=['ps1'])
  assert data.column('label').to_pylist() == ['des', 'ps1', 'unwise', 'gaia']
  assert data.column('value').to_pylist() == [120_000.0, 35_000.0, 0.0, 900.0]
  assert data.column('flagged').to_pylist() == [False, True, True, False]


def test_sort_orders() -> None:
  table = pa.table(COUNTS)
  up = compute_bar(table, 'survey', 'rows', sort='ascending')
  down = compute_bar(table, 'survey', 'rows', sort='descending')
  assert up.column('label').to_pylist() == ['unwise', 'gaia', 'ps1', 'des']
  assert down.column('label').to_pylist() == ['des', 'ps1', 'gaia', 'unwise']


def test_highlight_changes_the_drawing(tmp_path: Path) -> None:
  plain = _png_sha(tmp_path, 'plain', PARAMS)
  marked = _png_sha(tmp_path, 'marked', {**PARAMS, 'highlight': ['des']})
  assert plain != marked


def test_log_axis_changes_the_drawing(tmp_path: Path) -> None:
  assert _png_sha(tmp_path, 'lin', PARAMS) != _png_sha(tmp_path, 'log', {**PARAMS, 'log': True})


def test_height_follows_the_number_of_bars(tmp_path: Path) -> None:
  many = {'survey': [f's{i}' for i in range(30)], 'rows': list(range(1, 31))}
  few_png = run_step(tmp_path, 'core.bar', {'data': COUNTS}, params=PARAMS, label='few')
  many_png = run_step(tmp_path, 'core.bar', {'data': many}, params=PARAMS, label='many')
  few_head = few_png.bundle.read_asset(_figure(few_png).renditions[0])[16:24]
  many_head = many_png.bundle.read_asset(_figure(many_png).renditions[0])[16:24]
  # The PNG header stores width and height; only the height differs.
  assert few_head[:4] == many_head[:4]
  assert int.from_bytes(many_head[4:], 'big') > int.from_bytes(few_head[4:], 'big')


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  empty = {'survey': pa.array([], pa.string()), 'rows': pa.array([], pa.int64())}
  result = run_step(tmp_path, 'core.bar', {'data': empty}, params=PARAMS)
  fig = _figure(result)
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.bar', {'data': COUNTS}, params={**PARAMS, 'value_column': 'rowz'})
  assert caught.value.code == 'E603'
  assert 'rows' in str(caught.value)
