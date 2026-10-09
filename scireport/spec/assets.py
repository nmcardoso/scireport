"""Asset references: where a bundle's binary and long-text files live and how they are checked.

Every asset in a bundle sits under ``assets/<folder>/`` and is referenced from the manifest with
its path, SHA-256 and size (ADR-0001). Paths are restricted to a conservative character set so
that a bundle unpacks identically on Linux, macOS and Windows.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator
from pydantic_core import PydanticCustomError

ASSET_ROOT = 'assets'
"""Top-level directory of every asset inside a bundle."""

ASSET_FOLDERS = ('attachments', 'figures', 'images', 'tables', 'text')
"""The folders under :data:`ASSET_ROOT`, organised by what the asset is."""

MAX_ASSET_PATH_CHARS = 180
"""Longest asset path, short enough for Windows once a bundle is unpacked in a deep folder."""

_SEGMENT_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')
_WINDOWS_RESERVED = frozenset(
  ['con', 'prn', 'aux', 'nul']
  + [f'com{n}' for n in range(1, 10)]
  + [f'lpt{n}' for n in range(1, 10)]
)

AssetResolver = Callable[[str], tuple[str, int]]
"""Looks up ``(sha256, bytes)`` for an asset path; raises ``FileNotFoundError`` when missing."""

RESOLVER_CONTEXT_KEY = 'resolve_asset'
"""Validation-context key under which the reader passes an :data:`AssetResolver` (authoring)."""


def asset_path_problem(path: object) -> str | None:
  """Explain why ``path`` is not an acceptable asset path.

  Parameters
  ----------
  path : object
      The candidate, a relative POSIX path such as ``assets/tables/crossmatch.pairs.parquet``.

  Returns
  -------
  str or None
      A one-line reason, or None when the path is acceptable.
  """
  if not isinstance(path, str) or not path:
    return 'the path must be a non-empty string'
  if len(path) > MAX_ASSET_PATH_CHARS:
    return f'the path is longer than {MAX_ASSET_PATH_CHARS} characters'
  if '\\' in path:
    return 'use "/" as separator, never a backslash'
  if path.startswith('/'):
    return 'the path must be relative to the bundle root, not absolute'
  parts = path.split('/')
  if len(parts) < 3 or parts[0] != ASSET_ROOT:
    return f'the path must look like {ASSET_ROOT}/<folder>/<file>'
  if parts[1] not in ASSET_FOLDERS:
    return f'the folder must be one of {", ".join(ASSET_FOLDERS)}, not {parts[1]!r}'
  for part in parts:
    if part in ('.', '..') or not part:
      return 'the path must not contain empty, "." or ".." segments'
    if _SEGMENT_RE.fullmatch(part) is None:
      return f'segment {part!r} must match [A-Za-z0-9][A-Za-z0-9._-]*'
    if part.endswith('.'):
      return f'segment {part!r} must not end with a dot (not portable to Windows)'
    if part.split('.', 1)[0].lower() in _WINDOWS_RESERVED:
      return f'segment {part!r} is a reserved name on Windows'
  return None


def _check_path(value: Any) -> str:
  """Pydantic hook: return ``value`` when it is an acceptable asset path, else raise ``E404``."""
  problem = asset_path_problem(value)
  if problem is not None:
    raise PydanticCustomError(
      'E404', 'invalid asset path {path}: {problem}', {'path': repr(value), 'problem': problem}
    )
  return str(value)


class AssetRef(BaseModel):
  """A reference to one file in ``assets/``, with its integrity data.

  When the reader opens a hand-authored directory it passes a resolver in the validation
  context, and ``sha256`` and ``bytes`` may then be left out or the whole reference written as
  the bare path; ``pack`` writes the completed manifest. In a sealed bundle both are required.

  Parameters
  ----------
  path : str
      Relative POSIX path under ``assets/``.
  sha256 : str
      Lowercase hexadecimal SHA-256 of the file.
  bytes : int
      Size of the file in bytes.
  """

  model_config = ConfigDict(extra='forbid', frozen=True)

  path: Annotated[str, Field(json_schema_extra={'pattern': f'^{ASSET_ROOT}/'})]
  sha256: Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
  bytes: Annotated[int, Field(ge=0)]

  @model_validator(mode='before')
  @classmethod
  def _prepare(cls, data: Any, info: ValidationInfo) -> Any:
    """Check the path and, in authoring mode, fill in the hash and size from disk."""
    resolver = (info.context or {}).get(RESOLVER_CONTEXT_KEY)
    if resolver is not None and isinstance(data, str):
      data = {'path': data}
    if isinstance(data, dict) and 'path' in data:
      data = {**data, 'path': _check_path(data['path'])}
      if resolver is not None and not {'sha256', 'bytes'} <= data.keys():
        try:
          digest, size = resolver(data['path'])
        except FileNotFoundError:
          raise PydanticCustomError(
            'E401', 'asset file {path} does not exist', {'path': data['path']}
          ) from None
        data = {**data, 'sha256': data.get('sha256', digest), 'bytes': data.get('bytes', size)}
    return data
