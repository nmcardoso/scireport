"""``new``, ``export tex``, ``mplstyle``, ``agent``, ``templates``/``layouts NAME``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from render_fixtures import kitchen_sink
from typer.testing import CliRunner, Result

from scireport import open_bundle, write_bundle
from scireport.agent.skill import SKILL_DIR, skill_files
from scireport.cli import app

runner = CliRunner()


def invoke(*args: str, code: int = 0) -> Result:
  result = runner.invoke(app, list(args))
  assert result.exit_code == code, result.output
  return result


@pytest.fixture
def bundle_zip(tmp_path: Path) -> Path:
  return write_bundle(kitchen_sink(real=True), tmp_path / 'ks.scireport.zip')


# ---- new --------------------------------------------------------------------------------------


def test_new_writes_a_starter_that_validates_and_renders(tmp_path: Path) -> None:
  dest = tmp_path / 'r'
  invoke('new', str(dest), '--title', 'My report')
  assert (dest / 'scireport.yaml').is_file()
  assert json.loads(invoke('validate', str(dest), '--json').stdout)['ok'] is True
  invoke('render', str(dest), '-o', str(tmp_path / 'out'), '-f', 'html')
  assert 'My report' in (tmp_path / 'out' / 'html' / 'report.html').read_text(encoding='utf-8')


def test_new_refuses_a_non_empty_directory_unless_forced(tmp_path: Path) -> None:
  dest = tmp_path / 'r'
  invoke('new', str(dest))
  result = invoke('new', str(dest), '--json', code=2)
  assert json.loads(result.stdout)['issues'][0]['code'] == 'E410'
  invoke('new', str(dest), '--force', '--title', 'Again')
  with open_bundle(dest) as bundle:
    assert bundle.manifest.meta.title == 'Again'


def test_new_fills_the_required_fields_of_a_template(tmp_path: Path) -> None:
  dest = tmp_path / 'ks'
  result = invoke('new', str(dest), '-t', 'kitchen-sink', '--json')
  payload = json.loads(result.stdout)
  assert payload['values'] > 5
  with open_bundle(dest) as bundle:
    assert bundle.manifest.render.template == 'kitchen-sink@1'
  report = json.loads(invoke('validate', str(dest), '--json', '--no-render', code=2).stdout)
  # Values that need files (figures...) are listed as notes and then reported by validate.
  assert payload['notes'] and any(i['code'] == 'E105' for i in report['issues'])


# ---- export -----------------------------------------------------------------------------------


def test_export_tex_writes_fragments_and_reports_macros(bundle_zip: Path, tmp_path: Path) -> None:
  out = tmp_path / 'paper' / 'generated'
  result = invoke(
    'export', 'tex', str(bundle_zip), '-o', str(out), '-k', 'facts.*,tables.cut', '--json'
  )
  payload = json.loads(result.stdout)
  assert payload['files'] == ['numbers.tex', 'tab_tables.cut.tex']
  assert payload['macros']['FactsNPairs'] == 'facts.n_pairs'


def test_export_tex_graphics_prefix_defaults_to_the_directory_name(
  bundle_zip: Path, tmp_path: Path
) -> None:
  out = tmp_path / 'paper' / 'gen'
  invoke('export', 'tex', str(bundle_zip), '-o', str(out), '-k', 'figures.curve')
  assert '{gen/fig_figures.curve.pdf}' in (out / 'fig_figures.curve.tex').read_text(
    encoding='utf-8'
  )
  invoke(
    'export',
    'tex',
    str(bundle_zip),
    '-o',
    str(out),
    '-k',
    'figures.curve',
    '--graphics-prefix',
    'x/',
  )
  assert '{x/fig_figures.curve.pdf}' in (out / 'fig_figures.curve.tex').read_text(encoding='utf-8')


def test_export_tex_errors_exit_2(bundle_zip: Path, tmp_path: Path) -> None:
  result = invoke(
    'export', 'tex', str(bundle_zip), '-o', str(tmp_path / 'o'), '-k', 'nope', '--json', code=2
  )
  assert json.loads(result.stdout)['issues'][0]['code'] == 'E103'
  assert not (tmp_path / 'o').exists()


# ---- describing -------------------------------------------------------------------------------


def test_templates_and_layouts_can_be_described(tmp_path: Path) -> None:
  template = json.loads(invoke('templates', 'kitchen-sink@1', '--json').stdout)
  assert template['ref'] == 'kitchen-sink@1' and template['fields']
  layout = json.loads(invoke('layouts', 'default@1', '--json').stdout)
  assert {o['name'] for o in layout['options']} >= {'toc', 'cover', 'paper'}
  assert 'paper' in invoke('layouts', 'default@1').stdout
  assert 'required' in invoke('templates', 'kitchen-sink@1').stdout
  bad = invoke('templates', 'nope@9', '--json', code=2)
  assert json.loads(bad.stdout)['issues'][0]['code'] in {'E701', 'E504'}


# ---- mplstyle ---------------------------------------------------------------------------------


def test_mplstyle_commands() -> None:
  path = invoke('mplstyle', 'path', 'modern').stdout.strip()
  assert path.endswith('modern.mplstyle') and Path(path).is_file()
  assert json.loads(invoke('mplstyle', 'path', '--json').stdout)['layout'] == 'default'
  assert 'axes' in invoke('mplstyle', 'show').stdout
  assert json.loads(invoke('mplstyle', 'palette', '--json').stdout)
  assert invoke('mplstyle', 'palette').stdout
  invoke('mplstyle', 'path', 'nope@3', code=2)


# ---- agent ------------------------------------------------------------------------------------


def test_install_skill_copies_the_packaged_files(tmp_path: Path) -> None:
  dest = tmp_path / 'skills'
  result = invoke('agent', 'install-skill', '--dest', str(dest), '--json')
  assert json.loads(result.stdout)['files'] == skill_files()
  for name in skill_files():
    assert (dest / 'scireport' / name).read_bytes() == (SKILL_DIR / name).read_bytes()


def test_install_skill_check_reports_differences_with_exit_1(tmp_path: Path) -> None:
  dest = tmp_path / 'skills'
  missing = invoke('agent', 'install-skill', '--dest', str(dest), '--check', '--json', code=1)
  assert json.loads(missing.stdout)['missing'] == skill_files()
  invoke('agent', 'install-skill', '--dest', str(dest))
  assert 'up to date' in invoke('agent', 'install-skill', '--dest', str(dest), '--check').stdout
  (dest / 'scireport' / 'SKILL.md').write_text('changed', encoding='utf-8')
  (dest / 'scireport' / 'extra.md').write_text('x', encoding='utf-8')
  result = invoke('agent', 'install-skill', '--dest', str(dest), '--check', code=1)
  assert 'changed: SKILL.md' in result.output and 'extra: extra.md' in result.output
  invoke('agent', 'install-skill', '--dest', str(dest))
  assert not (dest / 'scireport' / 'extra.md').exists()


def test_install_skill_never_overwrites_another_skill(tmp_path: Path) -> None:
  other = tmp_path / 'skills' / 'scireport'
  other.mkdir(parents=True)
  (other / 'SKILL.md').write_text('---\nname: something-else\n---\n', encoding='utf-8')
  result = invoke('agent', 'install-skill', '--dest', str(tmp_path / 'skills'), '--json', code=2)
  assert json.loads(result.stdout)['issues'][0]['code'] == 'E410'
  assert 'something-else' in (other / 'SKILL.md').read_text(encoding='utf-8')


def test_mcp_config_prints_a_snippet_and_never_writes_a_file(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  monkeypatch.chdir(tmp_path)
  snippet = json.loads(invoke('agent', 'mcp-config', '--root', '/work').stdout)
  server = snippet['mcpServers']['scireport']
  assert server == {'command': 'scireport', 'args': ['mcp', 'serve', '--root', '/work']}
  uvx = json.loads(invoke('agent', 'mcp-config', '--uvx', '--ref', 'v1.0.0rc1').stdout)
  args = uvx['mcpServers']['scireport']['args']
  assert uvx['mcpServers']['scireport']['command'] == 'uvx'
  assert 'scireport[mcp] @ git+https://github.com/nmcardoso/scireport@v1.0.0rc1' in args
  assert list(tmp_path.iterdir()) == []


def test_mcp_serve_without_the_extra_exits_3(monkeypatch: pytest.MonkeyPatch) -> None:
  import sys

  monkeypatch.setitem(sys.modules, 'mcp', None)
  monkeypatch.setitem(sys.modules, 'mcp.server', None)
  result = invoke('mcp', 'serve', code=3)
  assert 'E904' in result.output or 'scireport[mcp]' in result.output


def test_install_skill_refuses_an_unrelated_folder(tmp_path: Path) -> None:
  folder = tmp_path / 'skills' / 'scireport'
  folder.mkdir(parents=True)
  (folder / 'notes.txt').write_text('mine', encoding='utf-8')
  invoke('agent', 'install-skill', '--dest', str(tmp_path / 'skills'), code=2)
  assert (folder / 'notes.txt').read_text(encoding='utf-8') == 'mine'
