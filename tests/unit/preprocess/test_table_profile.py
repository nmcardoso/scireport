from __future__ import annotations

from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from preprocess_harness import run_step

from scireport.preprocess.core.table_profile import (
  PROFILE_COLUMNS,
  _bytes,
  compute_table_profile,
)
from scireport.spec.kinds import MetricsValue, TableValue

NAN = float('nan')
FIXTURE = pa.table(
  {
    'flux': [1.0, 2.0, 3.0, 4.0, 5.0, 100.0],
    'count': pa.array([0, -1, 2, None, 2, 0], pa.int64()),
    'band': ['x', 'y', 'x', None, 'z', 'x'],
    'quality': [1.0, NAN, 1.0, None, 1.0, 1.0],
    'good': [True, False, True, True, False, True],
  }
)
OUTPUTS = {'profile': 'prof', 'summary': 'sum'}


def _rows(profile: pa.Table) -> dict[str, dict[str, Any]]:
  return {row['name']: row for row in profile.to_pylist()}


def test_profile_of_a_six_row_table_is_hand_checked() -> None:
  rows = _rows(compute_table_profile(FIXTURE))
  assert list(rows) == ['flux', 'count', 'band', 'quality', 'good']

  flux = rows['flux']
  # Quartiles of 1, 2, 3, 4, 5, 100 are 2.25 and 4.75: fences -1.5 and 8.5 leave 100 outside.
  assert (flux['type'], flux['nulls'], flux['zeros'], flux['negatives']) == ('double', 0, 0, 0)
  assert (flux['distinct'], flux['outliers']) == (None, 1)
  assert (flux['min'], flux['max']) == (1.0, 100.0)
  assert flux['mean'] == pytest.approx(115.0 / 6.0)

  count = rows['count']
  # Valid values -1, 0, 0, 2, 2: quartiles 0 and 2, fences -3 and 5, so no outlier.
  assert (count['type'], count['nulls'], count['zeros'], count['negatives']) == ('int64', 1, 2, 1)
  assert (count['distinct'], count['outliers']) == (3, 0)
  assert (count['min'], count['max']) == (-1.0, 2.0)
  assert count['mean'] == pytest.approx(0.6)

  band = rows['band']
  assert (band['type'], band['nulls'], band['distinct']) == ('string', 1, 3)
  for key in ('zeros', 'negatives', 'outliers', 'min', 'max', 'mean'):
    assert band[key] is None

  quality = rows['quality']
  # A null and a NaN are both missing; four equal values have no interquartile range.
  assert (quality['nulls'], quality['zeros'], quality['negatives']) == (2, 0, 0)
  assert (quality['distinct'], quality['outliers']) == (None, None)
  assert (quality['min'], quality['max'], quality['mean']) == (1.0, 1.0, 1.0)

  good = rows['good']
  assert (good['type'], good['nulls'], good['distinct']) == ('bool', 0, 2)
  assert good['mean'] is None


def test_infinite_values_are_extremes_and_outliers_but_not_in_the_mean() -> None:
  table = pa.table({'x': [1.0, 2.0, 3.0, 4.0, float('inf'), -float('inf')]})
  row = _rows(compute_table_profile(table))['x']
  assert (row['min'], row['max']) == (-float('inf'), float('inf'))
  assert row['mean'] == pytest.approx(2.5)
  assert (row['negatives'], row['outliers']) == (1, 2)


def test_empty_and_all_null_columns() -> None:
  table = pa.table({'a': pa.array([None, None], pa.float64()), 'c': [NAN, NAN]})
  rows = _rows(compute_table_profile(table))
  assert rows['a']['nulls'] == 2 and rows['a']['min'] is None and rows['a']['mean'] is None
  assert rows['c']['nulls'] == 2 and rows['c']['max'] is None
  empty = _rows(compute_table_profile(pa.table({'b': pa.array([], pa.string())})))
  assert empty['b']['nulls'] == 0 and empty['b']['distinct'] == 0


def test_the_step_stores_a_profile_table_and_a_summary(tmp_path: Path) -> None:
  result = run_step(tmp_path, 'core.table_profile', {'data': FIXTURE}, outputs=OUTPUTS)
  profile = result.bundle.manifest.values['prof']
  assert isinstance(profile, TableValue)
  assert profile.n_rows == 5
  assert [column.name for column in profile.columns] == [key for key, *_ in PROFILE_COLUMNS]
  by_name = {column.name: column for column in profile.columns}
  assert by_name['name'].label == 'Column' and by_name['name'].align == 'left'
  assert by_name['type'].align == 'left'
  assert by_name['nulls'].align == 'right' and by_name['nulls'].label == 'Nulls'
  assert by_name['mean'].align == 'right' and by_name['mean'].format is not None
  assert profile.caption
  stored = result.bundle.read_table('prof')
  assert stored.column('name').to_pylist() == ['flux', 'count', 'band', 'quality', 'good']
  assert stored.column('nulls').to_pylist() == [0, 1, 1, 2, 0]

  summary = result.bundle.manifest.values['sum']
  assert isinstance(summary, MetricsValue)
  assert [item.label for item in summary.items] == ['Rows', 'Columns', 'In memory']
  assert summary.items[0].value.model_dump()['value'] == 6
  assert summary.items[1].value.model_dump()['value'] == 5
  text = summary.items[2].value.model_dump()['text']
  assert text == _bytes(result.bundle.read_table('data').nbytes)


def test_two_runs_give_identical_table_bytes(tmp_path: Path) -> None:
  first = run_step(tmp_path, 'core.table_profile', {'data': FIXTURE}, outputs=OUTPUTS)
  second = run_step(
    tmp_path, 'core.table_profile', {'data': FIXTURE}, outputs=OUTPUTS, label='again'
  )
  one = first.bundle.manifest.values['prof']
  two = second.bundle.manifest.values['prof']
  assert isinstance(one, TableValue) and isinstance(two, TableValue)
  assert one.asset is not None and two.asset is not None
  assert first.bundle.read_asset(one.asset) == second.bundle.read_asset(two.asset)
  assert one.asset.sha256 == two.asset.sha256
  assert first.bundle.manifest.values['sum'] == second.bundle.manifest.values['sum']


def test_a_custom_caption(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'core.table_profile',
    {'data': FIXTURE},
    params={'caption': 'Columns of the fixture.'},
    outputs=OUTPUTS,
  )
  profile = result.bundle.manifest.values['prof']
  assert isinstance(profile, TableValue)
  assert profile.caption == 'Columns of the fixture.'


def test_a_table_without_rows(tmp_path: Path) -> None:
  empty = pa.table({'a': pa.array([], pa.int64()), 'b': pa.array([], pa.string())})
  result = run_step(tmp_path, 'core.table_profile', {'data': empty}, outputs=OUTPUTS)
  stored = result.bundle.read_table('prof')
  assert stored.column('nulls').to_pylist() == [0, 0]
  assert stored.column('min').to_pylist() == [None, None]
  summary = result.bundle.manifest.values['sum']
  assert isinstance(summary, MetricsValue)
  assert summary.items[0].value.model_dump()['value'] == 0


@pytest.mark.parametrize(
  ('size', 'text'),
  [(0, '0 B'), (1023, '1,023 B'), (1024, '1.0 KB'), (1536, '1.5 KB'), (5 * 1024**3, '5.0 GB')],
)
def test_bytes_text(size: int, text: str) -> None:
  assert _bytes(size) == text


def test_bytes_text_without_a_number() -> None:
  assert _bytes(None) == '--'
