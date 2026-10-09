"""Strict reading of manifest text: JSON for every bundle, YAML for hand-authored ones.

JSON rejects duplicate members and ``NaN``/``Infinity``. YAML follows the YAML 1.2 core schema
where it matters (only ``true``/``false`` are booleans, ``yes``/``no``/``on``/``off`` and
``12:30`` stay strings, dates stay strings) and rejects duplicate keys and aliases, so a
hand-written manifest means what it looks like (ADR-0001).
"""

from __future__ import annotations

import json
import re
from typing import Any

import yaml
from yaml.nodes import Node

from scireport.errors import BundleError

MAX_MANIFEST_BYTES = 32 * 1024 * 1024
"""Largest manifest accepted, in bytes."""

_YAML_BOOL = 'tag:yaml.org,2002:bool'
_YAML_INT = 'tag:yaml.org,2002:int'
_YAML_FLOAT = 'tag:yaml.org,2002:float'
_YAML_TIMESTAMP = 'tag:yaml.org,2002:timestamp'


class _StrictLoader(yaml.SafeLoader):
  """``yaml.SafeLoader`` with YAML 1.2 core scalars, no aliases and no duplicate keys."""

  def compose_node(self, parent: Node | None, index: int) -> Node | None:
    """Refuse aliases, which can multiply a small file into a huge structure."""
    if self.check_event(yaml.events.AliasEvent):
      event = self.peek_event()  # type: ignore[no-untyped-call]
      raise yaml.constructor.ConstructorError(
        None, None, 'YAML aliases are not allowed in a manifest', event.start_mark
      )
    return super().compose_node(parent, index)

  def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    """Build a mapping, rejecting repeated keys."""
    seen: set[Any] = set()
    for key_node, _ in node.value:
      key = self.construct_object(key_node, deep=True)
      if key in seen:
        raise yaml.constructor.ConstructorError(
          'while constructing a mapping',
          node.start_mark,
          f'found duplicate key {key!r}',
          key_node.start_mark,
        )
      seen.add(key)
    return super().construct_mapping(node, deep=deep)


_StrictLoader.yaml_implicit_resolvers = {
  first: [
    (tag, regexp)
    for tag, regexp in resolvers
    if tag not in (_YAML_BOOL, _YAML_INT, _YAML_FLOAT, _YAML_TIMESTAMP)
  ]
  for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_StrictLoader.add_implicit_resolver(
  _YAML_BOOL, re.compile(r'^(?:true|True|TRUE|false|False|FALSE)$'), list('tTfF')
)
_StrictLoader.add_implicit_resolver(
  _YAML_INT, re.compile(r'^[-+]?(?:0|[1-9][0-9]*)$'), list('-+0123456789')
)
_StrictLoader.add_implicit_resolver(
  _YAML_FLOAT,
  re.compile(
    r'^[-+]?(?:(?:0|[1-9][0-9]*)\.[0-9]*|\.[0-9]+|(?:0|[1-9][0-9]*)(?=[eE]))(?:[eE][-+]?[0-9]+)?$'
  ),
  list('-+0123456789.'),
)


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
  """JSON object hook: build a dict, rejecting repeated members."""
  out: dict[str, Any] = {}
  for key, value in pairs:
    if key in out:
      raise ValueError(f'duplicate member {key!r}')
    out[key] = value
  return out


def _reject_constant(name: str) -> Any:
  """JSON constant hook: ``NaN`` and ``Infinity`` are not JSON."""
  raise ValueError(f'{name} is not valid JSON')


def parse_manifest_text(data: bytes, *, yaml_format: bool, origin: str) -> Any:
  """Parse manifest bytes as JSON or YAML.

  Parameters
  ----------
  data : bytes
      The manifest file content, UTF-8 (a byte-order mark is ignored).
  yaml_format : bool
      True to parse as YAML, False for JSON.
  origin : str
      Where the data came from, for error messages.

  Returns
  -------
  Any
      The parsed document.

  Raises
  ------
  BundleError
      With code ``E408`` when the manifest is too large, not UTF-8 or not valid.
  """
  if len(data) > MAX_MANIFEST_BYTES:
    raise BundleError(
      f'{origin} is {len(data):,} bytes, over the {MAX_MANIFEST_BYTES:,}-byte manifest limit',
      code='E408',
    )
  try:
    text = data.decode('utf-8-sig')
    if yaml_format:
      return yaml.load(text, Loader=_StrictLoader)
    return json.loads(text, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)
  except (UnicodeDecodeError, ValueError, yaml.YAMLError) as exc:
    raise BundleError(f'{origin} cannot be parsed: {exc}', code='E408') from exc
