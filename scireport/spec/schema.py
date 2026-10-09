"""JSON Schemas for the data file, generated from the pydantic models (ADR-0008).

The frozen schema of each spec version lives in ``scireport/spec/schemas/`` and a test fails when
the models drift from it. The schema describes the canonical manifest, in which every value is an
envelope; loaders also accept the bare-JSON shorthand of :mod:`scireport.spec.kinds`, and a
hand-authored directory may leave out asset hashes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scireport.errors import SpecVersionError
from scireport.spec.manifest import Manifest
from scireport.spec.version import SPEC_VERSION, parse_version

SCHEMA_DIR = Path(__file__).resolve().parent / 'schemas'
"""Folder with the frozen schema files, shipped as package data."""

SCHEMA_ID = 'https://nmcardoso.github.io/scireport/schemas/data-{version}.schema.json'


def schema_filename(version: str = SPEC_VERSION) -> str:
  """Return the file name of the schema for a spec version.

  Parameters
  ----------
  version : str, default=SPEC_VERSION
      A spec version such as ``'1.0'``.

  Returns
  -------
  str
      For example ``data-1.0.schema.json``.
  """
  return f'data-{version}.schema.json'


def manifest_json_schema(version: str = SPEC_VERSION) -> dict[str, Any]:
  """Generate the JSON Schema of the manifest for the current spec version.

  Parameters
  ----------
  version : str, default=SPEC_VERSION
      Must equal the version this scireport writes; older schemas are read from
      :data:`SCHEMA_DIR` with :func:`load_frozen_schema`.

  Returns
  -------
  dict
      A JSON Schema (draft 2020-12) document.

  Raises
  ------
  SpecVersionError
      With code ``E501`` when ``version`` is newer than this scireport, or ``E503`` when it is
      older (use the frozen file).
  """
  if parse_version(version) != parse_version(SPEC_VERSION):
    raise SpecVersionError(
      f'cannot generate the schema of spec {version}; this scireport writes {SPEC_VERSION}',
      code='E501' if parse_version(version) > parse_version(SPEC_VERSION) else 'E503',
    )
  schema: dict[str, Any] = Manifest.model_json_schema()
  schema = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    '$id': SCHEMA_ID.format(version=version),
    **schema,
  }
  schema['title'] = f'scireport data file {version}'
  schema['description'] = (
    'The canonical manifest (scireport.json) of a scireport bundle. Every value is an envelope '
    'with a "kind". Loaders also accept bare JSON as shorthand (a string is text, a number is a '
    'number, an array is a list, an object without "kind" is a mapping) and, in hand-authored '
    'directories, asset references without sha256 and bytes.'
  )
  schema['properties']['scireport'] = {
    'const': version,
    'type': 'string',
    'description': 'Spec version, MAJOR.MINOR.',
  }
  schema['properties']['values']['additionalProperties'] = False
  return schema


def schema_text(schema: dict[str, Any]) -> str:
  """Serialise a schema the way the frozen files are stored.

  Parameters
  ----------
  schema : dict
      A schema from :func:`manifest_json_schema`.

  Returns
  -------
  str
      Two-space-indented JSON with sorted keys, ending in a newline.
  """
  return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + '\n'


def load_frozen_schema(version: str = SPEC_VERSION) -> dict[str, Any]:
  """Load the frozen schema file of a spec version.

  Parameters
  ----------
  version : str, default=SPEC_VERSION
      A spec version such as ``'1.0'``.

  Returns
  -------
  dict
      The schema as stored in the package.

  Raises
  ------
  FileNotFoundError
      When no schema was frozen for ``version``.
  """
  path = SCHEMA_DIR / schema_filename(version)
  loaded: dict[str, Any] = json.loads(path.read_text(encoding='utf-8'))
  return loaded
