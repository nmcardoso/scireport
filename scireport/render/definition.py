"""What templates and layouts have in common: spec ranges, YAML files, hashing, error mapping."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from scireport.bundle.textio import load_yaml
from scireport.errors import Issue, TemplateError
from scireport.spec.version import parse_version

Format = Literal['md', 'html', 'tex']
FORMATS: tuple[Format, ...] = ('md', 'html', 'tex')
"""The text formats a template or layout can support; PDF is made from HTML or TeX."""

_COMPARATOR_RE = re.compile(r'\s*(>=|<=|==|>|<)\s*(\d+\.\d+)\s*')
_OPS = {
  '>=': lambda a, b: a >= b,
  '<=': lambda a, b: a <= b,
  '==': lambda a, b: a == b,
  '>': lambda a, b: a > b,
  '<': lambda a, b: a < b,
}


def spec_range_problem(text: str) -> str | None:
  """Say why a spec range is malformed, or None when it is fine.

  A range is a comma-separated list of comparisons (``>=1.0,<2.0``), or a bare ``MAJOR.MINOR``,
  which means that minor version or any later minor of the same major (ADR-0008).

  Parameters
  ----------
  text : str
      The range from ``template.yaml`` or ``layout.yaml``.

  Returns
  -------
  str or None
      A one-line reason, or None.
  """
  try:
    _parse_range(text)
  except ValueError as exc:
    return str(exc)
  return None


def spec_in_range(text: str, version: str) -> bool:
  """Say whether a spec version satisfies a range.

  Parameters
  ----------
  text : str
      A range accepted by :func:`spec_range_problem`.
  version : str
      A spec version such as ``'1.0'``.

  Returns
  -------
  bool
      True when every comparison holds.
  """
  found = parse_version(version)
  return all(_OPS[op](found, bound) for op, bound in _parse_range(text))


def read_definition(path: Path, *, kind: str) -> dict[str, Any]:
  """Read a ``template.yaml`` or ``layout.yaml``.

  Parameters
  ----------
  path : pathlib.Path
      The file.
  kind : str
      ``'template'`` or ``'layout'``, for messages.

  Returns
  -------
  dict
      The parsed mapping.

  Raises
  ------
  TemplateError
      With code ``E703`` when the file is missing and ``E702`` when it is not a YAML mapping.
  """
  try:
    text = path.read_text(encoding='utf-8-sig')
  except FileNotFoundError:
    raise TemplateError(f'{path.parent} has no {path.name}', code='E703') from None
  except (OSError, UnicodeDecodeError) as exc:
    raise TemplateError(f'{path} cannot be read: {exc}', code='E702') from exc
  try:
    raw = load_yaml(text)
  except yaml.YAMLError as exc:
    raise TemplateError(f'{path.name} of the {kind} is not valid YAML: {exc}', code='E702') from exc
  if not isinstance(raw, dict):
    raise TemplateError(f'{path.name} of the {kind} must hold a mapping', code='E702')
  return raw


def definition_issues(exc: ValidationError, source: str) -> list[Issue]:
  """Turn a pydantic error in a definition file into ``E702`` issues.

  Parameters
  ----------
  exc : pydantic.ValidationError
      The error.
  source : str
      The file name, used as the location.

  Returns
  -------
  list of Issue
      One issue per problem, with a JSON pointer into the YAML document.
  """
  issues = []
  for err in exc.errors(include_url=False):
    pointer = ''.join(f'/{part}' for part in err['loc'])
    message = str(err['msg']).removeprefix('Value error, ')
    issues.append(Issue('E702', message, pointer=pointer, location=source))
  return issues


def require_file(root: Path, name: str, *, what: str) -> Path:
  """Return ``root / name`` or raise ``E703`` when the definition names a file that is not there.

  Parameters
  ----------
  root : pathlib.Path
      The template or layout directory.
  name : str
      A relative path from the definition file.
  what : str
      A description for the message (``'template entry'``).

  Returns
  -------
  pathlib.Path
      The existing file.

  Raises
  ------
  TemplateError
      With code ``E703``; also for a path that leaves ``root``.
  """
  path = (root / name).resolve()
  if not path.is_relative_to(root.resolve()):
    raise TemplateError(f'{what} {name!r} leaves the directory {root}', code='E703')
  if not path.is_file():
    raise TemplateError(f'{what} {name!r} is missing from {root}', code='E703')
  return path


def tree_hash(root: Path) -> str:
  """Hash the files of a template or layout directory.

  Parameters
  ----------
  root : pathlib.Path
      The directory.

  Returns
  -------
  str
      SHA-256 over the sorted relative paths and file hashes, recorded in the render manifest so
      that a changed "frozen" template or layout is noticed.
  """
  digest = hashlib.sha256()
  for path in sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts):
    digest.update(path.relative_to(root).as_posix().encode('utf-8') + b'\0')
    digest.update(hashlib.sha256(path.read_bytes()).digest())
  return digest.hexdigest()


def _parse_range(text: str) -> list[tuple[str, tuple[int, int]]]:
  """Parse a spec range into ``(operator, (major, minor))`` comparisons."""
  text = text.strip()
  if re.fullmatch(r'\d+\.\d+', text):
    major, minor = parse_version(text)
    return [('>=', (major, minor)), ('<', (major + 1, 0))]
  parts = [part for part in text.split(',') if part.strip()]
  if not parts:
    raise ValueError('the spec range is empty; write for example ">=1.0,<2.0"')
  out = []
  for part in parts:
    match = _COMPARATOR_RE.fullmatch(part)
    if match is None:
      raise ValueError(
        f'{part.strip()!r} is not a comparison such as ">=1.0"; '
        'a range is comparisons separated by commas, or a bare "1.0"'
      )
    out.append((match.group(1), parse_version(match.group(2))))
  return out
