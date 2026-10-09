"""The manifest: the blocks of ``scireport.json`` and the supported way to parse one (ADR-0002).

``scireport`` (spec version), ``meta``, ``render``, ``outline``, ``values``, ``preprocess`` and
``provenance``. Use :func:`parse_manifest` to read a manifest: it checks the spec version first,
validates the structure, aggregates every problem and then runs the cross-reference checks of
:func:`check_manifest`.
"""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import Field, JsonValue, ValidationError, model_validator
from pydantic_core import PydanticCustomError

from scireport.errors import Issue, SpecError
from scireport.spec.assets import RESOLVER_CONTEXT_KEY
from scireport.spec.keys import Key, find_prefix_conflicts
from scireport.spec.kinds import KINDS, AttachmentValue, IsoDate, Model, TableValue, Value
from scireport.spec.version import check_readable
from scireport.spec.walk import iter_assets

OutputFormat = Literal['md', 'html', 'tex', 'pdf', 'docx', 'odt', 'epub']
LayoutOption = str | int | float | bool | None

_LANGUAGE_RE = r'^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$'
_TEMPLATE_REF_RE = r'^[A-Za-z0-9][A-Za-z0-9_.-]*(@[0-9]+)?$'
_PREPROCESSOR_RE = r'^[A-Za-z_][A-Za-z0-9_.]*(:[A-Za-z_][A-Za-z0-9_.]*)?$'
_MD_FILE_RE = r'^[A-Za-z0-9][A-Za-z0-9._-]*\.md$'
_VALUE_PREFIX = '/values/'
_MAX_FOUND_CHARS = 80


class Author(Model):
  """A report author.

  Parameters
  ----------
  name : str
      Full name.
  affiliation : str or None
      Institution.
  orcid : str or None
      ORCID iD such as ``0000-0002-1825-0097``.
  """

  name: Annotated[str, Field(min_length=1)]
  affiliation: str | None = None
  orcid: Annotated[str, Field(pattern=r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$')] | None = None

  @model_validator(mode='before')
  @classmethod
  def _from_name(cls, data: Any) -> Any:
    """Accept a bare string as the author's name."""
    return {'name': data} if isinstance(data, str) else data


class Meta(Model):
  """Document metadata (the cover and running heads).

  Parameters
  ----------
  title : str
      Report title.
  subtitle : str or None
      Line under the title.
  authors : list of Author
      Authors in order; a bare string is a name.
  date : str or None
      ISO 8601 date, never filled in automatically (outputs hold no wall-clock time).
  version : str or None
      Version of the report or of the data it describes.
  pipeline : str or None
      Name of the pipeline or software that produced the content.
  footer : str or None
      Running footer text.
  abstract : str or None
      Summary, Markdown.
  keywords : list of str
      Keywords.
  language : str, default='en'
      BCP 47 language tag of the text.
  """

  title: Annotated[str, Field(min_length=1)]
  subtitle: str | None = None
  authors: list[Author] = []
  date: IsoDate | None = None
  version: str | None = None
  pipeline: str | None = None
  footer: str | None = None
  abstract: str | None = None
  keywords: list[str] = []
  language: Annotated[str, Field(pattern=_LANGUAGE_RE)] = 'en'


class Render(Model):
  """How to render: the template, the layout and the engines.

  Every field is optional; None leaves the choice to the template, the layout or the command
  line. ``template`` and ``layout`` are ``name`` or ``name@version`` (``default@1``); ``pack``
  pins the resolved version so a later render is identical (ADR-0008).

  Parameters
  ----------
  template : str or None
      Template name, for example ``generic@1``.
  layout : str or None
      Layout name, for example ``default@1``.
  formats : list of {'md', 'html', 'tex', 'pdf', 'docx', 'odt', 'epub'}
      Output formats wanted.
  pdf_engine : {'weasyprint', 'latex'} or None
      PDF engine.
  latex_engine : {'lualatex', 'xelatex', 'pdflatex'} or None
      TeX engine for ``pdf_engine: latex``.
  markup_engine : {'mistletoe', 'pandoc'} or None
      Markdown converter.
  math_renderer : {'mathtext', 'usetex'} or None
      How math becomes SVG for HTML and WeasyPrint.
  options : dict
      Layout options (paper, cover, toc, accent, chapter breaks) as scalars.
  """

  template: Annotated[str, Field(pattern=_TEMPLATE_REF_RE)] | None = None
  layout: Annotated[str, Field(pattern=_TEMPLATE_REF_RE)] | None = None
  formats: list[OutputFormat] = []
  pdf_engine: Literal['weasyprint', 'latex'] | None = None
  latex_engine: Literal['lualatex', 'xelatex', 'pdflatex'] | None = None
  markup_engine: Literal['mistletoe', 'pandoc'] | None = None
  math_renderer: Literal['mathtext', 'usetex'] | None = None
  options: dict[str, LayoutOption] = {}


class OutlineNode(Model):
  """One entry of the outline used by the built-in ``generic`` template.

  A node is either a heading (``title``, with optional ``children``) or a leaf that shows the
  value at ``key``. A bare string is a leaf.

  Parameters
  ----------
  title : str or None
      Heading text.
  key : str or None
      Key of the value to show.
  children : list of OutlineNode
      Entries under a heading.
  md_file : str or None
      For a heading: write its chapter to this separate Markdown file.
  page_break : bool or None
      Force or forbid a page break before the heading; None lets the layout decide.
  in_contents : bool, default=True
      List the heading in the table of contents.
  """

  title: Annotated[str, Field(min_length=1)] | None = None
  key: Key | None = None
  children: list[OutlineNode] = []
  md_file: Annotated[str, Field(pattern=_MD_FILE_RE)] | None = None
  page_break: bool | None = None
  in_contents: bool = True

  @model_validator(mode='before')
  @classmethod
  def _from_key(cls, data: Any) -> Any:
    """Accept a bare string as a leaf's key."""
    return {'key': data} if isinstance(data, str) else data

  @model_validator(mode='after')
  def _check(self) -> OutlineNode:
    """Require a heading or a leaf, and allow children and files only on headings."""
    if (self.title is None) == (self.key is None):
      raise PydanticCustomError('E206', 'an outline node needs exactly one of title and key')
    if self.key is not None and (self.children or self.md_file or self.page_break is not None):
      raise PydanticCustomError('E205', 'children, md_file and page_break belong to headings')
    return self


class PreprocessStep(Model):
  """One pre-processing step, declared by registered name (ADR-0006).

  Parameters
  ----------
  name : str
      Registered pre-processor name such as ``core.histogram``; ``module:func`` needs
      ``--allow-import``.
  version : int or None
      The pre-processor version the step was written for.
  id : str or None
      Identifier other steps and messages can use.
  inputs : dict
      Port name to value key.
  outputs : dict
      Port name to the value key the result is stored under.
  params : dict
      JSON parameters, validated by the pre-processor.
  """

  name: Annotated[str, Field(pattern=_PREPROCESSOR_RE)]
  version: Annotated[int, Field(ge=1)] | None = None
  id: str | None = None
  inputs: dict[str, Key] = {}
  outputs: dict[str, Key] = {}
  params: dict[str, JsonValue] = {}


class Generator(Model):
  """The program that produced the content.

  Parameters
  ----------
  name : str
      Program or package name.
  version : str
      Its version.
  """

  name: Annotated[str, Field(min_length=1)]
  version: Annotated[str, Field(min_length=1)]


class InputRef(Model):
  """One input the content was computed from.

  Parameters
  ----------
  name : str
      A label, for example a file or table name.
  sha256 : str or None
      SHA-256 of the input, when it is a file.
  uri : str or None
      Where the input came from.
  """

  name: Annotated[str, Field(min_length=1)]
  sha256: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')] | None = None
  uri: str | None = None


class Provenance(Model):
  """Where the content came from.

  Parameters
  ----------
  generator : Generator or None
      The producing program.
  writer : str or None
      ``scireport <version>`` of the writer, set by :class:`~scireport.report.Report`.
  inputs : list of InputRef
      The inputs, with hashes where they are files.
  """

  generator: Generator | None = None
  writer: str | None = None
  inputs: list[InputRef] = []


class Manifest(Model):
  """The whole manifest (``scireport.json``).

  Parameters
  ----------
  scireport : str
      Spec version, ``MAJOR.MINOR``.
  meta : Meta
      Document metadata.
  render : Render
      Rendering choices.
  outline : list of OutlineNode or None
      Outline for the ``generic`` template.
  values : dict
      Key to value; keys follow the key grammar and may not be prefixes of one another.
  preprocess : list of PreprocessStep
      Pre-processing steps.
  provenance : Provenance
      Origin of the content.
  """

  scireport: Annotated[str, Field(pattern=r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')]
  meta: Meta
  render: Render = Render()
  outline: list[OutlineNode] | None = None
  values: dict[Key, Value] = {}
  preprocess: list[PreprocessStep] = []
  provenance: Provenance = Provenance()


OutlineNode.model_rebuild()


def check_manifest(manifest: Manifest) -> list[Issue]:
  """Check what a field-by-field validation cannot: keys against each other and references.

  Parameters
  ----------
  manifest : Manifest
      A structurally valid manifest.

  Returns
  -------
  list of Issue
      Every problem found, in a stable order: ``E102`` prefix conflicts, ``E103`` dangling
      references, ``E202`` references to the wrong kind, ``E205`` repeated Markdown file names
      and ``E411`` assets declared twice with different hashes.
  """
  issues: list[Issue] = []
  values = manifest.values
  for prefix, longer in find_prefix_conflicts(values):
    issues.append(
      Issue(
        'E102',
        f'key {prefix!r} holds a value and is also the prefix of {longer!r}',
        pointer=f'{_VALUE_PREFIX}{_escape(prefix)}',
        key=prefix,
        hint='Rename one of them; templates reach values through data.a.b.c chains.',
      )
    )
  for pointer, key in _outline_keys(manifest):
    if key not in values:
      issues.append(_missing_key(key, pointer, values))
  files: dict[str, str] = {}
  for pointer, md_file in _outline_files(manifest):
    if md_file in files:
      issues.append(
        Issue('E205', f'Markdown file {md_file!r} is used twice', pointer=pointer, found=md_file)
      )
    files[md_file] = pointer
  for key, value in values.items():
    if isinstance(value, TableValue) and value.overflow_attachment is not None:
      target = value.overflow_attachment
      pointer = f'{_VALUE_PREFIX}{_escape(key)}/overflow_attachment'
      if target not in values:
        issues.append(_missing_key(target, pointer, values))
      elif not isinstance(values[target], AttachmentValue):
        issues.append(
          Issue(
            'E202',
            f'overflow_attachment must refer to an attachment, but {target!r} is a '
            f'{values[target].kind}',
            pointer=pointer,
            key=target,
            expected='attachment',
            found=values[target].kind,
          )
        )
  issues.extend(_asset_conflicts(manifest))
  return issues


def parse_manifest(raw: Any, *, resolver: Any = None) -> Manifest:
  """Parse and fully validate a manifest read from JSON or YAML.

  Parameters
  ----------
  raw : Any
      The parsed document.
  resolver : callable or None, default=None
      For hand-authored directories: a function ``path -> (sha256, bytes)`` that completes
      asset references that omit their hash. None for sealed bundles, which need every hash.

  Returns
  -------
  Manifest
      The validated manifest, with shorthand canonicalised.

  Raises
  ------
  SpecVersionError
      With code ``E501``, ``E502`` or ``E503`` when the spec version cannot be read.
  SpecError
      Carrying every issue found, when the structure or the cross-references are invalid.
  """
  check_readable(raw)
  context = {RESOLVER_CONTEXT_KEY: resolver} if resolver is not None else None
  try:
    manifest = Manifest.model_validate(raw, context=context)
  except ValidationError as exc:
    raise SpecError(issues_from_validation_error(exc, raw)) from None
  problems = check_manifest(manifest)
  if problems:
    raise SpecError(problems)
  return manifest


def manifest_to_dict(manifest: Manifest) -> dict[str, Any]:
  """Return the canonical JSON-ready form of a manifest.

  Optional fields that are None are left out; every other field is written, defaults included,
  so that a later change of a default never changes how a stored bundle reads. ``values`` is
  sorted by key, so the result does not depend on the order values were added in.

  Parameters
  ----------
  manifest : Manifest
      The manifest to serialise.

  Returns
  -------
  dict
      Ready for :func:`json.dumps`.
  """
  data: dict[str, Any] = manifest.model_dump(mode='json', exclude_none=True)
  data['values'] = {key: data['values'][key] for key in sorted(data['values'])}
  return data


def manifest_to_json(manifest: Manifest) -> str:
  """Serialise a manifest to its canonical JSON text.

  Parameters
  ----------
  manifest : Manifest
      The manifest to serialise.

  Returns
  -------
  str
      Two-space-indented JSON ending in a newline, with non-ASCII characters kept.
  """
  return (
    json.dumps(manifest_to_dict(manifest), indent=2, ensure_ascii=False, allow_nan=False) + '\n'
  )


def issues_from_validation_error(exc: ValidationError, raw: Any) -> list[Issue]:
  """Convert a pydantic error into coded issues with JSON pointers.

  Parameters
  ----------
  exc : pydantic.ValidationError
      The error from validating ``raw``.
  raw : Any
      The document that was validated; used to find the JSON pointer and the found value.

  Returns
  -------
  list of Issue
      One issue per problem. Codes come from validators that raise their own (``E101``,
      ``E301``, ...); the rest map to ``E201`` (unknown kind), ``E203`` (missing field),
      ``E204`` (unexpected field) or ``E205`` (invalid value). The alternatives of a failed
      union at one location (a number is an integer or a float) are merged into one issue.
  """
  merged: dict[tuple[str, str], Issue] = {}
  for err in exc.errors(include_url=False):
    pointer, key = _pointer(raw, err['loc'])
    code = _code_for(err['type'])
    ctx = err.get('ctx') or {}
    message = _message(err)
    expected = found = hint = None
    if code == 'E201':
      expected = ', '.join(KINDS)
      found = _short(ctx.get('tag', err.get('input')))
      hint = _did_you_mean(found, KINDS)
      message = f'unknown kind {found}'
    elif code == 'E101' and ctx.get('suggestion'):
      hint = f'Did you mean {ctx["suggestion"]!r}?'
    elif ctx.get('expected') is not None:
      expected, found = str(ctx['expected']), _short(err.get('input'))
    previous = merged.get((code, pointer))
    if previous is None:
      merged[code, pointer] = Issue(
        code, message, pointer=pointer, key=key, expected=expected, found=found, hint=hint
      )
    elif message not in previous.message:
      merged[code, pointer] = Issue(
        code,
        f'{previous.message}; {message}',
        pointer=pointer,
        key=key,
        expected=previous.expected,
        found=previous.found,
        hint=previous.hint,
      )
  return list(merged.values())


def _code_for(error_type: str) -> str:
  """Map a pydantic error type to a scireport code."""
  if re.fullmatch(r'[EW]\d{3}', error_type):
    return error_type
  if error_type == 'union_tag_invalid':
    return 'E201'
  if error_type == 'missing':
    return 'E203'
  if error_type == 'extra_forbidden':
    return 'E204'
  return 'E205'


def _message(err: Mapping[str, Any]) -> str:
  """Return the pydantic message, without the redundant ``Value error,`` prefix."""
  return str(err['msg']).removeprefix('Value error, ')


def _short(value: Any) -> str:
  """Render ``value`` for a message, truncated."""
  text = value if isinstance(value, str) else json.dumps(value, default=str)
  return text if len(text) <= _MAX_FOUND_CHARS else text[: _MAX_FOUND_CHARS - 1] + '…'


def _did_you_mean(found: str, choices: tuple[str, ...]) -> str | None:
  """Suggest the closest of ``choices`` to ``found``."""
  close = difflib.get_close_matches(found, choices, n=1)
  return f'Did you mean {close[0]!r}?' if close else None


def _escape(token: str) -> str:
  """Escape one JSON pointer token (RFC 6901)."""
  return token.replace('~', '~0').replace('/', '~1')


def _pointer(raw: Any, loc: tuple[int | str, ...]) -> tuple[str, str | None]:
  """Turn a pydantic location into a JSON pointer and the value key it falls under.

  Pydantic inserts the tag of a matched union member (``table``) and the ``[key]`` marker into
  locations; both are dropped here by walking the raw document alongside. Without a raw
  document (``raw`` is None, as in the ``Report`` builder) the location is used as it is.
  """
  tokens: list[str] = []
  node: Any = raw
  if raw is None:
    tokens = [_escape(str(part)) for part in loc if part != '[key]']
    loc = ()
  for part in loc:
    if part == '[key]':
      continue
    if isinstance(node, Mapping) and part in node:
      tokens.append(_escape(str(part)))
      node = node[part]
    elif isinstance(node, list | tuple) and isinstance(part, int) and 0 <= part < len(node):
      tokens.append(str(part))
      node = node[part]
    elif isinstance(node, Mapping) and node.get('kind') == part:
      continue
    elif isinstance(node, Mapping):
      tokens.append(_escape(str(part)))
      node = None
    else:
      break
  pointer = ''.join(f'/{token}' for token in tokens)
  key = None
  if pointer.startswith(_VALUE_PREFIX):
    key = pointer[len(_VALUE_PREFIX) :].split('/', 1)[0].replace('~1', '/').replace('~0', '~')
  return pointer, key


def _missing_key(key: str, pointer: str, values: Mapping[str, Any]) -> Issue:
  """Build the ``E103`` issue for a reference to an absent key, with a suggestion."""
  close = difflib.get_close_matches(key, list(values), n=1)
  hint = f'Did you mean {close[0]!r}?' if close else None
  return Issue('E103', f'no value with key {key!r}', pointer=pointer, key=key, hint=hint)


def _outline_keys(manifest: Manifest) -> list[tuple[str, str]]:
  """List ``(pointer, key)`` for every leaf of the outline."""
  found: list[tuple[str, str]] = []

  def walk(nodes: list[OutlineNode], base: str) -> None:
    for index, node in enumerate(nodes):
      pointer = f'{base}/{index}'
      if node.key is not None:
        found.append((f'{pointer}/key', node.key))
      walk(node.children, f'{pointer}/children')

  walk(manifest.outline or [], '/outline')
  return found


def _outline_files(manifest: Manifest) -> list[tuple[str, str]]:
  """List ``(pointer, md_file)`` for every heading with a Markdown file."""
  found: list[tuple[str, str]] = []

  def walk(nodes: list[OutlineNode], base: str) -> None:
    for index, node in enumerate(nodes):
      pointer = f'{base}/{index}'
      if node.md_file is not None:
        found.append((f'{pointer}/md_file', node.md_file))
      walk(node.children, f'{pointer}/children')

  walk(manifest.outline or [], '/outline')
  return found


def _asset_conflicts(manifest: Manifest) -> list[Issue]:
  """Find asset paths declared with more than one (sha256, bytes) pair."""
  seen: dict[str, tuple[str, int]] = {}
  issues: list[Issue] = []
  for pointer, ref in iter_assets(manifest):
    previous = seen.setdefault(ref.path, (ref.sha256, ref.bytes))
    if previous != (ref.sha256, ref.bytes):
      issues.append(
        Issue(
          'E411',
          f'asset {ref.path!r} is declared with different hashes',
          pointer=pointer,
          expected=f'sha256 {previous[0][:12]}…, {previous[1]} bytes',
          found=f'sha256 {ref.sha256[:12]}…, {ref.bytes} bytes',
        )
      )
  return issues
