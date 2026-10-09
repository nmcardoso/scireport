"""``scireport spec``: version, schema, kinds and migrate."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from scireport._version import __version__
from scireport.cli import app
from scireport.spec.kinds import KINDS
from scireport.spec.schema import SCHEMA_DIR, schema_filename

runner = CliRunner()


def test_version_flag() -> None:
  result = runner.invoke(app, ['--version'])
  assert result.exit_code == 0
  assert result.stdout.strip() == __version__


def test_spec_version() -> None:
  assert runner.invoke(app, ['spec', 'version']).stdout.strip() == '1.0'


def test_spec_schema_prints_the_frozen_schema(tmp_path: Path) -> None:
  result = runner.invoke(app, ['spec', 'schema'])
  assert result.exit_code == 0
  assert result.stdout == (SCHEMA_DIR / schema_filename('1.0')).read_text(encoding='utf-8')
  target = tmp_path / 'schema.json'
  written = runner.invoke(app, ['spec', 'schema', '-o', str(target)])
  assert written.exit_code == 0
  assert target.read_text(encoding='utf-8') == result.stdout
  assert b'\r' not in target.read_bytes()


def test_spec_kinds() -> None:
  as_json = runner.invoke(app, ['spec', 'kinds', '--json'])
  rows = json.loads(as_json.stdout)
  assert [row['kind'] for row in rows] == list(KINDS)
  figure = next(row for row in rows if row['kind'] == 'figure')
  assert 'alt' in figure['fields']
  assert 'kind' not in figure['fields']
  text = runner.invoke(app, ['spec', 'kinds'])
  assert text.exit_code == 0
  assert 'figure' in text.stdout
  assert '``' not in text.stdout


def test_spec_migrate(tmp_path: Path) -> None:
  source = tmp_path / 'm.yaml'
  source.write_text('scireport: "1.0"\nmeta: {title: T}\nvalues: {a: 1}\n', encoding='utf-8')
  result = runner.invoke(app, ['spec', 'migrate', str(source)])
  assert result.exit_code == 0
  assert json.loads(result.stdout) == {
    'scireport': '1.0',
    'meta': {'title': 'T'},
    'values': {'a': 1},
  }
  target = tmp_path / 'm.json'
  assert runner.invoke(app, ['spec', 'migrate', str(source), '-o', str(target)]).exit_code == 0
  assert json.loads(target.read_text(encoding='utf-8'))['values'] == {'a': 1}


def test_spec_migrate_errors(tmp_path: Path) -> None:
  source = tmp_path / 'm.json'
  source.write_text('{"scireport": "1.0"}', encoding='utf-8')
  future = runner.invoke(app, ['spec', 'migrate', str(source), '--to', '2.0'])
  assert future.exit_code == 2
  assert 'E501' in future.output
  source.write_text('{"meta": {}}', encoding='utf-8')
  assert runner.invoke(app, ['spec', 'migrate', str(source)]).exit_code == 2
  assert runner.invoke(app, ['spec', 'migrate', str(tmp_path / 'absent.json')]).exit_code == 1
