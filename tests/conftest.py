"""Shared fixtures and the hypothesis profile."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from helpers import PNG_BYTES
from hypothesis import HealthCheck, settings

settings.register_profile(
  'scireport',
  deadline=None,
  suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
settings.load_profile('scireport')


@pytest.fixture
def png_bytes() -> bytes:
  """Return a valid 1x1 PNG."""
  return PNG_BYTES


@pytest.fixture(autouse=True)
def _restore_logging() -> Iterator[None]:
  """Undo what ``setup_logging`` (called by CLI tests) does to the root logger."""
  root = logging.getLogger()
  handlers, level = list(root.handlers), root.level
  yield
  for handler in root.handlers:
    if handler not in handlers:
      handler.close()
  root.handlers[:] = handlers
  root.setLevel(level)
  logging.captureWarnings(False)
