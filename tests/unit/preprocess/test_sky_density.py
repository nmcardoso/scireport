from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

pytest.importorskip('astropy_healpix')

from scireport.errors import PreprocessError
from scireport.preprocess.astro._sky import pixel_area_deg2, pixel_grid, tally
from scireport.preprocess.astro.sky_density import compute_sky_density
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(7)
POINTS = {
  'ra': list(_RNG.uniform(0.0, 360.0, 300)) + list(_RNG.normal(120.0, 5.0, 200) % 360.0),
  'dec': list(np.degrees(np.arcsin(_RNG.uniform(-1.0, 1.0, 300))))
  + list(_RNG.normal(20.0, 4.0, 200)),
}
TALLY = {'pix': [0, 1, 1, 5, 40], 'n': [10, 4, 6, 100, 1]}


def _sidecar(result: Any, key: str = 'fig') -> pa.Table:
  value = result.bundle.manifest.values[key]
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def test_points(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path, 'astro.sky_density', {'cat': POINTS}, params={'order': 3, 'title': 'Density'}
  )


def test_points_linear_and_per_pixel(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'astro.sky_density',
    {'cat': POINTS},
    params={'order': 3, 'log': False, 'per_area': False, 'colorbar_label': 'n / pixel'},
  )


def test_precounted_pixels(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'astro.sky_density',
    {'cat': TALLY},
    params={'order': 2, 'ipix_column': 'pix', 'counts_column': 'n'},
  )


def test_compute_points_hand_checked() -> None:
  # Order 0 has 12 nested pixels; base pixel 0 holds RA 45, Dec 30..40 (north-east polar cap
  # of the first quadrant). The row without a position is skipped.
  table = pa.table({'ra': [45.0, 45.0, 45.0, 10.0], 'dec': [30.0, 40.0, 35.0, None]})
  data = compute_sky_density(table, order=0)
  assert data.column_names == ['ipix', 'count', 'order', 'area_deg2']
  assert data.column('ipix').to_pylist() == [0]
  assert data.column('count').to_pylist() == [3.0]
  assert data.column('order').to_pylist() == [0]
  assert data.column('area_deg2').to_pylist() == pytest.approx([41252.96 / 12], rel=1e-5)


def test_compute_tally_sums_and_min_count() -> None:
  data = compute_sky_density(
    pa.table(TALLY), order=2, ipix_column='pix', counts_column='n', min_count=5.0
  )
  assert data.column('ipix').to_pylist() == [0, 1, 5]
  assert data.column('count').to_pylist() == [10.0, 10.0, 100.0]


def test_pixel_area_is_sky_over_pixels() -> None:
  assert pixel_area_deg2(5) * 12 * 4**5 == pytest.approx(41252.96, rel=1e-6)


def test_index_outside_the_sky_is_coded() -> None:
  with pytest.raises(PreprocessError) as caught:
    compute_sky_density(pa.table({'p': [12]}), order=0, ipix_column='p')
  assert caught.value.code == 'E603'


def test_order_out_of_range_is_coded() -> None:
  with pytest.raises(PreprocessError) as caught:
    compute_sky_density(pa.table(POINTS), order=11)
  assert caught.value.code == 'E602'


@pytest.mark.parametrize(
  'table', [{'ra': [None, None], 'dec': [None, None]}, {'ra': [], 'dec': []}]
)
def test_empty_input_draws_a_placeholder(tmp_path: Path, table: dict[str, list[None]]) -> None:
  schema = pa.schema([('ra', pa.float64()), ('dec', pa.float64())])
  result = run_step(
    tmp_path, 'astro.sky_density', {'cat': pa.table(table, schema=schema)}, params={'order': 3}
  )
  fig = result.bundle.manifest.values['fig']
  assert fig.kind == 'figure'
  assert 'no positions' in fig.alt
  assert _sidecar(result).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'astro.sky_density', {'cat': POINTS}, params={'dec_column': 'dce'})
  assert caught.value.code == 'E603'
  assert 'dec' in str(caught.value)


def test_style_parameters_change_the_drawing(tmp_path: Path) -> None:
  def png(label: str, **params: object) -> bytes:
    result = run_step(
      tmp_path, 'astro.sky_density', {'cat': POINTS}, params={'order': 3, **params}, label=label
    )
    value = result.bundle.manifest.values['fig']
    assert isinstance(value, FigureValue)
    return bytes(result.bundle.read_asset(next(r for r in value.renditions if r.format == 'png')))

  base = png('a')
  assert png('b', log=False) != base
  assert png('c', per_area=False) != base
  assert png('d', colorbar_label='other') != base
  assert png('e', min_count=2.0) != base


def test_east_is_left() -> None:
  # A source at RA 90 deg must land left of the centre (negative x) on the Mollweide axes.
  found = tally(pa.table({'ra': [90.0], 'dec': [0.0]}), order=4)
  grid = pixel_grid(found.ipix, found.count, 4)
  columns = np.where(np.isfinite(grid).any(axis=0))[0]
  assert columns.max() < grid.shape[1] / 2
