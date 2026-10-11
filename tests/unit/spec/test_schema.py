import json

import pytest
from helpers import asset_ref, minimal_manifest
from jsonschema import Draft202012Validator

from scireport.errors import SpecVersionError
from scireport.spec import schema as schema_module
from scireport.spec.manifest import manifest_to_dict, parse_manifest
from scireport.spec.schema import (
  SCHEMA_DIR,
  load_frozen_schema,
  manifest_json_schema,
  schema_filename,
  schema_for_version,
  schema_text,
)
from scireport.spec.version import SPEC_VERSION

FROZEN_VERSIONS = sorted(
  path.name.removeprefix('data-').removesuffix('.schema.json')
  for path in SCHEMA_DIR.glob('data-*.schema.json')
)


@pytest.mark.parametrize('version', FROZEN_VERSIONS)
def test_frozen_schema_has_not_drifted(version: str) -> None:
  """The pydantic models still generate exactly each frozen schema (ADR-0008)."""
  frozen = (SCHEMA_DIR / schema_filename(version)).read_text(encoding='utf-8')
  assert schema_text(manifest_json_schema(version)) == frozen, (
    f'the models no longer match spec/schemas/data-{version}.schema.json; a change to a '
    'released spec version needs a new version, see ADR-0008 (before 1.0.0 is released: '
    'make schema). Mark fields added in a later minor with json_schema_extra={"since": ...}'
  )


def test_a_schema_is_frozen_for_the_current_version() -> None:
  assert SPEC_VERSION in FROZEN_VERSIONS


def test_an_older_minor_version_is_generated_from_the_newer_models(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setattr(schema_module, 'SPEC_VERSION', '1.2')
  frozen = (SCHEMA_DIR / schema_filename('1.0')).read_text(encoding='utf-8')
  assert schema_text(manifest_json_schema('1.0')) == frozen
  assert manifest_json_schema('1.2')['properties']['scireport']['const'] == '1.2'


def test_later_additions_are_left_out_of_an_older_schema() -> None:
  schema = {
    '$defs': {
      'Old': {'type': 'object', 'properties': {'a': {'type': 'integer'}}},
      'New': {'type': 'object', 'since': '1.1'},
      'Holder': {
        'type': 'object',
        'properties': {
          'a': {'type': 'integer'},
          'b': {'type': 'integer', 'since': '1.1'},
          'c': {'$ref': '#/$defs/New'},
        },
        'required': ['a', 'b', 'c'],
      },
    },
    'oneOf': [{'$ref': '#/$defs/Old'}, {'$ref': '#/$defs/New'}],
    'discriminator': {
      'propertyName': 'kind',
      'mapping': {'old': '#/$defs/Old', 'new': '#/$defs/New'},
    },
  }
  older = schema_for_version(schema, '1.0')
  assert set(older['$defs']) == {'Old', 'Holder'}
  assert set(older['$defs']['Holder']['properties']) == {'a'}
  assert older['$defs']['Holder']['required'] == ['a']
  assert older['oneOf'] == [{'$ref': '#/$defs/Old'}]
  assert older['discriminator']['mapping'] == {'old': '#/$defs/Old'}
  newer = schema_for_version(schema, '1.1')
  assert set(newer['$defs']) == {'Old', 'New', 'Holder'}
  assert set(newer['$defs']['Holder']['properties']) == {'a', 'b', 'c'}
  assert 'since' not in json.dumps(newer)
  assert 'since' in json.dumps(schema)


def test_frozen_schema_is_a_valid_json_schema() -> None:
  schema = load_frozen_schema('1.0')
  Draft202012Validator.check_schema(schema)
  assert schema['properties']['scireport'] == {
    'const': '1.0',
    'type': 'string',
    'description': 'Spec version, MAJOR.MINOR.',
  }
  assert set(schema['required']) == {'scireport', 'meta'}


def full_manifest() -> dict[str, object]:
  raw = minimal_manifest(
    text='x',
    n={'kind': 'number', 'value': 1, 'uncertainty': 0.5},
    t={'kind': 'table', 'columns': [{'name': 'a'}], 'rows': [[1]]},
    f={'kind': 'figure', 'renditions': [asset_ref('assets/figures/f.png')], 'alt': 'a'},
    lst=[1, 'two', {'k': True}],
  )
  raw['outline'] = ['text', {'title': 'T', 'children': ['n']}]
  return raw


def test_canonical_manifests_validate_against_the_schema() -> None:
  validator = Draft202012Validator(load_frozen_schema('1.0'))
  canonical = manifest_to_dict(parse_manifest(full_manifest()))
  assert list(validator.iter_errors(canonical)) == []


@pytest.mark.parametrize(
  'mutate',
  [
    lambda m: m['values'].__setitem__('Bad Key', {'kind': 'bool', 'value': True}),
    lambda m: m['values'].__setitem__('x', {'kind': 'nonsense'}),
    lambda m: m['values']['f'].pop('alt'),
    lambda m: m['values']['f'].__setitem__('renditions', []),
    lambda m: m.__setitem__('scireport', '1.1'),
    lambda m: m.__setitem__('surprise', 1),
    lambda m: m['values']['n'].__setitem__('value', 'one'),
    lambda m: m['values']['f']['renditions'][0].pop('sha256'),
  ],
)
def test_invalid_manifests_fail_the_schema(mutate: object) -> None:
  validator = Draft202012Validator(load_frozen_schema('1.0'))
  canonical = json.loads(json.dumps(manifest_to_dict(parse_manifest(full_manifest()))))
  mutate(canonical)  # type: ignore[operator]
  assert list(validator.iter_errors(canonical))


def test_no_schema_for_a_newer_version_or_an_older_major() -> None:
  for newer in ('1.1', '2.0'):
    with pytest.raises(SpecVersionError) as info:
      manifest_json_schema(newer)
    assert info.value.code == 'E501'
  with pytest.raises(SpecVersionError) as info:
    manifest_json_schema('0.9')
  assert info.value.code == 'E503'
  with pytest.raises(FileNotFoundError):
    load_frozen_schema('9.9')
