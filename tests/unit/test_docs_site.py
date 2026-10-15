"""The helpers of the documentation site, and the pages that must follow the code."""

from __future__ import annotations

import importlib.util
import io
import re
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs'
EXAMPLES = ROOT / 'examples'
sys.path.insert(0, str(EXAMPLES))


def load_docs_module(path: Path) -> ModuleType:
  """Import a file of ``docs/`` that is not part of the package."""
  spec = importlib.util.spec_from_file_location(path.stem, path)
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


@pytest.fixture(scope='module')
def render_all() -> ModuleType:
  return load_docs_module(EXAMPLES / 'render_all.py')


@pytest.fixture(scope='module')
def site_assets() -> ModuleType:
  pytest.importorskip('sphinx')
  return load_docs_module(DOCS / '_ext' / 'site_assets.py')


@pytest.fixture(scope='module')
def check_site() -> ModuleType:
  return load_docs_module(DOCS / 'check_site.py')


def fake_examples(root: Path) -> Path:
  layout = root / 'dataset-report' / 'default'
  for name in ('md/report.md', 'html/report.html', 'pdf-weasyprint/report.pdf', 'tex/report.tex'):
    (layout / name).parent.mkdir(parents=True, exist_ok=True)
    (layout / name).write_bytes(name.encode())
  (layout / 'md' / 'figures').mkdir()
  (layout / 'md' / 'figures' / 'f.png').write_bytes(b'png')
  return root


def test_the_gallery_page_links_every_example_in_both_layouts(
  site_assets: ModuleType, render_all: ModuleType
) -> None:
  page = (DOCS / 'examples.md').read_text(encoding='utf-8')
  linked = set(re.findall(r'\]\(https://nmcardoso\.github\.io/scireport/gallery/([^)]+)\)', page))
  published_names = set(site_assets.GALLERY_FILES.values())
  expected = {
    f'{example}/{layout}/{name}'
    for example in render_all.EXAMPLES
    for layout in render_all.LAYOUTS
    for name in published_names
  }
  assert linked == expected


def test_the_skill_zip_holds_the_whole_skill_and_is_reproducible(site_assets: ModuleType) -> None:
  from scireport.agent.skill import skill_files

  data = site_assets.skill_zip_bytes()
  assert data == site_assets.skill_zip_bytes()
  with zipfile.ZipFile(io.BytesIO(data)) as archive:
    assert archive.namelist() == [f'scireport/{name}' for name in skill_files()]
    assert {info.date_time for info in archive.infolist()} == {(1980, 1, 1, 0, 0, 0)}


def test_publishing_writes_the_zip_the_schemas_and_the_gallery(
  site_assets: ModuleType, tmp_path: Path
) -> None:
  out = tmp_path / 'site'
  published = site_assets.publish_files(out, fake_examples(tmp_path / 'examples'))
  assert 'downloads/scireport-skill.zip' in published
  assert 'schemas/data-1.0.schema.json' in published
  gallery = {name for name in published if name.startswith('gallery/')}
  assert gallery == {
    'gallery/dataset-report/default/report.md',
    'gallery/dataset-report/default/report.html',
    'gallery/dataset-report/default/weasyprint.pdf',
    'gallery/dataset-report/default/figures/f.png',
  }


def test_publishing_without_examples_still_writes_the_downloads_and_schemas(
  site_assets: ModuleType, tmp_path: Path
) -> None:
  published = site_assets.publish_files(tmp_path / 'site', tmp_path / 'absent')
  assert not [name for name in published if name.startswith('gallery/')]
  assert 'schemas/data-1.0.schema.json' in published


def build_fake_site(site_assets: ModuleType, check_site: ModuleType, site: Path) -> None:
  site_assets.publish_files(site, site / 'no-examples')
  names = check_site.page_names()
  for name in names:
    for suffix in ('html', 'md'):
      target = site / f'{name}.{suffix}'
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_text(f'page {name}', encoding='utf-8')
  links = 'llms.txt llms-full.txt downloads/scireport-skill.zip agent.md'
  for suffix in ('html', 'md'):
    (site / f'agent.{suffix}').write_text(links, encoding='utf-8')
  (site / 'llms-full.txt').write_text('all', encoding='utf-8')
  base = 'https://nmcardoso.github.io/scireport'
  (site / 'llms.txt').write_text(
    '\n'.join(f'- [x]({base}/{name}.md)' for name in check_site.llms_page_names()), encoding='utf-8'
  )


def test_a_complete_site_passes_the_check(
  site_assets: ModuleType, check_site: ModuleType, tmp_path: Path
) -> None:
  build_fake_site(site_assets, check_site, tmp_path)
  assert check_site.check_site(tmp_path, require_gallery=True) == []


def test_the_check_names_what_is_missing(
  site_assets: ModuleType, check_site: ModuleType, tmp_path: Path
) -> None:
  build_fake_site(site_assets, check_site, tmp_path)
  (tmp_path / 'llms-full.txt').unlink()
  (tmp_path / 'guide.md').unlink()
  (tmp_path / 'agent.md').write_text('no links', encoding='utf-8')
  (tmp_path / 'index.html').write_text(
    '<a href="https://nmcardoso.github.io/scireport/gallery/x/y/report.md">', encoding='utf-8'
  )
  problems = check_site.check_site(tmp_path, require_gallery=True)
  assert 'llms-full.txt: missing or empty' in problems
  assert 'guide.md: missing or empty' in problems
  assert 'agent.md: does not link llms.txt' in problems
  assert 'linked file missing: gallery/x/y/report.md' in problems
  assert 'linked file missing: gallery/x/y/report.md' not in check_site.check_site(
    tmp_path, require_gallery=False
  )


def test_the_check_main_returns_the_exit_code(
  check_site: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
  assert check_site.main([str(tmp_path)]) == 1
  assert 'llms.txt: missing or empty' in capsys.readouterr().err
