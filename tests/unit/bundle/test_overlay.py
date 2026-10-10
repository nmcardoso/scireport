from __future__ import annotations

import pytest

from scireport.bundle import MemoryBackend
from scireport.bundle.backends import OverlayBackend


class _Closing(MemoryBackend):
  closed = False

  def close(self) -> None:
    self.closed = True


def test_top_files_shadow_base_files_and_names_are_merged() -> None:
  overlay = OverlayBackend(
    MemoryBackend({'a': b'base-a', 'b': b'base-b'}), MemoryBackend({'b': b'top-b', 'c': b'top-c'})
  )
  assert overlay.names() == ['a', 'b', 'c']
  assert overlay.read('a') == b'base-a'
  assert overlay.read('b') == b'top-b'
  assert overlay.size('c') == 5
  with overlay.open('b') as handle:
    assert handle.read() == b'top-b'


def test_a_missing_name_is_file_not_found() -> None:
  overlay = OverlayBackend(MemoryBackend({}), MemoryBackend({}))
  with pytest.raises(FileNotFoundError):
    overlay.read('nope')


def test_closing_closes_both() -> None:
  base, top = _Closing({}), _Closing({})
  OverlayBackend(base, top).close()
  assert base.closed and top.closed
