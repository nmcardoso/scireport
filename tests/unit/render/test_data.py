from typing import Any

import pytest

from scireport.render.data import DataNamespace, MissingValue, UsageTracker, ValueStore
from scireport.spec.kinds import value_adapter


def values() -> dict[str, object]:
  return {
    key: value_adapter.validate_python(raw)
    for key, raw in {
      'crossmatch.n_pairs': 3061,
      'crossmatch.pairs': 'x',
      'summary': 'text',
      'a-b.c': 1,
    }.items()
  }


@pytest.fixture
def seen() -> list[tuple[str, str | None]]:
  return []


@pytest.fixture
def store(seen: list[tuple[str, str | None]]) -> ValueStore:
  return ValueStore(values(), lambda key, hint: seen.append((key, hint)))  # type: ignore[arg-type]


def test_attribute_chains_find_values(store: ValueStore) -> None:
  data = DataNamespace(store)
  assert data.crossmatch.n_pairs.value == 3061
  assert data.summary.text == 'text'
  assert data['crossmatch.pairs'].text == 'x'
  assert data['a-b'].c.value == 1


def test_a_namespace_is_returned_for_a_prefix(store: ValueStore) -> None:
  data = DataNamespace(store)
  assert isinstance(data.crossmatch, DataNamespace)
  assert repr(data.crossmatch) == '<data crossmatch>'
  assert repr(data) == '<data (root)>'


def test_reading_marks_values_as_taken(store: ValueStore) -> None:
  data = DataNamespace(store)
  assert store.tracker.leftovers() == ['a-b.c', 'crossmatch.n_pairs', 'crossmatch.pairs', 'summary']
  _ = data.crossmatch.n_pairs
  _ = data.summary
  assert store.tracker.leftovers() == ['a-b.c', 'crossmatch.pairs']


def test_peek_and_has_do_not_mark_values(store: ValueStore) -> None:
  assert store.has('summary')
  assert store.peek('summary') is not None
  assert store.peek('nope') is None
  assert store.tracker.leftovers()[-1] == 'summary'


def test_missing_keys_are_recorded_with_a_hint(
  store: ValueStore, seen: list[tuple[str, str | None]]
) -> None:
  data = DataNamespace(store)
  missing = data.crossmatch.n_pair
  assert isinstance(missing, MissingValue)
  assert seen == [('crossmatch.n_pair', "Did you mean 'crossmatch.n_pairs'?")]
  assert store.get('zzz') is not None
  assert seen[-1] == ('zzz', None)


def test_a_missing_value_renders_as_nothing(store: ValueStore) -> None:
  missing: Any = store.get('nope')
  assert not missing
  assert str(missing) == ''
  assert len(missing) == 0
  assert list(missing) == []
  assert missing.a.b.c is missing
  assert missing() is missing
  with pytest.raises(AttributeError):
    _ = missing._private


def test_private_names_are_not_reachable(store: ValueStore) -> None:
  with pytest.raises(AttributeError):
    DataNamespace(store)._anything  # noqa: B018
  with pytest.raises(AttributeError):
    DataNamespace(store).__secret  # noqa: B018


def test_keys_lists_by_prefix(store: ValueStore) -> None:
  assert store.keys() == ['a-b.c', 'crossmatch.n_pairs', 'crossmatch.pairs', 'summary']
  assert store.keys('crossmatch') == ['crossmatch.n_pairs', 'crossmatch.pairs']
  assert store.keys('crossmatch.') == ['crossmatch.n_pairs', 'crossmatch.pairs']
  assert store.keys('cross') == []


def test_key_of_finds_the_key_of_a_stored_value(store: ValueStore) -> None:
  value = store.peek('summary')
  assert store.key_of(value) == 'summary'
  assert store.key_of(object()) is None
  assert store.is_namespace('crossmatch') and not store.is_namespace('summary')


def test_tracker_standalone() -> None:
  tracker = UsageTracker(['b', 'a'])
  tracker.take('b')
  assert tracker.leftovers() == ['a']
