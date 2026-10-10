import pytest

from scireport.render.escape import TEX_SPECIALS, md_code_span, md_escape, tex_escape


@pytest.mark.parametrize(('char', 'expected'), sorted(TEX_SPECIALS.items()))
def test_tex_escape_covers_every_special_character(char: str, expected: str) -> None:
  assert tex_escape(f'a{char}b') == f'a{expected}b'


def test_tex_escape_names_the_specials_of_the_adr() -> None:
  assert set('#$%&~_^\\{}') <= set(TEX_SPECIALS)


def test_tex_escape_maps_unicode_symbols_by_default() -> None:
  assert tex_escape('±1 × 10 − 2 ≤ α') == (
    r'\ensuremath{\pm}1 \ensuremath{\times} 10 \ensuremath{-} 2 '
    r'\ensuremath{\leq} \ensuremath{\alpha}'
  )


def test_tex_escape_can_leave_unicode_to_the_font() -> None:
  assert tex_escape('± α é', unicode='keep') == '± α é'


def test_tex_escape_keeps_accented_letters_and_drops_control_characters() -> None:
  assert tex_escape('café\x00\x07') == 'café'


def test_tex_escape_inline_collapses_whitespace() -> None:
  assert tex_escape('  a \n\n b\t c  ', inline=True) == 'a b c'


@pytest.mark.parametrize(('text', 'expected'), [('[1]', '{[}1]'), ('*x', '{*}x'), ('a[1]', 'a[1]')])
def test_tex_escape_braces_a_leading_bracket_or_star(text: str, expected: str) -> None:
  assert tex_escape(text) == expected


@pytest.mark.parametrize(
  ('text', 'expected'),
  [
    ('plain', 'plain'),
    ('a*b', r'a\*b'),
    ('a_b', 'a_b'),
    ('_a', r'\_a'),
    ('a_', r'a\_'),
    ('__init__', r'\_\_init\_\_'),
    ('[x](y)', r'\[x\](y)'),
    ('<b>', r'\<b\>'),
    ('a|b', r'a\|b'),
    ('$5', r'\$5'),
    ('1 & 2', r'1 \& 2'),
    ('# title', r'\# title'),
    ('- item', r'\- item'),
    ('+ item', r'\+ item'),
    ('1. item', r'1\. item'),
    ('1) item', r'1\) item'),
    ('---', r'\---'),
    ('--', '--'),
    ('-5', '-5'),
    ('a  \n b', 'a b'),
    ('', ''),
  ],
)
def test_md_escape(text: str, expected: str) -> None:
  assert md_escape(text) == expected


@pytest.mark.parametrize(
  ('text', 'expected'),
  [
    ('a', '`a`'),
    ('a`b', '``a`b``'),
    ('`a', '`` `a ``'),
    ('a``b`c', '```a``b`c```'),
    ('a\nb', '`a b`'),
    ('', '` `'),
  ],
)
def test_md_code_span(text: str, expected: str) -> None:
  assert md_code_span(text) == expected


@pytest.mark.parametrize(('text', 'expected'), [('.', r'\.'), (')', r'\)'), ('. x', r'\. x')])
def test_md_escape_escapes_a_bare_ordered_marker(text: str, expected: str) -> None:
  # mistletoe, unlike CommonMark, reads a '.' or ')' without digits as an empty list item.
  assert md_escape(text) == expected
