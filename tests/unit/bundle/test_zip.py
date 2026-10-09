"""ZIP bundles: determinism, zip-slip and size-cap rejection, and entry checks."""

from __future__ import annotations

import stat
import sys
import zipfile
from pathlib import Path

import pytest

import scireport.bundle.backends as backends
from scireport import Report, open_bundle, write_bundle
from scireport.bundle.backends import ZipBackend, _check_entries, zip_name_problem
from scireport.errors import BundleError
from scireport.hashing import sha256_bytes
from scireport.spec.manifest import manifest_to_json


def make_report(png: bytes) -> Report:
  report = Report('Zip test', authors=['A'])
  report.add_number('stats.n', 3, format='int')
  report.add_table('t.pairs', {'a': [1, 2], 'b': ['x', 'y']})
  report.add_table('t.csv', {'a': [1]}, format='csv')
  report.add_image('img.logo', png, suffix='png', alt='logo')
  report.add_text('long', 'x' * 5000, format='markdown')
  return report


def raw_zip(path: Path, entries: dict[str, bytes], **infos: zipfile.ZipInfo) -> Path:
  """Write a ZIP with exact entry names, including ones ``zipfile`` would normally clean."""
  with zipfile.ZipFile(path, 'w') as archive:
    for name, data in entries.items():
      archive.writestr(infos.get(name, name), data)
  return path


def minimal_manifest_bytes() -> bytes:
  return manifest_to_json(Report('M').manifest()).encode()


# ---- determinism ------------------------------------------------------------------------------


def test_two_writes_give_identical_bytes(tmp_path: Path, png_bytes: bytes) -> None:
  one = make_report(png_bytes).write(tmp_path / 'one.scireport.zip')
  two = make_report(png_bytes).write(tmp_path / 'two.scireport.zip')
  assert one.read_bytes() == two.read_bytes()


def test_insertion_order_does_not_matter(tmp_path: Path) -> None:
  first = Report('Order').add_number('a', 1).add_number('b', 2).add_text('c', 'x')
  second = Report('Order').add_text('c', 'x').add_number('b', 2).add_number('a', 1)
  assert (
    first.write(tmp_path / '1.zip').read_bytes() == second.write(tmp_path / '2.zip').read_bytes()
  )


def test_zip_layout_is_normalised(tmp_path: Path, png_bytes: bytes) -> None:
  path = make_report(png_bytes).write(tmp_path / 'r.scireport.zip')
  with zipfile.ZipFile(path) as archive:
    infos = archive.infolist()
    names = [i.filename for i in infos]
    assert names == sorted(names)
    assert 'scireport.json' in names
    assert all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in infos)
    assert all(i.create_system == 3 for i in infos)
    assert all(i.external_attr == 0o100644 << 16 for i in infos)
    assert all(not i.flag_bits & 0x1 for i in infos)
    kinds = {i.filename.rpartition('.')[2]: i.compress_type for i in infos}
    assert kinds['png'] == zipfile.ZIP_STORED
    assert kinds['parquet'] == zipfile.ZIP_STORED
    assert kinds['json'] == zipfile.ZIP_DEFLATED
    assert kinds['csv'] == zipfile.ZIP_DEFLATED
    assert kinds['md'] == zipfile.ZIP_DEFLATED
    assert archive.testzip() is None
    assert archive.comment == b''


def test_directory_and_zip_round_trip_to_the_same_zip(tmp_path: Path, png_bytes: bytes) -> None:
  zipped = make_report(png_bytes).write(tmp_path / 'a.scireport.zip')
  with open_bundle(zipped) as bundle:
    unpacked = write_bundle(bundle, tmp_path / 'a.scireport')
  with open_bundle(unpacked) as bundle:
    again = write_bundle(bundle, tmp_path / 'b.scireport.zip')
  assert again.read_bytes() == zipped.read_bytes()


# ---- zip-slip and unsafe entries --------------------------------------------------------------


@pytest.mark.parametrize(
  'name',
  [
    '../evil.txt',
    'assets/../../evil.txt',
    '/etc/passwd',
    'C:/Windows/evil.txt',
    pytest.param(
      'assets\\tables\\x.csv',
      marks=pytest.mark.skipif(
        sys.platform == 'win32',
        reason='zipfile turns backslashes into "/" on Windows, both when writing and reading',
      ),
    ),
    'assets/tables/../../../evil',
    'a//b',
    './x',
    'assets/./x',
  ],
)
def test_unsafe_entry_names_are_rejected(tmp_path: Path, name: str) -> None:
  path = raw_zip(tmp_path / 'bad.zip', {'scireport.json': minimal_manifest_bytes(), name: b'x'})
  with pytest.raises(BundleError) as info:
    open_bundle(path)
  assert info.value.code == 'E407'
  assert 'rejected' in info.value.message


def test_unsafe_names_have_reasons() -> None:
  assert zip_name_problem('') is not None
  assert zip_name_problem('a\x00b') is not None
  assert zip_name_problem('scireport.json') is None
  assert zip_name_problem('assets/tables/x.parquet') is None
  assert zip_name_problem('assets/tables/') is None
  assert zip_name_problem('README.txt') is None
  assert 'folder' in (zip_name_problem('assets/other/x.csv') or '')


def test_assets_with_unportable_names_are_rejected(tmp_path: Path) -> None:
  path = raw_zip(
    tmp_path / 'bad.zip',
    {'scireport.json': minimal_manifest_bytes(), 'assets/tables/CON.csv': b'x'},
  )
  with pytest.raises(BundleError) as info:
    open_bundle(path)
  assert info.value.code == 'E407'


def test_symlink_entries_are_rejected(tmp_path: Path) -> None:
  link = zipfile.ZipInfo('assets/tables/link.csv')
  link.external_attr = (stat.S_IFLNK | 0o777) << 16
  path = raw_zip(
    tmp_path / 'bad.zip',
    {'scireport.json': minimal_manifest_bytes(), 'assets/tables/link.csv': b'/etc/passwd'},
    **{'assets/tables/link.csv': link},
  )
  with pytest.raises(BundleError, match='symbolic link') as info:
    open_bundle(path)
  assert info.value.code == 'E407'


def test_encrypted_entries_are_rejected() -> None:
  info = zipfile.ZipInfo('assets/tables/x.csv')
  info.flag_bits |= 0x1
  with pytest.raises(BundleError, match='encrypted'):
    _check_entries([info], 100)


def test_case_insensitive_duplicates_are_rejected() -> None:
  one, two = zipfile.ZipInfo('assets/text/a.md'), zipfile.ZipInfo('assets/text/A.md')
  with pytest.raises(BundleError, match='duplicated'):
    _check_entries([one, two], 100)


def test_directory_entries_are_ignored() -> None:
  folder = zipfile.ZipInfo('assets/tables/')
  folder.external_attr = (stat.S_IFDIR | 0o755) << 16
  index = _check_entries([folder, zipfile.ZipInfo('assets/tables/a.csv')], 100)
  assert list(index) == ['assets/tables/a.csv']


# ---- size cap ---------------------------------------------------------------------------------


def test_size_cap_on_open(tmp_path: Path, png_bytes: bytes) -> None:
  path = make_report(png_bytes).write(tmp_path / 'r.scireport.zip')
  with pytest.raises(BundleError) as info:
    open_bundle(path, max_bytes=1000)
  assert info.value.code == 'E405'
  assert 'size cap' in info.value.message
  assert info.value.hint is not None
  with open_bundle(path, max_bytes=10_000_000) as bundle:
    assert bundle.verify() == []


def test_size_cap_closes_the_file(tmp_path: Path) -> None:
  path = Report('x').add_text('a', 'y' * 100, as_asset=True).write(tmp_path / 'r.zip')
  with pytest.raises(BundleError):
    open_bundle(path, max_bytes=10)
  path.unlink()  # would fail on Windows if the handle leaked


def test_size_cap_on_write(tmp_path: Path) -> None:
  report = Report('big').add_text('a', 'y' * 6000)
  with open_bundle(report.write(tmp_path / 'src')) as bundle, pytest.raises(BundleError) as info:
    write_bundle(bundle, tmp_path / 'dst.zip', max_bytes=100)
  assert info.value.code == 'E405'
  assert not (tmp_path / 'dst.zip').exists()


def test_entry_count_cap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
  monkeypatch.setattr(backends, 'MAX_ENTRIES', 2)
  path = raw_zip(
    tmp_path / 'many.zip',
    {
      'scireport.json': minimal_manifest_bytes(),
      'assets/text/a.md': b'a',
      'assets/text/b.md': b'b',
    },
  )
  with pytest.raises(BundleError) as info:
    open_bundle(path)
  assert info.value.code == 'E405'


# ---- structure --------------------------------------------------------------------------------


def test_zip_without_manifest_is_not_a_bundle(tmp_path: Path) -> None:
  path = raw_zip(tmp_path / 'x.zip', {'README.txt': b'hi'})
  with pytest.raises(BundleError) as info:
    open_bundle(path)
  assert info.value.code == 'E406'


def test_yaml_manifest_in_a_zip_is_refused(tmp_path: Path) -> None:
  path = raw_zip(tmp_path / 'x.zip', {'scireport.yaml': b'scireport: "1.0"\n'})
  with pytest.raises(BundleError) as info:
    open_bundle(path)
  assert info.value.code == 'E409'
  assert 'hand-authored' in info.value.message


def test_corrupt_zip_is_not_a_bundle(tmp_path: Path) -> None:
  path = tmp_path / 'x.zip'
  path.write_bytes(b'PK\x03\x04 this is not really a zip')
  with pytest.raises(BundleError) as info:
    open_bundle(path)
  assert info.value.code == 'E406'


def test_zip_backend_reads_and_streams(tmp_path: Path) -> None:
  path = raw_zip(tmp_path / 'x.zip', {'assets/text/a.md': b'hello'})
  backend = ZipBackend(path)
  try:
    assert backend.names() == ['assets/text/a.md']
    assert backend.size('assets/text/a.md') == 5
    assert backend.read('assets/text/a.md') == b'hello'
    with backend.open('assets/text/a.md') as handle:
      assert handle.read() == b'hello'
    with pytest.raises(FileNotFoundError):
      backend.read('assets/text/none.md')
  finally:
    backend.close()


def test_corrupt_member_is_reported(tmp_path: Path) -> None:
  path = tmp_path / 'x.zip'
  with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
    archive.writestr('assets/text/a.md', b'hello world')
  data = bytearray(path.read_bytes())
  data[data.index(b'hello world')] ^= 0xFF
  path.write_bytes(bytes(data))
  backend = ZipBackend(path)
  try:
    with pytest.raises(BundleError) as info:
      backend.read('assets/text/a.md')
    assert info.value.code == 'E407'
  finally:
    backend.close()


def test_hash_in_manifest_is_what_integrity_rests_on(tmp_path: Path, png_bytes: bytes) -> None:
  path = make_report(png_bytes).write(tmp_path / 'r.scireport.zip')
  with open_bundle(path) as bundle:
    ref = bundle.asset_ref('assets/images/img.logo.png')
    assert ref.sha256 == sha256_bytes(png_bytes)
    assert ref.bytes == len(png_bytes)


def test_zip_backend_refuses_non_archives(tmp_path: Path) -> None:
  path = tmp_path / 'x.zip'
  path.write_bytes(b'plain bytes')
  with pytest.raises(BundleError) as info:
    ZipBackend(path)
  assert info.value.code == 'E406'
  with pytest.raises(BundleError):
    ZipBackend(tmp_path / 'absent.zip')


def test_memory_backend() -> None:
  from scireport.bundle.backends import MemoryBackend

  backend = MemoryBackend({'b': b'22', 'a': b'1'})
  assert backend.names() == ['a', 'b']
  assert backend.size('b') == 2
  with backend.open('a') as handle:
    assert handle.read() == b'1'
  with pytest.raises(FileNotFoundError):
    backend.read('c')
  backend.close()
