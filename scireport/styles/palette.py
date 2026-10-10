r"""The palette of a layout: colours, roles, fonts, spacing and page geometry (ADR-0007).

``palette.yaml`` in the layout directory is the one place where a colour is a constant. The
stylesheet (``tokens.css``), the LaTeX style (``\definecolor``) and the matplotlib style repeat
the hex values by hand, so that a reviewer can read them in a diff; a test parses all of them and
fails when one drifts from the palette.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError

from scireport.errors import Issue, TemplateError
from scireport.spec.kinds import Model

_NAME = r'^[a-z][a-z0-9-]*$'
MM_PER_INCH = 25.4

HexColor = Annotated[str, Field(pattern=r'^#[0-9a-f]{6}$')]


class Page(Model):
  """The page the layout prints on, in millimetres (A4 portrait).

  Parameters
  ----------
  width_mm, height_mm : float
      Paper size.
  margin_x_mm, margin_y_mm : float
      Left and right, top and bottom margins; the frame is what remains.
  """

  width_mm: float = 210.0
  height_mm: float = 297.0
  margin_x_mm: float = 9.0
  margin_y_mm: float = 18.0

  @property
  def frame_width_in(self) -> float:
    """Usable width in inches: what the width of a figure is a fraction of."""
    return (self.width_mm - 2 * self.margin_x_mm) / MM_PER_INCH

  @property
  def frame_height_in(self) -> float:
    """Usable height in inches: a backstop that no figure exceeds."""
    return (self.height_mm - 2 * self.margin_y_mm) / MM_PER_INCH


class Fonts(Model):
  """Font stacks, the vendored family first and a generic keyword last.

  Parameters
  ----------
  sans, mono : list of str
      Family names in order of preference.
  """

  sans: Annotated[list[str], Field(min_length=1)]
  mono: Annotated[list[str], Field(min_length=1)]


class Cmaps(Model):
  """The colour maps of the look.

  Parameters
  ----------
  sequential, diverging : str
      matplotlib colour map names.
  """

  sequential: str
  diverging: str


class Palette(Model):
  """A resolved ``palette.yaml``.

  Parameters
  ----------
  name : str
      The layout the palette belongs to.
  colors : dict
      Token name (``navy-deep``) to ``#rrggbb``, lower case. These are the CSS custom properties.
  role : dict
      Colour with a fixed meaning in a chart (``failed``, ``success`` ...) to a colour token.
  status : dict
      Level of the status component to a colour token.
  cycle : list of str
      Colour tokens that tell series apart, in order.
  cmap : Cmaps
      Sequential and diverging colour maps.
  fonts : Fonts
      Font stacks.
  spacing : list of int
      The spacing scale in points.
  type_scale : dict
      Point size per typographic rung.
  body_line_height, heading_line_height : float
      Line heights as multiples of the font size.
  page : Page
      Page geometry, A4 unless the file says otherwise.
  """

  name: Annotated[str, Field(pattern=_NAME)]
  colors: Annotated[dict[str, HexColor], Field(min_length=1)]
  role: dict[str, str]
  status: dict[str, str]
  cycle: Annotated[list[str], Field(min_length=1)]
  cmap: Cmaps
  fonts: Fonts
  spacing: list[int]
  type_scale: dict[str, float]
  body_line_height: float
  heading_line_height: float
  page: Page = Page()

  @model_validator(mode='after')
  def _tokens_exist(self) -> Palette:
    """Require every colour named by a role, a status level or the cycle to be defined."""
    named = [*self.role.values(), *self.status.values(), *self.cycle]
    unknown = sorted({token for token in named if token not in self.colors})
    if unknown:
      raise PydanticCustomError(
        'E702', 'palette.yaml names colours that are not defined: {names}', {'names': unknown}
      )
    return self

  def hex(self, token: str) -> str:
    """Return the ``#rrggbb`` value of a colour token.

    Parameters
    ----------
    token : str
        A key of :attr:`colors`.

    Returns
    -------
    str
        The colour.

    Raises
    ------
    KeyError
        When the palette has no such token.
    """
    return self.colors[token]

  @property
  def role_colors(self) -> dict[str, str]:
    """The chart roles with their colours resolved to ``#rrggbb``."""
    return {role: self.colors[token] for role, token in self.role.items()}

  @property
  def status_colors(self) -> dict[str, str]:
    """The status levels with their colours resolved to ``#rrggbb``."""
    return {level: self.colors[token] for level, token in self.status.items()}

  @property
  def cycle_colors(self) -> list[str]:
    """The property cycle with its colours resolved to ``#rrggbb``."""
    return [self.colors[token] for token in self.cycle]


def load_palette(path: Path) -> Palette:
  """Read and validate a ``palette.yaml``.

  Parameters
  ----------
  path : pathlib.Path
      The file.

  Returns
  -------
  Palette
      The palette.

  Raises
  ------
  TemplateError
      With ``E703`` when the file is missing and ``E702`` (carrying every problem) when it is
      invalid.
  """
  from scireport.render.definition import definition_issues, read_definition

  raw: dict[str, Any] = read_definition(path, kind='palette')
  raw = {**raw, 'colors': {k: str(v).lower() for k, v in (raw.get('colors') or {}).items()}}
  try:
    return Palette.model_validate(raw)
  except ValidationError as exc:
    issues: list[Issue] = definition_issues(exc, path.name)
    raise TemplateError(
      f'{path} is invalid: {issues[0].describe()}', code='E702', issues=issues
    ) from None
