"""Typed ports: what a pre-processor takes in and gives out (ADR-0006).

A port names a *kind* of value (``table``, ``figure``, ``number`` ...) or ``any``. The plan checks
that the value wired to an input has the port's kind before anything runs, so a figure is never
passed where a table is expected.
"""

from __future__ import annotations

from dataclasses import dataclass

from scireport.spec.kinds import KINDS

ANY = 'any'
"""The port kind that accepts a value of any kind."""

PORT_KINDS: tuple[str, ...] = (*KINDS, ANY)
"""Every kind a port may name."""


@dataclass(frozen=True)
class Port:
  """One input or output of a pre-processor.

  Parameters
  ----------
  kind : str
      A v1.0 value kind (``'table'``, ``'figure'``, ...) or ``'any'``.
  optional : bool, default=False
      An optional input may be left unwired (the function then gets ``None``); an optional
      output may be left out of the function's result.
  description : str, default=''
      One line saying what the port carries, shown by ``scireport preprocessors``.

  Raises
  ------
  ValueError
      When ``kind`` is not a value kind or ``'any'``.
  """

  kind: str
  optional: bool = False
  description: str = ''

  def __post_init__(self) -> None:
    """Reject a kind that no value can have."""
    if self.kind not in PORT_KINDS:
      raise ValueError(f'port kind must be one of {", ".join(PORT_KINDS)}, got {self.kind!r}')

  def accepts(self, kind: str) -> bool:
    """Return whether a value of ``kind`` can be wired to this port.

    Parameters
    ----------
    kind : str
        The kind of the value.

    Returns
    -------
    bool
        True when the port is ``any`` or has exactly this kind.
    """
    return self.kind == ANY or self.kind == kind
