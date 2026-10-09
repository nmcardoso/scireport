"""Lazy asset reads and verification."""

from __future__ import annotations

from pathlib import Path

import pytest

from scireport import Report, open_bundle
from scireport.errors import BundleError


@pytest.fixture
def directory(tmp_path: Path, png_bytes: bytes) -> Path:
  report = Report('Reader')
  report.add_text('intro', 'hello')
  report.add_text('long', 'L' * 5000, format='markdown')
  report.add_table('t.parquet', {'a': [1, 2, 3], 's': ['x', 'y', 'z']})
  report.add_table('t.csv', {'a': [1, 2]}, format='csv')
  report.add_table('t.inline', {'a': [1], 'b': [None]}, inline=True)
  report.add_image('img', png_bytes, suffix='png')
  report.add_number('n', 1)
  return report.write(tmp_path / 'bundle')


def test_opening_reads_only_the_manifest(
  directory: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  from scireport.bundle.backends import DirBackend, ZipBackend

  reads: list[str] = []
  for backend in (DirBackend, ZipBackend):
    for method in ('read', 'open'):
      original = getattr(backend, method)

      def spy(self: object, name: str, _original: object = original) -> object:
        reads.append(name)
        return _original(self, name)  # type: ignore[operator]

      monkeypatch.setattr(backend, method, spy)
  zipped = tmp_path / 'z.zip'
  with open_bundle(directory) as bundle:
    from scireport import write_bundle

    write_bundle(bundle, zipped)
  reads.clear()
  with open_bundle(directory), open_bundle(zipped):
    pass
  assert reads == ['scireport.json']


def test_a_missing_file_does_not_stop_the_bundle_from_opening(directory: Path) -> None:
  (directory / 'assets' / 'tables' / 't.csv.csv').unlink()
  with open_bundle(directory) as bundle:
    with pytest.raises(BundleError) as info:
      bundle.read_asset('assets/tables/t.csv.csv')
    assert info.value.code == 'E401'
    assert [i.code for i in bundle.verify()] == ['E401']


def test_read_text_inline_and_from_asset(directory: Path) -> None:
  with open_bundle(directory) as bundle:
    assert bundle.read_text('intro') == 'hello'
    assert bundle.read_text('long') == 'L' * 5000
    with pytest.raises(BundleError) as info:
      bundle.read_text('n')
    assert info.value.code == 'E202'
    with pytest.raises(BundleError) as info:
      bundle.read_text('absent')
    assert info.value.code == 'E103'


def test_read_table_all_storages(directory: Path) -> None:
  with open_bundle(directory) as bundle:
    assert bundle.read_table('t.parquet').to_pydict() == {'a': [1, 2, 3], 's': ['x', 'y', 'z']}
    assert bundle.read_table('t.csv').to_pydict() == {'a': [1, 2]}
    assert bundle.read_table('t.inline').to_pydict() == {'a': [1], 'b': [None]}
    with pytest.raises(BundleError) as info:
      bundle.read_table('intro')
    assert info.value.code == 'E202'


def test_open_asset_streams_without_checking(directory: Path, png_bytes: bytes) -> None:
  with open_bundle(directory) as bundle:
    with bundle.open_asset('assets/images/img.png') as handle:
      assert handle.read() == png_bytes
    with pytest.raises(BundleError) as info:
      bundle.open_asset('assets/images/other.png')
    assert info.value.code == 'E401'
    ref = bundle.asset_ref('assets/images/img.png')
    assert bundle.read_asset(ref) == png_bytes


def test_open_asset_of_a_vanished_file(directory: Path) -> None:
  with open_bundle(directory) as bundle:
    (directory / 'assets' / 'images' / 'img.png').unlink()
    with pytest.raises(BundleError) as info:
      bundle.open_asset('assets/images/img.png')
    assert info.value.code == 'E401'


def test_tampered_content_is_caught(directory: Path) -> None:
  image = directory / 'assets' / 'images' / 'img.png'
  original = image.read_bytes()
  image.write_bytes(original[:-1] + bytes([original[-1] ^ 0xFF]))
  with open_bundle(directory) as bundle:
    with pytest.raises(BundleError) as info:
      bundle.read_asset('assets/images/img.png')
    assert info.value.code == 'E402'
    [issue] = bundle.verify()
    assert issue.code == 'E402'
    assert issue.pointer == '/values/img/asset'
    assert issue.expected is not None
    assert issue.found is not None


def test_wrong_size_is_caught_before_reading(directory: Path) -> None:
  image = directory / 'assets' / 'images' / 'img.png'
  image.write_bytes(image.read_bytes() + b'extra')
  with open_bundle(directory) as bundle:
    with pytest.raises(BundleError) as info:
      bundle.read_asset('assets/images/img.png')
    assert info.value.code == 'E403'
    [issue] = bundle.verify()
    assert (issue.code, issue.expected) == (
      'E403',
      str(bundle.asset_ref('assets/images/img.png').bytes),
    )


def test_all_problems_are_reported_at_once(directory: Path) -> None:
  (directory / 'assets' / 'images' / 'img.png').unlink()
  (directory / 'assets' / 'tables' / 't.csv.csv').write_bytes(b'tampered!')
  (directory / 'assets' / 'text' / 'stray.md').write_bytes(b'stray')
  with open_bundle(directory) as bundle:
    assert sorted(i.code for i in bundle.verify()) == ['E401', 'E403', 'W402']


def test_asset_paths_are_unique_and_sorted(directory: Path) -> None:
  with open_bundle(directory) as bundle:
    paths = bundle.asset_paths
    assert paths == sorted(set(paths))
    with pytest.raises(BundleError):
      bundle.asset_ref('assets/text/none.md')


def test_close_twice_is_safe(tmp_path: Path) -> None:
  path = Report('x').add_number('n', 1).write(tmp_path / 'r.zip')
  bundle = open_bundle(path)
  bundle.close()
  bundle.close()
