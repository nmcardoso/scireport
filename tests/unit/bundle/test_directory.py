"""Directory and single-file bundles: hand-authoring, YAML, overwrite safety, atomic writes."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

from scireport import Report, open_bundle, write_bundle
from scireport.bundle.writer import infer_form
from scireport.errors import BundleError, SpecError
from scireport.hashing import sha256_bytes

YAML = """\
scireport: "1.0"
meta:
  title: Hand-authored
  authors: [N. Cardoso]
  date: 2026-10-09
render:
  layout: default@1
outline:
  - summary
  - title: Results
    children: [stats.n, crossmatch.pairs, flags]
values:
  summary: A short summary.
  stats.n: 3061
  stats.ok: true
  flags:
    answer: yes
    time: 12:30
  crossmatch.pairs:
    kind: table
    asset: assets/tables/pairs.csv
    caption: Pairs
"""
CSV = b'a,b\n1,2\n3,4\n'


def author_directory(root: Path, yaml_name: str = 'scireport.yaml') -> Path:
  (root / 'assets' / 'tables').mkdir(parents=True)
  (root / 'assets' / 'tables' / 'pairs.csv').write_bytes(CSV)
  (root / yaml_name).write_text(YAML, encoding='utf-8', newline='\n')
  return root


def test_hand_authored_yaml_directory_is_completed(tmp_path: Path) -> None:
  root = author_directory(tmp_path / 'report')
  with open_bundle(root) as bundle:
    assert bundle.form == 'directory'
    table = bundle.manifest.values['crossmatch.pairs']
    assert table.asset.sha256 == sha256_bytes(CSV)  # type: ignore[union-attr]
    assert table.asset.bytes == len(CSV)  # type: ignore[union-attr]
    assert bundle.manifest.meta.date == '2026-10-09'
    flags = bundle.manifest.values['flags']
    entries = [(e.key, e.value.kind) for e in flags.entries]  # type: ignore[union-attr]
    assert entries == [('answer', 'text'), ('time', 'text')]
    assert bundle.read_table('crossmatch.pairs').to_pydict() == {'a': [1, 3], 'b': [2, 4]}
    assert bundle.verify() == []


def test_yml_extension_and_json_directories(tmp_path: Path) -> None:
  yml = author_directory(tmp_path / 'y', 'scireport.yml')
  with open_bundle(yml) as bundle:
    assert bundle.manifest.meta.title == 'Hand-authored'
  built = Report('J').add_number('n', 1).write(tmp_path / 'j')
  assert (built / 'scireport.json').is_file()
  with open_bundle(built) as bundle:
    assert bundle.manifest.values['n'].value == 1  # type: ignore[union-attr]


def test_pack_converts_yaml_to_json_and_a_sealed_zip(tmp_path: Path) -> None:
  root = author_directory(tmp_path / 'report')
  stray = root / 'assets' / 'text'
  stray.mkdir()
  (stray / 'unused.md').write_bytes(b'not referenced')
  with open_bundle(root) as bundle:
    assert [i.code for i in bundle.verify()] == ['W402']
    packed = write_bundle(bundle, tmp_path / 'report.scireport.zip')
  with zipfile.ZipFile(packed) as archive:
    assert sorted(archive.namelist()) == ['assets/tables/pairs.csv', 'scireport.json']
    manifest = json.loads(archive.read('scireport.json'))
  assert manifest['values']['crossmatch.pairs']['asset']['sha256'] == sha256_bytes(CSV)
  with open_bundle(packed) as sealed:
    assert sealed.form == 'zip'
    assert sealed.verify() == []


def test_missing_asset_file_is_reported_with_the_manifest_error(tmp_path: Path) -> None:
  root = author_directory(tmp_path / 'report')
  (root / 'assets' / 'tables' / 'pairs.csv').unlink()
  with pytest.raises(SpecError) as info:
    open_bundle(root)
  assert [i.code for i in info.value.issues] == ['E401']
  assert info.value.issues[0].pointer == '/values/crossmatch.pairs/asset'


def test_single_file_form(tmp_path: Path) -> None:
  manifest = tmp_path / 'report.json'
  Report('Text only').add_text('a', 'x').write(manifest)
  assert json.loads(manifest.read_text(encoding='utf-8'))['scireport'] == '1.0'
  with open_bundle(manifest) as bundle:
    assert bundle.form == 'file'
    assert bundle.read_text('a') == 'x'
  yaml_file = tmp_path / 'alone.yaml'
  yaml_file.write_text(
    'scireport: "1.0"\nmeta: {title: Alone}\nvalues: {note: hi}\n', encoding='utf-8'
  )
  with open_bundle(yaml_file) as bundle:
    assert bundle.form == 'file'
    assert bundle.read_text('note') == 'hi'


def test_single_file_assets_resolve_next_to_the_file(tmp_path: Path) -> None:
  (tmp_path / 'assets' / 'text').mkdir(parents=True)
  (tmp_path / 'assets' / 'text' / 'long.md').write_bytes(b'# Long\n')
  doc = tmp_path / 'r.yaml'
  doc.write_text(
    'scireport: "1.0"\nmeta: {title: T}\n'
    'values:\n  long: {kind: text, asset: assets/text/long.md}\n',
    encoding='utf-8',
  )
  with open_bundle(doc) as bundle:
    assert bundle.read_text('long') == '# Long\n'


def test_single_file_form_cannot_carry_assets(tmp_path: Path) -> None:
  report = Report('x').add_text('a', 'y', as_asset=True)
  with pytest.raises(BundleError) as info:
    report.write(tmp_path / 'r.json')
  assert info.value.code == 'E409'
  assert not (tmp_path / 'r.json').exists()


def test_both_manifests_is_ambiguous(tmp_path: Path) -> None:
  root = author_directory(tmp_path / 'report')
  (root / 'scireport.json').write_text('{}', encoding='utf-8')
  with pytest.raises(BundleError) as info:
    open_bundle(root)
  assert info.value.code == 'E409'


def test_not_bundles(tmp_path: Path) -> None:
  empty = tmp_path / 'empty'
  empty.mkdir()
  text = tmp_path / 'notes.txt'
  text.write_text('hi', encoding='utf-8')
  for path in (empty, text, tmp_path / 'absent'):
    with pytest.raises(BundleError) as info:
      open_bundle(path)
    assert info.value.code == 'E406'


def test_bad_manifest_text_is_e408(tmp_path: Path) -> None:
  root = tmp_path / 'r'
  root.mkdir()
  (root / 'scireport.json').write_text('{"scireport": ', encoding='utf-8')
  with pytest.raises(BundleError) as info:
    open_bundle(root)
  assert info.value.code == 'E408'


@pytest.mark.skipif(sys.platform == 'win32', reason='symbolic links need privileges on Windows')
def test_symlinks_inside_a_bundle_directory_are_refused(tmp_path: Path) -> None:
  outside = tmp_path / 'secret.md'
  outside.write_bytes(b'secret')
  root = tmp_path / 'r'
  (root / 'assets' / 'text').mkdir(parents=True)
  (root / 'assets' / 'text' / 'a.md').symlink_to(outside)
  doc = root / 'scireport.json'
  doc.write_text(
    json.dumps(
      {
        'scireport': '1.0',
        'meta': {'title': 'T'},
        'values': {
          'a': {
            'kind': 'text',
            'asset': {'path': 'assets/text/a.md', 'sha256': sha256_bytes(b'secret'), 'bytes': 6},
          }
        },
      }
    ),
    encoding='utf-8',
  )
  with open_bundle(root) as bundle:
    [issue] = bundle.verify()
    assert issue.code == 'E404'
    with pytest.raises(BundleError) as info:
      bundle.read_asset('assets/text/a.md')
    assert info.value.code == 'E404'


# ---- writing safely ---------------------------------------------------------------------------


def test_infer_form() -> None:
  assert infer_form(Path('a.scireport.zip')) == 'zip'
  assert infer_form(Path('a.ZIP')) == 'zip'
  assert infer_form(Path('a.json')) == 'file'
  assert infer_form(Path('a.scireport')) == 'directory'
  assert infer_form(Path('a')) == 'directory'


def test_existing_destination_needs_overwrite(tmp_path: Path) -> None:
  report = Report('x').add_number('n', 1)
  dest = report.write(tmp_path / 'r.zip')
  before = dest.read_bytes()
  with pytest.raises(BundleError) as info:
    report.write(dest)
  assert info.value.code == 'E410'
  assert dest.read_bytes() == before
  report.write(dest, overwrite=True)


def test_overwriting_a_bundle_directory_drops_stale_assets(tmp_path: Path) -> None:
  dest = Report('x').add_text('a', 'y', as_asset=True).write(tmp_path / 'r')
  assert (dest / 'assets' / 'text' / 'a.txt').exists()
  Report('x').add_number('n', 1).write(dest, overwrite=True)
  assert not (dest / 'assets').exists()
  assert (dest / 'scireport.json').is_file()


def test_overwrite_refuses_directories_that_are_not_bundles(tmp_path: Path) -> None:
  precious = tmp_path / 'precious'
  precious.mkdir()
  (precious / 'thesis.tex').write_text('years of work', encoding='utf-8')
  with pytest.raises(BundleError) as info:
    Report('x').write(precious, overwrite=True)
  assert info.value.code == 'E410'
  assert (precious / 'thesis.tex').exists()
  empty = tmp_path / 'empty'
  empty.mkdir()
  Report('x').write(empty, overwrite=True)
  assert (empty / 'scireport.json').is_file()


def test_form_mismatches_with_existing_paths(tmp_path: Path) -> None:
  folder = tmp_path / 'folder.zip'
  folder.mkdir()
  with pytest.raises(BundleError) as info:
    Report('x').write(folder, overwrite=True)
  assert info.value.code == 'E410'
  plain = tmp_path / 'plain'
  plain.write_text('file', encoding='utf-8')
  with pytest.raises(BundleError) as info:
    Report('x').write(plain, overwrite=True)
  assert info.value.code == 'E410'


@pytest.mark.parametrize('name', ['r.scireport.zip', 'r.scireport', 'r.json'])
def test_failed_writes_leave_nothing_behind(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
  def explode(*_args: object, **_kwargs: object) -> None:
    raise OSError('disk full')

  monkeypatch.setattr(zipfile.ZipFile, 'writestr', explode)
  monkeypatch.setattr(Path, 'write_bytes', explode)
  with pytest.raises(OSError, match='disk full'):
    Report('x').add_number('n', 1).write(tmp_path / name)
  assert list(tmp_path.iterdir()) == []


def test_assets_that_differ_only_by_case_collide(tmp_path: Path) -> None:
  from scireport.bundle.backends import MemoryBackend
  from scireport.bundle.reader import Bundle
  from scireport.spec.manifest import parse_manifest

  def ref(name: str) -> dict[str, object]:
    return {'path': f'assets/text/{name}', 'sha256': sha256_bytes(b'x'), 'bytes': 1}

  manifest = parse_manifest(
    {
      'scireport': '1.0',
      'meta': {'title': 'T'},
      'values': {
        'a': {'kind': 'text', 'asset': ref('A.md')},
        'b': {'kind': 'text', 'asset': ref('a.md')},
      },
    }
  )
  bundle = Bundle(
    manifest,
    MemoryBackend({'assets/text/A.md': b'x', 'assets/text/a.md': b'x'}),
    form='directory',
  )
  with pytest.raises(BundleError) as info:
    write_bundle(bundle, tmp_path / 'r.zip')
  assert info.value.code == 'E404'
