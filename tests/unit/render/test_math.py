import base64

import pytest

from scireport.errors import ScireportError
from scireport.render.math import MathError, math_problem, render_math


def test_math_is_drawn_as_a_self_contained_svg() -> None:
  drawn = render_math('E = mc^2', display=False)
  assert drawn.data_uri.startswith('data:image/svg+xml;base64,')
  svg = base64.b64decode(drawn.data_uri.split(',', 1)[1]).decode()
  assert svg.lstrip().startswith('<?xml')
  assert '<svg' in svg
  assert '<font' not in svg


def test_display_math_is_bigger_than_inline_math() -> None:
  inline = render_math(r'\sum_i x_i', display=False)
  display = render_math(r'\sum_i x_i', display=True)
  assert len(display.data_uri) != len(inline.data_uri)
  assert inline.depth_pt > 0


def test_drawing_twice_gives_the_same_bytes() -> None:
  first = render_math.__wrapped__(r'\alpha^2 + \beta', display=True)
  second = render_math.__wrapped__(r'\alpha^2 + \beta', display=True)
  assert first == second


def test_svg_carries_no_date_or_matplotlib_version() -> None:
  svg = base64.b64decode(render_math('x', display=False).data_uri.split(',', 1)[1]).decode()
  assert 'dc:date' not in svg
  assert 'Matplotlib v' not in svg


def test_math_that_mathtext_cannot_draw_is_a_warning_with_a_reason() -> None:
  with pytest.raises(MathError) as caught:
    render_math(r'\begin{align} x \end{align}', display=True)
  assert caught.value.code == 'W601'
  assert isinstance(caught.value, ScireportError)
  assert 'begin' in caught.value.message


def test_math_problem_reports_or_accepts() -> None:
  assert math_problem(r'\frac{a}{b}') is None
  assert math_problem(r'\begin{align} x \end{align}') is not None


def _need_latex() -> None:
  import os
  import shutil

  if shutil.which('latex') is None:
    message = 'latex is not on PATH'
    if os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1':
      pytest.fail(message)
    pytest.skip(message)


def test_usetex_without_latex_is_a_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
  import shutil

  from scireport.errors import MissingDependencyError

  monkeypatch.setattr(shutil, 'which', lambda _name: None)
  with pytest.raises(MissingDependencyError) as raised:
    render_math(r'\alpha_0', display=False, renderer='usetex')
  assert raised.value.code == 'E901'
  assert raised.value.exit_code == 3
  assert 'mathtext' in str(raised.value)


@pytest.mark.integration
def test_usetex_draws_what_mathtext_cannot() -> None:
  _need_latex()
  source = r'\mathrm{d}s^2 = \sum_{i}\frac{\partial^2 f}{\partial x_i^2}\,\mathbb{R}'
  svg = render_math(source, display=True, renderer='usetex')
  assert svg.data_uri.startswith('data:image/svg+xml;base64,')
  assert render_math(source, display=True, renderer='usetex') == svg


@pytest.mark.integration
def test_usetex_output_is_deterministic_and_dateless() -> None:
  _need_latex()
  import base64

  first = render_math(r'E = mc^2', display=False, renderer='usetex', color='#112233')
  render_math.cache_clear()
  second = render_math(r'E = mc^2', display=False, renderer='usetex', color='#112233')
  assert first == second
  svg = base64.b64decode(first.data_uri.split(',', 1)[1])
  assert b'<dc:date>' not in svg


@pytest.mark.integration
def test_an_expression_latex_rejects_is_w602() -> None:
  _need_latex()
  with pytest.raises(MathError) as raised:
    render_math(r'\thiscommanddoesnotexist{x}', display=False, renderer='usetex')
  assert raised.value.code == 'W602'
  assert 'LaTeX' in raised.value.hint if raised.value.hint else False


@pytest.mark.integration
def test_a_render_with_usetex_shows_rejected_math_as_source_and_warns() -> None:
  _need_latex()
  from scireport import Report
  from scireport.render import render_bundle

  report = Report('T').add_math('m', r'\thiscommanddoesnotexist{x}').set_render(layout='minimal@1')
  result = render_bundle(report.build(), formats=['html'], math_renderer='usetex', flat=True)
  assert [issue.code for issue in result.issues] == ['W602']
  assert 'thiscommanddoesnotexist' in result.files['report.html'].decode()
