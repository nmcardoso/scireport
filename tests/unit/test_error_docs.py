"""The error catalogue in code and in the documentation must list the same codes."""

from __future__ import annotations

import re
from pathlib import Path

from scireport.errors import CODES

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'errors.md'
ROW = re.compile(r'^\| ([EW]\d{3}) \| (.+) \|$', re.MULTILINE)


def documented() -> dict[str, str]:
  return dict(ROW.findall(PAGE.read_text(encoding='utf-8')))


def test_every_code_is_documented_with_its_title() -> None:
  assert documented() == CODES


def test_codes_follow_the_family_scheme() -> None:
  assert all(re.fullmatch(r'[EW]\d{3}', code) for code in CODES)
  assert list(CODES) == sorted(CODES, key=lambda c: (c[0] != 'E', c))


def test_titles_are_one_line_and_unique() -> None:
  assert all('\n' not in title and title == title.strip() for title in CODES.values())
  assert len(set(CODES.values())) == len(CODES)


def test_every_code_used_in_the_source_is_in_the_catalogue() -> None:
  source = Path(__file__).resolve().parents[2] / 'scireport'
  literal = re.compile(r"""['"]([EW]\d{3})['"]""")
  used = {
    code
    for path in source.rglob('*.py')
    if path.name != 'errors.py'
    for code in literal.findall(path.read_text(encoding='utf-8'))
  }
  assert used - set(CODES) == set()


def test_every_code_has_a_test_that_names_it() -> None:
  tests = Path(__file__).resolve().parent.parent
  text = '\n'.join(
    path.read_text(encoding='utf-8')
    for path in tests.rglob('test_*.py')
    if path.name != Path(__file__).name
  )
  untested = [code for code in CODES if not re.search(rf"""['"]{code}['"]""", text)]
  assert untested == [], f'no test names these codes: {untested}'
