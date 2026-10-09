"""Template lint: walk the Jinja syntax tree for the keys a template reads (ADR-0005).

``data.crossmatch.n_pairs``, ``data['crossmatch']['n_pairs']`` and ``v('crossmatch.n_pairs')`` name
a key statically, so a typo is found before rendering. A key built at run time
(``v('qa.' ~ name)``) cannot be checked in advance; it gets warning ``W403`` and is checked while
rendering instead, through the usage tracker.
"""

from __future__ import annotations

import difflib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from jinja2 import TemplateSyntaxError, nodes

from scireport.errors import Issue
from scireport.render.environment import EnvKind, make_environment
from scireport.render.locate import syntax_location

KEY_FUNCTIONS = frozenset({'v', 'has', 'peek'})
"""Template functions whose first argument is a value key."""


@dataclass(frozen=True)
class KeyUse:
  """One place where a template reads a key.

  Parameters
  ----------
  segments : tuple of str
      The dotted path as segments; for ``v('a.b')`` the key split at the dots. A chain such as
      ``data.a.b.value`` is the path it walks, and may run past the key into attributes.
  location : str
      ``file:line`` in the template.
  dynamic : bool, default=False
      The path is only partly known (a computed segment or key): ``segments`` is the known part.
  """

  segments: tuple[str, ...]
  location: str
  dynamic: bool = False


@dataclass(frozen=True)
class LintResult:
  """What linting a set of template files found.

  Parameters
  ----------
  uses : tuple of KeyUse
      Every static or partly static key use.
  issues : tuple of Issue
      Syntax errors (``E704``), missing included files (``E703``) and ``W403`` notices.
  """

  uses: tuple[KeyUse, ...]
  issues: tuple[Issue, ...]


def lint_files(root: Path, entries: list[str], kind: EnvKind) -> LintResult:
  """Parse template files and everything they include, import or extend.

  Parameters
  ----------
  root : pathlib.Path
      The template or layout directory.
  entries : list of str
      File names relative to ``root`` to start from.
  kind : {'neutral', 'md', 'html', 'tex'}
      Which delimiters the files use.

  Returns
  -------
  LintResult
      The key uses and the problems found. Parsing stops at a file with a syntax error, but the
      other files are still read.
  """
  env = make_environment(kind)
  uses: list[KeyUse] = []
  issues: list[Issue] = []
  seen: set[str] = set()
  pending = list(entries)
  while pending:
    name = pending.pop(0)
    if name in seen:
      continue
    seen.add(name)
    path = root / name
    if not path.is_file():
      issues.append(
        Issue('E703', f'template file {name!r} is missing from {root.name}', location=name)
      )
      continue
    try:
      tree = env.parse(path.read_text(encoding='utf-8'), name=name, filename=str(path))
    except TemplateSyntaxError as exc:
      issues.append(Issue('E704', exc.message or str(exc), location=syntax_location(exc, [root])))
      continue
    for node in tree.find_all((nodes.Include, nodes.Import, nodes.FromImport, nodes.Extends)):
      target = getattr(node, 'template', None)
      if isinstance(target, nodes.Const) and isinstance(target.value, str):
        pending.append(target.value)
    for use, issue in _walk(tree, name):
      if use is not None:
        uses.append(use)
      if issue is not None:
        issues.append(issue)
  return LintResult(tuple(uses), tuple(issues))


def macro_names(root: Path, name: str, kind: EnvKind) -> set[str] | None:
  """List the macros a Jinja file defines at its top level.

  Parameters
  ----------
  root : pathlib.Path
      The layout directory.
  name : str
      The file, relative to ``root``.
  kind : {'neutral', 'md', 'html', 'tex'}
      Which delimiters the file uses.

  Returns
  -------
  set of str or None
      The macro names, or None when the file cannot be parsed (the syntax error is reported by
      :func:`lint_files`).
  """
  env = make_environment(kind)
  path = root / name
  try:
    tree = env.parse(path.read_text(encoding='utf-8'), name=name, filename=str(path))
  except (TemplateSyntaxError, OSError):
    return None
  return {node.name for node in tree.body if isinstance(node, nodes.Macro)}


def suggest(key: str, candidates: list[str]) -> str | None:
  """Return a "did you mean" hint for a key, or None when nothing is close."""
  close = difflib.get_close_matches(key, candidates, n=1)
  return f'Did you mean {close[0]!r}?' if close else None


def _walk(tree: nodes.Template, filename: str) -> Iterator[tuple[KeyUse | None, Issue | None]]:
  """Yield the key uses and ``W403`` notices of one parsed file."""
  stack: list[nodes.Node] = [tree]
  while stack:
    node = stack.pop()
    where = f'{filename}:{node.lineno}'
    if isinstance(node, nodes.Getattr | nodes.Getitem):
      parsed = _chain(node)
      if parsed is not None:
        segments, dynamic_args = parsed
        if segments:
          yield KeyUse(tuple(segments), where, dynamic=len(dynamic_args) > 0), None
        if dynamic_args:
          yield None, _dynamic(where)
        stack.extend(dynamic_args)
        continue
    elif (
      isinstance(node, nodes.Call)
      and isinstance(node.node, nodes.Name)
      and node.node.name in KEY_FUNCTIONS
      and node.args
    ):
      first = node.args[0]
      if isinstance(first, nodes.Const) and isinstance(first.value, str):
        yield KeyUse(tuple(first.value.split('.')), where), None
      else:
        yield None, _dynamic(where)
        stack.append(first)
      stack.extend(node.args[1:])
      continue
    stack.extend(reversed(list(node.iter_child_nodes())))


def _chain(node: nodes.Node) -> tuple[list[str], list[nodes.Node]] | None:
  """Read ``data.a.b`` / ``data['a']['b']`` as segments.

  Returns None when the chain is not rooted at the name ``data``. Otherwise returns the static
  prefix of the path and the expressions of any computed segment (to be walked separately).
  """
  parts: list[str | None] = []
  dynamic: list[nodes.Node] = []
  current: nodes.Node = node
  while True:
    if isinstance(current, nodes.Getattr):
      parts.append(current.attr)
      current = current.node
    elif isinstance(current, nodes.Getitem):
      arg = current.arg
      if isinstance(arg, nodes.Const) and isinstance(arg.value, str):
        parts.append(arg.value)
      else:
        parts.append(None)
        dynamic.append(arg)
      current = current.node
    elif isinstance(current, nodes.Name) and current.name == 'data':
      break
    else:
      return None
  parts.reverse()
  static: list[str] = []
  for part in parts:
    if part is None:
      break
    static.extend(part.split('.'))
  return static, dynamic


def _dynamic(where: str) -> Issue:
  """Build the ``W403`` notice for a key computed at render time."""
  return Issue(
    'W403',
    'this key is computed at render time and cannot be checked in advance',
    location=where,
    hint='It is checked while rendering; a missing key is reported then.',
  )
