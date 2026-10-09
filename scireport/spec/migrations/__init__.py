"""Migrations between spec versions: pure ``dict -> dict`` functions (ADR-0008).

Minor versions are additive, so every older minor reads natively and needs no migration. A major
bump ships a function registered with :func:`register_migration` that turns a manifest of major
``N`` into one of major ``N + 1``; :func:`migrate` chains them. Version 1.0 is the baseline and
has nothing to migrate from (see :mod:`scireport.spec.migrations.v1_0`).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from scireport.errors import SpecVersionError
from scireport.spec.migrations.v1_0 import migrate_to_1_0
from scireport.spec.version import SPEC_VERSION, parse_version, read_version

Migration = Callable[[dict[str, Any]], dict[str, Any]]
"""A pure function from a manifest dict of one major version to the next major version."""

_STEPS: dict[int, Migration] = {}


def register_migration(from_major: int) -> Callable[[Migration], Migration]:
  """Register the migration from ``from_major`` to ``from_major + 1``.

  Parameters
  ----------
  from_major : int
      The major version the function reads.

  Returns
  -------
  callable
      A decorator that registers and returns the function. The function must not mutate its
      argument and must return a manifest whose ``scireport`` entry names the new major.
  """

  def decorator(func: Migration) -> Migration:
    _STEPS[from_major] = func
    return func

  return decorator


def migrate(raw: dict[str, Any], *, target: str = SPEC_VERSION) -> dict[str, Any]:
  """Bring a manifest dict to the ``target`` spec version.

  A manifest already at the target major is returned as an unchanged copy, except that an older
  minor is re-stamped with ``target``.

  Parameters
  ----------
  raw : dict
      A parsed manifest. It is not modified.
  target : str, default=SPEC_VERSION
      The version wanted; not newer than this scireport writes.

  Returns
  -------
  dict
      A new dict at the target version.

  Raises
  ------
  SpecVersionError
      With code ``E501`` when the manifest or the target is newer than this scireport, ``E502``
      when a version is malformed or missing, ``E503`` when a major step has no migration.
  """
  newest = parse_version(SPEC_VERSION)
  wanted = parse_version(target)
  if wanted > newest:
    raise SpecVersionError(
      f'cannot migrate to spec {target}; this scireport writes {SPEC_VERSION}', code='E501'
    )
  found = read_version(raw)
  if found > wanted:
    raise SpecVersionError(
      f'manifest is spec {raw["scireport"]}, newer than the requested {target}', code='E501'
    )
  out = migrate_to_1_0(raw)
  major = found[0]
  while major < wanted[0]:
    step = _STEPS.get(major)
    if step is None:
      raise SpecVersionError(f'no migration from spec {major}.x to {major + 1}.0', code='E503')
    out = step(out)
    major += 1
  out['scireport'] = target
  return out
