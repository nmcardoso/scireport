"""A manuscript that inputs every exported fragment compiles (ADR-0010)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from render_fixtures import kitchen_sink

from scireport import export_tex, write_export

pytestmark = [pytest.mark.integration, pytest.mark.pdf_latex]
REQUIRED = os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1'

STUB = r"""\documentclass{article}
\usepackage{booktabs,longtable,graphicx}
\input{generated/numbers}
\begin{document}
We find \FactsNPairs{} pairs at \FactsSep{} with flux \FactsFlux{} (\FactsComplete).
%INPUTS%
See Table~\ref{tab:tables.cut} and Figure~\ref{fig:figures.curve}.
\end{document}
"""


@pytest.mark.parametrize('bare', [False, True])
def test_the_stub_manuscript_compiles(bare: bool, tmp_path: Path) -> None:
  if shutil.which('latexmk') is None or shutil.which('lualatex') is None:
    message = 'latexmk or lualatex is not on PATH'
    if REQUIRED:
      pytest.fail(message)
    pytest.skip(message)
  result = export_tex(kitchen_sink(real=True), bare=bare, graphics_prefix='generated/')
  write_export(result, tmp_path / 'generated')
  inputs = '\n'.join(
    f'\\input{{generated/{name.removesuffix(".tex")}}}'
    for name in result.files
    if name.endswith('.tex') and name != 'numbers.tex'
  )
  (tmp_path / 'main.tex').write_text(STUB.replace('%INPUTS%', inputs), encoding='utf-8')
  run = subprocess.run(
    ['latexmk', '-lualatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
    cwd=tmp_path,
    capture_output=True,
    text=True,
    timeout=600,
    check=False,
  )
  assert run.returncode == 0, run.stdout[-3000:]
  assert (tmp_path / 'main.pdf').read_bytes().startswith(b'%PDF')
