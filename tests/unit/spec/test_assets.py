import pytest
from pydantic import ValidationError

from scireport.spec.assets import AssetRef, asset_path_problem

GOOD = [
  'assets/tables/crossmatch.pairs.parquet',
  'assets/figures/f-1_a.data.parquet',
  'assets/text/Intro.md',
  'assets/attachments/a/b.csv',
]


@pytest.mark.parametrize('path', GOOD)
def test_good_paths(path: str) -> None:
  assert asset_path_problem(path) is None


@pytest.mark.parametrize(
  ('path', 'fragment'),
  [
    ('', 'non-empty'),
    (None, 'non-empty'),
    ('/assets/tables/a.csv', 'absolute'),
    ('assets\\tables\\a.csv', 'backslash'),
    ('tables/a.csv', 'assets/<folder>/<file>'),
    ('assets/a.csv', 'assets/<folder>/<file>'),
    ('assets/other/a.csv', 'folder'),
    ('assets/tables/../a.csv', '..'),
    ('assets/tables//a.csv', 'empty'),
    ('assets/tables/./a.csv', '"."'),
    ('assets/tables/.hidden', 'segment'),
    ('assets/tables/a b.csv', 'segment'),
    ('assets/tables/a:b.csv', 'segment'),
    ('assets/tables/é.csv', 'segment'),
    ('assets/tables/name.', 'dot'),
    ('assets/tables/CON.csv', 'reserved'),
    ('assets/tables/lpt1', 'reserved'),
    ('assets/tables/' + 'x' * 200, 'longer'),
  ],
)
def test_bad_paths(path: object, fragment: str) -> None:
  problem = asset_path_problem(path)
  assert problem is not None
  assert fragment in problem


def test_asset_ref_requires_hash_and_size_without_a_resolver() -> None:
  with pytest.raises(ValidationError):
    AssetRef.model_validate({'path': 'assets/tables/a.csv'})
  with pytest.raises(ValidationError):
    AssetRef.model_validate('assets/tables/a.csv')
  with pytest.raises(ValidationError, match=r'invalid asset path'):
    AssetRef.model_validate({'path': '../x', 'sha256': 'a' * 64, 'bytes': 1})


@pytest.mark.parametrize('sha', ['A' * 64, 'a' * 63, 'g' * 64, ''])
def test_sha256_format(sha: str) -> None:
  with pytest.raises(ValidationError):
    AssetRef(path='assets/tables/a.csv', sha256=sha, bytes=1)


def test_negative_size_rejected() -> None:
  with pytest.raises(ValidationError):
    AssetRef(path='assets/tables/a.csv', sha256='a' * 64, bytes=-1)


def test_resolver_completes_hand_authored_references() -> None:
  calls: list[str] = []

  def resolver(path: str) -> tuple[str, int]:
    calls.append(path)
    if path.endswith('missing.csv'):
      raise FileNotFoundError(path)
    return 'c' * 64, 9

  context = {'resolve_asset': resolver}
  from_string = AssetRef.model_validate('assets/tables/a.csv', context=context)
  from_path = AssetRef.model_validate({'path': 'assets/tables/b.csv'}, context=context)
  partial = AssetRef.model_validate(
    {'path': 'assets/tables/c.csv', 'sha256': 'd' * 64}, context=context
  )
  complete = AssetRef.model_validate(
    {'path': 'assets/tables/d.csv', 'sha256': 'e' * 64, 'bytes': 1}, context=context
  )
  assert (from_string.sha256, from_string.bytes) == ('c' * 64, 9)
  assert from_path.bytes == 9
  assert (partial.sha256, partial.bytes) == ('d' * 64, 9)
  assert complete.bytes == 1
  assert 'assets/tables/d.csv' not in calls
  with pytest.raises(ValidationError, match='does not exist'):
    AssetRef.model_validate({'path': 'assets/tables/missing.csv'}, context=context)
  with pytest.raises(ValidationError):
    AssetRef.model_validate({'path': '../escape'}, context=context)


def test_bare_rendition_paths_work_in_authoring_mode() -> None:
  from scireport.spec.kinds import Rendition

  context = {'resolve_asset': lambda path: ('f' * 64, 7)}
  rendition = Rendition.model_validate('assets/figures/f.svg', context=context)
  assert (rendition.format, rendition.bytes) == ('svg', 7)
  with pytest.raises(ValidationError):
    Rendition.model_validate('assets/figures/f.svg')
