"""Golden outputs: the Markdown, HTML and LaTeX of a small bundle, byte for byte (ADR-0008).

The bundle is ``kitchen_sink`` (every kind, a split Markdown outline) rendered with the built-in
``generic@1`` template and ``minimal@1`` layout. Both are frozen per version, so these files only
change together with a new version. ``SCIREPORT_UPDATE_GOLDEN=1 uv run pytest tests/golden``
rewrites them.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from render_fixtures import kitchen_sink
from render_helpers import check_golden, normalised

from scireport.render import render_bundle
from scireport.render.definition import Format

GOLDEN = Path(__file__).resolve().parent / 'kitchen-sink'
FORMATS: list[Format] = ['md', 'html', 'tex']


@pytest.mark.parametrize('fmt', FORMATS)
def test_output_matches_the_golden_files(fmt: Format) -> None:
  result = render_bundle(
    kitchen_sink(), template='generic@1', layout='minimal@1', formats=[fmt], flat=True
  )
  check_golden(normalised(result.files), GOLDEN / fmt)


def test_rendering_twice_gives_identical_bytes() -> None:
  first = render_bundle(kitchen_sink(), template='generic@1', layout='minimal@1')
  second = render_bundle(kitchen_sink(), template='generic@1', layout='minimal@1')
  assert first.files == second.files


def test_a_figure_built_with_matplotlib_renders_the_same_twice() -> None:
  first = render_bundle(kitchen_sink(real=True), template='generic@1', layout='minimal@1')
  second = render_bundle(kitchen_sink(real=True), template='generic@1', layout='minimal@1')
  assert first.files == second.files
