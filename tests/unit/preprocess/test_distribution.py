from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.distribution import (
  box_statistics,
  compute_distribution,
  gaussian_kde_curve,
)
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(11)
_VALUES = np.concatenate([_RNG.normal(0.0, 1.0, 150), _RNG.normal(3.0, 0.5, 150)])
_GROUPS = ['a'] * 150 + ['b'] * 150
GROUPED = {'v': list(_VALUES), 'g': _GROUPS}
SINGLE = {'v': list(_VALUES)}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  value = _figure(result)
  assert value.data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def _rows(data: pa.Table, group: str, part: str) -> pa.Table:
  groups, parts = data.column('group').to_pylist(), data.column('part').to_pylist()
  return data.filter(
    pa.array([g == group and p == part for g, p in zip(groups, parts, strict=True)])
  )


def _stat(data: pa.Table, group: str, name: str) -> float:
  summary = _rows(data, group, 'summary')
  names = summary.column('name').to_pylist()
  return float(summary.column('value').to_pylist()[names.index(name)])


def test_box_figure(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.distribution',
    {'data': GROUPED},
    params={'value_column': 'v', 'group_column': 'g', 'y_label': 'v'},
    min_sidecar_rows=10,
  )


def test_violin_figure(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.distribution',
    {'data': GROUPED},
    params={'value_column': 'v', 'group_column': 'g', 'kind': 'violin', 'y_label': 'v'},
    min_sidecar_rows=200,
  )
  assert 'violin' in value.alt.lower()


def test_single_group_named_after_the_column(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.distribution',
    {'data': SINGLE},
    params={'value_column': 'v', 'title': 'Spread'},
    render_params={'y_label': 'v', 'title': 'Spread'},
  )
  data = compute_distribution(pa.table(SINGLE), 'v')
  assert set(data.column('group').to_pylist()) == {'v'}


def test_box_statistics_on_a_hand_checked_example() -> None:
  stats = box_statistics(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 100.0]))
  assert stats['q1'] == 2.75 and stats['median'] == 4.5 and stats['q3'] == 6.25
  # reach is 1.5 * 3.5 = 5.25, so 100 is an outlier and 7 the upper whisker
  assert stats['whisker_high'] == 7.0 and stats['whisker_low'] == 1.0
  assert stats['outliers'].tolist() == [100.0]
  assert stats['n'] == 8.0 and stats['n_outliers'] == 1.0


def test_outliers_are_capped_deterministically() -> None:
  values = np.concatenate([np.linspace(0.0, 1.0, 2000), np.linspace(10.0, 20.0, 300)])
  first = box_statistics(values, max_outliers=50)
  assert first['n_outliers'] == 300.0
  assert first['outliers'].size == 50
  assert first['outliers'][0] == 10.0 and first['outliers'][-1] == 20.0
  assert first['outliers'].tolist() == box_statistics(values, max_outliers=50)['outliers'].tolist()
  table = pa.table({'v': list(values)})
  data = compute_distribution(table, 'v', max_outliers=50)
  assert _rows(data, 'v', 'outlier').num_rows == 50


def test_box_values_match_the_input() -> None:
  data = compute_distribution(pa.table(GROUPED), 'v', group_column='g')
  mine = _VALUES[:150]
  assert _stat(data, 'a', 'median') == pytest.approx(np.median(mine))
  assert _stat(data, 'a', 'n') == 150.0
  assert data.column('group').to_pylist()[0] == 'a'


def test_kde_integrates_to_one_and_peaks_near_the_mode() -> None:
  sample = np.random.default_rng(2).normal(5.0, 1.0, 2000)
  grid, density = gaussian_kde_curve(sample, 100)
  assert grid.size == density.size == 100
  assert grid[0] == sample.min() and grid[-1] == sample.max()
  area = float(np.sum(0.5 * (density[1:] + density[:-1]) * np.diff(grid)))
  assert area == pytest.approx(1.0, abs=0.02)
  assert abs(grid[np.argmax(density)] - 5.0) < 0.5


def test_kde_of_one_value_is_a_narrow_bump() -> None:
  grid, density = gaussian_kde_curve(np.array([2.0]), 100)
  assert grid[0] == 1.5 and grid[-1] == 2.5
  assert np.argmax(density) in (49, 50)


def test_violin_stores_a_density_curve_per_group() -> None:
  data = compute_distribution(pa.table(GROUPED), 'v', group_column='g', kind='violin', n_grid=40)
  assert _rows(data, 'a', 'density').num_rows == 40
  assert _rows(data, 'b', 'density').num_rows == 40
  assert _rows(data, 'a', 'outlier').num_rows == 0


def test_nulls_are_dropped_and_an_empty_group_is_kept() -> None:
  table = pa.table({'v': [1.0, 2.0, 3.0, None, float('nan')], 'g': ['x', 'x', 'x', 'y', 'y']})
  data = compute_distribution(table, 'v', group_column='g')
  assert _stat(data, 'x', 'n') == 3.0
  assert _stat(data, 'y', 'n') == 0.0
  assert _rows(data, 'y', 'summary').num_rows == 1


def test_all_null_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'core.distribution',
    {'data': {'v': [None, None]}},
    params={'value_column': 'v', 'kind': 'violin'},
  )
  value = _figure(result)
  assert 'no finite values' in value.alt
  sidecar = _sidecar(result)
  assert sidecar.column('name').to_pylist() == ['n'] and sidecar.column('value').to_pylist() == [
    0.0
  ]


def test_kind_must_be_box_or_violin(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path, 'core.distribution', {'data': SINGLE}, params={'value_column': 'v', 'kind': 'pie'}
    )
  assert caught.value.code == 'E602'


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.distribution', {'data': GROUPED}, params={'value_column': 'w'})
  assert caught.value.code == 'E603'
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.distribution',
      {'data': GROUPED},
      params={'value_column': 'v', 'group_column': 'h'},
    )
  assert caught.value.code == 'E603'
