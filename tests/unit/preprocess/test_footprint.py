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
from scireport.preprocess.astro.footprint import compute_footprint
from scireport.spec.kinds import FigureValue

_RNG = np.random.default_rng(11)


def _patch(n: int, ra: float, dec: float, size: float, name: str) -> dict[str, list[Any]]:
  return {
    'ra': list(_RNG.normal(ra, size, n) % 360.0),
    'dec': list(np.clip(_RNG.normal(dec, size, n), -89.0, 89.0)),
    'survey': [name] * n,
  }


def _stack(*parts: dict[str, list[Any]]) -> dict[str, list[Any]]:
  return {key: [item for part in parts for item in part[key]] for key in parts[0]}


SURVEYS = _stack(
  _patch(200, 150.0, 30.0, 25.0, 'north'),
  _patch(150, 300.0, -40.0, 20.0, 'south'),
  _patch(100, 10.0, 0.0, 15.0, 'equator'),
)


def _sidecar(result: Any, key: str = 'fig') -> pa.Table:
  value = result.bundle.manifest.values[key]
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))


def test_single_footprint(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'astro.footprint',
    {'cat': {'ra': SURVEYS['ra'], 'dec': SURVEYS['dec']}},
    params={'order': 3, 'title': 'Coverage'},
  )
  assert 'of the sky' in value.alt


def test_several_surveys_with_legend(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'astro.footprint',
    {'cat': SURVEYS},
    params={'order': 3, 'group_column': 'survey'},
  )


def test_precounted_pixels(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'astro.footprint',
    {'cat': {'pix': [0, 1, 2, 30, 31], 'n': [5, 1, 9, 2, 8]}},
    params={'order': 2, 'ipix_column': 'pix', 'counts_column': 'n'},
  )


def test_compute_hand_checked() -> None:
  table = pa.table(
    {
      'ra': [45.0, 46.0, 135.0, 45.0],
      'dec': [30.0, 31.0, 30.0, -30.0],
      'who': ['a', 'a', 'a', 'b'],
    }
  )
  data = compute_footprint(table, order=0, group_column='who')
  assert data.column_names == ['group', 'ipix', 'count', 'order']
  assert data.column('group').to_pylist() == ['a', 'a', 'b']
  assert data.column('ipix').to_pylist() == [0, 1, 8]
  assert data.column('count').to_pylist() == [2.0, 1.0, 1.0]
  only = compute_footprint(table, order=0, group_column='who', min_count=2.0)
  assert only.column('ipix').to_pylist() == [0]


def test_group_names_are_in_the_alt_text_and_legend_changes_the_drawing(tmp_path: Path) -> None:
  def png(label: str, **params: object) -> bytes:
    result = run_step(
      tmp_path, 'astro.footprint', {'cat': SURVEYS}, params={'order': 3, **params}, label=label
    )
    value = result.bundle.manifest.values['fig']
    assert isinstance(value, FigureValue)
    if label == 'grouped':
      assert 'north' in value.alt and 'south' in value.alt
    return bytes(result.bundle.read_asset(next(r for r in value.renditions if r.format == 'png')))

  assert png('grouped', group_column='survey') != png('plain')
  assert png('strict', min_count=3.0) != png('plain')


def test_too_many_groups_is_coded() -> None:
  table = pa.table({'ra': [1.0] * 13, 'dec': [1.0] * 13, 'g': [str(i) for i in range(13)]})
  with pytest.raises(PreprocessError) as caught:
    compute_footprint(table, group_column='g')
  assert caught.value.code == 'E602'


def test_empty_input_draws_a_placeholder(tmp_path: Path) -> None:
  schema = pa.schema([('ra', pa.float64()), ('dec', pa.float64())])
  empty = pa.table({'ra': [None], 'dec': [None]}, schema=schema)
  result = run_step(tmp_path, 'astro.footprint', {'cat': empty}, params={'order': 3})
  fig = result.bundle.manifest.values['fig']
  assert fig.kind == 'figure'
  assert 'nothing to draw' in fig.alt
  assert _sidecar(result).num_rows == 0


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'astro.footprint', {'cat': SURVEYS}, params={'group_column': 'surveys'})
  assert caught.value.code == 'E603'
  assert 'survey' in str(caught.value)
