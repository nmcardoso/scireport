from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from preprocess_dummies import CALLS

from scireport import Report, open_bundle
from scireport.errors import (
  MissingDependencyError,
  PreprocessError,
  PreprocessRunError,
  SpecError,
)
from scireport.preprocess import preprocess_bundle, write_back
from scireport.preprocess import runner as runner_module
from scireport.spec.kinds import FigureValue, TableValue

pytestmark = pytest.mark.usefixtures('no_builtins')


def _report(*, params: dict[str, Any] | None = None, outline: bool = False) -> Report:
  report = Report(title='Fixture')
  report.add_table('data', {'a': [1, 2, 3, 4], 'b': [0.5, 1.5, 2.5, None]})
  report.add_preprocess(
    'test.bars',
    version=2,
    id='bars',
    inputs={'table': 'data'},
    outputs={'figure': 'fig.bars'},
    params=params or {'column': 'a'},
  )
  if outline:
    report.set_outline(['fig.bars'])
  return report


def _run(report: Report, tmp_path: Path, **options: Any) -> Any:
  return preprocess_bundle(
    report.build(), work_dir=tmp_path / 'work', cache_dir=tmp_path / 'cache', **options
  )


def test_a_bundle_without_steps_is_returned_as_it_is() -> None:
  bundle = Report(title='T').build()
  result = preprocess_bundle(bundle)
  assert result.bundle is bundle and result.steps == []


def test_figure_and_sidecar_are_stored_at_the_step_key(tmp_path: Path) -> None:
  result = _run(_report(), tmp_path)
  value = result.bundle.manifest.values['fig.bars']
  assert isinstance(value, FigureValue)
  assert [r.format for r in value.renditions] == ['png', 'pdf']
  assert value.data is not None and value.data.path == 'assets/figures/fig.bars.data.parquet'
  sidecar = pq.read_table(pa.BufferReader(result.bundle.read_asset(value.data)))
  assert sidecar.column('value').to_pylist() == [1.0, 2.0, 3.0, 4.0]
  assert result.bundle.verify() == []


def test_the_input_bundle_is_not_changed(tmp_path: Path) -> None:
  bundle = _report().build()
  before = bundle.manifest.model_dump_json()
  result = preprocess_bundle(bundle, work_dir=tmp_path / 'work', cache_dir=tmp_path / 'cache')
  assert 'fig.bars' not in bundle.manifest.values
  assert bundle.manifest.model_dump_json() == before
  assert 'fig.bars' in result.bundle.manifest.values
  assert 'assets/figures/fig.bars.png' not in bundle.asset_paths


def test_the_work_dir_gets_the_assets_and_a_record_without_times(tmp_path: Path) -> None:
  _run(_report(), tmp_path)
  assert (tmp_path / 'work' / 'assets' / 'figures' / 'fig.bars.png').read_bytes()[:4] == b'\x89PNG'
  record = json.loads((tmp_path / 'work' / 'preprocess.json').read_text(encoding='utf-8'))
  (step,) = record['steps']
  assert step['label'] == 'bars' and step['name'] == 'test.bars' and step['version'] == 2
  assert step['cache'] == 'miss' and step['outputs'] == {'figure': 'fig.bars'}
  assert set(step) == {'label', 'name', 'version', 'cache', 'key', 'outputs'}


def test_same_inputs_are_a_cache_hit_and_nothing_runs(tmp_path: Path) -> None:
  first = _run(_report(), tmp_path)
  assert CALLS == ['test.bars']
  second = preprocess_bundle(
    _report().build(), work_dir=tmp_path / 'work2', cache_dir=tmp_path / 'cache'
  )
  assert CALLS == ['test.bars']
  assert [s.cache for s in first.steps] == ['miss'] and [s.cache for s in second.steps] == ['hit']
  assert first.steps[0].key == second.steps[0].key
  assert second.bundle.manifest.values['fig.bars'] == first.bundle.manifest.values['fig.bars']
  assert second.bundle.read_asset('assets/figures/fig.bars.png') == first.bundle.read_asset(
    'assets/figures/fig.bars.png'
  )


@pytest.mark.parametrize(
  'change',
  ['params', 'input', 'output_key', 'version', 'seed', 'layout'],
)
def test_any_change_of_the_inputs_of_a_step_is_a_miss(tmp_path: Path, change: str) -> None:
  _run(_report(), tmp_path)
  CALLS.clear()
  report = _report()
  options: dict[str, Any] = {}
  if change == 'params':
    report = _report(params={'column': 'a', 'scale': 2.0})
  elif change == 'input':
    report = Report(title='Fixture')
    report.add_table('data', {'a': [9, 9, 9, 9]})
    report.add_preprocess(
      'test.bars',
      version=2,
      id='bars',
      inputs={'table': 'data'},
      outputs={'figure': 'fig.bars'},
      params={'column': 'a'},
    )
  elif change == 'output_key':
    report = Report(title='Fixture')
    report.add_table('data', {'a': [1, 2, 3, 4]})
    report.add_preprocess(
      'test.bars',
      version=2,
      id='bars',
      inputs={'table': 'data'},
      outputs={'figure': 'other'},
      params={'column': 'a'},
    )
  elif change == 'version':
    report = Report(title='Fixture')
    report.add_table('data', {'a': [1, 2, 3, 4], 'b': [0.5, 1.5, 2.5, None]})
    report.add_preprocess(
      'test.bars',
      version=1,
      id='bars',
      inputs={'table': 'data'},
      outputs={'figure': 'fig.bars'},
      params={'column': 'a'},
    )
  elif change == 'seed':
    options = {'seed': 5}
  elif change == 'layout':
    options = {'layout': 'modern'}
  result = preprocess_bundle(
    report.build(), work_dir=tmp_path / 'w2', cache_dir=tmp_path / 'cache', **options
  )
  assert [s.cache for s in result.steps] == ['miss'] and CALLS == ['test.bars']


def test_a_different_scireport_version_is_a_miss(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  _run(_report(), tmp_path)
  CALLS.clear()
  monkeypatch.setattr('scireport.preprocess.cache.__version__', '999.0.0')
  result = _run(_report(), tmp_path)
  assert [s.cache for s in result.steps] == ['miss']


def test_use_cache_false_never_reads_or_writes(tmp_path: Path) -> None:
  _run(_report(), tmp_path, use_cache=False)
  _run(_report(), tmp_path, use_cache=False)
  assert CALLS == ['test.bars', 'test.bars']
  assert not (tmp_path / 'cache').exists()


def test_a_damaged_cache_entry_is_a_miss_not_an_error(
  tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
  first = _run(_report(), tmp_path)
  key = first.steps[0].key
  png = next((tmp_path / 'cache' / key[:2] / key / 'files').rglob('*.png'))
  png.write_bytes(b'not a png')
  CALLS.clear()
  with caplog.at_level('WARNING'):
    again = _run(_report(), tmp_path)
  assert [s.cache for s in again.steps] == ['miss'] and CALLS == ['test.bars']
  assert 'damaged cache entry' in caplog.text


def test_default_cache_dir_follows_the_environment(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  from scireport.preprocess.cache import default_cache_dir

  monkeypatch.setenv('SCIREPORT_CACHE_DIR', str(tmp_path / 'explicit'))
  assert default_cache_dir() == tmp_path / 'explicit'
  monkeypatch.delenv('SCIREPORT_CACHE_DIR')
  monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path / 'xdg'))
  assert default_cache_dir() == tmp_path / 'xdg' / 'scireport' / 'preprocess'


def test_a_later_step_reads_the_table_an_earlier_step_made(tmp_path: Path) -> None:
  report = Report(title='Fixture')
  report.add_table('data', {'a': [1, 2, 3]})
  report.add_preprocess(
    'test.bars',
    id='draw',
    inputs={'table': 'doubled'},
    outputs={'figure': 'fig'},
    params={'column': 'a'},
  )
  report.add_preprocess(
    'test.double',
    id='double',
    inputs={'table': 'data'},
    outputs={'table': 'doubled'},
    params={'column': 'a', 'factor': 3},
  )
  result = _run(report, tmp_path)
  assert [s.label for s in result.steps] == ['double', 'draw']
  table = result.bundle.read_table('doubled')
  assert table.column('a').to_pylist() == [3, 6, 9]
  figure = result.bundle.manifest.values['fig']
  assert isinstance(figure, FigureValue) and figure.data is not None
  sidecar = pq.read_table(pa.BufferReader(result.bundle.read_asset(figure.data)))
  assert sidecar.column('value').to_pylist() == [3.0, 6.0, 9.0]


def test_an_outline_may_name_a_key_a_step_will_write() -> None:
  bundle = _report(outline=True).build()
  assert 'fig.bars' not in bundle.manifest.values


def test_running_a_written_back_bundle_again_replaces_the_same_keys(tmp_path: Path) -> None:
  destination = tmp_path / 'report'
  _report(outline=True).write(destination)
  with open_bundle(destination) as bundle:
    first = preprocess_bundle(bundle, cache_dir=tmp_path / 'cache')
    write_back(first, destination)
  CALLS.clear()
  with open_bundle(destination) as bundle:
    assert isinstance(bundle.manifest.values['fig.bars'], FigureValue)
    second = preprocess_bundle(bundle, cache_dir=tmp_path / 'cache')
    assert [s.cache for s in second.steps] == ['hit'] and CALLS == []
    assert second.bundle.manifest.values == bundle.manifest.values
    assert second.bundle.verify() == []


def test_write_back_to_a_zip_keeps_the_steps_and_the_assets(tmp_path: Path) -> None:
  destination = tmp_path / 'report.scireport.zip'
  _report().write(destination)
  with open_bundle(destination) as bundle:
    write_back(preprocess_bundle(bundle, cache_dir=tmp_path / 'cache'), destination)
  with open_bundle(destination) as bundle:
    assert len(bundle.manifest.preprocess) == 1
    assert 'assets/figures/fig.bars.png' in bundle.asset_paths
    assert bundle.verify() == []


def test_a_failing_pre_processor_is_e606_with_the_cause(tmp_path: Path) -> None:
  report = _report()
  report.add_preprocess(
    'test.explode', id='bad', inputs={'table': 'data'}, outputs={'figure': 'bad.fig'}
  )
  with pytest.raises(PreprocessRunError) as caught:
    _run(report, tmp_path)
  error = caught.value
  assert error.code == 'E606' and error.exit_code == 1
  assert 'bad' in error.message and 'RuntimeError: boom' in error.message
  assert isinstance(error.__cause__, RuntimeError)


@pytest.mark.parametrize(
  ('name', 'fragment'),
  [
    ('test.wrong_port', 'must be a figure, got a table'),
    ('test.returns_number', 'must be a figure, got a number'),
    ('test.forgets', "returned no value for port 'figure'"),
  ],
)
def test_what_a_pre_processor_returns_is_checked_against_its_ports(
  tmp_path: Path, name: str, fragment: str
) -> None:
  report = Report(title='Fixture')
  report.add_table('data', {'a': [1]})
  report.add_preprocess(name, inputs={'table': 'data'}, outputs={'figure': 'fig'})
  with pytest.raises(PreprocessError) as caught:
    _run(report, tmp_path)
  assert caught.value.code == 'E603' and fragment in caught.value.message


def test_the_plan_runs_before_anything_so_nothing_is_written_on_error(tmp_path: Path) -> None:
  report = _report()
  report.add_preprocess('test.bars', id='bad', inputs={'table': 'nope'}, outputs={'figure': 'f2'})
  with pytest.raises(PreprocessError):
    _run(report, tmp_path)
  assert CALLS == [] and not (tmp_path / 'work').exists()


def test_a_missing_extra_is_e607_with_exit_code_3(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  from dataclasses import replace

  from scireport.preprocess import registry

  entry = registry.get_preprocessor('test.bars', 2)
  registry.register_preprocessor(replace(entry, requires='astro'), replace=True)
  monkeypatch.setattr(runner_module.importlib.util, 'find_spec', lambda name: None)
  with pytest.raises(MissingDependencyError) as caught:
    _run(_report(), tmp_path)
  assert caught.value.code == 'E607' and caught.value.exit_code == 3
  assert 'scireport[astro]' in (caught.value.hint or '')
  assert CALLS == []


def test_a_key_clash_with_an_unrelated_value_fails_the_manifest_check(tmp_path: Path) -> None:
  report = _report()
  report.add_text('fig.bars.extra', 'x')
  with pytest.raises(SpecError) as caught:
    _run(report, tmp_path)
  assert caught.value.code == 'E102'


def test_a_step_replaces_a_value_it_owns(tmp_path: Path) -> None:
  report = Report(title='Fixture')
  report.add_table('data', {'a': [1, 2]})
  report.add_text('fig', 'placeholder written by hand')
  report.add_preprocess(
    'test.bars', inputs={'table': 'data'}, outputs={'figure': 'fig'}, params={'column': 'a'}
  )
  result = _run(report, tmp_path)
  assert isinstance(result.bundle.manifest.values['fig'], FigureValue)


def test_an_optional_input_arrives_as_none(tmp_path: Path) -> None:
  report = Report(title='Fixture')
  report.add_table('data', {'a': [1, 2]})
  report.add_preprocess('test.two', inputs={'left': 'data'}, outputs={'table': 'copy'})
  result = _run(report, tmp_path)
  assert isinstance(result.bundle.manifest.values['copy'], TableValue)
  assert CALLS == ['test.two']
