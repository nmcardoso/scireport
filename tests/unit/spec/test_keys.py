import pytest

from scireport.spec.keys import (
  find_prefix_conflicts,
  is_valid_key,
  join_key,
  split_key,
  suggest_key,
)


@pytest.mark.parametrize(
  'key', ['a', 'a.b', 'a-b_c.d0', '0', 'crossmatch.pairs', 'a.b.c.d', '-', '_']
)
def test_valid_keys(key: str) -> None:
  assert is_valid_key(key)


@pytest.mark.parametrize(
  'key',
  [
    '',
    '.',
    'a.',
    '.a',
    'a..b',
    'A',
    'a b',
    'a/b',
    'é',
    'a\n',
    'a.b\n',
    'a\\b',
    'a:b',
    None,
    3,
    b'a',
  ],
)
def test_invalid_keys(key: object) -> None:
  assert not is_valid_key(key)


def test_split_and_join_round_trip() -> None:
  assert split_key('a.b-c.d_e') == ('a', 'b-c', 'd_e')
  assert join_key(('a', 'b-c', 'd_e')) == 'a.b-c.d_e'


@pytest.mark.parametrize('bad', ['A.b', 'a..b', ''])
def test_split_rejects_invalid(bad: str) -> None:
  with pytest.raises(ValueError, match='invalid key'):
    split_key(bad)


def test_join_rejects_invalid() -> None:
  with pytest.raises(ValueError, match='invalid key'):
    join_key(['a', 'B'])
  with pytest.raises(ValueError, match='invalid key'):
    join_key([])


@pytest.mark.parametrize(
  ('raw', 'expected'),
  [
    ('Cross Match.Pairs', 'cross-match.pairs'),
    ('a/b', 'a-b'),
    ('  Spaces  ', 'spaces'),
    ('a..b', 'a.b'),
    ('ok.key', None),
    ('!!!', None),
  ],
)
def test_suggest_key(raw: str, expected: str | None) -> None:
  assert suggest_key(raw) == expected


def test_prefix_conflicts() -> None:
  assert find_prefix_conflicts(['a', 'b.c', 'a.b', 'a.b.c', 'x']) == [
    ('a', 'a.b'),
    ('a.b', 'a.b.c'),
  ]
  assert find_prefix_conflicts(['a', 'ab', 'a-b']) == []
  assert find_prefix_conflicts([]) == []
