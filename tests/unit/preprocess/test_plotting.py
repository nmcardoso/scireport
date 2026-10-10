from __future__ import annotations

import matplotlib
import numpy as np
import pyarrow as pa
import pytest
from matplotlib.figure import Figure

from scireport.errors import PreprocessError
from scireport.preprocess.look import default_look
from scireport.preprocess.plotting import (
  draw_hex_bins,
  empty_axes,
  frame,
  hex_bins,
  labels,
  numbers,
  require_columns,
  table_columns,
  thin_count_axis,
  values_of,
)

matplotlib.use('Agg')


def test_require_columns_reports_each_missing_one_with_a_hint() -> None:
  table = pa.table({'alpha': [1], 'beta': [2]})
  require_columns(table, 'alpha', None)
  with pytest.raises(PreprocessError) as caught:
    require_columns(table, 'alpah', 'gamma')
  assert [i.code for i in caught.value.issues] == ['E603', 'E603']
  assert caught.value.issues[0].hint == "Did you mean 'alpha'?"
  assert caught.value.issues[1].hint is None


def test_numbers_turns_nulls_into_nan_and_rejects_text() -> None:
  table = pa.table({'x': [1, None, 3], 'name': ['a', 'b', 'c'], 'none': [None, None, None]})
  assert np.isnan(numbers(table, 'x')[1]) and numbers(table, 'x')[2] == 3.0
  assert np.isnan(numbers(table, 'none')).all()
  with pytest.raises(PreprocessError, match='not a number'):
    numbers(table, 'name')


def test_labels_frame_and_values_of() -> None:
  table = pa.table({'k': ['a', None]})
  assert labels(table, 'k') == ['a', '']
  built = frame(a=np.array([1.0, 2.0]), b=['x', 'y'])
  assert built.column_names == ['a', 'b']
  assert values_of(built, 'a').tolist() == [1.0, 2.0]
  assert values_of(built, 'b').tolist() == ['x', 'y']
  assert table_columns(built) == {'a': [1.0, 2.0], 'b': ['x', 'y']}


def test_empty_axes_and_thin_count_axis() -> None:
  ax = Figure().subplots()
  empty_axes(ax, 'Nothing')
  assert [t.get_text() for t in ax.texts] == ['Nothing'] and ax.get_xticks().size == 0
  ax2 = Figure().subplots()
  ax2.set_xlim(0, 2_000_000)
  thin_count_axis(ax2)
  assert ax2.xaxis.get_major_formatter()(1_500_000, 0) == '1,500,000'


def test_hex_bins_keep_every_point_either_in_a_cell_or_as_a_point() -> None:
  rng = np.random.default_rng(3)
  crowd = rng.normal(0.0, 0.1, (400, 2))
  loners = np.array([[5.0, 5.0], [-5.0, 4.0]])
  points = np.vstack([crowd, loners])
  data = hex_bins(points[:, 0], points[:, 1], 20, 3)
  kinds = np.asarray(data['kind'])
  assert data['n'][kinds == 'hex'].sum() + (kinds == 'point').sum() == 402
  assert (data['n'][kinds == 'hex'] > 3).all()
  assert (kinds == 'point').sum() >= 2
  again = hex_bins(points[:, 0], points[:, 1], 20, 3)
  for name in data:
    if name != 'kind':
      assert np.array_equal(np.asarray(data[name]), np.asarray(again[name]), equal_nan=True)


def test_hex_bins_drop_non_finite_pairs_and_handle_nothing() -> None:
  empty = hex_bins(np.array([np.nan, 1.0]), np.array([1.0, np.nan]), 10, 3)
  assert len(empty['kind']) == 0


@pytest.mark.parametrize('count', [1, 3])
def test_a_handful_of_points_draws_without_a_warning(count: int) -> None:
  x = np.arange(count, dtype=float) * 0 + 1.0
  data = pa.table(dict(hex_bins(x, x * 2, 10, 3)))
  figure = Figure()
  ax = figure.subplots()
  with matplotlib.rc_context():
    import warnings

    with warnings.catch_warnings():
      warnings.simplefilter('error')
      draw_hex_bins(ax, data, default_look())
      figure.savefig('/dev/null', format='png')
  assert ax.get_xlim()[0] < ax.get_xlim()[1]


def test_dense_cells_get_a_colour_bar() -> None:
  rng = np.random.default_rng(0)
  pts = rng.normal(0, 1, (500, 2))
  data = pa.table(dict(hex_bins(pts[:, 0], pts[:, 1], 15, 3)))
  figure = Figure()
  draw_hex_bins(figure.subplots(), data, default_look(), label='Objects')
  assert len(figure.axes) == 2
  figure2 = Figure()
  draw_hex_bins(figure2.subplots(), data, default_look(), colorbar=False)
  assert len(figure2.axes) == 1
