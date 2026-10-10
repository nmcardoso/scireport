"""The plain-data descriptions that the CLI, the MCP server and the skill share."""

from __future__ import annotations

import json

import pytest

from scireport import PreprocessError, TemplateError
from scireport.agent import catalogue
from scireport.errors import CODES


def test_listings_are_json_ready() -> None:
  for rows in (
    catalogue.list_templates_data(),
    catalogue.list_layouts_data(),
    catalogue.list_preprocessors_data(),
    catalogue.spec_kinds(),
  ):
    assert rows
    json.dumps(rows)
  refs = {row['ref'] for row in catalogue.list_templates_data()}
  assert {'generic@1', 'kitchen-sink@1'} <= refs


def test_describe_template_lists_the_contract() -> None:
  detail = catalogue.describe_template('kitchen-sink@1')
  assert detail['ref'] == 'kitchen-sink@1' and detail['formats']
  keys = {field['key'] for field in detail['fields']}
  assert keys and all(field['kinds'] for field in detail['fields'])
  json.dumps(detail)


def test_describe_layout_lists_options_and_engines() -> None:
  detail = catalogue.describe_layout('default@1')
  assert detail['pdf_engines'] == ['weasyprint', 'latex']
  paper = next(o for o in detail['options'] if o['name'] == 'paper')
  assert paper['default'] == 'a4' and paper['choices'] == ['a4', 'letter']


def test_describe_preprocessor_has_ports_and_a_parameter_schema() -> None:
  detail = catalogue.describe_preprocessor('core.histogram')
  assert detail['inputs'] and detail['outputs'] and detail['params']['type'] == 'object'
  assert catalogue.describe_preprocessor('core.histogram@1')['version'] == 1


def test_unknown_things_raise_coded_errors() -> None:
  with pytest.raises(TemplateError):
    catalogue.describe_template('nope')
  with pytest.raises(PreprocessError) as caught:
    catalogue.describe_preprocessor('nope.nothing')
  assert caught.value.code == 'E601'


def test_spec_schema_carries_its_version() -> None:
  schema = catalogue.spec_schema()
  assert schema['version'] == '1.0' and 'properties' in schema['schema']


def test_error_help_for_a_known_code_is_case_insensitive() -> None:
  info = catalogue.error_help(' e103 ')
  assert info['known'] is True and info['code'] == 'E103' and info['severity'] == 'error'
  assert info['title'] == CODES['E103'] and info['family'].startswith('keys')
  assert info['fix']
  assert catalogue.error_help('W401')['severity'] == 'warning'


def test_error_help_for_an_unknown_code_lists_its_family() -> None:
  info = catalogue.error_help('E199')
  assert info['known'] is False and 'E103' in info['similar']


def test_every_family_prefix_in_the_catalogue_is_described() -> None:
  assert {code[:2] for code in CODES} <= set(catalogue.FAMILIES)
