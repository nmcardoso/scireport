"""Build the files of gate HG-S1: the MOSAICS demo PDF beside the scireport PDFs, both engines.

Writes to ``examples/_out/hg-s1/``:

* ``mosaics-kitchen-sink.pdf``: the MOSAICS design-system demo (made by ``python -m
  datex.report.demo`` in the datex repository; pass its path with ``--mosaics``);
* ``<layout>-<engine>.pdf`` for the layouts ``default`` and ``modern`` and the engines
  ``weasyprint`` and ``lualatex``: ``kitchen-sink@1`` rendered by scireport;
* ``compare-default.png`` and ``compare-modern.png``: the same six pages of the documents side by
  side (cover, contents, a chapter opener, the status levels, the flow, a table).

It needs ``pdftoppm`` (poppler) and the PDF toolchains. Nothing is committed: ``_out/`` is ignored.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

import typer
from PIL import Image, ImageDraw

from scireport.demo import kitchen_sink_bundle
from scireport.logging_utils import get_logger, setup_logging
from scireport.render import render_bundle

log = get_logger(__name__)
HERE = Path(__file__).resolve().parent
PAGES = (
  ('cover', ('Kitchen Sink', 'KITCHEN SINK', 'Every Component')),
  ('contents', ('Contents',)),
  ('chapter opener', ('Quality Control Results Overview',)),
  ('status levels', ('COMPLETED WITH WARNINGS', 'Completed with warnings')),
  ('flow', ('INGESTION', 'Ingestion')),
  ('table', ('Long identifiers',)),
)
"""Row of the comparison: a label and the strings that identify the page in any layout."""
app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
  mosaics: Annotated[Path, typer.Option('--mosaics', help='The MOSAICS demo PDF.')],
  out: Annotated[Path, typer.Option('--out', '-o')] = HERE / '_out' / 'hg-s1',
) -> None:
  """Render the kitchen sink with both layouts and engines and compare it with MOSAICS."""
  setup_logging()
  out.mkdir(parents=True, exist_ok=True)
  shutil.copyfile(mosaics, out / 'mosaics-kitchen-sink.pdf')
  made: dict[str, Path] = {}
  for layout in ('default', 'modern'):
    for engine in ('weasyprint', 'lualatex'):
      kwargs = (
        {'pdf_engine': 'weasyprint'}
        if engine == 'weasyprint'
        else {'pdf_engine': 'latex', 'latex_engine': engine}
      )
      result = render_bundle(
        kitchen_sink_bundle(layout),
        template='kitchen-sink@1',
        layout=f'{layout}@1',
        formats=['pdf'],
        flat=True,
        **kwargs,
      )
      path = out / f'{layout}-{engine}.pdf'
      path.write_bytes(result.files['report.pdf'])
      made[f'{layout}-{engine}'] = path
      log.info('%s: %d bytes', path.name, path.stat().st_size)
  _compare(
    out / 'compare-default.png',
    [('MOSAICS', out / 'mosaics-kitchen-sink.pdf'), *_pick(made, 'default')],
  )
  _compare(out / 'compare-modern.png', _pick(made, 'modern'))


def _pick(made: dict[str, Path], layout: str) -> list[tuple[str, Path]]:
  """Return the labelled PDFs of one layout."""
  return [
    (f'scireport {layout} / {engine}', made[f'{layout}-{engine}'])
    for engine in ('weasyprint', 'lualatex')
  ]


def _compare(target: Path, documents: list[tuple[str, Path]]) -> None:
  """Write a grid with one column per document and one row per page of :data:`PAGES`."""
  with tempfile.TemporaryDirectory() as scratch:
    columns = [_page_images(path, Path(scratch) / str(i)) for i, (_, path) in enumerate(documents)]
  width, height = columns[0][0].size
  margin = 22
  sheet = Image.new('RGB', (width * len(columns), (height + margin) * len(PAGES)), 'white')
  draw = ImageDraw.Draw(sheet)
  for col, ((label, _), images) in enumerate(zip(documents, columns, strict=True)):
    for row, ((name, _), image) in enumerate(zip(PAGES, images, strict=True)):
      x, y = col * width, row * (height + margin)
      draw.text((x + 6, y + 5), f'{label}: {name}', fill='black')
      sheet.paste(image.resize((width, height)), (x, y + margin))
  sheet.save(target)
  log.info('wrote %s (%dx%d)', target.name, *sheet.size)


def _page_images(pdf: Path, scratch: Path) -> list[Image.Image]:
  """Rasterise a PDF and return the image of the first page that matches each row of PAGES."""
  scratch.mkdir(parents=True)
  subprocess.run(
    ['pdftoppm', '-r', '40', '-png', str(pdf), str(scratch / 'p')], check=True
  )
  texts = _page_texts(pdf)
  files = sorted(scratch.glob('p-*.png'))
  chosen: list[Image.Image] = []
  for name, needles in PAGES:
    index = (
      0
      if name == 'cover'
      else next((i for i, text in enumerate(texts) if any(n in text for n in needles)), 0)
    )
    chosen.append(Image.open(files[index]).convert('RGB'))
  return chosen


def _page_texts(pdf: Path) -> list[str]:
  """Return the text of every page of a PDF."""
  from pypdf import PdfReader

  return [page.extract_text() or '' for page in PdfReader(str(pdf)).pages]


if __name__ == '__main__':
  app()
