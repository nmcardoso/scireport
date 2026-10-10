"""The LaTeX project of the golden bundle compiles with every engine the layout supports."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from render_fixtures import kitchen_sink

from scireport import Bundle, Report
from scireport.render import render_bundle

REQUIRED = os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1'
ENGINES = {'pdflatex': '-pdf', 'xelatex': '-xelatex', 'lualatex': '-lualatex'}

# Every character with a meaning in LaTeX or Markdown, accents, symbols and a stray \end{document}.
HOSTILE = (
  r'50% of $x_1$ & #tags ~tilde ^caret \backslash {braces} [bracket] *star* _under_ < > | '
  r'« » ’ “q” α ≤ ± ° é ñ \textbf{x} \end{document}'
)

pytestmark = [pytest.mark.integration, pytest.mark.pdf_latex]


def compile_project(bundle: Bundle, engine: str, tmp_path: Path) -> Path:
  """Render the LaTeX project of ``bundle``, compile it with ``latexmk`` and return the PDF."""
  if shutil.which('latexmk') is None or shutil.which(engine) is None:
    message = f'latexmk or {engine} is not on PATH'
    if REQUIRED:
      pytest.fail(message)
    pytest.skip(message)
  result = render_bundle(
    bundle,
    template='generic@1',
    layout='minimal@1',
    formats=['tex'],
    flat=True,
    latex_engine=engine,
  )
  result.write(tmp_path)
  run = subprocess.run(
    ['latexmk', ENGINES[engine], '-interaction=nonstopmode', '-halt-on-error', 'report.tex'],
    cwd=tmp_path,
    capture_output=True,
    text=True,
    timeout=600,
    check=False,
  )
  assert run.returncode == 0, run.stdout[-3000:] + run.stderr[-1000:]
  pdf = tmp_path / 'report.pdf'
  assert pdf.read_bytes().startswith(b'%PDF')
  return pdf


@pytest.mark.parametrize('engine', sorted(ENGINES))
def test_the_tex_project_compiles(engine: str, tmp_path: Path) -> None:
  # Real matplotlib figures, so that the PDF figure is a valid file for \includegraphics.
  compile_project(kitchen_sink(real=True), engine, tmp_path)


@pytest.mark.parametrize('engine', sorted(ENGINES))
def test_hostile_text_compiles(engine: str, tmp_path: Path) -> None:
  report = Report(f'T {HOSTILE}', subtitle=HOSTILE, authors=[HOSTILE])
  report.add_text('a.intro', f'Prose with {HOSTILE}', format='markdown')
  report.add_text('a.plain', HOSTILE)
  report.add_table(
    'a.t',
    {'name': [HOSTILE, 'b_c'], 'v': [1.5, None]},
    caption=HOSTILE,
    inline=True,
    columns=[{'name': 'name', 'label': HOSTILE}, {'name': 'v', 'label': 'v', 'unit': 'deg'}],
  )
  # Code is typeset literally, so pdfLaTeX could not draw non-ASCII characters in it.
  report.add_code('a.code', 'x = "50% & #1"\n\\end{verbatim}', language='text')
  report.add_number('a.n', 3, unit=HOSTILE)
  report.set_outline(
    [{'title': HOSTILE, 'children': ['a.intro', 'a.plain', 'a.t', 'a.code', 'a.n']}]
  )
  compile_project(report.build(), engine, tmp_path)
