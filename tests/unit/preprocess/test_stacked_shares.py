from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.stacked_shares import compute_stacked_shares
from scireport.spec.kinds import FigureValue

TIERS = {
  'tier': ['train', 'train', 'train', 'val', 'val', 'test', 'test'],
  'cls': ['star', 'galaxy', 'qso', 'star', 'galaxy', 'galaxy', 'star'],
  'n': [700, 250, 50, 90, 10, 60, 40],
}
PARAMS = {'group_column': 'tier', 'label_column': 'cls', 'count_column': 'n'}
REFERENCE = {'star': 0.7, 'galaxy': 0.25, 'qso': 0.05}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _png_sha(tmp_path: Path, label: str, params: Mapping[str, object]) -> str:
  result = run_step(tmp_path, 'core.stacked_shares', {'data': TIERS}, params=params, label=label)
  return str(_figure(result).renditions[0].sha256)


def test_shares(tmp_path: Path) -> None:
  value = check_figure_preprocessor(tmp_path, 'core.stacked_shares', {'data': TIERS}, params=PARAMS)
  assert 'share of each cls within each tier' in value.alt


def test_reference_and_title(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.stacked_shares',
    {'data': TIERS},
    params={**PARAMS, 'reference': REFERENCE, 'title': 'Class shares by tier', 'height': 3.0},
  )
  assert 'requested shares' in value.alt


def test_compute_on_a_hand_checked_example() -> None:
  data = compute_stacked_shares(pa.table(TIERS), 'tier', 'cls', 'n', reference=REFERENCE)
  assert data.num_rows == 9
  rows = {
    (g, label): (count, share)
    for g, label, count, share in zip(
      data.column('group').to_pylist(),
      data.column('label').to_pylist(),
      data.column('count').to_pylist(),
      data.column('share').to_pylist(),
      strict=True,
    )
  }
  assert rows[('train', 'star')] == (700.0, 0.7)
  # A label missing from a group counts as zero.
  assert rows[('val', 'qso')] == (0.0, 0.0)
  assert rows[('test', 'galaxy')] == (60.0, 0.6)
  assert data.column('reference').to_pylist()[:3] == [0.7, 0.25, 0.05]
  assert data.column('group').to_pylist()[::3] == ['train', 'val', 'test']


def test_repeated_pairs_are_summed_and_nulls_are_zero() -> None:
  table = pa.table({'g': ['a', 'a', 'a'], 'l': ['x', 'x', 'y'], 'n': [1, 2, None]})
  data = compute_stacked_shares(table, 'g', 'l', 'n')
  assert data.column('count').to_pylist() == [3.0, 0.0]
  assert data.column('share').to_pylist() == [1.0, 0.0]
  assert data.column('reference').to_pylist() == [None, None]


def test_reference_changes_the_drawing(tmp_path: Path) -> None:
  assert _png_sha(tmp_path, 'plain', PARAMS) != _png_sha(
    tmp_path, 'ref', {**PARAMS, 'reference': REFERENCE}
  )


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  empty = {
    'tier': pa.array([], pa.string()),
    'cls': pa.array([], pa.string()),
    'n': pa.array([], pa.int64()),
  }
  result = run_step(tmp_path, 'core.stacked_shares', {'data': empty}, params=PARAMS)
  fig = _figure(result)
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.stacked_shares',
      {'data': TIERS},
      params={**PARAMS, 'group_column': 'teir'},
    )
  assert caught.value.code == 'E603'
  assert 'tier' in str(caught.value)
