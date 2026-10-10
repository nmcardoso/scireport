"""Pytest fixtures for the pre-processor tests (loaded as a plugin by ``tests/conftest.py``)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from preprocess_dummies import CALLS, entries

from scireport.preprocess import Preprocessor, register_preprocessor
from scireport.preprocess import registry as registry_module
from scireport.preprocess.registry import unregister_preprocessor


@pytest.fixture
def dummies() -> Iterator[list[Preprocessor]]:
  """Register the dummy pre-processors for one test and remove them after it."""
  CALLS.clear()
  made = entries()
  for entry in made:
    register_preprocessor(entry)
  yield made
  for entry in made:
    unregister_preprocessor(entry.name, entry.version)


@pytest.fixture
def fresh_discovery() -> Iterator[None]:
  """Let a test run plugin discovery again, and restore the discovery state after it."""
  state = dict(registry_module._STATE)
  registry_module._STATE['plugins'] = False
  yield
  registry_module._STATE.update(state)


@pytest.fixture
def no_builtins(dummies: list[Preprocessor]) -> Iterator[None]:
  """Register the dummies and skip the built-in catalogue: interface tests need no plot module."""
  state = dict(registry_module._STATE)
  registry_module._STATE['builtins'] = True
  yield
  registry_module._STATE.update(state)
