"""Rendering a spec-1.0 bundle with pandoc as the markup engine gives the frozen bytes (ADR-0008).

What pandoc writes depends on its version, so ``spec-1.0/pandoc-version.txt`` records the version
that made the files. With another pandoc these tests skip, and fail instead when
``SCIREPORT_REQUIRE_TOOLCHAIN=1`` (the ``pandoc`` CI job, which installs the version in
``uv.lock``): a pandoc upgrade is a decision, and the frozen files are never edited to follow it
(add a folder for the new version instead). The text hashes of the PDFs are checked by
``tests/integration/test_pdf.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import need_the_frozen_pandoc
from html_canonical import canonicalise, diff
from render_helpers import normalised

from scireport import open_bundle
from scireport.render import render_bundle
from scireport.render.definition import FORMATS, Format

CORPUS = Path(__file__).resolve().parent / 'spec-1.0'
SOURCES = {
  'minimal': ['bundle.scireport', 'bundle.scireport.zip'],
  'text-only': ['source', 'single.json', 'bundle.scireport.zip'],
  'full-kinds': ['bundle.scireport', 'bundle.scireport.zip'],
  'bibliography': ['bundle.scireport', 'bundle.scireport.zip'],
  'every-kind': ['bundle.scireport', 'bundle.scireport.zip'],
}
pytestmark = [pytest.mark.integration, pytest.mark.pandoc]


def expected_files(case: str, layout: str, fmt: Format) -> dict[str, bytes]:
  root = CORPUS / case / 'expected' / f'render-generic-1-{layout}-1-pandoc' / fmt
  return {
    path.relative_to(root).as_posix(): path.read_bytes()
    for path in sorted(root.rglob('*'))
    if path.is_file()
  }


@pytest.mark.parametrize('fmt', FORMATS)
@pytest.mark.parametrize('layout', ['minimal', 'default', 'modern'])
@pytest.mark.parametrize(('case', 'form'), [(c, f) for c, forms in SOURCES.items() for f in forms])
def test_every_form_renders_to_the_frozen_bytes(
  case: str, form: str, layout: str, fmt: Format
) -> None:
  need_the_frozen_pandoc()
  with open_bundle(CORPUS / case / form) as bundle:
    result = render_bundle(
      bundle,
      template='generic@1',
      layout=f'{layout}@1',
      formats=[fmt],
      flat=True,
      markup_engine='pandoc',
    )
  actual = normalised(result.files)
  expected = expected_files(case, layout, fmt)
  assert actual.keys() == expected.keys()
  if fmt == 'html':
    # DOM-equivalent: spelling (attribute order, whitespace, entities) is not frozen, content is.
    report = canonicalise(actual['report.html'].decode('utf-8'))
    frozen = canonicalise(expected['report.html'].decode('utf-8'))
    assert report == frozen, diff(frozen, report)[:3000]
    return
  assert actual == expected
