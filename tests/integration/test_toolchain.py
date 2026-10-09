"""Toolchain smoke tests: prove each CI job has the system dependency it is named after.

Locally a missing toolchain skips the test. With ``SCIREPORT_REQUIRE_TOOLCHAIN=1`` (set by
the dedicated CI jobs) a missing toolchain fails it, so a job can never go green by skipping.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REQUIRED = os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1'

pytestmark = pytest.mark.integration


def _missing(reason: str) -> None:
  if REQUIRED:
    pytest.fail(reason)
  pytest.skip(reason)


@pytest.mark.pdf_weasyprint
# WeasyPrint 70 warns when libharfbuzz-subset is absent; CI installs it, a laptop may not.
@pytest.mark.filterwarnings('ignore:HarfBuzz-Subset:DeprecationWarning')
def test_weasyprint_renders_pdf(tmp_path: Path) -> None:
  try:
    from weasyprint import HTML
  except (ImportError, OSError) as exc:  # OSError: pango shared libraries not found
    _missing(f'weasyprint is unavailable: {exc}')
    return
  out = tmp_path / 'smoke.pdf'
  HTML(string='<h1>scireport</h1><p>smoke</p>').write_pdf(str(out))
  assert out.read_bytes().startswith(b'%PDF')


@pytest.mark.pdf_latex
def test_latexmk_compiles_document(tmp_path: Path) -> None:
  if shutil.which('latexmk') is None or shutil.which('lualatex') is None:
    _missing('latexmk or lualatex is not on PATH')
    return
  (tmp_path / 'smoke.tex').write_text(
    '\\documentclass{article}\n'
    '\\usepackage{fontspec,booktabs,siunitx,tcolorbox,fancyhdr,longtable}\n'
    '\\begin{document}scireport smoke $x^2$\\end{document}\n',
    encoding='utf-8',
    newline='\n',
  )
  subprocess.run(
    ['latexmk', '-lualatex', '-interaction=nonstopmode', '-halt-on-error', 'smoke.tex'],
    cwd=tmp_path,
    check=True,
    capture_output=True,
    timeout=600,
  )
  assert (tmp_path / 'smoke.pdf').read_bytes().startswith(b'%PDF')


@pytest.mark.pandoc
def test_pypandoc_converts_markdown() -> None:
  try:
    import pypandoc
  except ImportError as exc:
    _missing(f'pypandoc is unavailable: {exc}')
    return
  html = pypandoc.convert_text('# Title\n\nSome *text*.', 'html', format='md')
  assert '<em>text</em>' in html
