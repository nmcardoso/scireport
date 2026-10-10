"""The built-in kitchen-sink template and the three examples render cleanly with every layout."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from scireport import Report
from scireport.demo import kitchen_sink_bundle, kitchen_sink_report
from scireport.errors import RenderError
from scireport.render import render_bundle
from scireport.render.layout import Layout
from scireport.render.registry import load_layout, load_template
from scireport.validate import validate_bundle

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples'
sys.path.insert(0, str(EXAMPLES))
import dataset_report  # noqa: E402
import metrics_dashboard  # noqa: E402
import text_report  # noqa: E402

LAYOUTS = ['default', 'modern', 'minimal']


@pytest.mark.parametrize('layout', LAYOUTS)
def test_the_kitchen_sink_renders_without_a_warning(layout: str) -> None:
  bundle = kitchen_sink_bundle('default', real_figures=False)
  result = render_bundle(
    bundle, template='kitchen-sink@1', layout=f'{layout}@1', strict=True, flat=False
  )
  assert result.issues == ()
  assert {'md/report.md', 'html/report.html', 'tex/report.tex'} <= set(result.files)


def test_the_kitchen_sink_uses_every_component_of_the_layout_api() -> None:
  html = (
    render_bundle(
      kitchen_sink_bundle(real_figures=False),
      template='kitchen-sink@1',
      layout='default@1',
      formats=['html'],
      flat=True,
    )
    .files['report.html']
    .decode()
  )
  for name in (
    'metric-grid',
    'status--running',
    'status--partial',
    'alert--error',
    'flow-stage--skipped',
    'flow-stage--reused',
    'equation-number',
    'table-block',
    'figure',
    'code-block',
    'metadata',
    'details',
    'note',
    'attachment',
    'cover',
    'toc',
    'chapter',
  ):
    assert name in html, name


def test_the_kitchen_sink_bundle_is_reproducible() -> None:
  first = kitchen_sink_report('default', real_figures=True).build()
  second = kitchen_sink_report('default', real_figures=True).build()
  assert first.manifest == second.manifest


def test_the_kitchen_sink_names_its_own_template_and_layout() -> None:
  render = kitchen_sink_report('modern', real_figures=False).manifest().render
  assert (render.template, render.layout) == ('kitchen-sink@1', 'modern@1')


def test_a_bundle_without_the_fields_of_the_template_is_invalid() -> None:
  empty = Report('Empty').add_text('a.b', 'x').build()
  report = validate_bundle(empty, load_template('kitchen-sink@1'), _layout(), ['md'])
  assert not report.ok
  assert {issue.code for issue in report.issues} >= {'E105'}


def _layout() -> Layout:
  return load_layout('default@1')


@pytest.mark.parametrize('layout', LAYOUTS)
@pytest.mark.parametrize(
  ('module', 'template'),
  [
    (dataset_report, None),
    (text_report, None),
    (metrics_dashboard, metrics_dashboard.TEMPLATE),
  ],
)
def test_an_example_renders_every_text_format_strictly(
  module: object, template: Path | None, layout: str
) -> None:
  build = module.build  # type: ignore[attr-defined]
  bundle = build('default' if layout == 'minimal' else layout).build()
  try:
    result = render_bundle(bundle, template=template, layout=f'{layout}@1', strict=True)
  except RenderError as exc:
    pytest.fail('\n'.join(issue.format() for issue in exc.issues))
  assert result.issues == ()
  assert 'md/index.md' in result.files or 'md/report.md' in result.files


def test_the_examples_are_seeded() -> None:
  first = dataset_report.build('default').build().manifest
  second = dataset_report.build('default').build().manifest
  assert first == second
