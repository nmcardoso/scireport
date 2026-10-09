"""What a template sees of the data file: the ``data`` namespace and usage tracking (ADR-0005).

``data.crossmatch.n_pairs`` walks the dotted key ``crossmatch.n_pairs`` one segment at a time;
``v('crossmatch.n_pairs')`` reads a key given as a string. Both mark the value as *taken*. The
tracker is the MOSAICS ``take``/``peek``/``leftovers`` idea: after rendering, the values nobody
took are reported as ``W401``. Reading a key the bundle does not have records ``E106`` with a
"did you mean" hint and returns a :class:`MissingValue`, which renders as nothing, so that one
render reports every missing key instead of stopping at the first.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from scireport.spec.kinds import Envelope


class UsageTracker:
  """Records which values of the bundle a render has used.

  Parameters
  ----------
  keys : iterable of str
      Every key of the bundle.
  """

  def __init__(self, keys: Iterable[str]) -> None:
    self._keys = sorted(keys)
    self._taken: set[str] = set()

  def take(self, key: str) -> None:
    """Mark ``key`` as used by the template."""
    self._taken.add(key)

  def leftovers(self) -> list[str]:
    """Return the keys that were never taken, sorted."""
    return [key for key in self._keys if key not in self._taken]


class MissingValue:
  """Stands in for a value that is not in the bundle.

  It is false, empty when iterated or printed, and every attribute of it is itself, so a template
  that reads ``data.x.value`` for a missing ``x`` carries on; the problem was already recorded.

  Parameters
  ----------
  key : str
      The key that was looked up.
  """

  def __init__(self, key: str) -> None:
    self.key = key

  def __bool__(self) -> bool:
    """Return False, so that ``{% if data.x %}`` skips missing values."""
    return False

  def __str__(self) -> str:
    """Return the empty string."""
    return ''

  def __iter__(self) -> Any:
    """Iterate over nothing."""
    return iter(())

  def __len__(self) -> int:
    """Return 0."""
    return 0

  def __call__(self, *args: Any, **kwargs: Any) -> MissingValue:
    """Return itself, so that a method call on a missing value is harmless."""
    return self

  def __getattr__(self, name: str) -> MissingValue:
    """Return itself for any public attribute."""
    if name.startswith('_'):
      raise AttributeError(name)
    return self


class ValueStore:
  """The values of a bundle with usage tracking and key lookup, shared by one render.

  Parameters
  ----------
  values : mapping
      Key to value, from the manifest.
  on_missing : callable
      Called with the key and a "did you mean" hint (or None) when a template reads a key the
      bundle does not have.
  """

  def __init__(
    self, values: Mapping[str, Envelope], on_missing: Callable[[str, str | None], None]
  ) -> None:
    self.values = values
    self.tracker = UsageTracker(values)
    self._on_missing = on_missing
    self._keys_by_id = {id(value): key for key, value in values.items()}
    self._prefixes = {
      '.'.join(parts[:end])
      for key in values
      for parts in [key.split('.')]
      for end in range(1, len(parts))
    }

  def get(self, key: str) -> Envelope | MissingValue:
    """Return the value at ``key``, marking it taken; a missing key is recorded and replaced.

    Parameters
    ----------
    key : str
        A value key.

    Returns
    -------
    Envelope or MissingValue
        The value, or a stand-in after recording ``E106``.
    """
    if key in self.values:
      self.tracker.take(key)
      return self.values[key]
    close = difflib.get_close_matches(key, list(self.values), n=1)
    self._on_missing(key, f'Did you mean {close[0]!r}?' if close else None)
    return MissingValue(key)

  def key_of(self, value: object) -> str | None:
    """Return the key under which ``value`` is stored, or None when it is not a bundle value."""
    return self._keys_by_id.get(id(value))

  def peek(self, key: str) -> Envelope | None:
    """Return the value at ``key`` without marking it taken; None when it is absent."""
    return self.values.get(key)

  def has(self, key: str) -> bool:
    """Say whether the bundle has a value at ``key``."""
    return key in self.values

  def keys(self, prefix: str = '') -> list[str]:
    """List the keys under a dotted prefix, sorted; all keys for an empty prefix.

    Parameters
    ----------
    prefix : str, default=''
        A key prefix such as ``qa`` or ``qa.``.

    Returns
    -------
    list of str
        Keys that start with the prefix as whole segments.
    """
    prefix = prefix.rstrip('.')
    if not prefix:
      return sorted(self.values)
    return sorted(key for key in self.values if key.startswith(prefix + '.'))

  def is_namespace(self, key: str) -> bool:
    """Say whether ``key`` is the dotted prefix of at least one value key."""
    return key in self._prefixes


class DataNamespace:
  """Attribute access to the values by dotted key: ``data.crossmatch.n_pairs``.

  Parameters
  ----------
  store : ValueStore
      The values and the tracker.
  prefix : str, default=''
      The dotted key reached so far.
  """

  __slots__ = ('_prefix', '_store')

  def __init__(self, store: ValueStore, prefix: str = '') -> None:
    self._store = store
    self._prefix = prefix

  def __getattr__(self, name: str) -> Any:
    """Descend one segment: a value if the key exists, else a namespace, else a missing value."""
    if name.startswith('_'):
      raise AttributeError(name)
    return self[name]

  def __getitem__(self, name: str) -> Any:
    """Descend by name; the name may itself be dotted (``data['crossmatch.pairs']``)."""
    key = f'{self._prefix}.{name}' if self._prefix else name
    if key in self._store.values:
      return self._store.get(key)
    if self._store.is_namespace(key):
      return DataNamespace(self._store, key)
    return self._store.get(key)

  def __repr__(self) -> str:
    """Return a short description for error messages."""
    return f'<data {self._prefix or "(root)"}>'
