"""Golden outputs of the designed layouts: kitchen-sink@1 rendered to md, html and tex.

The bundle is ``scireport.demo.kitchen_sink_bundle`` with placeholder pictures (so that the files
do not depend on matplotlib). The layouts are frozen per version, so these files only change
together with a new layout version (ADR-0008). ``SCIREPORT_UPDATE_GOLDEN=1 uv run pytest
tests/golden`` rewrites them; review the diff.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from render_helpers import check_golden, normalised

from scireport.demo import kitchen_sink_bundle
from scireport.render import render_bundle
from scireport.render.definition import Format

GOLDEN = Path(__file__).resolve().parent / 'layouts'
FORMATS: list[Format] = ['md', 'html', 'tex']
LAYOUTS = ['default', 'modern']


@pytest.mark.parametrize('fmt', FORMATS)
@pytest.mark.parametrize('layout', LAYOUTS)
def test_output_matches_the_golden_files(layout: str, fmt: Format) -> None:
  result = render_bundle(
    kitchen_sink_bundle(layout, real_figures=False),
    template='kitchen-sink@1',
    layout=f'{layout}@1',
    formats=[fmt],
    flat=True,
  )
  check_golden(normalised(result.files), GOLDEN / f'{layout}-1' / fmt)


@pytest.mark.parametrize('layout', LAYOUTS)
def test_two_renders_give_identical_bytes(layout: str) -> None:
  def render() -> dict[str, bytes]:
    return render_bundle(
      kitchen_sink_bundle(layout, real_figures=False),
      template='kitchen-sink@1',
      layout=f'{layout}@1',
    ).files

  assert render() == render()
