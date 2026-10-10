from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from matplotlib.axes import Axes
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import Context
from scireport.preprocess.astro.number_counts import compute_number_counts, render_number_counts
from scireport.spec.kinds import FigureValue

_CENTRES = np.arange(16.0, 24.0, 0.5)
# Euclidean growth of 0.6 dex per magnitude up to the limit, then incompleteness.
_COUNTS = np.round(10 ** (0.6 * (_CENTRES - 16.0) + 2.0) * np.where(_CENTRES > 21.5, 0.2, 1.0))
SINGLE = {'mag': list(_CENTRES), 'n': list(_COUNTS)}
LONG = {
  'mag': list(_CENTRES) * 2,
  'n': list(_COUNTS) + list(_COUNTS * 0.5),
  'survey': ['A'] * _CENTRES.size + ['B'] * _CENTRES.size,
}


def _context(tmp_path: Path) -> Context:
  result = run_step(
    tmp_path,
    'astro.number_counts',
    {'data': SINGLE},
    params={'center_column': 'mag', 'count_column': 'n'},
  )
  return Context(
    bundle=result.bundle,
    produced={},
    produced_assets={},
    outputs={},
    layout='default',
    seed=0,
    name='number_counts',
  )


def _legend(ax: Axes) -> list[str]:
  legend = ax.get_legend()
  assert legend is not None
  return [item.get_text() for item in legend.get_texts()]


def test_single_series(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'astro.number_counts',
    {'data': SINGLE},
    params={'center_column': 'mag', 'count_column': 'n', 'x_label': 'r (mag)'},
    min_sidecar_rows=16,
  )
  assert value.data is not None
  assert '1 series' in value.alt


def test_groups(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'astro.number_counts',
    {'data': LONG},
    params={
      'center_column': 'mag',
      'count_column': 'n',
      'group_column': 'survey',
      'reference_slope': 0.5,
      'title': 'Counts',
      'height': 3.0,
    },
    min_sidecar_rows=32,
  )
  assert '2 series' in value.alt


def test_compute_hand_checked() -> None:
  table = pa.table(
    {
      'mag': [19.0, 18.0, 20.0, 20.0, 21.0, None, 22.0],
      'n': [100, 10, 400, 600, 0, 5, float('nan')],
    }
  )
  data = compute_number_counts(table, 'mag', 'n')
  assert data.column_names == ['group', 'center', 'left', 'right', 'count']
  assert data.column('group').to_pylist() == ['', '', '']
  assert data.column('center').to_pylist() == [18.0, 19.0, 20.0]
  assert data.column('left').to_pylist() == [17.5, 18.5, 19.5]
  assert data.column('right').to_pylist() == [18.5, 19.5, 20.5]
  assert data.column('count').to_pylist() == [10.0, 100.0, 1000.0]


def test_compute_groups_are_sorted_and_independent() -> None:
  table = pa.table(
    {
      'mag': [20.0, 18.0, 19.0, 19.0],
      'n': [7, 5, 3, 9],
      'survey': ['B', 'A', 'B', 'B'],
    }
  )
  data = compute_number_counts(table, 'mag', 'n', group_column='survey')
  assert data.column('group').to_pylist() == ['A', 'B', 'B']
  assert data.column('center').to_pylist() == [18.0, 19.0, 20.0]
  assert data.column('count').to_pylist() == [5.0, 12.0, 7.0]
  assert data.column('right').to_pylist() == [18.5, 19.5, 20.5]


def test_reference_slope_and_groups_change_the_drawing(tmp_path: Path) -> None:
  ctx = _context(tmp_path)
  single = compute_number_counts(pa.table(SINGLE), 'mag', 'n')
  fig = render_number_counts(ctx, single, reference_slope=0.4)
  ax = fig.axes[0]
  assert _legend(ax) == ['Observed', 'Euclidean slope (0.4/mag)']
  reference = np.asarray(ax.lines[-1].get_ydata(), dtype=float)
  anchor = int(np.argmax(_COUNTS))
  assert reference[anchor] == pytest.approx(np.log10(_COUNTS[anchor]))
  assert np.diff(reference)[0] == pytest.approx(0.4 * 0.5)

  grouped = compute_number_counts(pa.table(LONG), 'mag', 'n', group_column='survey')
  ax = render_number_counts(ctx, grouped).axes[0]
  assert _legend(ax) == ['A', 'B', 'Euclidean slope (0.6/mag)']


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'astro.number_counts',
    {'data': {'mag': [None, 20.0], 'n': [4, 0]}},
    params={'center_column': 'mag', 'count_column': 'n'},
  )
  fig = result.bundle.manifest.values['fig']
  assert isinstance(fig, FigureValue)
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'astro.number_counts',
      {'data': LONG},
      params={'center_column': 'mag', 'count_column': 'n', 'group_column': 'surveys'},
    )
  assert caught.value.code == 'E603'
  assert 'survey' in str(caught.value)
