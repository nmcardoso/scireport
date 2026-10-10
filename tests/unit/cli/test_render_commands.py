"""``validate``, ``render``, ``templates`` and ``layouts`` through the Typer runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from render_fixtures import kitchen_sink, write_template
from typer.testing import CliRunner

from scireport import Report, open_bundle, write_bundle
from scireport.cli import app

runner = CliRunner()


@pytest.fixture
def bundle_zip(tmp_path: Path) -> Path:
  return write_bundle(kitchen_sink(), tmp_path / 'sink.scireport.zip')


@pytest.fixture
def broken_template(tmp_path: Path) -> Path:
  return write_template(
    tmp_path / 'needs',
    body='{{ c.value(v("must.exist")) }}',
    extra='fields:\n  - {key: must.exist, kind: number}\n  - {key: also.needed, kind: text}\n',
  )


def test_templates_lists_the_built_ins() -> None:
  result = runner.invoke(app, ['templates'])
  assert result.exit_code == 0, result.output
  assert result.stdout.startswith('generic@1')
  assert 'md,html,tex' in result.stdout


def test_layouts_lists_the_built_ins_as_json() -> None:
  result = runner.invoke(app, ['layouts', '--json'])
  assert result.exit_code == 0, result.output
  rows = json.loads(result.stdout)
  assert [row['ref'] for row in rows] == ['minimal@1']
  assert rows[0]['formats'] == ['md', 'html', 'tex']


def test_validate_passes_a_good_bundle(bundle_zip: Path) -> None:
  result = runner.invoke(app, ['validate', str(bundle_zip), '-l', 'minimal'])
  assert result.exit_code == 0, result.output
  assert result.stdout.strip() == 'valid: 0 error(s), 0 warning(s)'


def test_validate_json_reports_every_problem_and_exits_2(
  bundle_zip: Path, broken_template: Path
) -> None:
  result = runner.invoke(
    app, ['validate', str(bundle_zip), '-t', str(broken_template), '--json', '-f', 'md']
  )
  assert result.exit_code == 2, result.output
  report = json.loads(result.stdout)
  assert report['ok'] is False and report['exit_code'] == 2
  codes = {issue['code'] for issue in report['issues']}
  assert {'E105', 'E106'} <= codes
  assert report['counts']['errors'] >= 2
  first = next(issue for issue in report['issues'] if issue['code'] == 'E105')
  assert first['key'] == 'must.exist' or first['key'] == 'also.needed'


def test_validate_text_output_lists_the_issues(bundle_zip: Path, broken_template: Path) -> None:
  result = runner.invoke(app, ['validate', str(bundle_zip), '-t', str(broken_template)])
  assert result.exit_code == 2
  assert 'E105' in result.stdout
  assert result.stdout.strip().splitlines()[-1].startswith('invalid: ')


def test_strict_turns_warnings_into_failures(tmp_path: Path) -> None:
  path = Report('T').add_text('t', 'x').add_text('unused', 'y').write(tmp_path / 'w.scireport.zip')
  template = write_template(
    tmp_path / 'tpl', body='{{ c.value(v("t")) }}', extra='fields:\n  - {key: t, kind: text}\n'
  )
  lenient = runner.invoke(app, ['validate', str(path), '-t', str(template)])
  strict = runner.invoke(app, ['validate', str(path), '-t', str(template), '--strict'])
  assert lenient.exit_code == 0, lenient.output
  assert 'W401' in lenient.stdout
  assert strict.exit_code == 2


def test_render_writes_every_format(bundle_zip: Path, tmp_path: Path) -> None:
  out = tmp_path / 'out'
  result = runner.invoke(app, ['render', str(bundle_zip), '-o', str(out), '-l', 'minimal'])
  assert result.exit_code == 0, result.output
  assert (out / 'md' / 'index.md').is_file()
  assert (out / 'html' / 'report.html').is_file()
  assert (out / 'tex' / 'report.tex').is_file()
  assert (out / 'render-manifest.json').is_file()
  assert 'tex/report.tex' in result.stdout.splitlines()


def test_render_one_format_flat_as_json(bundle_zip: Path, tmp_path: Path) -> None:
  out = tmp_path / 'out'
  result = runner.invoke(
    app, ['render', str(bundle_zip), '-o', str(out), '-f', 'html', '--flat', '--json']
  )
  assert result.exit_code == 0, result.output
  payload = json.loads(result.stdout)
  assert payload['ok'] is True and 'report.html' in payload['files']
  assert (out / 'report.html').is_file() and not (out / 'md').exists()


def test_render_takes_layout_options(bundle_zip: Path, tmp_path: Path) -> None:
  out = tmp_path / 'out'
  result = runner.invoke(
    app, ['render', str(bundle_zip), '-o', str(out), '-f', 'tex', '-O', 'paper=letter', '--flat']
  )
  assert result.exit_code == 0, result.output
  assert 'letterpaper' in (out / 'report.tex').read_text(encoding='utf-8')


def test_a_bad_option_is_an_error(bundle_zip: Path, tmp_path: Path) -> None:
  out = tmp_path / 'out'
  for option, code in (('paper=tabloid', 'E806'), ('paper', 'E806')):
    result = runner.invoke(app, ['render', str(bundle_zip), '-o', str(out), '-O', option, '--json'])
    assert result.exit_code == 2, result.output
    assert json.loads(result.stdout)['issues'][0]['code'] == code
  assert not out.exists()


@pytest.mark.parametrize(('name', 'code'), [('pdf', 'E805'), ('rtf', 'E801')])
def test_unknown_or_later_formats_are_refused(
  bundle_zip: Path, tmp_path: Path, name: str, code: str
) -> None:
  result = runner.invoke(
    app, ['render', str(bundle_zip), '-o', str(tmp_path / 'o'), '-f', name, '--json']
  )
  assert result.exit_code == 2
  assert json.loads(result.stdout)['issues'][0]['code'] == code


def test_render_refuses_to_write_when_validation_fails(
  bundle_zip: Path, broken_template: Path, tmp_path: Path
) -> None:
  out = tmp_path / 'out'
  result = runner.invoke(
    app, ['render', str(bundle_zip), '-t', str(broken_template), '-o', str(out)]
  )
  assert result.exit_code == 2
  assert not out.exists()


def test_a_missing_bundle_exits_with_a_runtime_error(tmp_path: Path) -> None:
  result = runner.invoke(app, ['validate', str(tmp_path / 'nope.zip')])
  assert result.exit_code != 0


def test_pack_pins_the_named_template_and_layout(tmp_path: Path) -> None:
  report = Report('T').add_text('t', 'x').set_render(template='generic', layout='minimal')
  source = report.write(tmp_path / 'src.scireport.zip')
  packed = tmp_path / 'packed.scireport.zip'
  result = runner.invoke(app, ['pack', str(source), '-o', str(packed)])
  assert result.exit_code == 0, result.output
  with open_bundle(packed) as bundle:
    assert bundle.manifest.render.template == 'generic@1'
    assert bundle.manifest.render.layout == 'minimal@1'
