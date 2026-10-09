"""The template model: structure and the contract with the data file (ADR-0003).

A template is a directory with ``template.yaml`` and ``report.j2``. ``template.yaml`` names the
template, says which output formats and spec versions it supports, and lists the ``fields`` it
reads: key patterns with the kind each must have, whether it is required, the columns of a table
and the renditions of a figure. The validation engine checks a bundle against these fields before
anything is rendered. ``report.j2`` is the format-neutral body; ``report.md.j2``, ``report.html.j2``
and ``report.tex.j2`` next to it override the body for one format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError

from scireport.errors import TemplateError
from scireport.render.definition import (
  FORMATS,
  Format,
  definition_issues,
  read_definition,
  require_file,
  spec_range_problem,
  tree_hash,
)
from scireport.spec.kinds import KINDS, FigureFormat, Model

Dtype = Literal['any', 'int', 'float', 'number', 'string', 'bool', 'date', 'timestamp']
"""Abstract column types a template can ask for; ``number`` is an integer or a float."""

TEMPLATE_FILE = 'template.yaml'
_PATTERN_SEGMENT = r'(?:[a-z0-9_-]+|\*\*?)'
_PATTERN_RE = re.compile(rf'{_PATTERN_SEGMENT}(?:\.{_PATTERN_SEGMENT})*')
_NAME_RE = r'^[A-Za-z0-9][A-Za-z0-9_-]*$'


class ColumnSpec(Model):
  """A column a table field must have.

  Parameters
  ----------
  name : str
      Column name in the data.
  dtype : {'any', 'int', 'float', 'number', 'string', 'bool', 'date', 'timestamp'}, default='any'
      The type the column must have.
  required : bool, default=True
      Whether a table without the column is an error.
  """

  name: Annotated[str, Field(min_length=1)]
  dtype: Dtype = 'any'
  required: bool = True


class FieldSpec(Model):
  """One value (or family of values) the template reads.

  Parameters
  ----------
  key : str
      A value key, or a pattern in which ``*`` stands for one key segment and ``**`` for one or
      more (``qa.*.summary``).
  kind : str or list of str
      The kind the value must have, or the kinds it may have.
  required : bool, default=True
      Whether the bundle must have at least one value matching ``key``.
  description : str, default=''
      What the template uses it for; shown by ``describe_template`` and in error hints.
  columns : list of ColumnSpec
      For a table: the columns it must have.
  renditions : list of {'png', 'pdf', 'svg'}
      For a figure: the formats it must carry.
  """

  key: str
  kind: str | list[str]
  required: bool = True
  description: str = ''
  columns: list[ColumnSpec] = []
  renditions: list[FigureFormat] = []

  @field_validator('key')
  @classmethod
  def _key(cls, value: str) -> str:
    """Require a key or a key pattern."""
    if _PATTERN_RE.fullmatch(value) is None:
      raise PydanticCustomError(
        'E702',
        'field key {key} must be dotted segments of [a-z0-9_-]+, with * or ** as wildcards',
        {'key': repr(value)},
      )
    return value

  @model_validator(mode='after')
  def _check(self) -> FieldSpec:
    """Check the kinds, and that columns and renditions belong to a table or a figure."""
    unknown = [kind for kind in self.kinds if kind not in KINDS]
    if unknown:
      raise PydanticCustomError(
        'E702',
        'unknown kind {kind}; expected one of {kinds}',
        {'kind': unknown[0], 'kinds': ', '.join(KINDS)},
      )
    if self.columns and 'table' not in self.kinds:
      raise PydanticCustomError('E702', 'columns only make sense for a table field')
    if self.renditions and 'figure' not in self.kinds:
      raise PydanticCustomError('E702', 'renditions only make sense for a figure field')
    return self

  @property
  def kinds(self) -> list[str]:
    """The allowed kinds as a list."""
    return [self.kind] if isinstance(self.kind, str) else list(self.kind)

  @property
  def is_pattern(self) -> bool:
    """Whether ``key`` contains a wildcard."""
    return '*' in self.key

  def matches(self, key: str) -> bool:
    """Say whether a value key matches this field.

    Parameters
    ----------
    key : str
        A value key.

    Returns
    -------
    bool
        True for the exact key, or for a key the pattern covers (``*`` is one segment).
    """
    if not self.is_pattern:
      return key == self.key
    pattern = self.key.split('.')
    parts = key.split('.')
    if '**' not in pattern:
      return len(pattern) == len(parts) and all(
        pat in ('*', part) for pat, part in zip(pattern, parts, strict=True)
      )
    regex = '[.]'.join(
      '.+' if p == '**' else '[^.]+' if p == '*' else re.escape(p) for p in pattern
    )
    return re.fullmatch(regex, key) is not None


class TemplateDef(Model):
  """The contents of ``template.yaml``.

  Parameters
  ----------
  spec : str
      Compatible data-file spec versions, for example ``>=1.0,<2.0`` or a bare ``1.0``.
  name : str
      Template name.
  version : int
      Template version; a visual or structural change is a new version (ADR-0008).
  title : str, default=''
      One-line title.
  description : str, default=''
      What the template produces.
  formats : list of {'md', 'html', 'tex'}
      Output formats it supports.
  entry : str, default='report.j2'
      The format-neutral body.
  dynamic_keys : bool, default=False
      The template reads keys it computes while rendering (it walks the outline or loops over
      ``keys(...)``), so warning ``W403`` is not reported for it.
  fields : list of FieldSpec
      The values it reads.
  """

  spec: str
  name: Annotated[str, Field(pattern=_NAME_RE)]
  version: Annotated[int, Field(ge=1)]
  title: str = ''
  description: str = ''
  formats: Annotated[list[Format], Field(min_length=1)] = list(FORMATS)
  entry: str = 'report.j2'
  dynamic_keys: bool = False
  fields: list[FieldSpec] = []

  @field_validator('spec')
  @classmethod
  def _spec(cls, value: str) -> str:
    """Require a well-formed range."""
    problem = spec_range_problem(value)
    if problem:
      raise PydanticCustomError('E702', '{problem}', {'problem': problem})
    return value


@dataclass(frozen=True)
class Template:
  """A loaded template: its definition and the directory its files are in.

  Parameters
  ----------
  definition : TemplateDef
      The parsed ``template.yaml``.
  root : pathlib.Path
      The template directory.
  origin : str, default='path'
      Where it came from: ``builtin``, ``path`` or ``entry-point``.
  """

  definition: TemplateDef
  root: Path
  origin: str = 'path'

  @property
  def name(self) -> str:
    """The template name."""
    return self.definition.name

  @property
  def version(self) -> int:
    """The template version."""
    return self.definition.version

  @property
  def ref(self) -> str:
    """``name@version``, the form stored in a bundle."""
    return f'{self.name}@{self.version}'

  @cached_property
  def sha256(self) -> str:
    """Hash of the template directory, recorded in the render manifest."""
    return tree_hash(self.root)

  def entry_for(self, fmt: Format) -> str:
    """Return the file that renders the body for one format.

    Parameters
    ----------
    fmt : {'md', 'html', 'tex'}
        The output format.

    Returns
    -------
    str
        ``report.<fmt>.j2`` when the template has that override, else the neutral entry.
    """
    override = f'report.{fmt}.j2'
    return override if (self.root / override).is_file() else self.definition.entry

  def is_neutral(self, fmt: Format) -> bool:
    """Say whether the body for ``fmt`` is the format-neutral one (standard delimiters)."""
    return self.entry_for(fmt) == self.definition.entry

  def template_files(self) -> list[str]:
    """List the Jinja files of the template, entry and overrides, as relative paths."""
    names = {self.definition.entry}
    names.update(
      f'report.{fmt}.j2' for fmt in FORMATS if (self.root / f'report.{fmt}.j2').is_file()
    )
    return sorted(names)


def load_template_dir(root: Path, *, origin: str = 'path') -> Template:
  """Load a template from a directory.

  Parameters
  ----------
  root : pathlib.Path
      A directory with ``template.yaml``.
  origin : str, default='path'
      Where it came from, for listings.

  Returns
  -------
  Template
      The loaded template.

  Raises
  ------
  TemplateError
      With ``E703`` when ``template.yaml`` or the entry file is missing, and ``E702`` (carrying
      every problem) when the definition is invalid.
  """
  raw = read_definition(root / TEMPLATE_FILE, kind='template')
  try:
    definition = TemplateDef.model_validate(raw)
  except ValidationError as exc:
    issues = definition_issues(exc, f'{root.name}/{TEMPLATE_FILE}')
    raise TemplateError(
      f'{root / TEMPLATE_FILE} is invalid: {issues[0].describe()}', code='E702', issues=issues
    ) from None
  require_file(root, definition.entry, what='template entry')
  return Template(definition, root, origin)


def field_issue_hint(spec: FieldSpec) -> str:
  """Describe a field for an error hint: its kind, and its purpose when it has one."""
  text = f'a {" or ".join(spec.kinds)} value'
  return f'{text} ({spec.description})' if spec.description else text
