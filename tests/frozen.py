"""The freeze lists of the compat corpus and the check that they only grow (ADR-0008).

Two lists record SHA-256 hashes of files that a released package must keep byte for byte:
``spec-1.0/FROZEN.sha256`` (the fixtures and expected outputs of the compat corpus) and
``FROZEN-builtins.sha256`` (the built-in layouts and templates of every version, the fonts and
matplotlib styles they use, and the frozen JSON Schemas). The tests compare each list with the
files on disk. That alone does not stop someone from regenerating a file *and* its line in the
same change, so CI also runs ``python tests/frozen.py BASE_REF``: a line that exists at
``BASE_REF`` must still be there, with the same hash. Only new lines (a new case, a new layout
version) may be added.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / 'scireport'
COMPAT = Path(__file__).resolve().parent / 'compat'
BUILTINS_LIST = COMPAT / 'FROZEN-builtins.sha256'
LISTS = (COMPAT / 'spec-1.0' / 'FROZEN.sha256', BUILTINS_LIST)


def builtin_files() -> list[str]:
  """List the built-in files that a release freezes, relative to the repository root.

  They are every file of a versioned layout or template directory
  (``layouts/<name>/<n>/``, ``templates/<name>/<n>/``), the fonts and ``.mplstyle`` files of
  ``styles/`` and the frozen JSON Schemas.

  Returns
  -------
  list of str
      Sorted POSIX paths.
  """
  found: set[Path] = set()
  for kind in ('layouts', 'templates'):
    for version_dir in (PACKAGE / kind).glob('*/[0-9]*'):
      found.update(path for path in version_dir.rglob('*') if _is_source(path))
  found.update(path for path in (PACKAGE / 'styles' / 'fonts').glob('*') if _is_source(path))
  found.update((PACKAGE / 'styles').glob('*.mplstyle'))
  found.update((PACKAGE / 'spec' / 'schemas').glob('*.schema.json'))
  return sorted(path.relative_to(REPO).as_posix() for path in found)


def hash_line(path: str) -> str:
  """Return the freeze-list line (``<sha256>  <path>``) of a file.

  Parameters
  ----------
  path : str
      Path relative to the repository root.

  Returns
  -------
  str
      The digest, two spaces and the path.
  """
  return f'{hashlib.sha256((REPO / path).read_bytes()).hexdigest()}  {path}'


def parse_list(text: str) -> dict[str, str]:
  """Read a freeze list.

  Parameters
  ----------
  text : str
      The content: one ``<sha256>  <path>`` line per file.

  Returns
  -------
  dict
      Path to digest.
  """
  entries: dict[str, str] = {}
  for line in text.splitlines():
    digest, _, name = line.partition('  ')
    entries[name] = digest
  return entries


def growth_problems(base: str, current: str) -> list[str]:
  """Describe how a freeze list stopped being an extension of an earlier version of itself.

  Parameters
  ----------
  base : str
      The list as it was.
  current : str
      The list as it is now.

  Returns
  -------
  list of str
      One message per line that was removed or whose hash changed; empty when ``current`` only
      adds lines.
  """
  was, now = parse_list(base), parse_list(current)
  problems = [f'removed: {name}' for name in sorted(was.keys() - now.keys())]
  problems += [
    f'changed: {name}' for name in sorted(was.keys() & now.keys()) if was[name] != now[name]
  ]
  return problems


def main(argv: list[str] | None = None) -> int:
  """Fail when a freeze list lost or changed a line since a base revision.

  Parameters
  ----------
  argv : list of str, optional
      Command-line arguments (``BASE_REF``); ``sys.argv[1:]`` by default.

  Returns
  -------
  int
      0 when both lists only grew (a list that does not exist at the base is new), 1 when one did
      not, 2 when ``BASE_REF`` is not a revision of this repository.
  """
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
  parser.add_argument('base', help='git revision to compare with (a branch, tag or commit)')
  base = parser.parse_args(argv).base
  known = subprocess.run(
    ['git', 'rev-parse', '--verify', '--quiet', f'{base}^{{commit}}'],
    cwd=REPO,
    capture_output=True,
    check=False,
  )
  if known.returncode != 0:
    sys.stderr.write(f'{base} is not a revision of this repository\n')
    return 2
  failed = False
  for path in LISTS:
    name = path.relative_to(REPO).as_posix()
    shown = subprocess.run(
      ['git', 'show', f'{base}:{name}'], cwd=REPO, capture_output=True, text=True, check=False
    )
    if shown.returncode != 0:
      continue
    for problem in growth_problems(shown.stdout, path.read_text(encoding='utf-8')):
      sys.stderr.write(f'{name} {problem}\n')
      failed = True
  return 1 if failed else 0


def _is_source(path: Path) -> bool:
  """Tell a file that ships from Python's byte-code caches."""
  return path.is_file() and '__pycache__' not in path.parts


if __name__ == '__main__':
  sys.exit(main())
