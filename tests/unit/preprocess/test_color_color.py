from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess.astro.color_color import compute_color_color
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(7)
_GR = _RNG.normal(0.6, 0.3, 300)
LOCUS = {
  'g_r': list(_GR),
  'r_i': list(0.5 * _GR + _RNG.normal(0.0, 0.05, 300)),
}


def test_locus(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'astro.color_color',
    {'data': LOCUS},
    params={'color_x_column': 'g_r', 'color_y_column': 'r_i', 'gridsize': 10},
    render_params={'x_label': 'g_r', 'y_label': 'r_i'},
  )
  assert value.data is not None
  assert 'g_r' in value.alt and 'r_i' in value.alt


def test_labels_and_title_are_drawn(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'astro.color_color',
    {'data': LOCUS},
    params={
      'color_x_column': 'g_r',
      'color_y_column': 'r_i',
      'gridsize': 8,
      'threshold': 1,
      'x_label': 'g - r',
      'y_label': 'r - i',
      'title': 'Stellar locus',
      'height': 3.0,
      'width': 0.5,
    },
  )


def test_compute_splits_cells_and_points() -> None:
  table = pa.table(
    {
      'x': [0.0] * 5 + [1.0, None, float('nan')],
      'y': [0.0] * 5 + [1.0, 0.5, 0.5],
    }
  )
  data = compute_color_color(table, 'x', 'y', gridsize=4, threshold=3)
  assert data.column_names == ['kind', 'x', 'y', 'n', 'dx', 'dy']
  assert data.column('kind').to_pylist() == ['hex', 'point']
  assert data.column('n').to_pylist() == [5.0, 1.0]
  assert data.column('x').to_pylist()[1] == 1.0
  assert data.column('y').to_pylist()[1] == 1.0
  assert np.isnan(data.column('dx').to_pylist()[1])


def test_compute_keeps_every_finite_pair() -> None:
  data = compute_color_color(pa.table(LOCUS), 'g_r', 'r_i', gridsize=10, threshold=3)
  assert sum(data.column('n').to_pylist()) == 300.0
  assert data.num_rows < 300


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'astro.color_color',
    {'data': {'g_r': [None, None], 'r_i': [None, None]}},
    params={'color_x_column': 'g_r', 'color_y_column': 'r_i'},
  )
  fig = result.bundle.manifest.values['fig']
  assert isinstance(fig, FigureValue)
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'astro.color_color',
      {'data': LOCUS},
      params={'color_x_column': 'g_r', 'color_y_column': 'r_j'},
    )
  assert caught.value.code == 'E603'
  assert 'r_i' in str(caught.value)
