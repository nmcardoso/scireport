"""Property tests: the escape functions are total and their output is safe (ADR-0010)."""

from __future__ import annotations

import html
import re

from hypothesis import given, settings
from hypothesis import strategies as st

from scireport.render.escape import (
  TEX_SPECIALS,
  TEX_UNICODE,
  md_code_span,
  md_escape,
  tex_escape,
)
from scireport.render.markup import default_converter

TEXT = st.text(max_size=60)
TEX_CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')
UNSAFE = set('\\{}#$%&_~^<>|')
# '{[}' and '{*}' are the braces put around a leading bracket or star.
REPLACEMENTS = sorted(
  {*TEX_SPECIALS.values(), *TEX_UNICODE.values(), '{[}', '{*}'}, key=len, reverse=True
)


def strip_known_macros(source: str) -> str:
  """Remove every replacement the escape function can produce, longest first."""
  for macro in REPLACEMENTS:
    source = source.replace(macro, '')
  return source


@given(TEXT)
@settings(max_examples=300)
def test_tex_output_has_no_unescaped_special_character(text: str) -> None:
  out = strip_known_macros(tex_escape(text, unicode='keep'))
  assert not UNSAFE & set(out)


@given(TEXT)
@settings(max_examples=300)
def test_tex_output_with_unicode_map_has_no_unescaped_special_character(text: str) -> None:
  out = strip_known_macros(tex_escape(text))
  assert not UNSAFE & set(out)


@given(TEXT)
def test_tex_output_has_no_control_characters(text: str) -> None:
  assert not TEX_CONTROL.search(tex_escape(text))


@given(TEXT)
def test_tex_inline_has_no_blank_line_and_no_edge_whitespace(text: str) -> None:
  out = tex_escape(text, inline=True)
  assert '\n' not in out and out == out.strip()


@given(st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), max_size=60))
def test_tex_escape_keeps_plain_ascii_without_specials_unchanged(text: str) -> None:
  if not UNSAFE & set(text) and not text.startswith(('[', '*')):
    assert tex_escape(text) == text


@given(TEXT)
def test_md_escape_is_one_line(text: str) -> None:
  out = md_escape(text)
  assert '\n' not in out and '\r' not in out and out == out.strip()


def shown(source: str) -> str:
  """Return what a CommonMark reader shows for ``source``: its HTML text, entities decoded."""
  converted = default_converter().convert(source, 'html')
  assert converted.issues == ()  # nothing escaped may fall outside the supported subset
  return html.unescape(re.sub(r'<[^>]+>', '', str(converted.text))).strip()


@given(st.text(alphabet=st.characters(blacklist_categories=['Cs', 'Cc', 'Zl', 'Zp']), max_size=40))
@settings(max_examples=300)
def test_md_escape_renders_as_the_collapsed_text(text: str) -> None:
  collapsed = ' '.join(text.split())
  assert shown(md_escape(text)) == collapsed


@given(TEXT)
def test_md_code_span_is_one_span_that_holds_the_text(text: str) -> None:
  span = md_code_span(text)
  assert '\n' not in span
  fence = re.match(r'`+', span)
  assert fence is not None
  assert span.endswith(fence.group(0))
  inner = span[len(fence.group(0)) : -len(fence.group(0))]
  assert ' '.join(text.split()) in ' '.join(inner.split()) or not text.strip()
