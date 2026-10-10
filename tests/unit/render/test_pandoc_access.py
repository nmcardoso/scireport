"""Finding and running pandoc: a missing extra is E506 (exit 3), a failing pandoc is E507."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scireport import Bundle, MissingDependencyError, PandocError, Report
from scireport.cli import app
from scireport.render import pandoc as pandoc_module
from scireport.render import render_bundle
from scireport.render.pandoc import pandoc_available, pandoc_path, run_pandoc

runner = CliRunner()


@pytest.fixture
def no_pypandoc(monkeypatch: pytest.MonkeyPatch) -> None:
  """Make ``import pypandoc`` fail, as in an install without the extra."""
  monkeypatch.setitem(sys.modules, 'pypandoc', None)


def bundle() -> Bundle:
  return Report('T').add_text('intro', 'Some *prose*.', format='markdown').build()


def test_a_missing_extra_is_e506_with_the_install_command(no_pypandoc: None) -> None:
  with pytest.raises(MissingDependencyError) as caught:
    pandoc_path()
  assert caught.value.code == 'E506' and caught.value.exit_code == 3
  assert "uv add 'scireport[pandoc]'" in (caught.value.hint or '')
  assert not pandoc_available()


def test_pypandoc_without_an_executable_is_e506(monkeypatch: pytest.MonkeyPatch) -> None:
  class Fake:
    @staticmethod
    def get_pandoc_path() -> str:
      raise OSError('no pandoc')

  monkeypatch.setitem(sys.modules, 'pypandoc', Fake)
  with pytest.raises(MissingDependencyError, match='no pandoc executable'):
    pandoc_path()


def test_choosing_the_pandoc_engine_without_it_fails_before_rendering(no_pypandoc: None) -> None:
  with pytest.raises(MissingDependencyError) as caught:
    render_bundle(bundle(), markup_engine='pandoc', formats=['md'])
  assert caught.value.code == 'E506'


def test_an_office_format_without_pandoc_is_e506(no_pypandoc: None) -> None:
  with pytest.raises(MissingDependencyError) as caught:
    render_bundle(bundle(), template='generic@1', layout='minimal@1', formats=['docx'])
  assert caught.value.code == 'E506'


def test_the_core_install_renders_without_pandoc(no_pypandoc: None) -> None:
  result = render_bundle(bundle(), template='generic@1', layout='minimal@1', formats=['html'])
  assert 'html/report.html' in result.files
  assert result.manifest['engines']['pandoc'] is None


def test_the_command_line_exits_3(no_pypandoc: None, tmp_path: Path) -> None:
  source = Report('T').add_text('intro', 'x').write(tmp_path / 'b.scireport.zip')
  result = runner.invoke(
    app, ['render', str(source), '-o', str(tmp_path / 'o'), '-f', 'epub', '--json']
  )
  assert result.exit_code == 3, result.output
  assert json.loads(result.stdout)['issues'][0]['code'] == 'E506'


def test_a_failing_pandoc_is_e507(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  program = tmp_path / 'pandoc'
  program.write_text('#!/bin/sh\necho "boom" >&2\nexit 7\n', encoding='utf-8')
  program.chmod(program.stat().st_mode | stat.S_IXUSR)
  monkeypatch.setattr(pandoc_module, 'pandoc_path', lambda: str(program))
  with pytest.raises(PandocError) as caught:
    run_pandoc(['--version'], sandbox=False)
  assert caught.value.code == 'E507' and caught.value.exit_code == 1
  assert 'code 7' in caught.value.message and 'boom' in caught.value.message


def test_a_runaway_pandoc_is_stopped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  program = tmp_path / 'pandoc'
  program.write_text('#!/bin/sh\nsleep 5\n', encoding='utf-8')
  program.chmod(program.stat().st_mode | stat.S_IXUSR)
  monkeypatch.setattr(pandoc_module, 'pandoc_path', lambda: str(program))
  monkeypatch.setattr(pandoc_module, '_TIMEOUT_SECONDS', 0.2)
  with pytest.raises(PandocError, match='ran for more than'):
    run_pandoc(['--version'])


def test_an_unreadable_version_is_e507(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  program = tmp_path / 'pandoc'
  program.write_text('#!/bin/sh\necho "something else"\n', encoding='utf-8')
  program.chmod(program.stat().st_mode | stat.S_IXUSR)
  monkeypatch.setattr(pandoc_module, 'pandoc_path', lambda: str(program))
  pandoc_module.pandoc_version.cache_clear()
  try:
    with pytest.raises(PandocError, match='cannot read the pandoc version'):
      pandoc_module.pandoc_version()
  finally:
    pandoc_module.pandoc_version.cache_clear()
