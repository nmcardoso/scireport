"""The matplotlib style API: context manager, paths, palette, figure sizes and saving."""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm
import numpy as np
import pytest

import scireport
from scireport.errors import TemplateError
from scireport.styles import (
  STYLES_DIR,
  figure,
  figure_bytes,
  fonts,
  mplstyle,
  mplstyle_path,
  palette,
  save_figure,
)
from scireport.styles.palette import load_palette


def test_the_public_names_are_in_the_package() -> None:
  for name in ('mplstyle', 'mplstyle_path', 'palette', 'figure'):
    assert callable(getattr(scireport, name))


def test_mplstyle_path_is_the_shipped_style() -> None:
  assert mplstyle_path('default') == STYLES_DIR / 'default.mplstyle'
  assert mplstyle_path('default@1').is_file()


def test_mplstyle_path_of_an_unknown_layout_is_an_error() -> None:
  with pytest.raises(TemplateError) as raised:
    mplstyle_path('nope')
  assert raised.value.code == 'E701'


def test_the_style_applies_inside_the_block_and_is_restored() -> None:
  before = dict(matplotlib.rcParams)
  with mplstyle('default'):
    assert matplotlib.rcParams['font.sans-serif'][0] == 'Inter'
    assert matplotlib.rcParams['image.cmap'] == 'cividis'
    assert matplotlib.rcParams['axes.grid'] is True
  after = dict(matplotlib.rcParams)
  assert after == before


def test_the_style_does_not_leak_when_the_block_raises() -> None:
  sentinel = matplotlib.rcParams['image.cmap']
  with pytest.raises(RuntimeError), mplstyle('default'):
    raise RuntimeError('boom')
  assert matplotlib.rcParams['image.cmap'] == sentinel


def test_rc_overrides_the_style_for_the_block() -> None:
  with mplstyle('default', rc={'font.size': 11.0}):
    assert matplotlib.rcParams['font.size'] == 11.0
    assert matplotlib.rcParams['axes.grid'] is True


def test_the_palette_resolves_roles_status_and_cycle() -> None:
  pal = palette('default')
  assert pal.colors['navy-deep'] == '#0d1b2a'
  assert pal.role_colors['failed'] == pal.colors['red']
  assert pal.status_colors['running'] == pal.colors['cyan']
  assert pal.cycle_colors[0] == pal.colors['blue']
  assert pal.hex('ink') == '#17212b'
  assert pal.cmap.sequential == 'cividis'
  assert pal.page.frame_width_in == pytest.approx(192 / 25.4)


def test_a_palette_naming_an_undefined_colour_is_an_error(tmp_path: Path) -> None:
  path = tmp_path / 'palette.yaml'
  path.write_text(
    'name: x\ncolors: {ink: "#000000"}\nrole: {failed: red}\nstatus: {}\ncycle: [ink]\n'
    'cmap: {sequential: cividis, diverging: RdBu_r}\nfonts: {sans: [a], mono: [b]}\n'
    'spacing: [4]\ntype_scale: {body: 10}\nbody_line_height: 1.5\nheading_line_height: 1.2\n',
    encoding='utf-8',
  )
  with pytest.raises(TemplateError) as raised:
    load_palette(path)
  assert raised.value.code == 'E702'
  assert 'red' in str(raised.value)


def test_a_missing_palette_file_is_e703(tmp_path: Path) -> None:
  with pytest.raises(TemplateError) as raised:
    load_palette(tmp_path / 'palette.yaml')
  assert raised.value.code == 'E703'


def test_a_figure_has_its_final_physical_size() -> None:
  fig, ax = figure(0.5, 2.0)
  width, height = fig.get_size_inches()
  assert width == pytest.approx(192 / 25.4 * 0.5)
  assert height == pytest.approx(2.0)
  assert ax.get_xlabel() == ''


def test_a_figure_is_clamped_to_the_frame() -> None:
  fig, _ = figure(3.0, 99.0)
  width, height = fig.get_size_inches()
  assert width == pytest.approx(192 / 25.4)
  assert height == pytest.approx(261 / 25.4)


def test_a_figure_grid_returns_an_array_of_axes() -> None:
  _, axes = figure(1.0, 3.0, nrows=2, ncols=3)
  assert np.shape(axes) == (2, 3)


def test_letter_paper_has_a_wider_frame() -> None:
  fig, _ = figure(1.0, 2.0, paper='letter')
  assert fig.get_size_inches()[0] == pytest.approx((215.9 - 18) / 25.4)


@pytest.mark.parametrize(
  ('kwargs', 'message'),
  [({'paper': 'a0'}, 'paper'), ({'width': 0}, 'positive'), ({'nrows': 0}, 'row')],
)
def test_bad_figure_arguments_are_value_errors(kwargs: dict[str, object], message: str) -> None:
  with pytest.raises(ValueError, match=message):
    figure(**kwargs)  # type: ignore[arg-type]


def _drawn() -> object:
  with mplstyle('default'):
    fig, ax = figure(0.6, 2.0)
    ax.plot([0, 1, 2], [0, 1, 4])
    ax.set_xlabel('x')
    return fig


@pytest.mark.parametrize('fmt', ['png', 'pdf', 'svg'])
def test_the_same_drawing_gives_the_same_bytes(fmt: str) -> None:
  first = figure_bytes(_drawn(), fmt)  # type: ignore[arg-type]
  second = figure_bytes(_drawn(), fmt)  # type: ignore[arg-type]
  assert first == second


def test_saved_files_carry_no_version_and_no_date() -> None:
  png = figure_bytes(_drawn(), 'png')  # type: ignore[arg-type]
  assert b'Software' not in png
  pdf = figure_bytes(_drawn(), 'pdf')  # type: ignore[arg-type]
  assert b'CreationDate' not in pdf
  assert b'Producer' not in pdf
  svg = figure_bytes(_drawn(), 'svg')  # type: ignore[arg-type]
  assert b'<dc:date>' not in svg


def test_save_figure_picks_the_format_from_the_suffix(tmp_path: Path) -> None:
  target = save_figure(_drawn(), tmp_path / 'sub' / 'f.png')  # type: ignore[arg-type]
  assert target.read_bytes().startswith(b'\x89PNG')
  save_figure(_drawn(), tmp_path / 'f.pdf', close=True)  # type: ignore[arg-type]
  assert (tmp_path / 'f.pdf').read_bytes().startswith(b'%PDF')


def test_save_figure_refuses_an_unknown_suffix(tmp_path: Path) -> None:
  with pytest.raises(ValueError, match='cannot save'):
    save_figure(_drawn(), tmp_path / 'f.gif')  # type: ignore[arg-type]


def test_figure_bytes_refuses_an_unknown_format() -> None:
  with pytest.raises(ValueError, match='png, pdf or svg'):
    figure_bytes(_drawn(), 'gif')  # type: ignore[arg-type]


def test_every_vendored_face_ships_with_its_licence() -> None:
  for name in fonts.FACES.values():
    assert fonts.face_path(name).is_file()
  assert (fonts.FONTS_DIR / 'OFL.txt').read_text(encoding='utf-8').count('SIL OPEN FONT LICENSE')


def test_an_unknown_face_is_not_found() -> None:
  with pytest.raises(FileNotFoundError):
    fonts.face_path('Nope.otf')


def test_registered_families_resolve_to_a_same_named_font() -> None:
  fonts.register()
  fonts.register()  # idempotent
  for family in ('Inter', 'IBM Plex Mono'):
    found = fm.findfont(fm.FontProperties(family=family), fallback_to_default=False)
    assert fm.get_font(found).family_name == family
  assert fonts.probe() == []


def test_font_face_css_inlines_the_listed_faces_in_a_fixed_order() -> None:
  css = fonts.font_face_css(['Inter-SemiBold.otf', 'Inter-Regular.otf', 'unknown.otf'])
  assert css.count('@font-face') == 2
  assert css.index('font-weight: 400') < css.index('font-weight: 600')
  assert 'data:font/otf;base64,' in css
  assert fonts.font_face_css([]) == ''


def test_save_figure_output_is_a_valid_png() -> None:
  from PIL import Image

  image = Image.open(io.BytesIO(figure_bytes(_drawn(), 'png', dpi=50)))  # type: ignore[arg-type]
  assert image.format == 'PNG'
