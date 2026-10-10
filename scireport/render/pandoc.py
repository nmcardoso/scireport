"""Access to pandoc: finding it, running it safely and editing its document tree (ADR-0011).

pandoc is optional. ``scireport[pandoc]`` installs ``pypandoc-binary``, whose wheel carries the
pandoc executable, so no system pandoc is needed and every machine runs the same version. The
import of ``pypandoc`` is lazy, and a missing extra is error ``E506`` with an install hint (exit
code 3), never a raw ``ImportError``.

Two ways to run pandoc are offered, and the difference is the point of this module:

* :func:`run_pandoc` is for **prose** that comes from a bundle, which is untrusted. It always
  passes ``--sandbox`` (no reading of files other than those named on the command line, no
  network, no filters) and an empty data directory (no user templates or defaults).
* :func:`run_pandoc` with ``trusted=True`` is for converting the document scireport itself
  rendered to ``docx``, ``odt`` or ``epub``; it needs to read the figures next to the document,
  which the sandbox forbids. The caller cleans the document tree first (see :mod:`.office`).
"""

from __future__ import annotations

import functools
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

from scireport.errors import MissingDependencyError, PandocError
from scireport.logging_utils import get_logger

log = get_logger(__name__)

INSTALL_HINT = "Install the extra: uv add 'scireport[pandoc]' (or pip install 'scireport[pandoc]')."
"""What to do about ``E506``."""

PROSE_READER = (
  'commonmark_x-alerts-attributes-bracketed_spans-emoji-fancy_lists-fenced_divs'
  '-implicit_header_references-raw_attribute-raw_html-smart-subscript-superscript'
  '-yaml_metadata_block-gfm_auto_identifiers'
)
"""pandoc's reader for prose: CommonMark with pipe tables, footnotes, definition lists, task lists,
strikeout and ``$...$`` math, and without the extensions that would add raw content, attributes or
typographic rewriting. (pandoc's CommonMark reader still reads raw HTML; :func:`neutralise` turns
it into text.)"""

_TIMEOUT_SECONDS = 300
_VERSION_RE = re.compile(r'^pandoc(?:\.exe)?\s+(\d+(?:\.\d+)*)', re.MULTILINE)

Node = dict[str, Any]
"""A node of pandoc's JSON document tree: ``{"t": type, "c": content}``."""


def pandoc_path() -> str:
  """Return the path of the pandoc executable.

  Returns
  -------
  str
      The binary of ``pypandoc-binary``, or the ``pandoc`` on ``PATH`` when only ``pypandoc``
      is installed.

  Raises
  ------
  MissingDependencyError
      With ``E506`` (exit code 3) when ``pypandoc`` is not installed or finds no pandoc.
  """
  try:
    import pypandoc
  except ImportError:
    raise MissingDependencyError(
      'pandoc is needed for this and scireport[pandoc] is not installed',
      code='E506',
      hint=INSTALL_HINT,
    ) from None
  try:
    return str(pypandoc.get_pandoc_path())
  except OSError:
    raise MissingDependencyError(
      'pypandoc is installed but it found no pandoc executable',
      code='E506',
      hint=INSTALL_HINT,
    ) from None


def pandoc_available() -> bool:
  """Say whether pandoc can be run (the extra is installed and finds an executable).

  Returns
  -------
  bool
      False when :func:`pandoc_path` would raise ``E506``.
  """
  try:
    pandoc_path()
  except MissingDependencyError:
    return False
  return True


@functools.cache
def pandoc_version() -> str:
  """Return the version of the pandoc that will run, for example ``'3.9'``.

  Returns
  -------
  str
      Dotted numbers, as printed by ``pandoc --version``.

  Raises
  ------
  MissingDependencyError
      With ``E506`` when pandoc is missing.
  PandocError
      With ``E507`` when the version cannot be read.
  """
  out = run_pandoc(['--version'], sandbox=False).decode('utf-8', 'replace')
  match = _VERSION_RE.search(out)
  if match is None:
    raise PandocError(f'cannot read the pandoc version from {out[:60]!r}', code='E507')
  return match.group(1)


def run_pandoc(
  args: Sequence[str],
  data: bytes | None = None,
  *,
  cwd: Path | None = None,
  epoch: int | None = None,
  sandbox: bool = True,
) -> bytes:
  """Run pandoc and return its standard output.

  The environment is reduced to what pandoc needs, ``SOURCE_DATE_EPOCH`` is set from ``epoch``
  (so ``docx``, ``odt`` and ``epub`` archives get fixed timestamps), and an empty data directory
  hides the user's templates and defaults.

  Parameters
  ----------
  args : sequence of str
      The command-line arguments, without the program name.
  data : bytes or None, default=None
      Standard input.
  cwd : pathlib.Path or None, default=None
      The working directory; files named in ``args`` are read relative to it.
  epoch : int or None, default=None
      Seconds since 1970-01-01, for ``SOURCE_DATE_EPOCH``; not set when None.
  sandbox : bool, default=True
      Pass ``--sandbox``. Turn it off only for a document that scireport rendered itself.

  Returns
  -------
  bytes
      What pandoc wrote to standard output.

  Raises
  ------
  MissingDependencyError
      With ``E506`` when pandoc is missing.
  PandocError
      With ``E507`` when pandoc exits with an error or runs too long.
  """
  program = pandoc_path()
  env = {
    name: os.environ[name] for name in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR') if name in os.environ
  }
  if epoch is not None:
    env['SOURCE_DATE_EPOCH'] = str(epoch)
  with tempfile.TemporaryDirectory(prefix='scireport-pandoc-') as data_dir:
    command = [program, f'--data-dir={data_dir}', *(['--sandbox'] if sandbox else []), *args]
    try:
      done = subprocess.run(
        command,
        input=data,
        capture_output=True,
        cwd=cwd,
        env=env,
        timeout=_TIMEOUT_SECONDS,
        check=False,
      )
    except subprocess.TimeoutExpired:
      raise PandocError(f'pandoc ran for more than {_TIMEOUT_SECONDS} s', code='E507') from None
  stderr = done.stderr.decode('utf-8', 'replace').strip()
  if done.returncode != 0:
    raise PandocError(
      f'pandoc exited with code {done.returncode}: {stderr[-600:]}',
      code='E507',
      hint='Run the same conversion with the pandoc command line to see the whole message.',
    )
  for line in stderr.splitlines():
    log.debug('pandoc: %s', line)
  return done.stdout


def read_ast(source: str, reader: str = PROSE_READER) -> Node:
  """Parse text with pandoc into its JSON document tree.

  Parameters
  ----------
  source : str
      The text.
  reader : str, default=PROSE_READER
      pandoc's ``--from`` value.

  Returns
  -------
  dict
      The document: ``pandoc-api-version``, ``meta`` and ``blocks``.
  """
  out = run_pandoc(['-f', reader, '-t', 'json'], source.encode('utf-8'))
  document: Node = json.loads(out)
  return document


def write_ast(document: Node, writer: str, extra: Sequence[str] = ()) -> str:
  """Write a document tree with pandoc.

  Parameters
  ----------
  document : dict
      The document, as returned by :func:`read_ast` (possibly edited).
  writer : str
      pandoc's ``--to`` value.
  extra : sequence of str, default=()
      More arguments.

  Returns
  -------
  str
      The converted text.
  """
  data = json.dumps(document, ensure_ascii=False).encode('utf-8')
  return run_pandoc(['-f', 'json', '-t', writer, *extra], data).decode('utf-8')


def walk(node: Any, visit: Callable[[Node], Node | list[Node] | None]) -> Any:
  """Apply ``visit`` to every typed node of a tree, children first.

  ``visit`` returns the node (possibly new) to put in its place, a list of nodes to splice in
  when the node sits in a list, or None to leave it as it is.

  Parameters
  ----------
  node : Any
      A document, node or list from pandoc's JSON.
  visit : callable
      Called with each dict that has a ``"t"`` key.

  Returns
  -------
  Any
      The edited tree.
  """
  if isinstance(node, list):
    out: list[Any] = []
    for item in node:
      new = walk(item, visit)
      if isinstance(item, dict) and 't' in item and isinstance(new, list):
        out.extend(new)
      else:
        out.append(new)
    return out
  if isinstance(node, dict):
    walked = {name: walk(value, visit) for name, value in node.items()}
    if 't' in walked:
      replaced = visit(walked)
      return walked if replaced is None else replaced
    return walked
  return node


def iter_nodes(node: Any) -> Iterator[Node]:
  """Yield every typed node of a tree, parents before children.

  Parameters
  ----------
  node : Any
      A document, node or list from pandoc's JSON.

  Yields
  ------
  dict
      The nodes that have a ``"t"`` key, in document order.
  """
  if isinstance(node, list):
    for item in node:
      yield from iter_nodes(item)
  elif isinstance(node, dict):
    if 't' in node:
      yield node
    for value in node.values():
      yield from iter_nodes(value)
