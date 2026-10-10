from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import Context
from scireport.preprocess.astro.color_magnitude import (
  compute_color_magnitude,
  render_color_magnitude,
)
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(11)
CATALOGUE = {
  'g_r': list(_RNG.normal(0.5, 0.25, 300)),
  'r_mag': list(_RNG.normal(20.0, 1.5, 300)),
}


def test_cmd(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'astro.color_magnitude',
    {'data': CATALOGUE},
    params={'color_column': 'g_r', 'magnitude_column': 'r_mag', 'gridsize': 10},
    render_params={'x_label': 'g_r', 'y_label': 'r_mag'},
  )
  assert value.data is not None
  assert 'r_mag' in value.alt


def test_labels_and_title_are_drawn(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'astro.color_magnitude',
    {'data': CATALOGUE},
    params={
      'color_column': 'g_r',
      'magnitude_column': 'r_mag',
      'gridsize': 8,
      'threshold': 1,
      'x_label': 'g - r',
      'y_label': 'r (mag)',
      'title': 'CMD',
    },
  )


def test_magnitude_axis_is_inverted(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'astro.color_magnitude',
    {'data': CATALOGUE},
    params={'color_column': 'g_r', 'magnitude_column': 'r_mag', 'gridsize': 10},
  )
  data = compute_color_magnitude(pa.table(CATALOGUE), 'g_r', 'r_mag', gridsize=10)
  ctx = Context(
    bundle=result.bundle,
    produced={},
    produced_assets={},
    outputs={},
    layout='default',
    seed=0,
    name='color_magnitude',
  )
  ax = render_color_magnitude(ctx, data).axes[0]
  low, high = ax.get_ylim()
  assert low > high
  assert not ax.xaxis_inverted()


def test_compute_splits_cells_and_points() -> None:
  table = pa.table(
    {
      'color': [0.5] * 4 + [1.5, 0.2],
      'mag': [20.0] * 4 + [22.0, None],
    }
  )
  data = compute_color_magnitude(table, 'color', 'mag', gridsize=4, threshold=3)
  assert data.column('kind').to_pylist() == ['hex', 'point']
  assert data.column('n').to_pylist() == [4.0, 1.0]
  assert data.column('y').to_pylist()[1] == 22.0


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'astro.color_magnitude',
    {'data': {'g_r': [None], 'r_mag': [None]}},
    params={'color_column': 'g_r', 'magnitude_column': 'r_mag'},
  )
  fig = result.bundle.manifest.values['fig']
  assert isinstance(fig, FigureValue)
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'astro.color_magnitude',
      {'data': CATALOGUE},
      params={'color_column': 'g_r', 'magnitude_column': 'r_magg'},
    )
  assert caught.value.code == 'E603'
  assert 'r_mag' in str(caught.value)
