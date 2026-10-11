"""Write ``FROZEN-builtins.sha256``, the freeze list of the built-in layouts, templates and schemas.

Run it for a release, and again when a new layout or template *version* is added: it appends the
lines of files that are not listed yet and refuses to change a line that exists, so a frozen
built-in can never be updated through it (a visual change is a new version, ADR-0008).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frozen import BUILTINS_LIST, builtin_files, hash_line, parse_list


def main() -> int:
  """Append the lines of the unlisted built-in files."""
  listed = parse_list(BUILTINS_LIST.read_text(encoding='utf-8')) if BUILTINS_LIST.exists() else {}
  current = parse_list('\n'.join(hash_line(path) for path in builtin_files()))
  changed = sorted(name for name, digest in current.items() if listed.get(name, digest) != digest)
  if changed:
    sys.stderr.write('frozen built-ins changed (a change is a new version):\n')
    sys.stderr.write(''.join(f'  {name}\n' for name in changed))
    return 1
  merged = sorted(f'{digest}  {name}' for name, digest in {**listed, **current}.items())
  BUILTINS_LIST.write_text('\n'.join(merged) + '\n', encoding='utf-8', newline='\n')
  return 0


if __name__ == '__main__':
  sys.exit(main())
