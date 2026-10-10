"""The PDF engines without a toolchain: planning, errors, log parsing and reproducibility inputs."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest
from render_fixtures import kitchen_sink
from typer.testing import CliRunner

from scireport import Report, write_bundle
from scireport.cli import app
from scireport.errors import MissingDependencyError, PdfError, RenderError, TemplateError
from scireport.render import render_bundle
from scireport.render.pdf import EPOCH_DEFAULT, fixed_epoch, source_date_epoch, weasy
from scireport.render.pdf import latex as latex_engine

runner = CliRunner()


def test_the_epoch_of_the_environment_wins(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setenv('SOURCE_DATE_EPOCH', '1700000000')
  assert source_date_epoch('2026-10-09') == 1700000000


def test_the_epoch_comes_from_the_date_of_the_report(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.delenv('SOURCE_DATE_EPOCH', raising=False)
  assert source_date_epoch('2026-10-09') == 1791504000
  assert source_date_epoch('2026-10-09T00:00:00Z') == 1791504000


def test_the_epoch_never_comes_from_the_clock(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.delenv('SOURCE_DATE_EPOCH', raising=False)
  assert source_date_epoch(None) == EPOCH_DEFAULT
  assert source_date_epoch('not a date') == EPOCH_DEFAULT


def test_fixed_epoch_restores_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.delenv('SOURCE_DATE_EPOCH', raising=False)
  with fixed_epoch(5):
    assert os.environ['SOURCE_DATE_EPOCH'] == '5'
  assert 'SOURCE_DATE_EPOCH' not in os.environ
  monkeypatch.setenv('SOURCE_DATE_EPOCH', '9')
  with pytest.raises(RuntimeError), fixed_epoch(5):
    raise RuntimeError('boom')
  assert os.environ['SOURCE_DATE_EPOCH'] == '9'


def test_a_latex_error_is_read_with_its_file_and_line() -> None:
  log = (
    'This is LuaHBTeX\n'
    './report.tex:38: Undefined control sequence.\n'
    'l.38 \\toprule\n'
    './report.tex:38: Undefined control sequence.\n'
    './scireport-default.sty:12: Missing $ inserted.\n'
  )
  issues = latex_engine.parse_log(log)
  assert [(i.code, i.location) for i in issues] == [
    ('E902', './report.tex:38'),
    ('E902', './scireport-default.sty:12'),
  ]
  assert issues[0].message == 'Undefined control sequence.'


def test_a_bang_line_is_read_when_there_is_no_file_line_form() -> None:
  issues = latex_engine.parse_log('! Emergency stop.\n<*> report.tex\n')
  assert [(i.code, i.message) for i in issues] == [('E902', 'Emergency stop.')]


def test_a_missing_package_is_a_missing_dependency() -> None:
  log = "./report.tex:5: LaTeX Error: File `tcolorbox.sty' not found.\n"
  assert [i.code for i in latex_engine.parse_log(log)] == ['E901']
  failure = latex_engine._failure(log)
  assert isinstance(failure, MissingDependencyError)
  assert failure.exit_code == 3
  assert 'tcolorbox.sty' in failure.message
  assert 'tlmgr' in str(failure)


def test_a_compile_that_leaves_no_error_line_is_still_an_error() -> None:
  failure = latex_engine._failure('')
  assert isinstance(failure, PdfError)
  assert failure.code == 'E902'
  assert failure.exit_code == 1


def test_the_font_fallback_and_missing_glyphs_are_warnings() -> None:
  log = (
    'Package scireport-default Warning: W901: pdfLaTeX cannot load the OpenType fonts\n'
    'Missing character: There is no ≥ (U+2265) in font [./fonts/Inter-Regular.otf]:\n'
    'Missing character: There is no ∑ (U+2211) in font [./fonts/Inter-Regular.otf]:\n'
  )
  issues = latex_engine._warnings(log)
  assert [i.code for i in issues] == ['W901', 'W902']
  assert 'U+2211' in issues[1].message
  assert latex_engine._warnings('all fine') == []


def test_without_latexmk_the_engine_exits_3(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(shutil, 'which', lambda _name: None)
  assert not latex_engine.latex_available()
  with pytest.raises(MissingDependencyError) as raised:
    latex_engine.compile_project({'report.tex': b''}, engine='lualatex', epoch=0)
  assert raised.value.code == 'E901'
  assert raised.value.exit_code == 3
  assert 'TeX Live' in str(raised.value)
  assert latex_engine.latex_version('lualatex') == ''


def test_an_unknown_tex_engine_is_refused() -> None:
  with pytest.raises(PdfError):
    latex_engine.compile_project({'report.tex': b''}, engine='tex', epoch=0)


def test_without_weasyprint_the_hint_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setitem(sys.modules, 'weasyprint', None)
  monkeypatch.setattr(weasy, 'weasyprint_version', lambda: '')
  with pytest.raises(MissingDependencyError) as raised:
    weasy.html_to_pdf('<p>x</p>')
  assert raised.value.code == 'E901'
  assert raised.value.exit_code == 3
  assert 'scireport[pdf]' in str(raised.value)


@pytest.mark.parametrize(
  ('platform', 'word'), [('linux', 'apt'), ('darwin', 'brew'), ('win32', 'MSYS2')]
)
def test_the_pango_hint_is_for_the_platform(
  monkeypatch: pytest.MonkeyPatch, platform: str, word: str
) -> None:
  monkeypatch.setattr(sys, 'platform', platform)
  error = weasy._missing(OSError('cannot load library libpango-1.0-0'))
  assert word in str(error)
  assert error.exit_code == 3


def test_a_layout_without_the_engine_is_e903() -> None:
  with pytest.raises(TemplateError) as raised:
    render_bundle(kitchen_sink(), layout='minimal@1', formats=['pdf'])
  assert raised.value.code == 'E903'
  assert 'minimal@1' in raised.value.message


def test_an_unknown_pdf_engine_is_e805() -> None:
  with pytest.raises(TemplateError) as raised:
    render_bundle(kitchen_sink(), layout='default@1', formats=['pdf'], pdf_engine='prince')
  assert raised.value.code == 'E805'
  assert 'weasyprint' in str(raised.value)


def test_an_unknown_tex_engine_for_the_project_is_e805() -> None:
  with pytest.raises(TemplateError) as raised:
    render_bundle(kitchen_sink(), layout='default@1', formats=['tex'], latex_engine='tex')
  assert raised.value.code == 'E805'


def test_a_pdf_alone_is_flat_and_needs_only_its_source(monkeypatch: pytest.MonkeyPatch) -> None:
  calls: list[str] = []

  def fake(html: str, *, epoch: int = 0) -> tuple[bytes, list[object]]:
    calls.append(html[:15])
    return b'%PDF-fake', []

  monkeypatch.setattr(weasy, 'html_to_pdf', fake)
  result = render_bundle(kitchen_sink(), layout='default@1', formats=['pdf'], flat=True)
  assert sorted(result.files) == ['render-manifest.json', 'report.pdf']
  assert result.files['report.pdf'] == b'%PDF-fake'
  assert calls == ['<!DOCTYPE html>']
  assert result.formats == ('pdf',)
  assert result.manifest['engines']['pdf'] == 'weasyprint'
  assert result.manifest['formats'] == ['pdf']


def test_a_pdf_next_to_other_formats_goes_in_its_own_folder(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setattr(weasy, 'html_to_pdf', lambda html, *, epoch=0: (b'%PDF-fake', []))
  result = render_bundle(kitchen_sink(), layout='default@1', formats=['html', 'pdf'])
  assert 'pdf/report.pdf' in result.files
  assert 'html/report.html' in result.files
  assert result.formats == ('html', 'pdf')


def test_flat_output_of_two_formats_is_refused() -> None:
  with pytest.raises(TemplateError) as raised:
    render_bundle(kitchen_sink(), layout='default@1', formats=['html', 'pdf'], flat=True)
  assert raised.value.code == 'E801'


def test_a_bundle_can_ask_for_a_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
  monkeypatch.setattr(weasy, 'html_to_pdf', lambda html, *, epoch=0: (b'%PDF-fake', []))
  report = Report('A title').set_render(layout='default@1', formats=['pdf'])
  report.add_text('a.b', 'Some text.')
  result = render_bundle(report.build(), flat=True)
  assert result.files['report.pdf'] == b'%PDF-fake'


def test_the_cli_exits_3_when_the_engine_is_missing(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  def missing(html: str, *, epoch: int = 0) -> tuple[bytes, list[object]]:
    raise MissingDependencyError('no pango', code='E901', hint='Install pango.')

  monkeypatch.setattr(weasy, 'html_to_pdf', missing)
  source = write_bundle(kitchen_sink(), tmp_path / 'sink.scireport.zip')
  result = runner.invoke(
    app, ['render', str(source), '-o', str(tmp_path / 'out'), '-l', 'default', '-f', 'pdf']
  )
  assert result.exit_code == 3, result.output
  assert not (tmp_path / 'out').exists()


def test_the_cli_writes_the_pdf_flat_and_json(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  monkeypatch.setattr(weasy, 'html_to_pdf', lambda html, *, epoch=0: (b'%PDF-fake', []))
  source = write_bundle(kitchen_sink(), tmp_path / 'sink.scireport.zip')
  result = runner.invoke(
    app,
    ['render', str(source), '-o', str(tmp_path / 'out'), '-l', 'default', '-f', 'pdf', '--flat'],
  )
  assert result.exit_code == 0, result.output
  assert (tmp_path / 'out' / 'report.pdf').read_bytes() == b'%PDF-fake'


def test_a_missing_dependency_is_not_swallowed_into_a_render_error(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setattr(shutil, 'which', lambda _name: None)
  with pytest.raises(MissingDependencyError):
    render_bundle(
      kitchen_sink(), layout='default@1', formats=['pdf'], pdf_engine='latex', flat=True
    )
  assert not issubclass(MissingDependencyError, RenderError)
