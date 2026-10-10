"""Golden outputs of the two markup engines on the same prose, and of citations (ADR-0011).

``prose_sampler`` holds one Markdown sample per topic. It is rendered with ``mistletoe`` and with
``pandoc`` to Markdown, HTML and LaTeX; the two sets of files are committed side by side
(``markup/mistletoe/`` and ``markup/pandoc/``) so that a diff between the folders is the list of
differences that ``docs/markup.md`` documents. The pandoc files depend on the pandoc version
(``uv.lock`` pins ``pypandoc-binary``), so a pandoc upgrade may need
``SCIREPORT_UPDATE_GOLDEN=1 uv run pytest tests/golden -m pandoc``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from helpers import require_extra
from render_fixtures import citation_bundle, prose_sampler
from render_helpers import check_golden, normalised

from scireport.render import render_bundle
from scireport.render.definition import Format

GOLDEN = Path(__file__).resolve().parent
FORMATS: list[Format] = ['md', 'html', 'tex']


def render(engine: str, fmt: Format) -> dict[str, bytes]:
  result = render_bundle(
    prose_sampler(),
    template='generic@1',
    layout='minimal@1',
    formats=[fmt],
    flat=True,
    markup_engine=engine,
  )
  return normalised(result.files)


@pytest.mark.parametrize('fmt', FORMATS)
def test_mistletoe_matches_its_golden_files(fmt: Format) -> None:
  check_golden(render('mistletoe', fmt), GOLDEN / 'markup' / 'mistletoe' / fmt)


@pytest.mark.integration
@pytest.mark.pandoc
@pytest.mark.parametrize('fmt', FORMATS)
def test_pandoc_matches_its_golden_files(fmt: Format) -> None:
  require_extra('pypandoc')
  check_golden(render('pandoc', fmt), GOLDEN / 'markup' / 'pandoc' / fmt)


def test_citations_in_tex_match_the_golden_files() -> None:
  result = render_bundle(
    citation_bundle(style='authoryear'),
    template='generic@1',
    layout='minimal@1',
    formats=['tex'],
    flat=True,
  )
  check_golden(normalised(result.files), GOLDEN / 'citations' / 'tex')


@pytest.mark.integration
@pytest.mark.pandoc
@pytest.mark.parametrize('fmt', ['md', 'html'])
@pytest.mark.parametrize('engine', ['mistletoe', 'pandoc'])
def test_citations_in_md_and_html_match_the_golden_files(engine: str, fmt: Format) -> None:
  require_extra('pypandoc')
  result = render_bundle(
    citation_bundle(),
    template='generic@1',
    layout='minimal@1',
    formats=[fmt],
    flat=True,
    markup_engine=engine,
  )
  # Both engines hand the citations to the same citation processor: one golden folder.
  check_golden(normalised(result.files), GOLDEN / 'citations' / fmt)
