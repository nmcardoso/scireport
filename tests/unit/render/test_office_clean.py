"""The cleaning of the document tree before pandoc reads local files (no pandoc needed)."""

from __future__ import annotations

from typing import Any

from scireport.render.office import _clean


def image(target: str) -> dict[str, Any]:
  return {'t': 'Image', 'c': [['', [], []], [{'t': 'Str', 'c': 'alt'}], [target, '']]}


def link(target: str) -> dict[str, Any]:
  return {'t': 'Link', 'c': [['', [], []], [{'t': 'Str', 'c': 'text'}], [target, '']]}


def kinds(blocks: list[dict[str, Any]]) -> list[str]:
  return [node['t'] for block in blocks for node in block['c']]


def test_only_images_that_are_files_of_the_render_survive() -> None:
  para = {
    't': 'Para',
    'c': [image('figures/a.png'), image('/etc/passwd'), image('../x.png'), image('http://x/y.png')],
  }
  (out,) = _clean([para], {'figures/a.png'})
  assert kinds([out]) == ['Image', 'Str', 'Str', 'Str']


def test_raw_content_and_unsafe_links_are_dropped() -> None:
  blocks: list[dict[str, Any]] = [
    {'t': 'RawBlock', 'c': ['html', '<!-- x -->']},
    {
      't': 'Para',
      'c': [
        {'t': 'RawInline', 'c': ['openxml', '<w:p/>']},
        link('javascript:x'),
        link('https://ok'),
      ],
    },
  ]
  out = _clean(blocks, set())
  assert len(out) == 1 and kinds(out) == ['Str', 'Link']
