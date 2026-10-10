from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import Context, PreprocessResult
from scireport.preprocess.astro.snr_magnitude import (
  compute_snr_magnitude,
  five_sigma_depth,
  render_snr_magnitude,
)
from scireport.spec.kinds import FigureValue


def _catalogue() -> dict[str, list[float]]:
  """Magnitude 16-24 with log10 S/N falling 0.4 per mag from 3 (S/N = 5 at mag 21.75)."""
  rng = np.random.default_rng(3)
  mag = rng.uniform(16.0, 24.0, 400)
  log_snr = 3.0 - 0.4 * (mag - 16.0) + rng.normal(0.0, 0.05, mag.size)
  return {'mag': list(mag), 'snr': list(10.0**log_snr)}


CATALOGUE = _catalogue()
PARAMS = {'magnitude_column': 'mag', 'snr_column': 'snr', 'gridsize': 20}


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
    name='astro.snr_magnitude',
  )


def test_figure(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path, 'astro.snr_magnitude', {'cat': CATALOGUE}, params=PARAMS
  )
  assert 'mag' in value.alt and 'snr' in value.alt and '5-sigma depth at magnitude' in value.alt


def test_depth_is_estimated_from_the_running_median() -> None:
  data = compute_snr_magnitude(pa.table(CATALOGUE), 'mag', 'snr', gridsize=20)
  kinds = data.column('kind').to_pylist()
  assert kinds.count('depth') == 1
  row = kinds.index('depth')
  assert data.column('x').to_pylist()[row] == pytest.approx(21.75, abs=0.3)
  assert np.isnan(data.column('y').to_pylist()[row])


def test_five_sigma_depth_on_an_exact_line() -> None:
  mag = np.arange(0.0, 10.0, 0.01)
  log_snr = 1.0 - 0.1 * mag
  assert five_sigma_depth(mag, log_snr) == pytest.approx((1.0 - np.log10(5.0)) / 0.1, abs=0.02)


def test_no_depth_when_the_median_never_crosses_five() -> None:
  mag = np.linspace(0.0, 10.0, 200)
  assert five_sigma_depth(mag, np.full(200, 2.0)) is None
  assert five_sigma_depth(mag, np.full(200, 0.0)) is None
  assert five_sigma_depth(np.full(50, 3.0), np.full(50, 2.0)) is None
  assert five_sigma_depth(np.empty(0), np.empty(0)) is None


def test_explicit_depth_wins_and_estimation_can_be_off() -> None:
  table = pa.table(CATALOGUE)
  given = compute_snr_magnitude(table, 'mag', 'snr', depth=20.5)
  rows = given.filter(pc.equal(given.column('kind'), 'depth'))
  assert rows.column('x').to_pylist() == [20.5]
  off = compute_snr_magnitude(table, 'mag', 'snr', estimate_depth=False)
  assert 'depth' not in off.column('kind').to_pylist()


def test_non_positive_snr_is_dropped() -> None:
  table = pa.table({'mag': [20.0, 21.0, 22.0, 23.0], 'snr': [10.0, 0.0, -3.0, None]})
  data = compute_snr_magnitude(table, 'mag', 'snr', estimate_depth=False)
  assert data.num_rows == 1
  assert data.column('y').to_pylist() == [pytest.approx(1.0)]


def test_depth_and_title_change_the_drawing(tmp_path: Path) -> None:
  plain = run_step(
    tmp_path, 'astro.snr_magnitude', {'cat': CATALOGUE}, params={**PARAMS, 'estimate_depth': False}
  )
  marked = run_step(
    tmp_path,
    'astro.snr_magnitude',
    {'cat': CATALOGUE},
    params={**PARAMS, 'depth': 20.0},
    label='marked',
  )
  titled = run_step(
    tmp_path,
    'astro.snr_magnitude',
    {'cat': CATALOGUE},
    params={**PARAMS, 'estimate_depth': False, 'title': 'Band g'},
    label='titled',
  )
  assert _png(plain) != _png(marked)
  assert _png(plain) != _png(titled)
  assert 'depth' not in _sidecar(plain).column('kind').to_pylist()
  assert 'depth' in _sidecar(marked).column('kind').to_pylist()


def test_legend_names_the_depth(tmp_path: Path) -> None:
  result = run_step(tmp_path, 'astro.snr_magnitude', {'cat': CATALOGUE}, params=PARAMS)
  figure = render_snr_magnitude(_context(result), _sidecar(result))
  legend = figure.axes[0].get_legend()
  assert legend is not None
  texts = [item.get_text() for item in legend.get_texts()]
  assert texts[0] == 'S/N = 5'
  assert texts[1].startswith('5σ depth 21.')


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  result = run_step(
    tmp_path,
    'astro.snr_magnitude',
    {'cat': {'mag': [None, None], 'snr': [None, None]}},
    params=PARAMS,
  )
  assert _sidecar(result).num_rows == 0
  figure = render_snr_magnitude(_context(result), _sidecar(result))
  assert [text.get_text() for text in figure.axes[0].texts] == ['No data']


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'astro.snr_magnitude',
      {'cat': CATALOGUE},
      params={'magnitude_column': 'mag', 'snr_column': 'snrr'},
    )
  assert caught.value.code == 'E603'
  assert 'snr' in str(caught.value)
