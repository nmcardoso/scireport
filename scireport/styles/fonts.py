"""The vendored faces: where they live, and a probe that catches a silent fallback.

Six static OpenType faces (Inter and IBM Plex Mono subsets, licence ``fonts/OFL.txt``) ship inside
the package. The HTML writer inlines them, the LaTeX project gets a copy for ``fontspec`` and
matplotlib registers them for the figure styles. Fontconfig will silently hand back an unrelated
font for a family it does not know (``fc-match 'IBM Plex Mono'`` can return a proportional sans
face), so every stack the layouts write ends in a generic keyword and :func:`probe` checks, at run
time, that the specific families resolved to a face of the same name.

The subsets cover Basic Latin, Latin-1 and a few symbols (dashes, ``×``, ``·``, ``→``, ``−``,
``∞``).
Greek letters and ``≤ ≥ ≈ √`` are not in them: the LaTeX writer maps those to math macros and
HTML falls back to the next family of the stack.
"""

from __future__ import annotations

import base64
from pathlib import Path

from scireport.logging_utils import get_logger

log = get_logger(__name__)

FONTS_DIR = Path(__file__).resolve().parent / 'fonts'
"""Where the six vendored faces and ``OFL.txt`` are."""

FACES: dict[str, str] = {
  'Inter Regular': 'Inter-Regular.otf',
  'Inter Medium': 'Inter-Medium.otf',
  'Inter SemiBold': 'Inter-SemiBold.otf',
  'Inter Italic': 'Inter-Italic.otf',
  'IBM Plex Mono Regular': 'IBMPlexMono-Regular.otf',
  'IBM Plex Mono Medium': 'IBMPlexMono-Medium.otf',
}
"""Face label to file name inside :data:`FONTS_DIR`. The label is documentation only."""

CSS_FACES: tuple[tuple[str, str, int, str], ...] = (
  ('Inter', 'Inter-Regular.otf', 400, 'normal'),
  ('Inter', 'Inter-Medium.otf', 500, 'normal'),
  ('Inter', 'Inter-SemiBold.otf', 600, 'normal'),
  ('Inter', 'Inter-Italic.otf', 400, 'italic'),
  ('IBM Plex Mono', 'IBMPlexMono-Regular.otf', 400, 'normal'),
  ('IBM Plex Mono', 'IBMPlexMono-Medium.otf', 500, 'normal'),
)
"""``@font-face`` rows: family, file, weight and style."""

_PROBED_FAMILIES = ('Inter', 'IBM Plex Mono')
_state = {'registered': False}


def face_path(name: str) -> Path:
  """Return the path of a vendored face.

  Parameters
  ----------
  name : str
      A file name such as ``'Inter-Regular.otf'``.

  Returns
  -------
  pathlib.Path
      The file inside the package.

  Raises
  ------
  FileNotFoundError
      When the package does not ship a face of that name.
  """
  path = FONTS_DIR / name
  if not path.is_file():
    raise FileNotFoundError(f'the package does not ship the font {name!r}')
  return path


def font_face_css(files: list[str]) -> str:
  """Write the ``@font-face`` rules of the listed faces, with each font inlined as a ``data:`` URI.

  A self-contained HTML file and the PDF made from it need no font on the machine that reads
  them. The rules come out in the order of :data:`CSS_FACES`, whatever the order of ``files``.

  Parameters
  ----------
  files : list of str
      File names of vendored faces, for example ``['Inter-Regular.otf']``. A name that is not a
      known face is ignored: it can only be a font the layout loads itself.

  Returns
  -------
  str
      CSS text, or an empty string when ``files`` names no known face.
  """
  wanted = set(files)
  rules = []
  for family, name, weight, style in CSS_FACES:
    if name not in wanted:
      continue
    data = base64.b64encode(face_path(name).read_bytes()).decode('ascii')
    rules.append(
      f"@font-face {{ font-family: '{family}'; font-weight: {weight}; font-style: {style}; "
      f"src: url('data:font/otf;base64,{data}') format('opentype'); }}"
    )
  return '\n'.join(rules)


def register() -> None:
  """Register every vendored face with matplotlib's font manager.

  ``addfont`` only adds to the manager's list and never writes to disk, so it is safe to call
  from any process. Registering twice would add duplicates, so a second call does nothing.
  """
  if _state['registered']:
    return
  import matplotlib.font_manager as fm

  for name in FACES.values():
    fm.fontManager.addfont(str(face_path(name)))
  _state['registered'] = True


def probe() -> list[str]:
  """Check that the report's font families resolve to a real match, not a substitute.

  Registers the faces first, because a family cannot resolve to a file matplotlib does not know
  about. The check is the resolved file's own family name, not whether it is the vendored file: a
  machine that has the full family installed may resolve to that copy, which is fine. What it
  guards against is the manager returning an unrelated font under the requested name.

  Returns
  -------
  list of str
      The families that did not resolve to a face of the same name, each logged as a warning.
      Empty when both are found.
  """
  import matplotlib.font_manager as fm

  register()
  fallbacks: list[str] = []
  for family in _PROBED_FAMILIES:
    try:
      resolved = fm.findfont(fm.FontProperties(family=family), fallback_to_default=False)
      resolved_family = fm.get_font(resolved).family_name
    except (ValueError, OSError, RuntimeError):
      log.warning('font family %r did not resolve to any installed face', family)
      fallbacks.append(family)
      continue
    if resolved_family != family:
      log.warning(
        'font family %r resolved to %s (%s) instead of a matching face',
        family,
        resolved,
        resolved_family,
      )
      fallbacks.append(family)
  return fallbacks
