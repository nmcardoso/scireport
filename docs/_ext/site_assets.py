"""Sphinx extension: files that are published next to the HTML pages but are not pages.

When the HTML builder finishes it writes, into the output directory:

* ``downloads/scireport-skill.zip``: the packaged agent skill (``scireport/SKILL.md`` and its
  ``references/``), ready to unpack into ``.claude/skills/``; the archive is reproducible;
* ``schemas/data-<version>.schema.json``: the frozen JSON Schemas of the data file. Their ``$id``
  is ``https://nmcardoso.github.io/scireport/schemas/...``, so the site is where they resolve;
* ``gallery/<example>/<layout>/``: Markdown, HTML and PDF outputs of ``make examples``
  (``examples/_out``), when that folder exists. Without it the gallery page's links stay dead,
  which only matters on the published site (``check_site.py --require-gallery`` guards that).
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Any

from sphinx.application import Sphinx
from sphinx.util import logging

from scireport.agent.skill import SKILL_DIR, SKILL_NAME, skill_files
from scireport.spec.schema import SCHEMA_DIR

log = logging.getLogger(__name__)

EXAMPLES_OUT = Path(__file__).resolve().parents[2] / 'examples' / '_out'
"""Where ``make examples`` writes."""
GALLERY_FILES = {
  'md/report.md': 'report.md',
  'html/report.html': 'report.html',
  'pdf-weasyprint/report.pdf': 'weasyprint.pdf',
  'pdf-lualatex/report.pdf': 'lualatex.pdf',
}
"""Output of ``make examples`` (relative to ``<example>/<layout>/``) to published name."""
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
"""Fixed time stamp of every entry, so the same skill gives the same archive."""


def skill_zip_bytes() -> bytes:
  """Pack the skill into a ZIP whose entries are sorted and carry a fixed time stamp.

  Returns
  -------
  bytes
      The archive; its entries are ``scireport/SKILL.md``, ``scireport/references/*.md``.
  """
  import io

  buffer = io.BytesIO()
  with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in skill_files():
      info = zipfile.ZipInfo(f'{SKILL_NAME}/{name}', ZIP_TIMESTAMP)
      info.external_attr = 0o644 << 16
      info.compress_type = zipfile.ZIP_DEFLATED
      archive.writestr(info, (SKILL_DIR / name).read_bytes())
  return buffer.getvalue()


def publish_files(out: Path, examples_out: Path = EXAMPLES_OUT) -> list[str]:
  """Write the downloads, the schemas and the gallery into an HTML output directory.

  Parameters
  ----------
  out : pathlib.Path
      The output directory of the HTML builder.
  examples_out : pathlib.Path, default=EXAMPLES_OUT
      The output of ``make examples``; no gallery is written when it does not exist.

  Returns
  -------
  list of str
      The published paths relative to ``out``, sorted.
  """
  (out / 'downloads').mkdir(parents=True, exist_ok=True)
  (out / 'downloads' / f'{SKILL_NAME}-skill.zip').write_bytes(skill_zip_bytes())
  (out / 'schemas').mkdir(exist_ok=True)
  for schema in sorted(SCHEMA_DIR.glob('data-*.schema.json')):
    shutil.copyfile(schema, out / 'schemas' / schema.name)
  _copy_gallery(out / 'gallery', examples_out)
  return sorted(p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file())


def setup(app: Sphinx) -> dict[str, Any]:
  """Register the build hook; see the module docstring."""
  app.connect('build-finished', _on_build_finished)
  return {'version': '1', 'parallel_read_safe': True, 'parallel_write_safe': True}


def _on_build_finished(app: Sphinx, exception: Exception | None) -> None:
  """Publish the extra files once the HTML builder has succeeded."""
  if exception is not None or app.builder.name != 'html':
    return
  published = publish_files(Path(app.outdir))
  gallery = sum(1 for name in published if name.startswith('gallery/'))
  log.info('site_assets: skill zip, schemas and %d gallery files published', gallery)


def _copy_gallery(target: Path, examples_out: Path) -> None:
  """Copy the chosen outputs of every ``<example>/<layout>`` folder of ``make examples``."""
  if not examples_out.is_dir():
    return
  for report_md in sorted(examples_out.glob('*/*/md/report.md')):
    layout_dir = report_md.parents[1]
    destination = target / layout_dir.parent.name / layout_dir.name
    destination.mkdir(parents=True, exist_ok=True)
    for source, name in GALLERY_FILES.items():
      if (layout_dir / source).is_file():
        shutil.copyfile(layout_dir / source, destination / name)
    figures = layout_dir / 'md' / 'figures'
    if figures.is_dir():
      shutil.copytree(figures, destination / 'figures', dirs_exist_ok=True)
