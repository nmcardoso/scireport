"""Complete the frozen spec-1.0 compat corpus with the pandoc markup engine and the new cases.

``make_render_1_0.py`` and ``make_render_layouts_1_0.py`` froze the renders of three cases with
the default engine (``mistletoe``). This script adds what they left out, so that the corpus covers
every kind, both designed layouts, every output format and both markup engines (ADR-0008):

* ``every-kind`` (see ``make_every_kind_1_0.py``) with ``minimal@1``, ``default@1`` and
  ``modern@1`` and the ``mistletoe`` engine, in Markdown, HTML and LaTeX;
* ``bibliography`` with ``default@1`` and ``modern@1`` in LaTeX and ``mistletoe`` (citations in
  LaTeX need no pandoc);
* every case with ``pandoc`` as the markup engine, for the three layouts, in Markdown, HTML and
  LaTeX (``<case>/expected/render-generic-1-<layout>-1-pandoc/<format>/``);
* for the designed layouts, the text hash of the PDF that LuaLaTeX makes of each render, and that
  WeasyPrint makes of each render but the ``bibliography`` case with ``mistletoe`` (its HTML needs
  pandoc).

What pandoc writes depends on its version, so ``pandoc-version.txt`` records the one that made the
files and the tests only compare against it. The PDFs are made without a table of contents and
without a running header, because their text depends on pagination.

The script only adds files and appends their hashes to ``FROZEN.sha256``; it refuses to run when a
folder exists. It needs ``scireport[pandoc]``, pango, TeX Live and biber.
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
from scireport.render.pandoc import pandoc_version

SOURCES = {
  'minimal': 'bundle.scireport',
  'text-only': 'source',
  'full-kinds': 'bundle.scireport',
  'bibliography': 'bundle.scireport',
  'every-kind': 'bundle.scireport',
}
LAYOUTS = ('minimal', 'default', 'modern')
DESIGNED = ('default', 'modern')
OPTIONS = {'toc': 'false', 'header': 'false'}
ENGINES: tuple[tuple[str, dict[str, Any]], ...] = (
  ('weasyprint', {'pdf_engine': 'weasyprint'}),
  ('lualatex', {'pdf_engine': 'latex', 'latex_engine': 'lualatex'}),
)


def folder(layout: str, markup: str) -> str:
  """Return the folder name of one layout's expected renders for a markup engine."""
  suffix = '-pandoc' if markup == 'pandoc' else ''
  return f'render-generic-1-{layout}-1{suffix}'


def targets() -> list[tuple[str, str, str]]:
  """Return the (case, layout, markup engine) combinations this script adds."""
  found = [(case, layout, 'pandoc') for case in SOURCES for layout in LAYOUTS]
  found += [('every-kind', layout, 'mistletoe') for layout in LAYOUTS]
  found += [('bibliography', layout, 'mistletoe') for layout in DESIGNED]
  return found


def main() -> None:
  """Render the missing combinations and extend the freeze list."""
  planned = targets()
  for case, layout, markup in planned:
    if (ROOT / case / 'expected' / folder(layout, markup)).exists():
      raise SystemExit(f'{case}/{folder(layout, markup)} exists: the expected renders are frozen.')
  frozen = (ROOT / 'FROZEN.sha256').read_text(encoding='utf-8').splitlines()
  version_file = ROOT / 'pandoc-version.txt'
  version_file.write_text(f'{pandoc_version()}\n', encoding='utf-8', newline='\n')
  added = [f'{sha256_of(version_file)}  {version_file.relative_to(ROOT).as_posix()}']
  for case, layout, markup in planned:
    base = ROOT / case / 'expected' / folder(layout, markup)
    with open_bundle(ROOT / case / SOURCES[case]) as bundle:
      _write_formats(bundle, base, layout, markup, case)
      if layout in DESIGNED:
        _write_pdf_hashes(bundle, base, layout, markup, case)
    added.extend(
      f'{sha256_of(path)}  {path.relative_to(ROOT).as_posix()}'
      for path in sorted(base.rglob('*'))
      if path.is_file()
    )
  merged = sorted([*frozen, *added])
  assert set(frozen) <= set(merged) and len(merged) == len(frozen) + len(added)
  (ROOT / 'FROZEN.sha256').write_text('\n'.join(merged) + '\n', encoding='utf-8', newline='\n')


def _write_formats(bundle: Any, base: Path, layout: str, markup: str, case: str) -> None:
  """Write the Markdown, HTML and LaTeX renders of one combination."""
  formats = ['tex'] if (case, markup) == ('bibliography', 'mistletoe') else list(FORMATS)
  for fmt in formats:
    result = render_bundle(
      bundle,
      template='generic@1',
      layout=f'{layout}@1',
      formats=[fmt],
      flat=True,
      markup_engine=markup,
    )
    for name, data in normalised(result.files).items():
      target = base / fmt / name
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes(data)


def _write_pdf_hashes(bundle: Any, base: Path, layout: str, markup: str, case: str) -> None:
  """Write the hash of the text of the PDFs that each engine makes of one combination."""
  for engine, kwargs in ENGINES:
    if (case, markup, engine) == ('bibliography', 'mistletoe', 'weasyprint'):
      continue
    pdf = render_bundle(
      bundle,
      template='generic@1',
      layout=f'{layout}@1',
      formats=['pdf'],
      options=OPTIONS,
      flat=True,
      markup_engine=markup,
      **kwargs,
    ).files['report.pdf']
    digest = hashlib.sha256(letters(pdf_text(pdf)).encode('utf-8')).hexdigest()
    (base / f'pdf-text-{engine}.sha256').write_text(digest + '\n', encoding='utf-8')


if __name__ == '__main__':
  main()
