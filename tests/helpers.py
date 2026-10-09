"""Helpers imported by test modules (``tests`` is on ``sys.path``)."""

from __future__ import annotations

from typing import Any

PNG_BYTES = (
  b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f'
  b'\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00'
  b'\x00IEND\xaeB`\x82'
)
SHA_A = 'a' * 64


def asset_ref(path: str, sha: str = SHA_A, size: int = 1) -> dict[str, Any]:
  """Return an asset reference dict for use in hand-written manifests."""
  return {'path': path, 'sha256': sha, 'bytes': size}


def minimal_manifest(**values: Any) -> dict[str, Any]:
  """Return a minimal manifest dict holding ``values``."""
  return {'scireport': '1.0', 'meta': {'title': 'T'}, 'values': values}
