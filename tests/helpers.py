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


def require_extra(module: str) -> None:
  """Skip the calling test when an optional extra is not installed.

  With ``SCIREPORT_REQUIRE_TOOLCHAIN=1`` (the dedicated CI jobs) a missing extra fails the test
  instead, so that a job can never go green by skipping.

  Parameters
  ----------
  module : str
      The importable name of the extra's package (``pypandoc``, ``mcp``).
  """
  import importlib.util
  import os

  import pytest

  if importlib.util.find_spec(module) is not None:
    return
  message = f'{module} is not installed (needs the matching scireport extra)'
  if os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1':
    pytest.fail(message)
  pytest.skip(message)


def need_the_frozen_pandoc() -> None:
  """Skip unless the installed pandoc is the one that made the frozen compat files.

  What pandoc writes depends on its version, so ``tests/compat/spec-1.0/pandoc-version.txt``
  records the version of the frozen files. With another version the caller skips, and fails with
  ``SCIREPORT_REQUIRE_TOOLCHAIN=1``: a pandoc upgrade is a decision, and the frozen files are never
  edited to follow it.
  """
  import os
  from pathlib import Path

  import pytest

  require_extra('pypandoc')
  from scireport.render.pandoc import pandoc_version

  frozen = (Path(__file__).parent / 'compat' / 'spec-1.0' / 'pandoc-version.txt').read_text(
    encoding='utf-8'
  )
  found = pandoc_version()
  if found == frozen.strip():
    return
  message = f'pandoc {found} is installed, the frozen files were made with pandoc {frozen.strip()}'
  if os.environ.get('SCIREPORT_REQUIRE_TOOLCHAIN') == '1':
    pytest.fail(message)
  pytest.skip(message)
