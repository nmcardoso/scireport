"""The key grammar: semantic, dotted paths whose segments match ``[a-z0-9_-]+`` (ADR-0002)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Annotated, Any

from pydantic import BeforeValidator, Field
from pydantic_core import PydanticCustomError

KEY_PATTERN = r'[a-z0-9_-]+(?:\.[a-z0-9_-]+)*'
"""Regular expression (without anchors) that every key matches in full."""

_KEY_RE = re.compile(KEY_PATTERN)
_SUGGEST_DROP_RE = re.compile(r'[^a-z0-9_.-]+')
_SUGGEST_DOTS_RE = re.compile(r'\.{2,}')


def is_valid_key(key: object) -> bool:
  """Say whether ``key`` follows the key grammar.

  Parameters
  ----------
  key : object
      The candidate. Anything that is not a string is invalid.

  Returns
  -------
  bool
      True when every dot-separated segment is non-empty and matches ``[a-z0-9_-]+``.
  """
  return isinstance(key, str) and _KEY_RE.fullmatch(key) is not None


def split_key(key: str) -> tuple[str, ...]:
  """Split a key into its segments.

  Parameters
  ----------
  key : str
      A valid key.

  Returns
  -------
  tuple of str
      The segments, in order.

  Raises
  ------
  ValueError
      When ``key`` is not valid.
  """
  if not is_valid_key(key):
    raise ValueError(f'invalid key {key!r}')
  return tuple(key.split('.'))


def join_key(segments: Iterable[str]) -> str:
  """Join segments into a key; the inverse of :func:`split_key`.

  Parameters
  ----------
  segments : iterable of str
      Non-empty segments, each matching ``[a-z0-9_-]+``.

  Returns
  -------
  str
      The dotted key.

  Raises
  ------
  ValueError
      When the result is not a valid key.
  """
  key = '.'.join(segments)
  if not is_valid_key(key):
    raise ValueError(f'invalid key {key!r}')
  return key


def suggest_key(raw: str) -> str | None:
  """Propose the closest valid key to an invalid one.

  Lower-cases, turns whitespace and slashes into ``-`` and drops other forbidden characters.

  Parameters
  ----------
  raw : str
      The invalid key.

  Returns
  -------
  str or None
      A valid key different from ``raw``, or None when nothing sensible can be proposed.
  """
  text = re.sub(r'[\s/:]+', '-', raw.strip().lower())
  text = _SUGGEST_DROP_RE.sub('', text)
  text = _SUGGEST_DOTS_RE.sub('.', text).strip('.')
  return text if text != raw and is_valid_key(text) else None


def find_prefix_conflicts(keys: Iterable[str]) -> list[tuple[str, str]]:
  """Find keys that are also the dotted prefix of another key.

  A template reaches values through attribute chains (``data.a.b.c``), so ``a.b`` cannot be a
  value and also a namespace for ``a.b.c``.

  Parameters
  ----------
  keys : iterable of str
      Valid keys.

  Returns
  -------
  list of tuple of (str, str)
      ``(prefix, longer_key)`` pairs, sorted; one pair per conflicting prefix key.
  """
  ordered = sorted(set(keys))
  present = set(ordered)
  found: dict[str, str] = {}
  for key in ordered:
    parts = key.split('.')
    for end in range(1, len(parts)):
      prefix = '.'.join(parts[:end])
      if prefix in present and prefix not in found:
        found[prefix] = key
  return sorted(found.items())


def _validate_key(value: Any) -> str:
  """Pydantic hook: return ``value`` when it is a valid key, else raise ``E101``."""
  if is_valid_key(value):
    return str(value)
  suggestion = suggest_key(value) if isinstance(value, str) else None
  raise PydanticCustomError(
    'E101',
    'invalid key {key}: segments must match [a-z0-9_-]+ and be joined by single dots',
    {'key': repr(value), 'suggestion': suggestion or ''},
  )


Key = Annotated[
  str,
  BeforeValidator(_validate_key),
  Field(json_schema_extra={'pattern': f'^{KEY_PATTERN}$'}),
]
"""Pydantic type of a value key."""
