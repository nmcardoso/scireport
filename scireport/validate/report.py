"""The result of validating a bundle against a template and layout (ADR-0005)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from scireport.errors import Issue, RenderError

EXIT_OK = 0
EXIT_VALIDATION = 2


@dataclass(frozen=True)
class ValidationReport:
  """Every problem found, aggregated, with the strictness that decides what counts as failure.

  Parameters
  ----------
  issues : tuple of Issue
      All issues, in the order they were found, errors and warnings together.
  strict : bool, default=False
      Treat warnings as errors (``--strict``).
  """

  issues: tuple[Issue, ...]
  strict: bool = False

  @property
  def errors(self) -> tuple[Issue, ...]:
    """The issues that make validation fail: errors, and warnings too when strict."""
    return tuple(i for i in self.issues if i.severity == 'error' or self.strict)

  @property
  def warnings(self) -> tuple[Issue, ...]:
    """The warnings that do not make validation fail (none when strict)."""
    return () if self.strict else tuple(i for i in self.issues if i.severity == 'warning')

  @property
  def ok(self) -> bool:
    """Whether validation passed."""
    return not self.errors

  @property
  def exit_code(self) -> int:
    """The process exit code: 0 when it passed, 2 when it did not."""
    return EXIT_OK if self.ok else EXIT_VALIDATION

  def to_dict(self) -> dict[str, Any]:
    """Return the report as JSON-ready data, the format of ``--json``.

    Returns
    -------
    dict
        ``ok``, ``strict``, ``exit_code``, ``counts`` and ``issues``.
    """
    return {
      'ok': self.ok,
      'strict': self.strict,
      'exit_code': self.exit_code,
      'counts': {
        'errors': sum(1 for i in self.issues if i.severity == 'error'),
        'warnings': sum(1 for i in self.issues if i.severity == 'warning'),
      },
      'issues': [issue.to_dict() for issue in self.issues],
    }

  def raise_for_errors(self) -> None:
    """Raise :class:`~scireport.errors.RenderError` with every issue when validation failed.

    Raises
    ------
    RenderError
        Carrying all issues, errors first.
    """
    if not self.ok:
      ordered = sorted(self.issues, key=lambda i: i.severity != 'error' and not self.strict)
      raise RenderError(ordered)


def dedupe(issues: Iterable[Issue]) -> list[Issue]:
  """Drop repeated issues (one problem found in several formats), keeping the order."""
  seen: set[Issue] = set()
  out = []
  for issue in issues:
    if issue not in seen:
      seen.add(issue)
      out.append(issue)
  return out
