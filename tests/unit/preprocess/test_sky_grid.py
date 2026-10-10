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
from scireport.preprocess.astro.sky_grid import compute_sky_grid, default_height
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(5)


def _survey(name: str, n: int, ra: float, dec: float, size: float) -> dict[str, list[Any]]:
  return {
    'ra': list(_RNG.normal(ra, size, n) % 360.0),
    'dec': list(np.clip(_RNG.normal(dec, size, n), -89.0, 89.0)),
    'source': [name] * n,
  }


def _stack(*parts: dict[str, list[Any]]) -> dict[str, list[Any]]:
  return {key: [item for part in parts for item in part[key]] for key in parts[0]}


SOURCES = _stack(
  _survey('alpha', 250, 150.0, 30.0, 25.0),
  _survey('beta', 120, 300.0, -40.0, 20.0),
  _survey('gamma', 300, 10.0, 0.0, 15.0),
  _survey('delta', 60, 200.0, 60.0, 30.0),
)


def _sidecar(result: Any, key: str = 'fig') -> pa.Table:
  value = result.bundle.manifest.values[key]
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def _png(tmp_path: Path, label: str, **params: object) -> bytes:
  result = run_step(
    tmp_path,
    'astro.sky_grid',
    {'cat': SOURCES},
    params={'group_column': 'source', 'order': 3, **params},
    label=label,
  )
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return bytes(result.bundle.read_asset(next(r for r in value.renditions if r.format == 'png')))


def test_grid_of_four_in_three_columns(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'astro.sky_grid',
    {'cat': SOURCES},
    params={'group_column': 'source', 'order': 3, 'title': 'Per-source coverage'},
  )
  assert 'alpha' in value.alt and 'delta' in value.alt


def test_one_column_linear_per_pixel(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'astro.sky_grid',
    {'cat': SOURCES},
    params={
      'group_column': 'source',
      'order': 3,
      'ncols': 1,
      'log': False,
      'per_area': False,
      'height': 6.0,
    },
  )


def test_precounted_pixels(tmp_path: Path) -> None:
  table = {'g': ['a', 'a', 'b', 'b'], 'pix': [0, 1, 1, 7], 'n': [3, 4, 5, 6]}
  check_figure_preprocessor(
    tmp_path,
    'astro.sky_grid',
    {'cat': table},
    params={'group_column': 'g', 'order': 1, 'ipix_column': 'pix', 'counts_column': 'n'},
  )


def test_compute_hand_checked() -> None:
  table = pa.table(
    {
      'ra': [45.0, 46.0, 135.0, 45.0],
      'dec': [30.0, 31.0, 30.0, -30.0],
      'who': ['b', 'b', 'b', 'a'],
    }
  )
  data = compute_sky_grid(table, 'who', order=0)
  assert data.column_names == ['group', 'ipix', 'count', 'order']
  assert data.column('group').to_pylist() == ['a', 'b', 'b']
  assert data.column('ipix').to_pylist() == [8, 0, 1]
  assert data.column('count').to_pylist() == [1.0, 2.0, 1.0]


def test_default_height_grows_with_rows() -> None:
  assert default_height(3, 3, 1.0) < default_height(4, 3, 1.0) < default_height(30, 3, 1.0)


def test_style_parameters_change_the_drawing(tmp_path: Path) -> None:
  base = _png(tmp_path, 'a')
  assert _png(tmp_path, 'b', ncols=2) != base
  assert _png(tmp_path, 'c', log=False) != base
  assert _png(tmp_path, 'd', per_area=False) != base
  assert _png(tmp_path, 'e', colorbar_label='other') != base


def test_more_than_30_panels_is_coded() -> None:
  table = pa.table({'ra': [1.0] * 31, 'dec': [1.0] * 31, 'g': [str(i) for i in range(31)]})
  with pytest.raises(PreprocessError) as caught:
    compute_sky_grid(table, 'g')
  assert caught.value.code == 'E602'


def test_thirty_panels_are_accepted(tmp_path: Path) -> None:
  table = {'ra': [float(i * 10) for i in range(30)], 'dec': [0.0] * 30, 'g': list('abcdefghij') * 3}
  table['g'] = [f'g{i:02d}' for i in range(30)]
  result = run_step(tmp_path, 'astro.sky_grid', {'cat': table}, params={'group_column': 'g'})
  assert _sidecar(result).num_rows == 30


def test_bad_ncols_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path, 'astro.sky_grid', {'cat': SOURCES}, params={'group_column': 'source', 'ncols': 0}
    )
  assert caught.value.code == 'E602'


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  schema = pa.schema([('ra', pa.float64()), ('dec', pa.float64()), ('g', pa.string())])
  empty = pa.table({'ra': [None], 'dec': [None], 'g': ['a']}, schema=schema)
  result = run_step(
    tmp_path, 'astro.sky_grid', {'cat': empty}, params={'group_column': 'g', 'order': 3}
  )
  fig = result.bundle.manifest.values['fig']
  assert fig.kind == 'figure'
  assert 'no positions' in fig.alt
  assert _sidecar(result).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'astro.sky_grid', {'cat': SOURCES}, params={'group_column': 'sorce'})
  assert caught.value.code == 'E603'
  assert 'source' in str(caught.value)
