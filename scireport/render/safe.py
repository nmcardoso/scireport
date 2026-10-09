"""The marker for text that is already written in the target format and must not be escaped."""

from __future__ import annotations


class Safe(str):
  """A string that is already valid in the output format being written.

  Components and the ``md`` filter return :class:`Safe` strings. The environments of the three
  formats leave them alone when a template interpolates them, and escape every other string.
  The ``__html__`` hook makes Jinja's HTML autoescaping accept them as well.
  """

  __slots__ = ()

  def __html__(self) -> str:
    """Return the text unchanged, so that autoescaping does not touch it."""
    return str(self)

  def __repr__(self) -> str:
    """Return ``Safe('...')`` so that test failures show what was marked safe."""
    return f'Safe({str(self)!r})'


EMPTY = Safe('')
"""The empty safe string, returned by components that render nothing."""
