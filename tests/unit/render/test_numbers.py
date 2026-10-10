import datetime as dt
from typing import Any

import pytest

from scireport.render.filters import Scientific
from scireport.render.numbers import (
  NUMBER_FORMATS,
  Target,
  format_cell,
  format_number_value,
  format_problem,
  format_scalar,
  typeset_scalar,
  typeset_unit,
)
from scireport.render.safe import Safe
from scireport.spec.kinds import NumberValue


@pytest.mark.parametrize('name', sorted(NUMBER_FORMATS))
def test_every_format_name_is_valid(name: str) -> None:
  assert format_problem(name) is None


@pytest.mark.parametrize('spec', [None, ',.2f', '.3e', '08.3f', ',d'])
def test_python_format_specifications_are_valid(spec: str | None) -> None:
  assert format_problem(spec) is None


@pytest.mark.parametrize('spec', ['bogus', '.2q', 'int2'])
def test_unusable_formats_are_explained(spec: str) -> None:
  assert 'neither one of' in str(format_problem(spec))


@pytest.mark.parametrize(
  ('value', 'spec', 'expected'),
  [
    (3061, None, '3061'),
    (0.5, None, '0.5'),
    (3061, 'int', '3,061'),
    (0.9875, 'pct', '98.75%'),
    (1234.567, ',.2f', '1,234.57'),
    (None, 'int', '--'),
    (True, None, 'true'),
    ('text', 'int', 'text'),
    (dt.date(2026, 10, 9), None, '2026-10-09'),
    (7, '.2q', '7'),
  ],
)
def test_format_scalar(value: object, spec: str | None, expected: str) -> None:
  assert format_scalar(value, spec) == expected


def test_format_scalar_returns_scientific_for_sci() -> None:
  assert format_scalar(123456.0, 'sci') == Scientific('1.23', 5)


@pytest.mark.parametrize(
  ('target', 'expected'),
  [('md', '1.23×10⁵'), ('html', '1.23×10<sup>5</sup>'), ('tex', r'\ensuremath{1.23\times10^{5}}')],
)
def test_typeset_scientific(target: str, expected: str) -> None:
  assert typeset_scalar(Scientific('1.23', 5), target) == expected  # type: ignore[arg-type]


def test_zero_in_scientific_notation_is_plain() -> None:
  assert typeset_scalar(Scientific('0', 0), 'html') == '0'


@pytest.mark.parametrize(
  ('target', 'expected'),
  [('md', r'x\*y \& z'), ('html', 'x*y &amp; z'), ('tex', r'x*y \& z')],
)
def test_typeset_scalar_escapes_text(target: str, expected: str) -> None:
  assert typeset_scalar('x*y & z', target) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
  ('target', 'expected'),
  [
    ('md', 'erg s⁻¹ cm⁻²'),
    ('html', 'erg s<sup>-1</sup> cm<sup>-2</sup>'),
    ('tex', r'erg s\ensuremath{^{-1}} cm\ensuremath{^{-2}}'),
  ],
)
def test_typeset_unit_makes_superscripts_and_keeps_spaces(target: str, expected: str) -> None:
  assert typeset_unit('erg s^-1 cm^-2', target) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
  ('fields', 'target', 'expected'),
  [
    ({'value': 3061, 'format': 'int', 'unit': 'pairs'}, 'md', '3,061 pairs'),
    ({'value': 3061, 'format': 'int', 'unit': 'pairs'}, 'html', '3,061&nbsp;pairs'),
    ({'value': 3061, 'format': 'int', 'unit': 'pairs'}, 'tex', '3,061~pairs'),
    ({'value': 1.234, 'uncertainty': 0.04, 'format': ',.2f'}, 'md', '1.23 ± 0.04'),
    ({'value': 1.234, 'uncertainty': 0.04, 'format': ',.2f'}, 'tex', r'1.23 \ensuremath{\pm} 0.04'),
    ({'value': 1.5, 'interval': (1.1, 1.9)}, 'md', '1.5 [1.1, 1.9]'),
    ({'value': None}, 'md', '--'),
    ({'value': None, 'missing': 'n/a'}, 'html', 'n/a'),
    ({'value': None, 'missing': '50%'}, 'tex', r'50\%'),
  ],
)
def test_format_number_value(fields: dict[str, Any], target: Target, expected: str) -> None:
  value = NumberValue(kind='number', **fields)
  result = format_number_value(value, target)
  assert isinstance(result, Safe)
  assert result == expected


def test_format_cell_plain_and_scientific() -> None:
  assert format_cell('a_b', None, 'md') == 'a_b'
  cell = format_cell(1500.0, 'sci', 'html')
  assert isinstance(cell, Safe)
  assert cell == '1.50×10<sup>3</sup>'
