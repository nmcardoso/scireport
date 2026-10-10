from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import Context, PreprocessResult
from scireport.preprocess.astro.zeropoint_offsets import (
  compute_zeropoint_offsets,
  render_zeropoint_offsets,
)
from scireport.spec.kinds import FigureValue


def _catalogue() -> dict[str, list[float]]:
  """Offset with a colour term of 0.1 and a zero-point of 0.05."""
  rng = np.random.default_rng(7)
  color = rng.uniform(-0.5, 2.5, 300)
  return {'gr': list(color), 'dm': list(0.05 + 0.1 * color + rng.normal(0.0, 0.02, color.size))}


CATALOGUE = _catalogue()
PARAMS = {'color_column': 'gr', 'delta_column': 'dm', 'gridsize': 15}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  value = _figure(result)
  assert value.data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def _png(result: PreprocessResult) -> bytes:
  ref = next(item for item in _figure(result).renditions if item.format == 'png')
  return bytes(result.bundle.read_asset(ref))


def _context(result: PreprocessResult) -> Context:
  return Context(
    bundle=result.bundle,
    produced={},
    produced_assets={},
    outputs={},
    layout='default',
    seed=0,
    name='astro.zeropoint_offsets',
  )


def test_figure(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path, 'astro.zeropoint_offsets', {'cat': CATALOGUE}, params=PARAMS
  )
  assert 'fitted line has slope 0.098' in value.alt


def test_fit_is_exact_on_a_line() -> None:
  table = pa.table({'c': [0.0, 1.0, 2.0, 3.0], 'd': [1.0, 3.0, 5.0, 7.0]})
  data = compute_zeropoint_offsets(table, 'c', 'd', gridsize=4, threshold=3)
  kinds = data.column('kind').to_pylist()
  assert kinds == ['point'] * 4 + ['fit'] * 2
  rows = [i for i, kind in enumerate(kinds) if kind == 'fit']
  assert [data.column('x').to_pylist()[i] for i in rows] == [0.0, 3.0]
  assert [data.column('y').to_pylist()[i] for i in rows] == [
    pytest.approx(1.0),
    pytest.approx(7.0),
  ]


def test_fit_recovers_the_colour_term() -> None:
  data = compute_zeropoint_offsets(pa.table(CATALOGUE), 'gr', 'dm')
  kinds = data.column('kind').to_pylist()
  x = [data.column('x').to_pylist()[i] for i, kind in enumerate(kinds) if kind == 'fit']
  y = [data.column('y').to_pylist()[i] for i, kind in enumerate(kinds) if kind == 'fit']
  assert (y[1] - y[0]) / (x[1] - x[0]) == pytest.approx(0.1, abs=0.01)


def test_fit_off_or_degenerate_stores_no_line() -> None:
  table = pa.table(CATALOGUE)
  assert (
    'fit' not in compute_zeropoint_offsets(table, 'gr', 'dm', fit=False).column('kind').to_pylist()
  )
  same = pa.table({'c': [1.0] * 6, 'd': [0.1, 0.2, 0.3, 0.1, 0.2, 0.3]})
  assert 'fit' not in compute_zeropoint_offsets(same, 'c', 'd').column('kind').to_pylist()
  one = pa.table({'c': [1.0], 'd': [0.1]})
  assert 'fit' not in compute_zeropoint_offsets(one, 'c', 'd').column('kind').to_pylist()


def test_fit_changes_the_drawing_and_the_legend(tmp_path: Path) -> None:
  fitted = run_step(tmp_path, 'astro.zeropoint_offsets', {'cat': CATALOGUE}, params=PARAMS)
  plain = run_step(
    tmp_path,
    'astro.zeropoint_offsets',
    {'cat': CATALOGUE},
    params={**PARAMS, 'fit': False},
    label='plain',
  )
  assert _png(fitted) != _png(plain)
  ax = render_zeropoint_offsets(_context(fitted), _sidecar(fitted)).axes[0]
  legend = ax.get_legend()
  assert legend is not None
  assert legend.get_texts()[0].get_text().startswith('fit: 0.098x')
  assert render_zeropoint_offsets(_context(plain), _sidecar(plain)).axes[0].get_legend() is None


def test_title_changes_the_drawing(tmp_path: Path) -> None:
  base = run_step(tmp_path, 'astro.zeropoint_offsets', {'cat': CATALOGUE}, params=PARAMS)
  titled = run_step(
    tmp_path,
    'astro.zeropoint_offsets',
    {'cat': CATALOGUE},
    params={**PARAMS, 'title': 'g band'},
    label='titled',
  )
  assert _png(base) != _png(titled)


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'astro.zeropoint_offsets',
    {'cat': {'gr': [None, None], 'dm': [None, None]}},
    params=PARAMS,
  )
  assert _sidecar(result).num_rows == 0
  figure = render_zeropoint_offsets(_context(result), _sidecar(result))
  assert [text.get_text() for text in figure.axes[0].texts] == ['No data']


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'astro.zeropoint_offsets',
      {'cat': CATALOGUE},
      params={'color_column': 'gr', 'delta_column': 'dmm'},
    )
  assert caught.value.code == 'E603'
  assert 'dm' in str(caught.value)
