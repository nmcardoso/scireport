"""The content-hash cache of pre-processor results (ADR-0006).

A result is stored under the SHA-256 of everything that can change it: the pre-processor's name
and version, its validated parameters, the content hashes of its inputs, the keys it writes to
(asset file names contain them), its seed, the scireport version and the hash of the layout's
style files. The same inputs therefore never run twice, and a change of any of them is a miss.

An entry is a directory ``<root>/<hash[:2]>/<hash>/`` with ``entry.json`` (the values) and the
asset files under ``files/``. A damaged entry is a miss, never an error.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from scireport._version import __version__
from scireport.hashing import sha256_bytes
from scireport.logging_utils import get_logger
from scireport.spec.assets import AssetRef
from scireport.spec.kinds import Envelope, Value
from scireport.spec.walk import iter_assets

log = get_logger(__name__)

_ENTRY = 'entry.json'
_FILES = 'files'
_VALUES: TypeAdapter[dict[str, Envelope]] = TypeAdapter(dict[str, Value])


def default_cache_dir() -> Path:
  """Return the cache directory: ``$SCIREPORT_CACHE_DIR``, else ``$XDG_CACHE_HOME/scireport``.

  Returns
  -------
  pathlib.Path
      ``<cache home>/scireport/preprocess``; the directory is created on first write.
  """
  explicit = os.environ.get('SCIREPORT_CACHE_DIR')
  if explicit:
    return Path(explicit)
  home = os.environ.get('XDG_CACHE_HOME') or str(Path.home() / '.cache')
  return Path(home) / 'scireport' / 'preprocess'


def value_hash(value: Envelope) -> str:
  """Return a hash of a value's content: its envelope, which includes the hashes of its assets.

  Parameters
  ----------
  value : Envelope
      A value model.

  Returns
  -------
  str
      Lowercase hex SHA-256 of the canonical JSON of the envelope.
  """
  return sha256_bytes(_canonical(value.model_dump(mode='json', exclude_none=True)))


def cache_key(
  *,
  name: str,
  version: int,
  params: Mapping[str, Any],
  inputs: Mapping[str, str],
  outputs: Mapping[str, str],
  seed: int,
  style_hash: str,
) -> str:
  """Return the cache key of one step.

  Parameters
  ----------
  name : str
      Pre-processor name.
  version : int
      Pre-processor version.
  params : dict
      Validated parameters as JSON values.
  inputs : dict
      Input port to the content hash of its value (:func:`value_hash`).
  outputs : dict
      Output port to the key it is stored under.
  seed : int
      The step's seed.
  style_hash : str
      Hash of the layout's style and palette files.

  Returns
  -------
  str
      Lowercase hex SHA-256.
  """
  return sha256_bytes(
    _canonical(
      {
        'name': name,
        'version': version,
        'params': params,
        'inputs': dict(inputs),
        'outputs': dict(outputs),
        'seed': seed,
        'scireport': __version__,
        'style': style_hash,
      }
    )
  )


@dataclass(frozen=True)
class CacheEntry:
  """A stored result.

  Parameters
  ----------
  values : dict
      Output key to the value the step made.
  assets : dict
      Bundle-relative path to content, for the assets those values reference.
  """

  values: dict[str, Envelope]
  assets: dict[str, bytes]


class Cache:
  """A directory of cached step results.

  Parameters
  ----------
  root : pathlib.Path
      The cache directory.
  """

  def __init__(self, root: Path) -> None:
    self.root = root

  def load(self, key: str) -> CacheEntry | None:
    """Return the entry stored under ``key``, or None on a miss or a damaged entry.

    Parameters
    ----------
    key : str
        A :func:`cache_key`.

    Returns
    -------
    CacheEntry or None
        The stored result, with every asset checked against its recorded hash.
    """
    folder = self._folder(key)
    try:
      raw = json.loads((folder / _ENTRY).read_text(encoding='utf-8'))
      values = _VALUES.validate_python(raw['values'])
      assets: dict[str, bytes] = {}
      for _, ref in _refs(values):
        data = (folder / _FILES / ref.path).read_bytes()
        if sha256_bytes(data) != ref.sha256 or len(data) != ref.bytes:
          raise ValueError(f'asset {ref.path} does not match its hash')
        assets[ref.path] = data
    except FileNotFoundError:
      return None
    except (ValueError, KeyError, OSError) as exc:
      log.warning('ignoring a damaged cache entry %s: %s', key[:12], exc)
      return None
    return CacheEntry(values=values, assets=assets)

  def store(self, key: str, entry: CacheEntry) -> None:
    """Store a result under ``key``, atomically.

    Parameters
    ----------
    key : str
        A :func:`cache_key`.
    entry : CacheEntry
        The result to keep.
    """
    folder = self._folder(key)
    staging = folder.with_name(f'{folder.name}.tmp{os.getpid()}')
    shutil.rmtree(staging, ignore_errors=True)
    for path, data in entry.assets.items():
      target = staging / _FILES / path
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_bytes(data)
    staging.mkdir(parents=True, exist_ok=True)
    payload = {
      'values': {k: v.model_dump(mode='json', exclude_none=True) for k, v in entry.values.items()}
    }
    (staging / _ENTRY).write_text(
      json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )
    shutil.rmtree(folder, ignore_errors=True)
    folder.parent.mkdir(parents=True, exist_ok=True)
    staging.replace(folder)

  def _folder(self, key: str) -> Path:
    """Return the directory of an entry."""
    return self.root / key[:2] / key


def _refs(values: Mapping[str, Envelope]) -> list[tuple[str, AssetRef]]:
  """List the asset references of some values."""
  from scireport.spec.manifest import Manifest, Meta

  holder = Manifest.model_construct(
    scireport='1.0', meta=Meta.model_construct(title='cache'), values=dict(values)
  )
  return list(iter_assets(holder))


def _canonical(payload: Any) -> bytes:
  """Return canonical JSON bytes: sorted keys, no spaces, UTF-8."""
  return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
