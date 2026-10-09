"""``pack``, ``unpack`` and ``inspect`` through the Typer runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scireport import Report, open_bundle
from scireport.cli import app
from scireport.cli.bundle import default_destination

runner = CliRunner()


@pytest.fixture
def bundle_zip(tmp_path: Path, png_bytes: bytes) -> Path:
  report = Report('CLI demo', authors=['A B'])
  report.add_number('stats.n', 3061, unit='pairs', format='int')
  report.add_text('intro', 'Hello **world**', format='markdown')
  report.add_table('t.pairs', {'a': [1, 2], 'b': [0.5, None]}, caption='Pairs')
  report.add_image('logo', png_bytes, suffix='png', alt='logo')
  return report.write(tmp_path / 'demo.scireport.zip')


def test_inspect_prints_a_summary(bundle_zip: Path) -> None:
  result = runner.invoke(app, ['inspect', str(bundle_zip)])
  assert result.exit_code == 0, result.output
  out = result.stdout
  assert out.splitlines()[0] == 'CLI demo'
  assert 'spec 1.0, zip bundle' in out
  assert 'authors: A B' in out
  assert 'values: 4 (image 1, number 1, table 1, text 1)' in out
  assert 'integrity: ok' in out
  assert '3061 pairs' in out
  assert '2 rows, 2 columns, parquet' in out


def test_inspect_json_is_machine_readable(bundle_zip: Path) -> None:
  result = runner.invoke(app, ['inspect', str(bundle_zip), '--json'])
  assert result.exit_code == 0, result.output
  report = json.loads(result.stdout)
  assert report['ok'] is True
  assert report['spec'] == '1.0'
  assert report['counts'] == {'image': 1, 'number': 1, 'table': 1, 'text': 1}
  assert {v['key'] for v in report['values']} == {'stats.n', 'intro', 't.pairs', 'logo'}
  logo = next(v for v in report['values'] if v['key'] == 'logo')
  assert logo['assets'] == ['assets/images/logo.png']
  assert report['assets']['count'] == 2


def test_inspect_one_key(bundle_zip: Path) -> None:
  result = runner.invoke(app, ['inspect', str(bundle_zip), '--key', 'stats.n'])
  assert result.exit_code == 0
  assert json.loads(result.stdout) == {
    'kind': 'number',
    'value': 3061,
    'unit': 'pairs',
    'format': 'int',
  }
  missing = runner.invoke(app, ['inspect', str(bundle_zip), '--key', 'nope'])
  assert missing.exit_code == 2


def test_inspect_reports_integrity_problems_with_exit_2(tmp_path: Path, bundle_zip: Path) -> None:
  directory = tmp_path / 'broken'
  assert runner.invoke(app, ['unpack', str(bundle_zip), '-o', str(directory)]).exit_code == 0
  (directory / 'assets' / 'images' / 'logo.png').write_bytes(b'tampered')
  human = runner.invoke(app, ['inspect', str(directory)])
  assert human.exit_code == 2
  assert 'integrity: 1 problem(s)' in human.stdout
  assert 'E403' in human.stdout
  as_json = runner.invoke(app, ['inspect', str(directory), '--json'])
  assert as_json.exit_code == 2
  assert json.loads(as_json.stdout)['issues'][0]['code'] == 'E403'
  skipped = runner.invoke(app, ['inspect', str(directory), '--no-verify'])
  assert skipped.exit_code == 0
  assert 'integrity: not checked' in skipped.stdout


def test_inspect_errors_exit_2_and_log_codes(tmp_path: Path) -> None:
  result = runner.invoke(app, ['inspect', str(tmp_path / 'absent')])
  assert result.exit_code == 2
  assert 'E406' in result.output
  as_json = runner.invoke(app, ['inspect', str(tmp_path / 'absent'), '--json'])
  assert json.loads(as_json.stdout) == {
    'ok': False,
    'issues': [
      {'code': 'E406', 'severity': 'error', 'message': f'{tmp_path / "absent"} does not exist'}
    ],
  }


def test_invalid_manifests_list_every_problem(tmp_path: Path) -> None:
  bad = tmp_path / 'bad.json'
  bad.write_text(
    json.dumps(
      {
        'scireport': '1.0',
        'meta': {'title': 'T'},
        'values': {'Bad Key': 1, 'x': {'kind': 'tabel'}},
        'surprise': 1,
      }
    ),
    encoding='utf-8',
  )
  result = runner.invoke(app, ['inspect', str(bad), '--json'])
  assert result.exit_code == 2
  assert sorted(i['code'] for i in json.loads(result.stdout)['issues']) == ['E101', 'E201', 'E204']
  human = runner.invoke(app, ['inspect', str(bad)])
  assert human.exit_code == 2
  assert human.output.count('E1') + human.output.count('E2') >= 3


def test_newer_spec_versions_exit_2_with_an_upgrade_hint(tmp_path: Path) -> None:
  future = tmp_path / 'future.json'
  future.write_text('{"scireport": "1.7", "meta": {"title": "T"}}', encoding='utf-8')
  result = runner.invoke(app, ['inspect', str(future)])
  assert result.exit_code == 2
  assert 'E501' in result.output
  assert 'Upgrade scireport' in result.output


def test_pack_and_unpack_round_trip(tmp_path: Path, bundle_zip: Path) -> None:
  unpacked = runner.invoke(app, ['unpack', str(bundle_zip)])
  assert unpacked.exit_code == 0, unpacked.output
  directory = tmp_path / 'demo.scireport'
  assert unpacked.stdout.strip() == directory.as_posix()
  assert (directory / 'scireport.json').is_file()
  repacked = runner.invoke(
    app, ['pack', str(directory), '-o', str(tmp_path / 'again.scireport.zip')]
  )
  assert repacked.exit_code == 0, repacked.output
  assert (tmp_path / 'again.scireport.zip').read_bytes() == bundle_zip.read_bytes()


def test_pack_default_destination_and_json(tmp_path: Path, bundle_zip: Path) -> None:
  runner.invoke(app, ['unpack', str(bundle_zip), '-o', str(tmp_path / 'src')])
  result = runner.invoke(app, ['pack', str(tmp_path / 'src'), '--json'])
  assert result.exit_code == 0, result.output
  payload = json.loads(result.stdout)
  assert payload['path'] == (tmp_path / 'src.scireport.zip').as_posix()
  assert (payload['form'], payload['values'], payload['assets']) == ('zip', 4, 2)
  assert payload['warnings'] == []


def test_destinations_are_not_overwritten_without_force(tmp_path: Path, bundle_zip: Path) -> None:
  target = tmp_path / 'out.scireport.zip'
  assert runner.invoke(app, ['pack', str(bundle_zip), '-o', str(target)]).exit_code == 0
  refused = runner.invoke(app, ['pack', str(bundle_zip), '-o', str(target)])
  assert refused.exit_code == 2
  assert 'E410' in refused.output
  assert runner.invoke(app, ['pack', str(bundle_zip), '-o', str(target), '--force']).exit_code == 0


def test_pack_refuses_a_bundle_with_bad_hashes(tmp_path: Path, bundle_zip: Path) -> None:
  directory = tmp_path / 'tampered'
  runner.invoke(app, ['unpack', str(bundle_zip), '-o', str(directory)])
  (directory / 'assets' / 'images' / 'logo.png').write_bytes(b'tampered')
  result = runner.invoke(app, ['pack', str(directory), '-o', str(tmp_path / 'x.zip')])
  assert result.exit_code == 2
  assert 'E403' in result.output
  assert not (tmp_path / 'x.zip').exists()


def test_pack_warns_about_unreferenced_files(tmp_path: Path, bundle_zip: Path) -> None:
  directory = tmp_path / 'stray'
  runner.invoke(app, ['unpack', str(bundle_zip), '-o', str(directory)])
  (directory / 'assets' / 'text').mkdir()
  (directory / 'assets' / 'text' / 'stray.md').write_bytes(b'x')
  result = runner.invoke(app, ['pack', str(directory), '-o', str(tmp_path / 'p.zip'), '--json'])
  assert result.exit_code == 0
  assert [w['code'] for w in json.loads(result.stdout)['warnings']] == ['W402']
  with open_bundle(tmp_path / 'p.zip') as bundle:
    assert bundle.verify() == []


def test_max_size_is_enforced(tmp_path: Path) -> None:
  big = Report('big').add_text('a', 'x' * 3_000_000, as_asset=True).write(tmp_path / 'big.zip')
  result = runner.invoke(app, ['inspect', str(big), '--max-size', '1'])
  assert result.exit_code == 2
  assert 'E405' in result.output
  assert runner.invoke(app, ['inspect', str(big), '--max-size', '8']).exit_code == 0


def test_unwritable_destination_exits_1(tmp_path: Path, bundle_zip: Path) -> None:
  blocker = tmp_path / 'blocker'
  blocker.write_text('a file where a directory is needed', encoding='utf-8')
  result = runner.invoke(app, ['pack', str(bundle_zip), '-o', str(blocker / 'out.zip')])
  assert result.exit_code == 1
  result = runner.invoke(app, ['pack', str(bundle_zip), '-o', str(blocker / 'out.zip'), '--json'])
  assert result.exit_code == 1
  assert json.loads(result.stdout)['ok'] is False


@pytest.mark.parametrize(
  ('name', 'suffix', 'expected'),
  [
    ('demo.scireport.zip', '.scireport', 'demo.scireport'),
    ('demo.scireport', '.scireport.zip', 'demo.scireport.zip'),
    ('report.yaml', '.scireport.zip', 'report.scireport.zip'),
    ('report.json', '.scireport', 'report.scireport'),
    ('plain', '.scireport.zip', 'plain.scireport.zip'),
    ('x.ZIP', '.scireport', 'x.scireport'),
    ('.zip', '.scireport', '.zip.scireport'),
  ],
)
def test_default_destination(name: str, suffix: str, expected: str) -> None:
  assert default_destination(Path('d') / name, suffix) == Path('d') / expected


def test_global_options(tmp_path: Path, bundle_zip: Path) -> None:
  log_file = tmp_path / 'run.log'
  result = runner.invoke(
    app, ['--log-level', 'DEBUG', '--log-file', str(log_file), 'inspect', str(bundle_zip)]
  )
  assert result.exit_code == 0
  assert 'opened zip bundle' in log_file.read_text(encoding='utf-8')
  assert runner.invoke(app, ['--log-level', 'LOUD', 'inspect', str(bundle_zip)]).exit_code == 2
  assert runner.invoke(app, []).exit_code in (0, 2)
