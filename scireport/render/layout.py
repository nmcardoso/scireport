"""The layout model: the look of a report, per output format (ADR-0003).

A layout is a directory with ``layout.yaml``. For each format it supports it names a ``document``
skeleton that wraps the rendered body, a ``components`` file with one macro per component
(``chapter``, ``table``, ``figure`` ...), and the stylesheets or LaTeX style file that go with
them. It also declares the options a user may set (paper size, cover, table of contents, accent
colour ...) with their defaults. Fonts, the matplotlib style and the palette are declared here
too; the PDF engines of phase S3 use them.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError

from scireport.errors import Issue, TemplateError
from scireport.render.definition import (
  Format,
  definition_issues,
  read_definition,
  require_file,
  spec_range_problem,
  tree_hash,
)
from scireport.spec.kinds import Model

LAYOUT_FILE = 'layout.yaml'
OptionValue = bool | int | float | str | None
_NAME_RE = r'^[A-Za-z0-9][A-Za-z0-9_-]*$'
_TRUE = frozenset({'1', 'true', 'yes', 'on'})
_FALSE = frozenset({'0', 'false', 'no', 'off'})


class LayoutOption(Model):
  """An option the layout lets the user set.

  Parameters
  ----------
  name : str
      Option name, as used in ``render.options`` and ``--option name=value``.
  type : {'bool', 'str', 'int', 'float'}
      The value type.
  default : bool or int or float or str or None
      The value when the user gives none.
  choices : list or None
      The allowed values, when there is a closed set.
  pattern : str or None
      For a ``str`` option: a regular expression the whole value must match. Options end up in
      CSS and LaTeX, so a colour is constrained to ``#rrggbb`` rather than trusted.
  description : str, default=''
      What the option does.
  """

  name: Annotated[str, Field(pattern=r'^[a-z][a-z0-9_]*$')]
  type: Literal['bool', 'str', 'int', 'float']
  default: OptionValue = None
  choices: list[bool | int | float | str] | None = None
  pattern: str | None = None
  description: str = ''

  @model_validator(mode='after')
  def _check(self) -> LayoutOption:
    """Require a default and choices of the declared type."""
    if self.default is not None and not _has_type(self.default, self.type):
      raise PydanticCustomError(
        'E702', 'default of option {name} is not a {type}', {'name': self.name, 'type': self.type}
      )
    for choice in self.choices or ():
      if not _has_type(choice, self.type):
        raise PydanticCustomError(
          'E702',
          'choice {choice} of option {name} is not a {type}',
          {'choice': repr(choice), 'name': self.name, 'type': self.type},
        )
    if self.choices is not None and self.default is not None and self.default not in self.choices:
      raise PydanticCustomError(
        'E702', 'default of option {name} is not among its choices', {'name': self.name}
      )
    if self.pattern is not None:
      try:
        compiled = re.compile(self.pattern)
      except re.error as exc:
        raise PydanticCustomError(
          'E702',
          'pattern of option {name} is not a regular expression: {why}',
          {'name': self.name, 'why': str(exc)},
        ) from None
      if isinstance(self.default, str) and compiled.fullmatch(self.default) is None:
        raise PydanticCustomError(
          'E702', 'default of option {name} does not match its pattern', {'name': self.name}
        )
    return self


class FormatFiles(Model):
  """The files a layout provides for one format.

  Parameters
  ----------
  document : str
      The skeleton that wraps the body (a Jinja file).
  components : str
      The file with one macro per component (a Jinja file).
  css : list of str
      Stylesheets inlined into the HTML document, in order.
  style : str or None
      For ``tex``: the LaTeX style file written next to ``report.tex``.
  assets : list of str
      Other files copied next to the output (fonts, logos).
  """

  document: str
  components: str
  css: list[str] = []
  style: str | None = None
  assets: list[str] = []


class LayoutDef(Model):
  """The contents of ``layout.yaml``.

  Parameters
  ----------
  spec : str
      Compatible data-file spec versions.
  name : str
      Layout name.
  version : int
      Layout version; any visual change is a new version (ADR-0008).
  title : str, default=''
      One-line title.
  description : str, default=''
      What the layout looks like.
  formats : dict
      Format to :class:`FormatFiles`.
  options : list of LayoutOption
      The options and their defaults.
  pdf_engines : list of {'weasyprint', 'latex'}
      PDF engines the layout supports.
  mplstyle : str or None
      Matplotlib style file for figures drawn in this look.
  palette : str or None
      Palette file shared by the stylesheet, the matplotlib style and the LaTeX colours.
  fonts : list of str
      Font files the layout ships.
  """

  spec: str
  name: Annotated[str, Field(pattern=_NAME_RE)]
  version: Annotated[int, Field(ge=1)]
  title: str = ''
  description: str = ''
  formats: Annotated[dict[Format, FormatFiles], Field(min_length=1)]
  options: list[LayoutOption] = []
  pdf_engines: list[Literal['weasyprint', 'latex']] = []
  mplstyle: str | None = None
  palette: str | None = None
  fonts: list[str] = []

  @field_validator('spec')
  @classmethod
  def _spec(cls, value: str) -> str:
    """Require a well-formed range."""
    problem = spec_range_problem(value)
    if problem:
      raise PydanticCustomError('E702', '{problem}', {'problem': problem})
    return value

  @model_validator(mode='after')
  def _unique_options(self) -> LayoutDef:
    """Reject two options with one name."""
    names = [option.name for option in self.options]
    if len(set(names)) != len(names):
      raise PydanticCustomError('E702', 'option names must be unique')
    return self


@dataclass(frozen=True)
class Layout:
  """A loaded layout: its definition and the directory its files are in.

  Parameters
  ----------
  definition : LayoutDef
      The parsed ``layout.yaml``.
  root : pathlib.Path
      The layout directory.
  origin : str, default='path'
      Where it came from: ``builtin``, ``path`` or ``entry-point``.
  """

  definition: LayoutDef
  root: Path
  origin: str = 'path'

  @property
  def name(self) -> str:
    """The layout name."""
    return self.definition.name

  @property
  def version(self) -> int:
    """The layout version."""
    return self.definition.version

  @property
  def ref(self) -> str:
    """``name@version``, the form stored in a bundle."""
    return f'{self.name}@{self.version}'

  @cached_property
  def sha256(self) -> str:
    """Hash of the layout directory, recorded in the render manifest."""
    return tree_hash(self.root)

  def files(self, fmt: Format) -> FormatFiles:
    """Return the files for one format.

    Parameters
    ----------
    fmt : {'md', 'html', 'tex'}
        The output format.

    Returns
    -------
    FormatFiles
        The document, components and style files.

    Raises
    ------
    TemplateError
        With code ``E706`` when the layout does not support ``fmt``.
    """
    try:
      return self.definition.formats[fmt]
    except KeyError:
      supported = ', '.join(sorted(self.definition.formats))
      raise TemplateError(
        f'layout {self.ref} does not support the {fmt} format (it supports {supported})',
        code='E706',
      ) from None

  def read(self, name: str) -> str:
    r"""Read a text file of the layout (a stylesheet or the LaTeX style file).

    Parameters
    ----------
    name : str
        A path relative to the layout directory.

    Returns
    -------
    str
        The file's text, with ``\n`` line endings.
    """
    return (self.root / name).read_text(encoding='utf-8').replace('\r\n', '\n')

  def jinja_files(self) -> list[str]:
    """List the Jinja files (documents and component files) of every format."""
    names = []
    for files in self.definition.formats.values():
      names.extend([files.document, files.components])
    return sorted(set(names))

  def resolve_options(self, given: dict[str, Any] | None = None) -> dict[str, OptionValue]:
    """Merge the options a user gave with the layout's defaults.

    Strings from the command line are converted to the declared type.

    Parameters
    ----------
    given : dict or None, default=None
        Option name to value. A value of None means "use the default", as in a bundle's
        ``render.options``.

    Returns
    -------
    dict
        Every option of the layout with its final value, in declaration order.

    Raises
    ------
    TemplateError
        With code ``E806`` (carrying every problem) for an unknown option, a value of the wrong
        type or a value outside the choices.
    """
    given = {name: value for name, value in (given or {}).items() if value is not None}
    issues: list[Issue] = []
    resolved: dict[str, OptionValue] = {}
    declared = {option.name: option for option in self.definition.options}
    for option in self.definition.options:
      if option.name not in given:
        resolved[option.name] = option.default
        continue
      try:
        value = _coerce(given.pop(option.name), option)
      except ValueError as exc:
        issues.append(Issue('E806', str(exc), key=option.name, location=self.ref))
        continue
      resolved[option.name] = value
    for name in given:
      close = difflib.get_close_matches(name, list(declared), n=1)
      known = ', '.join(declared) or 'none'
      issues.append(
        Issue(
          'E806',
          f'layout {self.ref} has no option {name!r} (it has: {known})',
          key=name,
          hint=f'Did you mean {close[0]!r}?' if close else None,
        )
      )
    if issues:
      raise TemplateError(issues[0].describe(), code='E806', issues=issues)
    return resolved


def load_layout_dir(root: Path, *, origin: str = 'path') -> Layout:
  """Load a layout from a directory.

  Parameters
  ----------
  root : pathlib.Path
      A directory with ``layout.yaml``.
  origin : str, default='path'
      Where it came from, for listings.

  Returns
  -------
  Layout
      The loaded layout.

  Raises
  ------
  TemplateError
      With ``E703`` when ``layout.yaml`` or a file it names is missing, and ``E702`` (carrying
      every problem) when the definition is invalid.
  """
  raw = read_definition(root / LAYOUT_FILE, kind='layout')
  try:
    definition = LayoutDef.model_validate(raw)
  except ValidationError as exc:
    issues = definition_issues(exc, f'{root.name}/{LAYOUT_FILE}')
    raise TemplateError(
      f'{root / LAYOUT_FILE} is invalid: {issues[0].describe()}', code='E702', issues=issues
    ) from None
  for files in definition.formats.values():
    for name in (files.document, files.components, *files.css, *files.assets):
      require_file(root, name, what='layout file')
    if files.style:
      require_file(root, files.style, what='layout style file')
  return Layout(definition, root, origin)


def _has_type(value: object, kind: str) -> bool:
  """Say whether a Python value matches a declared option type."""
  if kind == 'bool':
    return isinstance(value, bool)
  if kind == 'int':
    return isinstance(value, int) and not isinstance(value, bool)
  if kind == 'float':
    return isinstance(value, int | float) and not isinstance(value, bool)
  return isinstance(value, str)


def _coerce(value: object, option: LayoutOption) -> OptionValue:
  """Convert a user value to the option's type and check the choices."""
  if isinstance(value, str) and option.type != 'str':
    text = value.strip().lower()
    try:
      if option.type == 'bool':
        if text not in _TRUE | _FALSE:
          raise ValueError
        value = text in _TRUE
      elif option.type == 'int':
        value = int(text)
      else:
        value = float(text)
    except ValueError:
      raise ValueError(f'option {option.name} expects a {option.type}, got {value!r}') from None
  if not _has_type(value, option.type):
    raise ValueError(f'option {option.name} expects a {option.type}, got {value!r}')
  if option.type == 'float' and isinstance(value, int):
    value = float(value)
  if option.choices is not None and value not in option.choices:
    raise ValueError(
      f'option {option.name} must be one of {", ".join(map(str, option.choices))}, got {value!r}'
    )
  if option.pattern is not None and re.fullmatch(option.pattern, str(value)) is None:
    raise ValueError(f'option {option.name} must match {option.pattern}, got {value!r}')
  assert isinstance(value, bool | int | float | str)
  return value
