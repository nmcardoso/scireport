"""A LaTeX project with citations compiles with biblatex and biber (ADR-0011)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from render_fixtures import citation_bundle

from scireport.render import render_bundle

pytestmark = [pytest.mark.integration, pytest.mark.pdf_latex]
REQUIRED = os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1'


@pytest.mark.parametrize('style', [None, 'authoryear'])
def test_the_citations_resolve_through_biber(style: str | None, tmp_path: Path) -> None:
  if any(shutil.which(tool) is None for tool in ('latexmk', 'lualatex', 'biber')):
    message = 'latexmk, lualatex or biber is not on PATH'
    if REQUIRED:
      pytest.fail(message)
    pytest.skip(message)
  render_bundle(
    citation_bundle(style=style),
    template='generic@1',
    layout='minimal@1',
    formats=['tex'],
    flat=True,
  ).write(tmp_path)
  run = subprocess.run(
    ['latexmk', '-lualatex', '-interaction=nonstopmode', '-halt-on-error', 'report.tex'],
    cwd=tmp_path,
    capture_output=True,
    text=True,
    timeout=600,
    check=False,
  )
  assert run.returncode == 0, run.stdout[-3000:]
  bbl = (tmp_path / 'report.bbl').read_text(encoding='utf-8')
  assert 'doe2020' in bbl and 'smith2018' in bbl and 'unused2001' not in bbl
