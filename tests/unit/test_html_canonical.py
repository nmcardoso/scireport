"""The canonical form of HTML ignores spelling and keeps content."""

from __future__ import annotations

from html_canonical import canonicalise, diff


def test_attribute_order_entities_and_whitespace_do_not_matter() -> None:
  a = '<p class="x" id="y">It&#39;s   here</p>\n\n<div>\n  hi\n</div>'
  b = '<p id="y" class="x">It\'s here</p><div> hi </div>'
  assert canonicalise(a) == canonicalise(b)


def test_text_attributes_and_tags_do_matter() -> None:
  base = canonicalise('<p class="x">a</p>')
  assert canonicalise('<p class="x">b</p>') != base
  assert canonicalise('<p class="y">a</p>') != base
  assert canonicalise('<div class="x">a</div>') != base


def test_comments_are_dropped_and_pre_keeps_its_whitespace() -> None:
  assert canonicalise('<!-- one --><p>a</p>') == canonicalise('<!-- two --><p>a</p>')
  assert canonicalise('<pre>a  b\n c</pre>') != canonicalise('<pre>a b c</pre>')


def test_a_data_uri_is_replaced_by_a_hash_of_itself() -> None:
  one = canonicalise('<img src="data:image/png;base64,AAAA">')
  two = canonicalise('<img src="data:image/png;base64,AAAB">')
  assert one != two
  assert 'AAAA' not in one
  assert 'sha256:' in one


def test_a_void_tag_and_a_bare_attribute_are_kept() -> None:
  assert canonicalise('<details open><br/></details>') == ('<details open>\n<br/>\n</details>\n')


def test_diff_is_empty_for_equal_documents() -> None:
  text = canonicalise('<p>a</p>')
  assert diff(text, text) == ''
  assert '-TEXT:a' in diff(text, canonicalise('<p>b</p>'))
