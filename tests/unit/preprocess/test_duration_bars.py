from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.duration_bars import _format_duration, compute_duration_bars
from scireport.spec.kinds import FigureValue

ARTIFACTS = {
  'artifact': ['catalogue', 'xmatch', 'cutouts', 'summary'],
  'seconds': [3725.0, 125.4, 0.0, None],
  'reused': [False, False, True, None],
}
PARAMS = {'label_column': 'artifact', 'seconds_column': 'seconds', 'reused_column': 'reused'}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _sidecar(result: PreprocessResult) -> pa.Table:
  data = _figure(result).data
  assert data is not None
  return pq.read_table(pa.BufferReader(result.bundle.read_asset(data)))


@pytest.mark.parametrize(
  ('seconds', 'text'),
  [
    (None, '--'),
    (float('nan'), '--'),
    (float('inf'), '--'),
    (0.0, '0.0 s'),
    (0.34, '0.3 s'),
    (1.0, '1 s'),
    (43.4, '43 s'),
    (59.6, '1 min 00 s'),
    (125.0, '2 min 05 s'),
    (3600.0, '1 h 00 min'),
    (3725.0, '1 h 02 min'),
    (90000.0, '25 h 00 min'),
    (-125.0, '-2 min 05 s'),
  ],
)
def test_format_duration(seconds: float | None, text: str) -> None:
  assert _format_duration(seconds) == text


def test_artifacts(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path,
    'core.duration_bars',
    {'data': ARTIFACTS},
    params={**PARAMS, 'title': 'Build time'},
    min_sidecar_rows=4,
  )
  assert '4 artifacts' in value.alt
  assert '1 reused' in value.alt


def test_without_a_reused_column(tmp_path: Path) -> None:
  check_figure_preprocessor(
    tmp_path,
    'core.duration_bars',
    {'data': ARTIFACTS},
    params={'label_column': 'artifact', 'seconds_column': 'seconds', 'height': 3.0},
  )


def test_reused_flag_changes_the_drawing(tmp_path: Path) -> None:
  plain = run_step(
    tmp_path,
    'core.duration_bars',
    {'data': ARTIFACTS},
    params={'label_column': 'artifact', 'seconds_column': 'seconds'},
  )
  flagged = run_step(
    tmp_path, 'core.duration_bars', {'data': ARTIFACTS}, params=PARAMS, label='flagged'
  )
  assert _figure(plain).renditions[0].sha256 != _figure(flagged).renditions[0].sha256


def test_compute_hand_checked() -> None:
  data = compute_duration_bars(pa.table(ARTIFACTS), 'artifact', 'seconds', reused_column='reused')
  assert data.column_names == ['label', 'seconds', 'reused']
  assert data.column('seconds').to_pylist() == [3725.0, 125.4, 0.0, None]
  assert data.column('reused').to_pylist() == [False, False, True, False]


def test_empty_table_draws_a_placeholder(tmp_path: Path) -> None:
  table = pa.table({'artifact': pa.array([], pa.string()), 'seconds': pa.array([], pa.float64())})
  result = run_step(
    tmp_path,
    'core.duration_bars',
    {'data': table},
    params={'label_column': 'artifact', 'seconds_column': 'seconds'},
  )
  fig = _figure(result)
  assert fig.alt == 'No artifacts were recorded.'
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_all_null_seconds_still_draw(tmp_path: Path) -> None:
  table = {'artifact': ['a', 'b'], 'seconds': [None, None]}
  check_figure_preprocessor(
    tmp_path,
    'core.duration_bars',
    {'data': table},
    params={'label_column': 'artifact', 'seconds_column': 'seconds'},
  )


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(
      tmp_path,
      'core.duration_bars',
      {'data': ARTIFACTS},
      params={**PARAMS, 'reused_column': 'reuse'},
    )
  assert caught.value.code == 'E603'
  assert 'reused' in str(caught.value)
