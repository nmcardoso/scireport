"""The 1.0 baseline: the first spec version, so there is nothing to migrate from."""

from __future__ import annotations

import copy
from typing import Any

BASELINE = (1, 0)
"""Oldest spec version scireport knows."""


def migrate_to_1_0(raw: dict[str, Any]) -> dict[str, Any]:
  """Return an independent copy of a 1.0 manifest; there is nothing to change.

  Every later version module has the same shape (``migrate_to_X_Y``) and does its real work
  here, so the chain in :func:`scireport.spec.migrations.migrate` always starts from a copy.

  Parameters
  ----------
  raw : dict
      A manifest at spec 1.0.

  Returns
  -------
  dict
      A deep copy of ``raw``.
  """
  return copy.deepcopy(raw)
