from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess.core.histogram import compute_histogram

SAMPLES = {'value': list(np.random.default_rng(1).normal(0.0, 1.0, 300))}
TALLY = {'size': [1, 2, 3, 4], 'groups': [900, 120, 14, 2]}
LABELS = {'flag': ['a', 'b', 'a', 'c', 'a', 'b'], 'n': [3, 1, 2, 5, 1, 1]}


def test_samples(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.histogram',
    {'data': SAMPLES},
    params={'column': 'value', 'bins': 12, 'x_label': 'value'},
  )
  assert value.data is not None


def test_pre_tallied_counts(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.histogram',
    {'data': TALLY},
    params={'column': 'size', 'counts_column': 'groups', 'log': True, 'x_label': 'size'},
  )


def test_categorical_counts(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.histogram',
    {'data': LABELS},
    params={'column': 'flag', 'counts_column': 'n', 'x_label': 'flag'},
  )


def test_tally_sums_repeated_labels() -> None:
  data = compute_histogram(pa.table(LABELS), 'flag', counts_column='n', categorical=True)
  assert data.column('label').to_pylist() == ['a', 'b', 'c']
  assert data.column('count').to_pylist() == [6.0, 2.0, 5.0]


def test_empty_samples_draw_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path, 'core.histogram', {'data': {'value': [None, None]}}, params={'column': 'value'}
  )
  fig = result.bundle.manifest.values['fig']
  assert fig.kind == 'figure'
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.histogram', {'data': SAMPLES}, params={'column': 'valeu'})
  assert caught.value.code == 'E603'
  assert 'value' in str(caught.value)
