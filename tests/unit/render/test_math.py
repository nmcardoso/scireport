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
