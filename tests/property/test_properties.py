"""Property tests: key grammar, canonicalisation of bare JSON, and bundle round trips."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from scireport import Report, open_bundle, write_bundle
from scireport.spec.keys import (
  KEY_PATTERN,
  find_prefix_conflicts,
  is_valid_key,
  join_key,
  split_key,
  suggest_key,
)
from scireport.spec.kinds import value_adapter
from scireport.spec.manifest import Manifest, manifest_to_dict, manifest_to_json, parse_manifest

SEGMENT = st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_-', min_size=1, max_size=8)
KEYS = st.lists(SEGMENT, min_size=1, max_size=4).map('.'.join)

JSON_LEAVES = (
  st.none()
  | st.booleans()
  | st.integers(min_value=-(2**53), max_value=2**53)
  | st.floats(allow_nan=False, allow_infinity=False)
  | st.text(max_size=20)
)
JSON_VALUES = st.recursive(
  JSON_LEAVES,
  lambda children: (
    st.lists(children, max_size=4)
    | st.dictionaries(
      st.text(min_size=1, max_size=8).filter(lambda k: k != 'kind'), children, max_size=4
    )
  ),
  max_leaves=15,
)


# ---- keys -------------------------------------------------------------------------------------


@given(KEYS)
def test_generated_keys_are_valid_and_round_trip(key: str) -> None:
  assert is_valid_key(key)
  assert join_key(split_key(key)) == key
  assert all(re.fullmatch(r'[a-z0-9_-]+', part) for part in split_key(key))


@given(st.text(max_size=30))
def test_validity_is_exactly_the_documented_grammar(text: str) -> None:
  assert is_valid_key(text) == (re.fullmatch(KEY_PATTERN, text) is not None)


@given(st.text(max_size=30))
def test_suggestions_are_valid_and_different(text: str) -> None:
  suggestion = suggest_key(text)
  if suggestion is not None:
    assert is_valid_key(suggestion)
    assert suggestion != text


@given(st.lists(KEYS, max_size=8))
def test_prefix_conflicts_are_found_exactly(keys: list[str]) -> None:
  conflicts = find_prefix_conflicts(keys)
  expected = {a for a in set(keys) for b in set(keys) if b.startswith(a + '.')}
  assert {prefix for prefix, _ in conflicts} == expected
  for prefix, longer in conflicts:
    assert longer.startswith(prefix + '.')
    assert longer in keys


# ---- canonicalisation -------------------------------------------------------------------------


@given(JSON_VALUES)
def test_canonicalisation_is_idempotent_and_json_stable(raw: Any) -> None:
  first = value_adapter.validate_python(raw)
  dumped = first.model_dump(mode='json')
  assert json.loads(json.dumps(dumped, allow_nan=False)) == dumped
  second = value_adapter.validate_python(dumped)
  assert second == first
  assert second.model_dump(mode='json') == dumped


@given(JSON_VALUES)
def test_bare_json_never_loses_information(raw: Any) -> None:
  """Scalars keep their value and type; containers keep their length and order."""
  value = value_adapter.validate_python(raw)
  if raw is None:
    assert value.kind == 'number'
    assert value.value is None
  elif isinstance(raw, bool):
    assert value.kind == 'bool'
    assert value.value is raw
  elif isinstance(raw, int | float):
    assert value.kind == 'number'
    assert value.value == raw
    assert type(value.value) is type(raw)
  elif isinstance(raw, str):
    assert value.kind == 'text'
    assert value.text == raw
  elif isinstance(raw, list):
    assert value.kind == 'list'
    assert len(value.items) == len(raw)
  else:
    assert value.kind == 'mapping'
    assert [entry.key for entry in value.entries] == list(raw)


@given(
  st.dictionaries(KEYS, JSON_VALUES, max_size=6).filter(lambda d: not find_prefix_conflicts(d))
)
def test_manifest_round_trips_through_canonical_json(values: dict[str, Any]) -> None:
  manifest = parse_manifest({'scireport': '1.0', 'meta': {'title': 'T'}, 'values': values})
  text = manifest_to_json(manifest)
  again = parse_manifest(json.loads(text))
  assert again == manifest
  assert manifest_to_json(again) == text
  assert list(manifest_to_dict(manifest)['values']) == sorted(values)
  assert Manifest.model_validate(manifest_to_dict(manifest)) == manifest


# ---- pack / unpack round trips ----------------------------------------------------------------

COLUMN = st.one_of(
  st.lists(st.one_of(st.none(), st.integers(-(2**40), 2**40)), min_size=1, max_size=6),
  st.lists(
    st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False)), min_size=1, max_size=6
  ),
  st.lists(st.one_of(st.none(), st.text(max_size=10)), min_size=1, max_size=6),
)


@st.composite
def reports(draw: st.DrawFn) -> Report:
  report = Report(
    draw(st.text(min_size=1, max_size=20)),
    authors=draw(st.lists(st.text(min_size=1, max_size=10), max_size=2)),
  )
  report.add_text(
    'text', draw(st.text(max_size=6000)), format=draw(st.sampled_from(['plain', 'markdown']))
  )
  report.add_number(
    'number',
    draw(st.one_of(st.integers(-(2**40), 2**40), st.floats(allow_nan=True, allow_infinity=False))),
  )
  rows = draw(st.integers(min_value=1, max_value=5))
  columns = {
    f'c{i}': draw(COLUMN)[:rows] for i in range(draw(st.integers(min_value=1, max_value=3)))
  }
  height = min(len(values) for values in columns.values())
  report.add_table(
    'table',
    {name: values[:height] for name, values in columns.items()},
    format=draw(st.sampled_from(['parquet', 'csv'])),
  )
  report.add_attachment('blob', draw(st.binary(max_size=2000)), filename='blob.bin')
  report.add_list('items', draw(st.lists(JSON_VALUES, max_size=3)))
  return report


@settings(max_examples=25)
@given(reports())
def test_pack_unpack_round_trips_are_lossless_and_byte_stable(report: Report) -> None:
  with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    first = report.write(root / 'a.scireport.zip')
    with open_bundle(first) as bundle:
      assert bundle.verify() == []
      manifest_text = manifest_to_json(bundle.manifest)
      unpacked = write_bundle(bundle, root / 'a.scireport')
    with open_bundle(unpacked) as directory:
      assert directory.verify() == []
      assert manifest_to_json(directory.manifest) == manifest_text
      repacked = write_bundle(directory, root / 'b.scireport.zip')
    assert repacked.read_bytes() == first.read_bytes()
    as_file_tree = report.write(root / 'c.scireport')
    with open_bundle(as_file_tree) as built, open_bundle(first) as archived:
      assert built.asset_paths == archived.asset_paths
      for path in built.asset_paths:
        assert built.read_asset(path) == archived.read_asset(path)


@settings(max_examples=25)
@given(st.permutations(['a', 'b', 'c', 'd.e', 'f-g']))
def test_value_insertion_order_never_changes_the_bytes(order: list[str]) -> None:
  def build(keys: list[str]) -> Report:
    report = Report('Order')
    for key in keys:
      report.add_text(key, f'value of {key}')
    return report

  with tempfile.TemporaryDirectory() as tmp:
    reference = build(['a', 'b', 'c', 'd.e', 'f-g']).write(Path(tmp) / 'ref.zip').read_bytes()
    assert build(order).write(Path(tmp) / 'perm.zip').read_bytes() == reference
