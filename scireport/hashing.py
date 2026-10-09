"""SHA-256 helpers shared by the spec, the bundle reader and the writer."""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_BYTES = 1 << 20
"""Read size, in bytes, used when hashing a file or a stream."""


def sha256_bytes(data: bytes) -> str:
  """Return the lowercase hex SHA-256 of ``data``.

  Parameters
  ----------
  data : bytes
      The content to hash.

  Returns
  -------
  str
      64 hexadecimal characters.
  """
  return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> tuple[str, int]:
  """Hash a file without loading it whole.

  Parameters
  ----------
  path : pathlib.Path
      The file to read.

  Returns
  -------
  tuple of (str, int)
      The lowercase hex SHA-256 and the size in bytes.
  """
  digest = hashlib.sha256()
  size = 0
  with path.open('rb') as handle:
    while chunk := handle.read(CHUNK_BYTES):
      digest.update(chunk)
      size += len(chunk)
  return digest.hexdigest(), size
