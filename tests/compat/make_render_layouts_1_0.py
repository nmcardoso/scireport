"""Add the renders of the designed layouts to the frozen spec-1.0 compat corpus.

Each case is rendered with ``generic@1`` and ``default@1`` and ``modern@1`` to Markdown, HTML and
LaTeX (``<case>/expected/render-generic-1-<layout>-1/<format>/``), and the text of the PDF that
each of the WeasyPrint and the LuaLaTeX engines makes of it is reduced to its letters and hashed
(``pdf-text-weasyprint.sha256``, ``pdf-text-lualatex.sha256``). The PDFs are made without a table of
contents and without a running header, because their text depends on pagination.

The layouts are frozen per version, so rendering a spec-1.0 bundle with them must give these bytes
for as long as the package exists (ADR-0008). The script only adds files and appends their hashes
to ``FROZEN.sha256``; it refuses to run when a folder exists. It needs pango and TeX Live.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from make_spec_1_0 import ROOT, sha256_of
from pdf_text import letters, pdf_text
from render_helpers import normalised

from scireport import open_bundle
from scireport.render import render_bundle
from scireport.render.definition import FORMATS

SOURCES = {
  'minimal': 'bundle.scireport',
  'text-only': 'source',
  'full-kinds': 'bundle.scireport',
}
LAYOUTS = ('default', 'modern')
OPTIONS = {'toc': 'false', 'header': 'false'}


def folder(layout: str) -> str:
  """Return the name of the folder of one layout's expected renders."""
  return f'render-generic-1-{layout}-1'


def main() -> None:
  """Render every case with every layout and extend the freeze list."""
  for layout in LAYOUTS:
    if any((ROOT / case / 'expected' / folder(layout)).exists() for case in SOURCES):
      raise SystemExit(f'{folder(layout)} exists: the expected renders are frozen.')
  frozen = (ROOT / 'FROZEN.sha256').read_text(encoding='utf-8').splitlines()
  added: list[str] = []
  for layout in LAYOUTS:
    for case, source in SOURCES.items():
      base = ROOT / case / 'expected' / folder(layout)
      with open_bundle(ROOT / case / source) as bundle:
        for fmt in FORMATS:
          result = render_bundle(
            bundle, template='generic@1', layout=f'{layout}@1', formats=[fmt], flat=True
          )
          for name, data in normalised(result.files).items():
            target = base / fmt / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        engines: tuple[tuple[str, dict[str, Any]], ...] = (
          ('weasyprint', {'pdf_engine': 'weasyprint'}),
          ('lualatex', {'pdf_engine': 'latex', 'latex_engine': 'lualatex'}),
        )
        for engine, kwargs in engines:
          pdf = render_bundle(
            bundle,
            template='generic@1',
            layout=f'{layout}@1',
            formats=['pdf'],
            options=OPTIONS,
            flat=True,
            **kwargs,
          ).files['report.pdf']
          digest = hashlib.sha256(letters(pdf_text(pdf)).encode('utf-8')).hexdigest()
          (base / f'pdf-text-{engine}.sha256').write_text(digest + '\n', encoding='utf-8')
      added.extend(
        f'{sha256_of(path)}  {path.relative_to(ROOT).as_posix()}'
        for path in sorted(base.rglob('*'))
        if path.is_file()
      )
  merged = sorted([*frozen, *added])
  assert set(frozen) <= set(merged) and len(merged) == len(frozen) + len(added)
  (ROOT / 'FROZEN.sha256').write_text('\n'.join(merged) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
  main()
