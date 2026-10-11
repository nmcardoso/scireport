"""Check a built wheel and sdist: ``python .github/check_dist.py DIST_DIR``.

The release workflow runs it after ``uv build``. It fails (exit code 1, one line per problem on
stderr) unless the wheel and the sdist each hold every file of the freeze list
``tests/compat/FROZEN-builtins.sha256`` (the built-in layouts, templates, fonts, styles and JSON
Schema) with the recorded SHA-256, and the wheel holds the packaged agent skill. A build
configuration that drops or rewrites a frozen file would break every old report (ADR-0008).
"""

from __future__ import annotations

import hashlib
import sys
import tarfile
import zipfile
from pathlib import Path

FROZEN = Path(__file__).resolve().parents[1] / 'tests' / 'compat' / 'FROZEN-builtins.sha256'
SKILL = 'scireport/agent/skill/scireport/SKILL.md'


def main(argv: list[str]) -> int:
  """Check the archives in a directory.

  Parameters
  ----------
  argv : list of str
      The directory that holds one ``.whl`` and one ``.tar.gz``.

  Returns
  -------
  int
      0 when both archives are complete and unchanged, 1 otherwise.
  """
  dist = Path(argv[0])
  wheels, sdists = sorted(dist.glob('*.whl')), sorted(dist.glob('*.tar.gz'))
  if len(wheels) != 1 or len(sdists) != 1:
    sys.stderr.write(
      f'{dist}: expected one wheel and one sdist, found {len(wheels)} and {len(sdists)}\n'
    )
    return 1
  lines = (line.partition('  ') for line in FROZEN.read_text(encoding='utf-8').splitlines())
  frozen = {name: digest for digest, _, name in lines}
  problems = _compare('wheel', _wheel_files(wheels[0]), frozen)
  problems += _compare('sdist', _sdist_files(sdists[0]), frozen)
  if SKILL not in _wheel_files(wheels[0]):
    problems.append(f'wheel: {SKILL} is missing')
  for problem in problems:
    sys.stderr.write(f'{problem}\n')
  return 1 if problems else 0


def _wheel_files(path: Path) -> dict[str, str]:
  """Map each file of a wheel to its SHA-256."""
  with zipfile.ZipFile(path) as archive:
    return {
      info.filename: hashlib.sha256(archive.read(info)).hexdigest()
      for info in archive.infolist()
      if not info.is_dir()
    }


def _sdist_files(path: Path) -> dict[str, str]:
  """Map each file of an sdist to its SHA-256, without the leading ``<name>-<version>/``."""
  found: dict[str, str] = {}
  with tarfile.open(path) as archive:
    for member in archive.getmembers():
      handle = archive.extractfile(member) if member.isfile() else None
      if handle is not None:
        found[member.name.partition('/')[2]] = hashlib.sha256(handle.read()).hexdigest()
  return found


def _compare(label: str, files: dict[str, str], frozen: dict[str, str]) -> list[str]:
  """List the frozen files that an archive lacks or holds with other bytes."""
  problems = []
  for name, digest in sorted(frozen.items()):
    if name not in files:
      problems.append(f'{label}: {name} is missing')
    elif files[name] != digest:
      problems.append(f'{label}: {name} differs from the frozen file')
  return problems


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
