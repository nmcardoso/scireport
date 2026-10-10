"""Design-token consistency: one source of truth, four readers (ADR-0007).

``palette.yaml`` is the only place where a colour is a constant. ``tokens.css``, the LaTeX style
and the matplotlib style repeat the values by hand, so that a reviewer can read them in a diff,
which only stays honest if something notices when they drift. These tests parse each file and
compare it with the palette, rather than with a second copy of the numbers.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scireport.render.registry import list_layouts, load_layout
from scireport.styles import mplstyle_path, palette
from scireport.styles.palette import Palette

CSS_TOKEN = re.compile(r'--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;')
CSS_SIZE = re.compile(r'--(text|space)-([a-z0-9]+):\s*([0-9.]+)pt\s*;')
STY_COLOR = re.compile(r'\\definecolor\{sc-([a-z0-9-]+)\}\{HTML\}\{([0-9A-Fa-f]{6})\}')
MPL_COLOR = re.compile(r'"(#[0-9a-fA-F]{6})"')
EXTRA_STY_COLORS = {'code-ink'}
"""Colours the LaTeX style defines that are not tokens of the palette (the code-block ink)."""
EXTRA_CSS_COLORS = {'#e6edf2'}
"""Hex values in components.css that are not tokens (the code-block ink)."""

LAYOUTS = sorted({item.name for item in list_layouts() if load_layout(item.ref).definition.palette})


def _paths(name: str) -> tuple[Palette, Path]:
  layout = load_layout(name)
  return palette(name), layout.root


def test_the_designed_layouts_have_a_palette() -> None:
  assert {'default', 'modern'} <= set(LAYOUTS)


@pytest.mark.parametrize('name', LAYOUTS)
def test_tokens_css_matches_the_palette(name: str) -> None:
  pal, root = _paths(name)
  found = dict(CSS_TOKEN.findall((root / 'html' / 'tokens.css').read_text(encoding='utf-8')))
  assert found, 'no --token: #hex; declaration was found in tokens.css'
  for token, value in pal.colors.items():
    assert token in found, f'tokens.css is missing --{token}'
    assert found[token].lower() == value, f'--{token} is {found[token]}, palette has {value}'
  assert set(found) == set(pal.colors), 'tokens.css declares colours the palette does not'


@pytest.mark.parametrize('name', LAYOUTS)
def test_tokens_css_sizes_match_the_palette(name: str) -> None:
  pal, root = _paths(name)
  found = {
    (kind, label): float(value)
    for kind, label, value in CSS_SIZE.findall(
      (root / 'html' / 'tokens.css').read_text(encoding='utf-8')
    )
  }
  for label, size in pal.type_scale.items():
    assert found[('text', label)] == size, f'--text-{label}'
  assert [found[('space', str(i))] for i in range(1, len(pal.spacing) + 1)] == [
    float(x) for x in pal.spacing
  ]


@pytest.mark.parametrize('name', LAYOUTS)
def test_the_latex_style_defines_the_palette_colours(name: str) -> None:
  pal, root = _paths(name)
  style = load_layout(name).definition.formats['tex'].style
  assert style
  found = {
    token: value.lower()
    for token, value in STY_COLOR.findall((root / style).read_text(encoding='utf-8'))
  }
  for token, value in pal.colors.items():
    assert token in found, f'{style} does not define sc-{token}'
    assert f'#{found[token]}' == value, f'sc-{token} is #{found[token]}, palette has {value}'
  assert set(found) - set(pal.colors) <= EXTRA_STY_COLORS


@pytest.mark.parametrize('name', LAYOUTS)
def test_the_mplstyle_colours_are_drawn_from_the_palette(name: str) -> None:
  pal, _ = _paths(name)
  text = mplstyle_path(name).read_text(encoding='utf-8')
  declared = {value.lower() for value in MPL_COLOR.findall(text)}
  assert declared, 'no "#hex" colour in the style'
  assert declared <= set(pal.colors.values()), declared - set(pal.colors.values())


@pytest.mark.parametrize('name', LAYOUTS)
def test_the_mplstyle_cycle_and_cmap_are_the_palettes(name: str) -> None:
  pal, _ = _paths(name)
  text = mplstyle_path(name).read_text(encoding='utf-8')
  cycle = next(line for line in text.splitlines() if line.startswith('axes.prop_cycle'))
  assert [value.lower() for value in MPL_COLOR.findall(cycle)] == pal.cycle_colors
  assert f'image.cmap: {pal.cmap.sequential}' in text
  assert pal.fonts.sans[0] in text
  assert pal.fonts.mono[0] in text


@pytest.mark.parametrize('name', LAYOUTS)
def test_the_css_uses_only_palette_colours(name: str) -> None:
  pal, root = _paths(name)
  css = load_layout(name).definition.formats['html'].css
  allowed = set(pal.colors.values()) | EXTRA_CSS_COLORS
  hexes = re.compile(r'#[0-9a-fA-F]{6}\b')
  for sheet in css:
    if sheet.endswith('tokens.css'):
      continue
    stray = {
      value.lower() for value in hexes.findall((root / sheet).read_text(encoding='utf-8'))
    } - allowed
    assert not stray, f'{sheet} uses colours that are not palette tokens: {sorted(stray)}'


@pytest.mark.parametrize('name', LAYOUTS)
def test_a_layout_lists_only_fonts_that_ship(name: str) -> None:
  layout = load_layout(name)
  assert layout.definition.fonts
  assert (Path(layout.root) / 'palette.yaml').is_file()
