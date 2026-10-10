"""The PDF engines end to end: examples x layouts x engines (needs pango and/or TeX Live).

Locally a missing toolchain skips a test; with ``SCIREPORT_REQUIRE_TOOLCHAIN=1`` (set by the
dedicated CI jobs) it fails, so a job cannot go green by skipping. Every PDF is checked for four
things: it has pages, its text contains the words of the Markdown output, two builds give the same
bytes, and (for the frozen compat cases) its text hashes to the recorded value.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from pdf_text import letters, missing_words, pages, pdf_text

from scireport import Bundle, open_bundle
from scireport.render import render_bundle
from scireport.render.pdf import LATEX_ENGINES

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'examples'))
import dataset_report
import metrics_dashboard
import text_report

REQUIRED = os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1'
LAYOUTS = ['default', 'modern']
EXAMPLES = {
  'dataset-report': (dataset_report.build, None),
  'metrics-dashboard': (metrics_dashboard.build, metrics_dashboard.TEMPLATE),
  'text-report': (text_report.build, None),
}
CORPUS = Path(__file__).resolve().parents[1] / 'compat' / 'spec-1.0'
NO_PAGE_NUMBERS = {'toc': 'false', 'header': 'false'}
"""Options that remove the text which depends on pagination (contents rows, page counters)."""

pytestmark = pytest.mark.integration


def _need(*programs: str) -> None:
  missing = [name for name in programs if shutil.which(name) is None]
  if missing:
    message = f'{", ".join(missing)} not on PATH'
    if REQUIRED:
      pytest.fail(message)
    pytest.skip(message)


def _need_weasyprint() -> None:
  try:
    import weasyprint  # noqa: F401
  except (ImportError, OSError) as exc:
    if REQUIRED:
      pytest.fail(f'weasyprint is unavailable: {exc}')
    pytest.skip(f'weasyprint is unavailable: {exc}')


def _bundle(name: str, layout: str, tmp_path: Path) -> tuple[Bundle, Path | None]:
  build, template = EXAMPLES[name]
  path = build(layout).write(tmp_path / f'{name}.scireport.zip', overwrite=True)
  return open_bundle(path), template


def _markdown(bundle: Bundle, layout: str, template: Path | None) -> str:
  result = render_bundle(bundle, template=template, layout=f'{layout}@1', formats=['md'], flat=True)
  return '\n'.join(
    data.decode('utf-8') for name, data in sorted(result.files.items()) if name.endswith('.md')
  )


def _check_text(pdf: bytes, md: str) -> None:
  assert pages(pdf) >= 2
  missing = missing_words(md, pdf)
  # The Markdown names a status level, a flow state or a verdict in words; the designed layouts
  # show them as a shape and a colour, so a few words are expected to be missing.
  assert len(missing) <= 6, f'words of the Markdown output missing from the PDF: {missing}'


@pytest.mark.pdf_weasyprint
@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('name', sorted(EXAMPLES))
def test_weasyprint_pdf_has_the_text_of_the_markdown(
  name: str, layout: str, tmp_path: Path
) -> None:
  _need_weasyprint()
  with _opened(name, layout, tmp_path) as (bundle, template):
    pdf = render_bundle(
      bundle, template=template, layout=f'{layout}@1', formats=['pdf'], flat=True
    ).files['report.pdf']
    _check_text(pdf, _markdown(bundle, layout, template))


@pytest.mark.pdf_weasyprint
@pytest.mark.parametrize('layout', LAYOUTS)
def test_weasyprint_pdf_is_reproducible(layout: str, tmp_path: Path) -> None:
  _need_weasyprint()
  with _opened('dataset-report', layout, tmp_path) as (bundle, template):
    first, second = (
      render_bundle(
        bundle, template=template, layout=f'{layout}@1', formats=['pdf'], flat=True
      ).files['report.pdf']
      for _ in range(2)
    )
  assert first == second


@pytest.mark.pdf_weasyprint
@pytest.mark.parametrize('layout', LAYOUTS)
def test_weasyprint_pdf_is_tagged_and_titled(layout: str, tmp_path: Path) -> None:
  _need_weasyprint()
  from pypdf import PdfReader

  with _opened('text-report', layout, tmp_path) as (bundle, template):
    data = render_bundle(
      bundle, template=template, layout=f'{layout}@1', formats=['pdf'], flat=True
    ).files['report.pdf']
  import io

  reader = PdfReader(io.BytesIO(data))
  assert reader.metadata is not None
  assert reader.metadata.title == 'Design notes: a reproducible pipeline'
  assert reader.trailer['/Root'].get('/StructTreeRoot') is not None


@pytest.mark.pdf_weasyprint
@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('case', ['minimal', 'text-only', 'full-kinds'])
def test_weasyprint_text_hash_of_the_compat_cases(case: str, layout: str) -> None:
  _need_weasyprint()
  expected = _recorded(case, layout, 'weasyprint')
  with open_bundle(_source(case)) as bundle:
    pdf = render_bundle(
      bundle,
      template='generic@1',
      layout=f'{layout}@1',
      formats=['pdf'],
      options=NO_PAGE_NUMBERS,
      flat=True,
    ).files['report.pdf']
  assert _digest(pdf) == expected


@pytest.mark.pdf_latex
@pytest.mark.parametrize('engine', LATEX_ENGINES)
@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('name', sorted(EXAMPLES))
def test_latex_pdf_has_the_text_of_the_markdown(
  name: str, layout: str, engine: str, tmp_path: Path
) -> None:
  _need('latexmk', engine)
  with _opened(name, layout, tmp_path) as (bundle, template):
    result = render_bundle(
      bundle,
      template=template,
      layout=f'{layout}@1',
      formats=['pdf'],
      pdf_engine='latex',
      latex_engine=engine,
      flat=True,
    )
    _check_text(result.files['report.pdf'], _markdown(bundle, layout, template))
  codes = [issue.code for issue in result.issues]
  assert codes == (['W901'] if engine == 'pdflatex' else [])


@pytest.mark.pdf_latex
@pytest.mark.parametrize('engine', LATEX_ENGINES)
def test_latex_pdf_is_reproducible(engine: str, tmp_path: Path) -> None:
  _need('latexmk', engine)
  with _opened('text-report', 'default', tmp_path) as (bundle, template):
    first, second = (
      render_bundle(
        bundle,
        template=template,
        layout='default@1',
        formats=['pdf'],
        pdf_engine='latex',
        latex_engine=engine,
        flat=True,
      ).files['report.pdf']
      for _ in range(2)
    )
  assert first == second


@pytest.mark.pdf_latex
@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize('case', ['minimal', 'text-only', 'full-kinds'])
def test_lualatex_text_hash_of_the_compat_cases(case: str, layout: str) -> None:
  _need('latexmk', 'lualatex')
  expected = _recorded(case, layout, 'lualatex')
  with open_bundle(_source(case)) as bundle:
    pdf = render_bundle(
      bundle,
      template='generic@1',
      layout=f'{layout}@1',
      formats=['pdf'],
      pdf_engine='latex',
      latex_engine='lualatex',
      options=NO_PAGE_NUMBERS,
      flat=True,
    ).files['report.pdf']
  assert _digest(pdf) == expected


@pytest.mark.pdf_latex
def test_a_latex_error_is_reported_with_file_and_line(tmp_path: Path) -> None:
  _need('latexmk', 'lualatex')
  from scireport.errors import PdfError
  from scireport.render.pdf.latex import compile_project

  source = b'\\documentclass{article}\n\\begin{document}\n\\undefinedmacro\n\\end{document}\n'
  with pytest.raises(PdfError) as raised:
    compile_project({'report.tex': source}, engine='lualatex', epoch=0)
  assert raised.value.code == 'E902'
  assert raised.value.issues[0].location == './report.tex:3'
  assert 'Undefined control sequence' in raised.value.issues[0].message


@pytest.mark.pdf_latex
def test_a_missing_tex_package_is_exit_3(tmp_path: Path) -> None:
  _need('latexmk', 'lualatex')
  from scireport.errors import MissingDependencyError
  from scireport.render.pdf.latex import compile_project

  source = (
    b'\\documentclass{article}\n\\usepackage{nopackagewiththisname}\n'
    b'\\begin{document}x\\end{document}\n'
  )
  with pytest.raises(MissingDependencyError) as raised:
    compile_project({'report.tex': source}, engine='lualatex', epoch=0)
  assert raised.value.exit_code == 3
  assert 'nopackagewiththisname.sty' in raised.value.message


def _source(case: str) -> Path:
  names = {'minimal': 'bundle.scireport', 'text-only': 'source', 'full-kinds': 'bundle.scireport'}
  return CORPUS / case / names[case]


def _digest(pdf: bytes) -> str:
  return hashlib.sha256(letters(pdf_text(pdf)).encode('utf-8')).hexdigest()


def _recorded(case: str, layout: str, engine: str) -> str:
  path = CORPUS / case / 'expected' / f'render-generic-1-{layout}-1' / f'pdf-text-{engine}.sha256'
  return path.read_text(encoding='utf-8').strip()


@contextmanager
def _opened(name: str, layout: str, tmp_path: Path) -> Iterator[tuple[Bundle, Path | None]]:
  """Build an example bundle and keep it open for the length of a ``with`` block."""
  bundle, template = _bundle(name, layout, tmp_path)
  try:
    yield bundle, template
  finally:
    bundle.close()
