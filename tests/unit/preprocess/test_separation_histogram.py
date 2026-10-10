from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.separation_histogram import compute_separation_histogram
from scireport.spec.kinds import FigureValue

SAMPLES = {'sep': list(np.abs(np.random.default_rng(3).normal(0.0, 0.5, 250)))}
TALLY = {'centre': [0.25, 0.75, 1.25, 1.75], 'matches': [400, 220, 35, 3]}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  data = _figure(result).data
  assert data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(data)))


def test_samples_with_radius(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.separation_histogram',
    {'data': SAMPLES},
    params={'column': 'sep', 'radius': 1.0, 'bins': 20},
  )
  assert 'sep' in value.alt
  assert '1 arcsec' in value.alt


def test_pre_tallied_counts(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.separation_histogram',
    {'data': TALLY},
    params={'column': 'centre', 'counts_column': 'matches', 'radius': 2.0, 'title': 'Matches'},
  )


def test_radius_changes_the_drawing(tmp_path: Path) -> None:
  params = {'column': 'sep', 'bins': 20}
  plain = run_step(tmp_path, 'core.separation_histogram', {'data': SAMPLES}, params=params)
  ruled = run_step(
    tmp_path,
    'core.separation_histogram',
    {'data': SAMPLES},
    params={**params, 'radius': 1.0},
    label='ruled',
  )
  assert _figure(plain).renditions[0].sha256 != _figure(ruled).renditions[0].sha256
  assert _sidecar(plain).equals(_sidecar(ruled))


def test_compute_samples_hand_checked() -> None:
  data = compute_separation_histogram(pa.table({'s': [0.0, 1.0, 1.0, 2.0, None]}), 's', bins=2)
  assert data.column_names == ['left', 'right', 'count']
  assert data.column('left').to_pylist() == [0.0, 1.0]
  assert data.column('right').to_pylist() == [1.0, 2.0]
  assert data.column('count').to_pylist() == [1.0, 3.0]


def test_compute_tally_hand_checked() -> None:
  table = pa.table({'c': [1.5, 0.5, 2.5], 'n': [4, 10, None]})
  data = compute_separation_histogram(table, 'c', counts_column='n')
  assert data.column('left').to_pylist() == [0.0, 1.0, 2.0]
  assert data.column('right').to_pylist() == [1.0, 2.0, 3.0]
  assert data.column('count').to_pylist() == [10.0, 4.0, 0.0]


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path, 'core.separation_histogram', {'data': {'sep': [None, None]}}, params={'column': 'sep'}
  )
  value = _figure(result)
  assert value.kind == 'figure'
  assert value.alt.startswith('No separations')
  assert _sidecar(result).num_rows == 0


def test_all_zero_tally_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'core.separation_histogram',
    {'data': {'c': [0.5, 1.5], 'n': [0, 0]}},
    params={'column': 'c', 'counts_column': 'n'},
  )
  assert _figure(result).alt.startswith('No separations')


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.separation_histogram', {'data': SAMPLES}, params={'column': 'spe'})
  assert caught.value.code == 'E603'
  assert 'sep' in str(caught.value)


def test_missing_counts_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.separation_histogram',
      {'data': TALLY},
      params={'column': 'centre', 'counts_column': 'match'},
    )
  assert caught.value.code == 'E603'
