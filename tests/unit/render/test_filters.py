import math

import pytest

from scireport.render import filters as f


@pytest.mark.parametrize(
  ('value', 'expected'),
  [
    (None, '--'),
    (math.nan, 'NaN'),
    (math.inf, '∞'),
    (-math.inf, '−∞'),
    (1.5, None),
    ('x', None),
    (0, None),
  ],
)
def test_missing(value: object, expected: str | None) -> None:
  assert f.missing(value) == expected


@pytest.mark.parametrize('value', [True, 'x', None, math.nan, math.inf, [1]])
def test_number_coerces_non_numbers_to_zero(value: object) -> None:
  assert f.number(value) == 0.0


def test_number_passes_finite_numbers() -> None:
  assert f.number(3) == 3.0
  assert f.number(2.5) == 2.5


@pytest.mark.parametrize(
  ('value', 'expected'),
  [
    (12483921, '12,483,921'),
    (0, '0'),
    (-1234.4, '-1,234'),
    (None, '--'),
    (math.nan, 'NaN'),
    ('7', '--'),
    (True, '--'),
  ],
)
def test_fmt_int(value: object, expected: str) -> None:
  assert f.fmt_int(value) == expected


@pytest.mark.parametrize(
  ('value', 'digits', 'expected'),
  [
    (0.99724, 4, '0.9972'),
    (1234567.0, 4, '1.235e+06'),
    (3, 4, '3'),
    (None, 4, '--'),
    ('x', 4, '--'),
    (0.5, 2, '0.5'),
  ],
)
def test_fmt_float(value: object, digits: int, expected: str) -> None:
  assert f.fmt_float(value, digits) == expected


@pytest.mark.parametrize(
  ('part', 'whole', 'expected'),
  [(1, 8, '12.50%'), (0, 5, '0.00%'), (3, 0, '--'), (3, None, '--'), (None, 4, '0.00%')],
)
def test_share(part: object, whole: object, expected: str) -> None:
  assert f.share(part, whole) == expected


@pytest.mark.parametrize(
  ('value', 'expected'),
  [
    (None, 'not recorded'),
    (0, '0 B'),
    (512, '512.0 B'),
    (2048, '2.0 KiB'),
    (4.5 * 1024**3, '4.5 GiB'),
    (3 * 1024**5, '3,072.0 TiB'),
    (math.nan, 'NaN'),
    ('x', '--'),
  ],
)
def test_fmt_bytes(value: object, expected: str) -> None:
  assert f.fmt_bytes(value) == expected


@pytest.mark.parametrize(
  ('value', 'expected'),
  [
    (0.3, '0.3s'),
    (0, '0.0s'),
    (43, '43s'),
    (125, '2m5s'),
    (3661, '1h1m1s'),
    (3600, '1h'),
    (-90, '-1m30s'),
    (None, '--'),
    (math.inf, '∞'),
    ('x', '--'),
  ],
)
def test_duration(value: object, expected: str) -> None:
  assert f.duration(value) == expected


@pytest.mark.parametrize(
  ('value', 'digits', 'expected'),
  [(0.9972, 2, '99.72%'), (0.5, 0, '50%'), (None, 2, '--'), ('x', 2, '--')],
)
def test_pct(value: object, digits: int, expected: str) -> None:
  assert f.pct(value, digits) == expected


@pytest.mark.parametrize(
  ('value', 'expected'), [(800000, '800,000 ppm'), (None, '--'), ('x', '--')]
)
def test_ppm(value: object, expected: str) -> None:
  assert f.ppm(value) == expected


@pytest.mark.parametrize(
  ('value', 'digits', 'expected'),
  [
    (123456.0, 3, f.Scientific('1.23', 5)),
    (0.000314, 3, f.Scientific('3.14', -4)),
    (9.999e3, 3, f.Scientific('1.00', 4)),
    (-2500, 2, f.Scientific('-2.5', 3)),
    (0, 3, f.Scientific('0', 0)),
    (None, 3, '--'),
    ('x', 3, '--'),
    (math.nan, 3, 'NaN'),
  ],
)
def test_sci(value: object, digits: int, expected: object) -> None:
  assert f.sci(value, digits) == expected


def test_scientific_has_a_plain_text_form() -> None:
  assert str(f.Scientific('3.14', 5)) == '3.14e+05'
  assert str(f.Scientific('3.14', -5)) == '3.14e-05'


@pytest.mark.parametrize(
  ('value', 'digits', 'expected'),
  [
    (12483921, 1, '12.5M'),
    (3.2e9, 1, '3.2B'),
    (999, 1, '999'),
    (-4500, 1, '-4.5K'),
    (2e12, 0, '2T'),
    (None, 1, '--'),
    ('x', 1, '--'),
  ],
)
def test_compact(value: object, digits: int, expected: str) -> None:
  assert f.compact(value, digits) == expected


def test_breakable_inserts_zero_width_spaces_after_separators() -> None:
  assert f.breakable('a/b_c-d.e') == 'a/​b_​c-​d.​e'
  assert f.breakable(None) == ''


@pytest.mark.parametrize(
  ('text', 'expected'), [('Hello, World!', 'hello-world'), ('  ', 'section'), ('A_b c', 'a-b-c')]
)
def test_slug(text: str, expected: str) -> None:
  assert f.slug(text) == expected


def test_filters_are_registered_by_name() -> None:
  assert set(f.FILTERS) == {
    'fmt_int',
    'fmt_float',
    'share',
    'fmt_bytes',
    'duration',
    'pct',
    'ppm',
    'sci',
    'compact',
    'missing',
    'breakable',
    'slug',
  }
