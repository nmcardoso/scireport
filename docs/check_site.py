"""Check a built documentation site: ``python docs/check_site.py SITE_DIR [--require-gallery]``.

``make docs`` and the docs workflow run it after both Sphinx builds (``html`` and ``markdown``
into the same directory). It fails (exit code 1, one line per problem on stderr) unless:

* ``llms.txt`` and ``llms-full.txt`` exist, and ``llms.txt`` lists every page except those marked
  ``llms-txt-ignore: true`` in their front matter;
* every page has an ``.html`` and an ``.md`` twin that is not empty;
* the agent page links ``llms.txt``, ``llms-full.txt``, the skill zip and its own ``.md`` twin,
  in both the HTML and the Markdown version;
* the skill zip holds ``scireport/SKILL.md`` and the schema files of the package are published
  under ``schemas/`` (their ``$id`` points there);
* every local file a page links under ``downloads/``, ``schemas/`` and, with
  ``--require-gallery``, ``gallery/`` exists.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
BASE = 'https://nmcardoso.github.io/scireport/'
_TARGET = r'((?:downloads|schemas|gallery)/'
LOCAL_LINK = re.compile(rf'(?:href|src)="(?:{re.escape(BASE)})?{_TARGET}[^"#?]+)"')
MARKDOWN_LINK = re.compile(rf'\]\({re.escape(BASE)}{_TARGET}[^)#?\s]+)\)')


def main(argv: list[str] | None = None) -> int:
  """Check the site and return the exit code: 0 when it is complete, 1 otherwise."""
  parser = argparse.ArgumentParser(description=(__doc__ or '').splitlines()[0])
  parser.add_argument('site', type=Path, help='the output directory of the two Sphinx builds')
  parser.add_argument(
    '--require-gallery', action='store_true', help='fail when a gallery file is missing'
  )
  args = parser.parse_args(argv)
  problems = check_site(args.site, require_gallery=args.require_gallery)
  for problem in problems:
    sys.stderr.write(f'{problem}\n')
  if not problems:
    sys.stdout.write(f'site ok: {len(page_names())} pages, llms files, downloads, schemas\n')
  return 1 if problems else 0


def page_names() -> list[str]:
  """List the document names of the Sphinx sources (``adr/index``, ``guide``, ...), sorted."""
  return sorted(
    path.relative_to(DOCS).with_suffix('').as_posix()
    for path in DOCS.rglob('*.md')
    if not {'_build', '_ext'} & set(path.relative_to(DOCS).parts)
  )


def llms_page_names() -> list[str]:
  """List the pages that ``llms.txt`` must list: all except those marked ``llms-txt-ignore``."""
  return [
    name
    for name in page_names()
    if 'llms-txt-ignore: true' not in (DOCS / f'{name}.md').read_text(encoding='utf-8')[:200]
  ]


def check_site(site: Path, *, require_gallery: bool) -> list[str]:
  """Return one message per problem found in a built site.

  Parameters
  ----------
  site : pathlib.Path
      The output directory of the HTML and Markdown builds.
  require_gallery : bool
      Whether a missing gallery file is a problem (the docs workflow) or only skipped (a local
      build without ``make examples``).

  Returns
  -------
  list of str
      The problems; empty when the site is complete.
  """
  problems: list[str] = []
  problems += _check_llms(site)
  problems += _check_pages(site)
  problems += _check_agent(site)
  problems += _check_downloads(site)
  problems += _check_local_links(site, require_gallery=require_gallery)
  return problems


def _check_llms(site: Path) -> list[str]:
  """Check that both llms files exist and the short one lists every page."""
  problems = []
  for name in ('llms.txt', 'llms-full.txt'):
    path = site / name
    if not path.is_file() or not path.read_text(encoding='utf-8').strip():
      problems.append(f'{name}: missing or empty')
  short = site / 'llms.txt'
  if short.is_file():
    text = short.read_text(encoding='utf-8')
    problems += [
      f'llms.txt: does not list {name}.md'
      for name in llms_page_names()
      if f'/{name}.md)' not in text
    ]
  return problems


def _check_pages(site: Path) -> list[str]:
  """Check that every page has a non-empty HTML and Markdown twin."""
  problems = []
  for name in page_names():
    for suffix in ('html', 'md'):
      path = site / f'{name}.{suffix}'
      if not path.is_file() or not path.read_text(encoding='utf-8').strip():
        problems.append(f'{name}.{suffix}: missing or empty')
  return problems


def _check_agent(site: Path) -> list[str]:
  """Check that the agent page links the llms files, the skill zip and its own Markdown twin."""
  problems = []
  wanted = ('llms.txt', 'llms-full.txt', 'downloads/scireport-skill.zip', 'agent.md')
  for suffix in ('html', 'md'):
    path = site / f'agent.{suffix}'
    text = path.read_text(encoding='utf-8') if path.is_file() else ''
    problems += [
      f'agent.{suffix}: does not link {target}' for target in wanted if target not in text
    ]
  return problems


def _check_downloads(site: Path) -> list[str]:
  """Check the skill zip and that every schema file of the package is published."""
  problems = []
  archive = site / 'downloads' / 'scireport-skill.zip'
  if archive.is_file():
    with zipfile.ZipFile(archive) as zipped:
      if 'scireport/SKILL.md' not in zipped.namelist():
        problems.append('downloads/scireport-skill.zip: no scireport/SKILL.md')
  else:
    problems.append('downloads/scireport-skill.zip: missing')
  schemas = ROOT / 'scireport' / 'spec' / 'schemas'
  for schema in sorted(schemas.glob('data-*.schema.json')):
    published = site / 'schemas' / schema.name
    if not published.is_file() or published.read_bytes() != schema.read_bytes():
      problems.append(f'schemas/{schema.name}: missing or different from the package')
  return problems


def _check_local_links(site: Path, *, require_gallery: bool) -> list[str]:
  """Check that every downloads, schemas or gallery file a page links exists in the site."""
  missing: set[str] = set()
  for page in sorted([*site.rglob('*.html'), *site.glob('*.md'), *site.glob('adr/*.md')]):
    if page.parts[len(site.parts)] in ('gallery', '_sources'):
      continue
    text = page.read_text(encoding='utf-8')
    for target in (*LOCAL_LINK.findall(text), *MARKDOWN_LINK.findall(text)):
      if target.startswith('gallery/') and not require_gallery:
        continue
      if not (site / target).is_file():
        missing.add(target)
  return [f'linked file missing: {target}' for target in sorted(missing)]


if __name__ == '__main__':
  sys.exit(main())
