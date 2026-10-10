from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_harness import PNG_MAGIC, check_figure_preprocessor, run_step

from scireport.errors import PreprocessError
from scireport.preprocess import PreprocessResult
from scireport.preprocess.core.funnel import compute_funnel
from scireport.spec.kinds import FigureValue

STEPS = {
  'step': ['all rows', 'mag_g < 21', 'flag = 0', 'ra in [1, 2]', 'broken cut'],
  'n': [1_000_000, 800_000, 800_000, 120_000, None],
}
PARAMS = {'label_column': 'step', 'count_column': 'n'}


def _figure(result: PreprocessResult) -> FigureValue:
  value = result.bundle.manifest.values['fig']
  assert isinstance(value, FigureValue)
  return value


def _png(tmp_path: Path, label: str, params: Mapping[str, object]) -> bytes:
  result = run_step(tmp_path, 'core.funnel', {'data': STEPS}, params=params, label=label)
  png = result.bundle.read_asset(_figure(result).renditions[0])
  assert png.startswith(PNG_MAGIC)
  return bytes(png)


def test_both_panels(tmp_path: Path) -> None:
  value = check_figure_preprocessor(
    tmp_path, 'core.funnel', {'data': STEPS}, params={**PARAMS, 'title': 'Cuts'}
  )
  assert 'Two panels' in value.alt
  assert 'Failed steps: 1.' in value.alt


@pytest.mark.parametrize('panels', ['counts', 'drops'])
def test_one_panel(tmp_path: Path, panels: str) -> None:
  check_figure_preprocessor(
    tmp_path, 'core.funnel', {'data': STEPS}, params={**PARAMS, 'panels': panels}
  )


def test_compute_on_a_hand_checked_example() -> None:
  data = compute_funnel(pa.table(STEPS), 'step', 'n')
  assert data.column('label').to_pylist()[0] == 'all rows'
  assert data.column('count').to_pylist() == [1_000_000.0, 800_000.0, 800_000.0, 120_000.0, None]
  # The first step is the baseline, and a failed step has no measurable drop.
  assert data.column('removed').to_pylist() == [None, 200_000.0, 0.0, 680_000.0, None]


def test_step_after_a_failed_one_has_no_drop() -> None:
  data = compute_funnel(pa.table({'s': ['a', 'b', 'c'], 'n': [10, None, 4]}), 's', 'n')
  assert data.column('removed').to_pylist() == [None, None, None]


def test_panels_change_the_drawing(tmp_path: Path) -> None:
  both = _png(tmp_path, 'both', PARAMS)
  counts = _png(tmp_path, 'counts', {**PARAMS, 'panels': 'counts'})
  drops = _png(tmp_path, 'drops', {**PARAMS, 'panels': 'drops'})
  assert len({both, counts, drops}) == 3


def test_empty_input_draws_placeholders(tmp_path: Path) -> None:
  empty = {'step': pa.array([], pa.string()), 'n': pa.array([], pa.int64())}
  result = run_step(tmp_path, 'core.funnel', {'data': empty}, params=PARAMS)
  fig = _figure(result)
  assert fig.data is not None
  assert pq.read_table(pa.BufferReader(result.bundle.read_asset(fig.data))).num_rows == 0


def test_all_failed_draws_the_drop_placeholder(tmp_path: Path) -> None:
  failed = {'step': ['a', 'b'], 'n': pa.array([None, None], pa.int64())}
  result = run_step(tmp_path, 'core.funnel', {'data': failed}, params=PARAMS)
  assert _figure(result).data is not None


def test_missing_column_is_coded(tmp_path: Path) -> None:
  with pytest.raises(PreprocessError) as caught:
    run_step(tmp_path, 'core.funnel', {'data': STEPS}, params={**PARAMS, 'count_column': 'm'})
  assert caught.value.code == 'E603'
  assert "'n'" in str(caught.value)
