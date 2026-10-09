"""Summarise a bundle as plain data, for the ``inspect`` command and agents."""

from __future__ import annotations

from collections import Counter
from typing import Any

from scireport.bundle.reader import Bundle
from scireport.spec.kinds import (
  AlertValue,
  BoolValue,
  CodeValue,
  DateValue,
  Envelope,
  FigureValue,
  FlowValue,
  ImageValue,
  ListValue,
  MappingValue,
  MathValue,
  MetricsValue,
  NumberValue,
  StatusValue,
  TableValue,
  TextValue,
)
from scireport.spec.walk import iter_assets

SUMMARY_CHARS = 60


def summarise_value(value: Envelope) -> str:
  """Describe one value in a short line.

  Parameters
  ----------
  value : Envelope
      Any value.

  Returns
  -------
  str
      For example ``3,061 × 8 columns, parquet`` for a table or ``Hello wor…`` for text.
  """
  if isinstance(value, TextValue):
    body = (
      value.text if value.text is not None else f'file {value.asset.path}' if value.asset else ''
    )
    return f'{value.format}: {_clip(body)}'
  if isinstance(value, NumberValue):
    if value.value is None:
      return 'missing'
    parts = [str(value.value)]
    if value.uncertainty is not None:
      parts.append(f'± {value.uncertainty}')
    if value.interval is not None:
      parts.append(f'[{value.interval[0]}, {value.interval[1]}]')
    if value.unit:
      parts.append(value.unit)
    return ' '.join(parts)
  if isinstance(value, BoolValue | DateValue):
    return str(value.value)
  if isinstance(value, ListValue):
    return f'{len(value.items)} items'
  if isinstance(value, MappingValue):
    return f'{len(value.entries)} entries'
  if isinstance(value, TableValue):
    rows = '?' if value.n_rows is None else f'{value.n_rows:,}'
    cols = f'{len(value.columns)} columns, ' if value.columns else ''
    return f'{rows} rows, {cols}{value.format}'
  if isinstance(value, FigureValue):
    return f'{", ".join(r.format for r in value.renditions)}; {_clip(value.alt)}'
  if isinstance(value, ImageValue):
    return value.asset.path.rpartition('/')[2]
  if isinstance(value, MathValue):
    return _clip(value.latex)
  if isinstance(value, CodeValue):
    return f'{value.language or "text"}, {len(value.source or "")} chars'
  if isinstance(value, MetricsValue):
    return f'{len(value.items)} tiles'
  if isinstance(value, StatusValue | AlertValue):
    return (
      f'{value.level}: {_clip(value.headline if isinstance(value, StatusValue) else value.text)}'
    )
  if isinstance(value, FlowValue):
    return f'{len(value.stages)} stages'
  return f'{value.filename} ({value.asset.bytes:,} bytes)'


def inspect_bundle(bundle: Bundle, *, verify: bool = True) -> dict[str, Any]:
  """Summarise a bundle: metadata, every value and the integrity check.

  Parameters
  ----------
  bundle : Bundle
      An opened bundle.
  verify : bool, default=True
      Check every asset's size and SHA-256 (reads all assets).

  Returns
  -------
  dict
      JSON-ready: ``spec``, ``form``, ``meta``, ``render``, ``counts`` (values per kind),
      ``values`` (key, kind, summary, assets), ``assets`` (count and bytes), ``issues`` and
      ``ok``.
  """
  manifest = bundle.manifest
  assets_by_key: dict[str, list[str]] = {}
  for pointer, ref in iter_assets(manifest):
    key = pointer.split('/')[2].replace('~1', '/').replace('~0', '~')
    assets_by_key.setdefault(key, []).append(ref.path)
  issues = [issue.to_dict() for issue in bundle.verify()] if verify else []
  declared = [bundle.asset_ref(path) for path in bundle.asset_paths]
  return {
    'spec': manifest.scireport,
    'form': bundle.form,
    'source': bundle.source.as_posix() if bundle.source else None,
    'meta': manifest.meta.model_dump(mode='json', exclude_none=True),
    'render': manifest.render.model_dump(mode='json', exclude_none=True),
    'counts': dict(sorted(Counter(v.kind for v in manifest.values.values()).items())),
    'values': [
      {
        'key': key,
        'kind': manifest.values[key].kind,
        'summary': summarise_value(manifest.values[key]),
        'assets': sorted(set(assets_by_key.get(key, []))),
      }
      for key in sorted(manifest.values)
    ],
    'assets': {'count': len(declared), 'bytes': sum(ref.bytes for ref in declared)},
    'verified': verify,
    'issues': issues,
    'ok': not any(issue['severity'] == 'error' for issue in issues),
  }


def _clip(text: str) -> str:
  """Shorten ``text`` to one line of at most ``SUMMARY_CHARS`` characters."""
  line = ' '.join(text.split())
  return line if len(line) <= SUMMARY_CHARS else line[: SUMMARY_CHARS - 1] + '…'
