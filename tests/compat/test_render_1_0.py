"""Rendering a spec-1.0 bundle with the frozen built-ins gives the frozen bytes (ADR-0008)."""

from __future__ import annotations

from pathlib import Path

import pytest
from render_helpers import normalised

from scireport import open_bundle
from scireport.render import render_bundle
from scireport.render.definition import FORMATS, Format

CORPUS = Path(__file__).resolve().parent / 'spec-1.0'
FOLDER = 'render-generic-1-minimal-1'
SOURCES = {
  'minimal': ['bundle.scireport', 'bundle.scireport.zip'],
  'text-only': ['source', 'single.json', 'bundle.scireport.zip'],
  'full-kinds': ['bundle.scireport', 'bundle.scireport.zip'],
}


def expected_files(case: str, fmt: Format) -> dict[str, bytes]:
  root = CORPUS / case / 'expected' / FOLDER / fmt
  return {
    path.relative_to(root).as_posix(): path.read_bytes()
    for path in sorted(root.rglob('*'))
    if path.is_file()
  }


@pytest.mark.parametrize('fmt', FORMATS)
@pytest.mark.parametrize(('case', 'form'), [(c, f) for c, forms in SOURCES.items() for f in forms])
def test_every_form_renders_to_the_frozen_bytes(case: str, form: str, fmt: Format) -> None:
  with open_bundle(CORPUS / case / form) as bundle:
    result = render_bundle(
      bundle, template='generic@1', layout='minimal@1', formats=[fmt], flat=True
    )
  assert normalised(result.files) == expected_files(case, fmt)
