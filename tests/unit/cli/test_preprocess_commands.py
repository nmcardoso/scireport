"""``preprocess`` and ``preprocessors``, and pre-processing inside ``render`` and ``validate``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scireport import Report, open_bundle
from scireport.cli import app
from scireport.spec.kinds import FigureValue

pytestmark = pytest.mark.usefixtures('no_builtins')
runner = CliRunner()


def _report(**step: object) -> Report:
  report = Report(title='Fixture')
  report.add_table('data', {'a': [1, 2, 3, 4]})
  report.add_preprocess(
    'test.bars',
    version=2,
    id='bars',
    inputs={'table': 'data'},
    outputs={'figure': 'fig.bars'},
    params={'column': 'a'},
    **step,
  )
  report.set_outline(['fig.bars'])
  return report


@pytest.fixture
def source(tmp_path: Path) -> Path:
  return _report().write(tmp_path / 'report')


def test_preprocessors_lists_the_registry(tmp_path: Path) -> None:
  result = runner.invoke(app, ['preprocessors'])
  assert result.exit_code == 0, result.output
  assert 'test.bars@2' in result.stdout and 'test.double@1' in result.stdout


def test_preprocessors_json_lists_every_entry() -> None:
  result = runner.invoke(app, ['preprocessors', '--json'])
  rows = json.loads(result.stdout)
  assert {'test.bars@1', 'test.bars@2'} <= {row['ref'] for row in rows}


def test_one_preprocessor_is_described_with_ports_and_parameters() -> None:
  result = runner.invoke(app, ['preprocessors', 'test.bars'])
  assert result.exit_code == 0, result.output
  assert 'test.bars@2' in result.stdout
  assert 'table: table' in result.stdout and 'figure: figure' in result.stdout
  assert 'column (required)' in result.stdout and 'scale = 1.0' in result.stdout
  detail = json.loads(runner.invoke(app, ['preprocessors', 'test.bars', '--json']).stdout)
  assert detail['params']['required'] == ['column']


def test_an_unknown_preprocessor_exits_2_with_a_suggestion() -> None:
  result = runner.invoke(app, ['preprocessors', 'test.bar'])
  assert result.exit_code == 2
  assert 'E601' in result.output and "Did you mean 'test.bars'?" in result.output


def test_preprocess_leaves_the_source_alone_and_fills_the_work_dir(
  source: Path, tmp_path: Path
) -> None:
  before = sorted(p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file())
  work = tmp_path / 'work'
  result = runner.invoke(
    app,
    ['preprocess', str(source), '--work-dir', str(work), '--cache-dir', str(tmp_path / 'cache')],
  )
  assert result.exit_code == 0, result.output
  assert 'bars' in result.stdout and 'miss' in result.stdout
  assert (work / 'assets' / 'figures' / 'fig.bars.png').is_file()
  assert (
    sorted(p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()) == before
  )


def test_preprocess_json_and_a_second_run_hits_the_cache(source: Path, tmp_path: Path) -> None:
  args = [
    'preprocess', str(source), '--work-dir', str(tmp_path / 'w'),
    '--cache-dir', str(tmp_path / 'cache'), '--json',
  ]  # fmt: skip
  first = json.loads(runner.invoke(app, args).stdout)
  second = json.loads(runner.invoke(app, args).stdout)
  assert first['ok'] and first['steps'][0]['cache'] == 'miss'
  assert second['steps'][0]['cache'] == 'hit'


def test_write_back_replaces_the_source(source: Path, tmp_path: Path) -> None:
  result = runner.invoke(
    app,
    [
      'preprocess', str(source), '--write-back', '--work-dir', str(tmp_path / 'w'),
      '--cache-dir', str(tmp_path / 'cache'),
    ],
  )  # fmt: skip
  assert result.exit_code == 0, result.output
  with open_bundle(source) as bundle:
    assert isinstance(bundle.manifest.values['fig.bars'], FigureValue)
    assert bundle.verify() == []


def test_output_writes_a_new_bundle(source: Path, tmp_path: Path) -> None:
  out = tmp_path / 'done.scireport.zip'
  result = runner.invoke(
    app,
    [
      'preprocess', str(source), '-o', str(out), '--work-dir', str(tmp_path / 'w'),
      '--cache-dir', str(tmp_path / 'cache'),
    ],
  )  # fmt: skip
  assert result.exit_code == 0, result.output
  with open_bundle(out) as bundle:
    assert 'fig.bars' in bundle.manifest.values


def test_output_and_write_back_exclude_each_other(source: Path, tmp_path: Path) -> None:
  result = runner.invoke(
    app, ['preprocess', str(source), '-o', str(tmp_path / 'x'), '--write-back']
  )
  assert result.exit_code == 2


def test_a_bundle_without_steps_says_so(tmp_path: Path) -> None:
  plain = Report(title='T').write(tmp_path / 'plain')
  result = runner.invoke(app, ['preprocess', str(plain), '--work-dir', str(tmp_path / 'w')])
  assert result.exit_code == 0 and result.stdout.strip() == 'no steps'


def test_plan_errors_are_reported_together_with_exit_code_2(tmp_path: Path) -> None:
  report = Report(title='T')
  report.add_table('data', {'a': [1]})
  report.add_preprocess('test.bar', inputs={'table': 'data'}, outputs={'figure': 'f'})
  report.add_preprocess(
    'test.bars', inputs={'table': 'dta'}, outputs={'figure': 'g'}, params={'colum': 'a'}
  )
  path = report.write(tmp_path / 'bad')
  result = runner.invoke(app, ['preprocess', str(path), '--json', '--no-cache'])
  assert result.exit_code == 2
  codes = [issue['code'] for issue in json.loads(result.stdout)['issues']]
  assert 'E601' in codes and 'E602' in codes and 'E603' in codes


def test_a_failing_step_exits_1(tmp_path: Path) -> None:
  report = Report(title='T')
  report.add_table('data', {'a': [1]})
  report.add_preprocess('test.explode', inputs={'table': 'data'}, outputs={'figure': 'f'})
  path = report.write(tmp_path / 'boom')
  result = runner.invoke(
    app, ['preprocess', str(path), '--no-cache', '--work-dir', str(tmp_path / 'w')]
  )
  assert result.exit_code == 1 and 'E606' in result.output


def test_module_function_steps_need_the_flag(tmp_path: Path) -> None:
  report = Report(title='T')
  report.add_table('data', {'a': [1]})
  report.add_preprocess('os.path:join', inputs={'table': 'data'}, outputs={'figure': 'f'})
  path = report.write(tmp_path / 'imp')
  result = runner.invoke(app, ['preprocess', str(path), '--no-cache'])
  assert result.exit_code == 2 and 'E605' in result.output and '--allow-import' in result.output


def test_render_runs_the_steps_first(source: Path, tmp_path: Path) -> None:
  out = tmp_path / 'out'
  result = runner.invoke(
    app,
    ['render', str(source), '-o', str(out), '-f', 'md', '--cache-dir', str(tmp_path / 'cache')],
  )
  assert result.exit_code == 0, result.output
  assert (out / 'md' / 'assets' / 'figures' / 'fig.bars.png').is_file() or any(
    out.rglob('fig.bars.png')
  )


def test_render_without_preprocessing_cannot_find_the_figure(source: Path, tmp_path: Path) -> None:
  result = runner.invoke(
    app, ['render', str(source), '-o', str(tmp_path / 'out'), '-f', 'md', '--no-preprocess']
  )
  assert result.exit_code == 2, result.output


def test_validate_runs_the_steps_too(source: Path, tmp_path: Path) -> None:
  result = runner.invoke(
    app, ['validate', str(source), '-f', 'md', '--cache-dir', str(tmp_path / 'cache')]
  )
  assert result.exit_code == 0, result.output
