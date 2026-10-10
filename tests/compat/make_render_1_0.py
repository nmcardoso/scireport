"""Add the expected renders to the frozen spec-1.0 compat corpus (``tests/compat/spec-1.0/``).

Each case is rendered with ``generic@1`` and ``minimal@1`` to Markdown, HTML and LaTeX, one
folder per format under ``<case>/expected/render/``. Both are frozen per version, so rendering a
spec-1.0 bundle with them must give these bytes for as long as the package exists (ADR-0008).

The script only adds files and appends their hashes to ``FROZEN.sha256``; it refuses to run when
the renders exist, and it refuses to touch a line that is already frozen. A later renderer gets
its own folder (for example ``render-default-1``) and its own script.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from make_spec_1_0 import ROOT, sha256_of
from render_helpers import normalised

from scireport import open_bundle
from scireport.render import render_bundle
from scireport.render.definition import FORMATS

SOURCES = {
  'minimal': 'bundle.scireport',
  'text-only': 'source',
  'full-kinds': 'bundle.scireport',
}
TEMPLATE = 'generic@1'
LAYOUT = 'minimal@1'
FOLDER = 'render-generic-1-minimal-1'


def main() -> None:
  """Render every case and extend the freeze list."""
  if any((ROOT / case / 'expected' / FOLDER).exists() for case in SOURCES):
    raise SystemExit(f'{FOLDER} exists: the expected renders are frozen and never regenerated.')
  frozen = (ROOT / 'FROZEN.sha256').read_text(encoding='utf-8').splitlines()
  for case, source in SOURCES.items():
    with open_bundle(ROOT / case / source) as bundle:
      for fmt in FORMATS:
        result = render_bundle(bundle, template=TEMPLATE, layout=LAYOUT, formats=[fmt], flat=True)
        for name, data in normalised(result.files).items():
          target = ROOT / case / 'expected' / FOLDER / fmt / name
          target.parent.mkdir(parents=True, exist_ok=True)
          target.write_bytes(data)
  added = sorted(
    f'{sha256_of(path)}  {path.relative_to(ROOT).as_posix()}'
    for path in ROOT.rglob('*')
    if path.is_file() and FOLDER in path.parts
  )
  merged = sorted([*frozen, *added])
  assert set(frozen) <= set(merged) and len(merged) == len(frozen) + len(added)
  (ROOT / 'FROZEN.sha256').write_text('\n'.join(merged) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
  main()
