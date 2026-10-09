"""The data-file specification: models, key grammar, versions, schemas and migrations."""

from __future__ import annotations

from scireport.spec.assets import AssetRef
from scireport.spec.keys import Key, is_valid_key, join_key, split_key
from scireport.spec.kinds import KINDS, Value, canonicalise, value_adapter
from scireport.spec.manifest import (
  Manifest,
  check_manifest,
  manifest_to_dict,
  manifest_to_json,
  parse_manifest,
)
from scireport.spec.version import SPEC_VERSION

__all__ = [
  'KINDS',
  'SPEC_VERSION',
  'AssetRef',
  'Key',
  'Manifest',
  'Value',
  'canonicalise',
  'check_manifest',
  'is_valid_key',
  'join_key',
  'manifest_to_dict',
  'manifest_to_json',
  'parse_manifest',
  'split_key',
  'value_adapter',
]
