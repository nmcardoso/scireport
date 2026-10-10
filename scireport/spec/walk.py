"""Walk a manifest's values to find the assets they reference."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from scireport.spec.assets import AssetRef
from scireport.spec.kinds import (
  AttachmentValue,
  BibliographyValue,
  CodeValue,
  FigureValue,
  ImageValue,
  ListValue,
  MappingValue,
  TableValue,
  TextValue,
)

if TYPE_CHECKING:
  from scireport.spec.manifest import Manifest


def iter_assets(manifest: Manifest) -> Iterator[tuple[str, AssetRef]]:
  """Yield every asset reference in a manifest, in key order.

  Parameters
  ----------
  manifest : Manifest
      The manifest to walk.

  Yields
  ------
  tuple of (str, AssetRef)
      The JSON pointer of the reference and the reference. A path used by several values is
      yielded once per use.
  """
  for key in sorted(manifest.values):
    base = '/values/' + key.replace('~', '~0').replace('/', '~1')
    yield from _walk(manifest.values[key], base)


def _walk(value: object, pointer: str) -> Iterator[tuple[str, AssetRef]]:
  """Yield the references of one value, recursing into lists and mappings."""
  if isinstance(value, TextValue | CodeValue | TableValue):
    if value.asset is not None:
      yield f'{pointer}/asset', value.asset
  elif isinstance(value, ImageValue | AttachmentValue):
    yield f'{pointer}/asset', value.asset
  elif isinstance(value, BibliographyValue):
    yield f'{pointer}/asset', value.asset
    if value.csl is not None:
      yield f'{pointer}/csl', value.csl
  elif isinstance(value, FigureValue):
    for index, rendition in enumerate(value.renditions):
      yield f'{pointer}/renditions/{index}', rendition
    if value.data is not None:
      yield f'{pointer}/data', value.data
  elif isinstance(value, ListValue):
    for index, item in enumerate(value.items):
      yield from _walk(item, f'{pointer}/items/{index}')
  elif isinstance(value, MappingValue):
    for index, entry in enumerate(value.entries):
      yield from _walk(entry.value, f'{pointer}/entries/{index}/value')
