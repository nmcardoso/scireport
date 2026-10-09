"""Spec versions: parsing, comparison and the readability check (ADR-0008)."""

from __future__ import annotations

import re
from typing import Any

from scireport.errors import SpecVersionError

SPEC_VERSION = '1.0'
"""The newest data-file specification this scireport reads and writes (``MAJOR.MINOR``)."""

_VERSION_RE = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
UPGRADE_HINT = 'Upgrade scireport (uv add -U scireport, or pip install -U scireport).'


def parse_version(text: str) -> tuple[int, int]:
  """Parse ``'MAJOR.MINOR'`` into a tuple of integers.

  Parameters
  ----------
  text : str
      A spec version such as ``'1.0'``.

  Returns
  -------
  tuple of (int, int)
      Major and minor version.

  Raises
  ------
  SpecVersionError
      With code ``E502`` when ``text`` is not ``MAJOR.MINOR``.
  """
  match = _VERSION_RE.fullmatch(text) if isinstance(text, str) else None
  if match is None:
    raise SpecVersionError(
      f'spec version {text!r} is not of the form MAJOR.MINOR',
      code='E502',
      hint='Write the version as a string such as "1.0".',
    )
  return int(match.group(1)), int(match.group(2))


def read_version(raw: Any) -> tuple[int, int]:
  """Return the spec version stored in a parsed manifest.

  Parameters
  ----------
  raw : Any
      The parsed manifest.

  Returns
  -------
  tuple of (int, int)
      Major and minor version.

  Raises
  ------
  SpecVersionError
      With code ``E502`` when ``raw`` has no well-formed ``scireport`` entry.
  """
  if not isinstance(raw, dict) or 'scireport' not in raw:
    raise SpecVersionError(
      'the manifest has no "scireport" entry with the spec version',
      code='E502',
      hint='Add "scireport": "1.0" at the top level of the manifest.',
    )
  return parse_version(raw['scireport'])


def check_readable(raw: Any, *, supported: str = SPEC_VERSION) -> tuple[int, int]:
  """Check that a manifest dict has a spec version this scireport can read natively.

  Older minor versions of the supported major are read natively. A newer minor or major gives
  ``E501`` with an upgrade hint; an older major gives ``E503``.

  Parameters
  ----------
  raw : Any
      The parsed manifest. Anything that is not a mapping with a ``scireport`` entry gives
      ``E502``.
  supported : str, default=SPEC_VERSION
      The newest version the caller can read.

  Returns
  -------
  tuple of (int, int)
      The version found in ``raw``.

  Raises
  ------
  SpecVersionError
      With code ``E501``, ``E502`` or ``E503``.
  """
  found = read_version(raw)
  newest = parse_version(supported)
  if found[0] < newest[0]:
    raise SpecVersionError(
      f'spec version {raw["scireport"]} is older than the oldest major this scireport migrates '
      f'(reads {newest[0]}.x)',
      code='E503',
      hint='Run "scireport spec migrate" with a scireport release that still knows that version.',
    )
  if found > newest:
    raise SpecVersionError(
      f'this bundle uses spec {raw["scireport"]}, newer than the {supported} this scireport reads',
      code='E501',
      hint=UPGRADE_HINT,
    )
  return found
