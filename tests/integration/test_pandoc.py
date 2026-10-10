"""pandoc as the markup engine, the citation processor and the office writer (ADR-0011).

These tests run the real pandoc that ``scireport[pandoc]`` installs (``pypandoc-binary``), so
they are marked ``integration`` and ``pandoc``; the dedicated CI job sets
``SCIREPORT_REQUIRE_TOOLCHAIN=1``.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import pytest
from helpers import require_extra
from render_fixtures import PROSE_SAMPLES, citation_bundle, kitchen_sink, prose_sampler
from typer.testing import CliRunner

from scireport import PandocError, RenderError, Report, open_bundle
from scireport.cli import app
from scireport.render import render_bundle
from scireport.render.markup import make_converter
from scireport.render.pandoc import pandoc_version, run_pandoc

pytestmark = [pytest.mark.integration, pytest.mark.pandoc]

runner = CliRunner()
CSL = Path(__file__).resolve().parents[1] / 'fixtures' / 'numeric-test.csl'
GENERIC: dict[str, Any] = {'template': 'generic@1', 'layout': 'minimal@1'}


@pytest.fixture(autouse=True)
def _need_pandoc() -> None:
  require_extra('pypandoc')


def convert(source: str, target: str = 'html', **kwargs: Any) -> tuple[str, list[str]]:
  result = make_converter('pandoc').convert(source, target, **kwargs)  # type: ignore[arg-type]
  return str(result.text), [i.code for i in result.issues]


# ---- the converter ----------------------------------------------------------------------------


def test_the_version_is_the_one_of_the_bundled_binary() -> None:
  assert re.fullmatch(r'\d+(\.\d+)+', pandoc_version())


def test_it_reads_what_mistletoe_cannot() -> None:
  html, issues = convert(PROSE_SAMPLES['extras'])
  assert issues == []
  assert 'role="doc-endnotes"' in html and '<dl>' in html and 'type="checkbox"' in html


def test_footnote_ids_are_unique_per_fragment() -> None:
  converter = make_converter('pandoc')
  first = str(converter.convert('a[^1]\n\n[^1]: n', 'html').text)
  second = str(converter.convert('b[^1]\n\n[^1]: m', 'html').text)
  assert 'id="s1-fn1"' in first and 'id="s2-fn1"' in second


def test_what_is_outside_the_subset_is_reported_and_shown_as_text() -> None:
  html, issues = convert(PROSE_SAMPLES['outside'])
  assert issues == ['W701'] * 4
  assert '<h1' not in html and '<img' not in html and 'javascript' not in html
  assert '<strong>A heading</strong>' in html and 'alt text' in html
  assert '&lt;b&gt;' in html and '<b>' not in html


def test_raw_html_cannot_get_through() -> None:
  html, issues = convert('<script>alert(1)</script>\n\nok <img src=x onerror=y>')
  assert 'W701' in issues and '<script' not in html and '<img' not in html


def test_markdown_is_kept_as_written_and_only_checked() -> None:
  text, issues = convert('# H\n\nA *b* [^n]\n\n[^n]: x', 'md')
  assert text == '# H\n\nA *b* [^n]\n\n[^n]: x' and issues == ['W701']


def test_math_is_drawn_by_the_hook_for_html_and_native_for_tex() -> None:
  html, _ = convert(
    'Inline $x^2$ and\n\n$$y$$', math=lambda latex, display: f'<M {latex} {display}>'
  )
  assert '<M x^2 False>' in html and '<M y True>' in html
  tex, _ = convert('Inline $x^2$ and\n\n$$y$$', 'tex')
  assert r'\(x^2\)' in tex and r'\[' in tex


def test_math_that_cannot_be_drawn_falls_back_to_code_with_w601() -> None:
  from scireport.render.math import MathError

  def fail(latex: str, display: bool) -> str:
    raise MathError(latex, 'cannot draw')

  html, issues = convert('$\\bad$', math=fail)
  assert issues == ['W601'] and '<code>' in html


def test_an_inline_phrase_has_no_paragraph() -> None:
  html, issues = convert('a *b*', inline=True)
  assert html == 'a <em>b</em>' and issues == []
  _, issues = convert('a\n\nb', inline=True)
  assert issues == ['W701']


def test_tex_output_declares_what_pandoc_needs() -> None:
  converter = make_converter('pandoc')
  assert converter.tex_preamble() == ''
  converter.convert('- a\n- b', 'tex')
  assert r'\providecommand{\tightlist}' in converter.tex_preamble()


@pytest.mark.pdf_latex
def test_the_tex_project_of_the_sampler_compiles(tmp_path: Path) -> None:
  if shutil.which('latexmk') is None or shutil.which('lualatex') is None:
    pytest.skip('latexmk or lualatex is not on PATH')
  result = render_bundle(
    prose_sampler(), formats=['tex'], flat=True, markup_engine='pandoc', **GENERIC
  )
  result.write(tmp_path)
  run = subprocess.run(
    ['latexmk', '-lualatex', '-interaction=nonstopmode', '-halt-on-error', 'report.tex'],
    cwd=tmp_path,
    capture_output=True,
    text=True,
    timeout=600,
    check=False,
  )
  assert run.returncode == 0, run.stdout[-3000:]


# ---- the render manifest and the version warning ---------------------------------------------


def test_the_manifest_records_the_pandoc_version_only_when_pandoc_took_part() -> None:
  plain = render_bundle(prose_sampler(), formats=['html'], **GENERIC)
  with_pandoc = render_bundle(prose_sampler(), formats=['html'], markup_engine='pandoc', **GENERIC)
  assert plain.manifest['engines']['pandoc'] is None
  assert with_pandoc.manifest['engines']['pandoc'] == pandoc_version()
  assert with_pandoc.manifest['engines']['markup'] == 'pandoc'


def test_a_bundle_with_citations_records_pandoc_for_html_but_not_for_tex() -> None:
  html = render_bundle(citation_bundle(), formats=['html'], **GENERIC)
  tex = render_bundle(citation_bundle(), formats=['tex'], **GENERIC)
  assert html.manifest['engines']['pandoc'] == pandoc_version()
  assert tex.manifest['engines']['pandoc'] is None


def test_another_pandoc_version_than_the_recorded_one_warns_w501() -> None:
  report = Report('T').add_text('t', 'x *y*', format='markdown')
  report.set_render(markup_engine='pandoc', pandoc_version='1.0')
  result = render_bundle(report.build(), formats=['html'], **GENERIC)
  warning = next(i for i in result.issues if i.code == 'W501')
  assert warning.expected == '1.0' and warning.found == pandoc_version()
  with pytest.raises(RenderError):
    render_bundle(report.build(), formats=['html'], strict=True, **GENERIC)


def test_the_recorded_version_is_silent() -> None:
  report = Report('T').add_text('t', 'x', format='markdown')
  report.set_render(markup_engine='pandoc', pandoc_version=pandoc_version())
  assert render_bundle(report.build(), formats=['html'], **GENERIC).issues == ()


def test_pack_records_the_pandoc_version(tmp_path: Path) -> None:
  report = Report('T').add_text('t', 'x').set_render(markup_engine='pandoc')
  source = report.write(tmp_path / 'a.scireport.zip')
  packed = tmp_path / 'b.scireport.zip'
  assert runner.invoke(app, ['pack', str(source), '-o', str(packed)]).exit_code == 0
  with open_bundle(packed) as bundle:
    assert bundle.manifest.render.pandoc_version == pandoc_version()


def test_pack_leaves_a_bundle_that_does_not_use_pandoc_alone(tmp_path: Path) -> None:
  source = Report('T').add_text('t', 'x').write(tmp_path / 'a.scireport.zip')
  packed = tmp_path / 'b.scireport.zip'
  assert runner.invoke(app, ['pack', str(source), '-o', str(packed)]).exit_code == 0
  with open_bundle(packed) as bundle:
    assert bundle.manifest.render.pandoc_version is None


# ---- citations --------------------------------------------------------------------------------


def test_citations_are_formatted_once_for_the_whole_document() -> None:
  result = render_bundle(
    citation_bundle(csl=CSL.read_bytes()), formats=['md'], flat=True, **GENERIC
  )
  md = result.files['report.md'].decode()
  assert 'Agreement with \\[1, 2\\] is shown.' in md
  assert 'The result of \\[2\\] holds; see also \\[see 1\\].' in md
  # The list holds the cited works in citation order, and not the one nobody cites.
  assert md.index('\\[1\\] Smith') < md.index('\\[2\\] Doe') and 'Nobody' not in md


def test_the_html_list_keeps_pandocs_structure() -> None:
  html = (
    render_bundle(citation_bundle(), formats=['html'], flat=True, **GENERIC)
    .files['report.html']
    .decode()
  )
  assert 'class="citation" data-cites="smith2018 doe2020"' in html
  assert html.count('class="csl-entry"') == 2 and '.references .csl-entry' in html


def test_both_engines_format_citations_alike() -> None:
  one = render_bundle(citation_bundle(), formats=['html'], flat=True, **GENERIC)
  two = render_bundle(
    citation_bundle(), formats=['html'], flat=True, markup_engine='pandoc', **GENERIC
  )
  assert re.findall(r'<span class="citation".*?</span>', one.files['report.html'].decode()) == (
    re.findall(r'<span class="citation".*?</span>', two.files['report.html'].decode())
  )


def test_the_whole_bibliography_can_be_listed() -> None:
  report = Report('T').add_text('t', 'See [@doe2020].', format='markdown')
  report.add_bibliography('refs', citation_bundle().read_asset('assets/text/refs.bib'))
  report.set_outline(['t'])
  template = Path(__file__).parent / 'everything_template'
  template.mkdir(exist_ok=True)
  (template / 'template.yaml').write_text(
    'spec: ">=1.0,<2.0"\nname: everything\nversion: 1\nformats: [md]\nfields: []\n'
    'dynamic_keys: true\n',
    encoding='utf-8',
  )
  (template / 'report.j2').write_text(
    "{{ c.chapter('Refs') }}{{ c.value('t') }}{{ c.references('refs', everything=True) }}",
    encoding='utf-8',
  )
  try:
    result = render_bundle(
      report.build(), template=template, layout='minimal@1', formats=['md'], flat=True
    )
  finally:
    shutil.rmtree(template)
  assert 'Nobody' in result.files['report.md'].decode()


# ---- office formats ---------------------------------------------------------------------------


def office(fmt: str, **kwargs: Any) -> bytes:
  result = render_bundle(
    kitchen_sink(real=True, split=False), formats=[fmt], flat=True, **GENERIC, **kwargs
  )
  return result.files[f'report.{fmt}']


def test_docx_holds_the_text_the_table_and_the_figure() -> None:
  with zipfile.ZipFile(io.BytesIO(office('docx'))) as archive:
    names = archive.namelist()
    document = archive.read('word/document.xml').decode()
  assert 'Cross-match' in document and 'COMPLETED SUCCESSFULLY' in document
  assert '<w:tbl>' in document and '<m:oMath' in document
  assert any(name.startswith('word/media/') for name in names)


def test_odt_and_epub_are_made_from_the_same_markdown() -> None:
  with zipfile.ZipFile(io.BytesIO(office('odt'))) as archive:
    assert 'Cross-match' in archive.read('content.xml').decode()
  with zipfile.ZipFile(io.BytesIO(office('epub'))) as archive:
    names = archive.namelist()
    assert 'mimetype' in names and 'EPUB/content.opf' in names
    assert 'Cross-match' in archive.read('EPUB/content.opf').decode()


def test_office_files_are_reproducible() -> None:
  for fmt in ('docx', 'odt', 'epub'):
    assert office(fmt) == office(fmt)


def test_the_archive_timestamps_come_from_the_report_date() -> None:
  with zipfile.ZipFile(io.BytesIO(office('docx'))) as archive:
    assert {info.date_time[:3] for info in archive.infolist()} == {(2026, 10, 9)}


def test_the_html_source_works_too() -> None:
  data = office('docx', office_source='html')
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
    assert 'Cross-match' in archive.read('word/document.xml').decode()


def test_office_formats_land_in_their_own_folders() -> None:
  result = render_bundle(kitchen_sink(real=True), formats=['md', 'docx', 'epub'], **GENERIC)
  assert 'docx/report.docx' in result.files and 'epub/report.epub' in result.files
  assert 'md/index.md' in result.files  # the split Markdown is not what the office file used
  assert result.formats == ('md', 'docx', 'epub')
  assert result.manifest['formats'] == ['md', 'docx', 'epub']


def test_a_reference_document_is_used(tmp_path: Path) -> None:
  reference = tmp_path / 'reference.docx'
  reference.write_bytes(run_pandoc(['--print-default-data-file', 'reference.docx'], sandbox=False))
  with zipfile.ZipFile(reference) as source:
    parts = {name: source.read(name) for name in source.namelist()}
  marker = (
    b'<w:style w:type="paragraph" w:customStyle="1" w:styleId="ScireportMarker">'
    b'<w:name w:val="ScireportMarker"/></w:style></w:styles>'
  )
  parts['word/styles.xml'] = parts['word/styles.xml'].replace(b'</w:styles>', marker)
  buffer = io.BytesIO()
  with zipfile.ZipFile(buffer, 'w') as target:
    for name, data in parts.items():
      target.writestr(name, data)
  reference.write_bytes(buffer.getvalue())
  data = office('docx', reference_doc=reference)
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
    assert b'ScireportMarker' in archive.read('word/styles.xml')


def test_a_broken_reference_document_is_e507(tmp_path: Path) -> None:
  reference = tmp_path / 'reference.docx'
  reference.write_bytes(b'not a zip')
  with pytest.raises(PandocError) as caught:
    office('docx', reference_doc=reference)
  assert caught.value.code == 'E507'


def test_the_command_line_writes_every_office_format(tmp_path: Path) -> None:
  source = (
    Report('T', date='2026-10-09')
    .add_text('t', 'Hello *you*.', format='markdown')
    .write(tmp_path / 'b.scireport.zip')
  )
  result = runner.invoke(
    app,
    [
      'render',
      str(source),
      '-o',
      str(tmp_path / 'o'),
      '-f',
      'docx',
      '-f',
      'odt',
      '-f',
      'epub',
      '--json',
    ],
  )
  assert result.exit_code == 0, result.output
  assert {'docx/report.docx', 'odt/report.odt', 'epub/report.epub'} <= set(
    json.loads(result.stdout)['files']
  )
