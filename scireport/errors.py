"""Error classes and the stable error-code catalogue (ADR-0005, ADR-0008).

Every problem scireport reports carries a code (``E`` for errors, ``W`` for warnings) that never
changes meaning once released. The families are ``E1xx`` keys, ``E2xx`` kinds and value fields,
``E3xx`` table schema, ``E4xx`` assets and bundles, ``E5xx`` spec versions and ``W4xx`` unused
items. Phase S2 extends the catalogue with the template and render codes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

CODES: dict[str, str] = {
  'E101': 'Key does not follow the key grammar',
  'E102': 'Key is both a value and the prefix of another key',
  'E103': 'Reference to a key that does not exist',
  'E104': 'Key is already in use',
  'E201': 'Unknown kind',
  'E202': 'Value has the wrong kind for this use',
  'E203': 'Required field is missing',
  'E204': 'Unexpected field',
  'E205': 'Field has an invalid value',
  'E206': 'Exactly one of several fields must be given',
  'E301': 'Inline table rows do not match its columns',
  'E302': 'Table column definitions are inconsistent',
  'E401': 'Asset file is missing from the bundle',
  'E402': 'Asset sha256 does not match its file',
  'E403': 'Asset size does not match its file',
  'E404': 'Asset path is invalid or unsafe',
  'E405': 'Bundle is larger than the size cap',
  'E406': 'Not a scireport bundle',
  'E407': 'Archive entry rejected',
  'E408': 'Manifest cannot be parsed',
  'E409': 'Bundle form is not allowed here',
  'E410': 'Destination cannot be written',
  'E411': 'One asset path is declared with different hashes',
  'E501': 'Bundle was written by a newer spec version',
  'E502': 'Spec version is missing or malformed',
  'E503': 'Spec version is too old and has no migration',
  'W402': 'Asset file is not referenced by the manifest',
}
"""Code to one-line title. Documented in ``docs`` from phase S6."""


@dataclass(frozen=True)
class Issue:
  """One problem found in a manifest or bundle.

  Parameters
  ----------
  code : str
      Stable error code, a key of :data:`CODES`.
  message : str
      What is wrong, in plain words.
  pointer : str, default=''
      RFC 6901 JSON pointer into the manifest; the empty string is the whole document.
  key : str or None, default=None
      The value key concerned, when there is one.
  expected : str or None, default=None
      What was expected, when that can be said briefly.
  found : str or None, default=None
      What was found instead (truncated).
  hint : str or None, default=None
      A suggestion, for example the closest valid spelling.
  """

  code: str
  message: str
  pointer: str = ''
  key: str | None = None
  expected: str | None = None
  found: str | None = None
  hint: str | None = None

  @property
  def severity(self) -> str:
    """``'error'`` for ``E`` codes and ``'warning'`` for ``W`` codes."""
    return 'warning' if self.code.startswith('W') else 'error'

  def to_dict(self) -> dict[str, Any]:
    """Return the issue as a JSON-ready dict, omitting empty optional fields.

    Returns
    -------
    dict
        ``code``, ``severity``, ``message`` and the optional fields that are set.
    """
    out: dict[str, Any] = {
      'code': self.code,
      'severity': self.severity,
      'message': self.message,
    }
    for name in ('pointer', 'key', 'expected', 'found', 'hint'):
      value = getattr(self, name)
      if value:
        out[name] = value
    return out

  def describe(self) -> str:
    """Return the issue without its code: location, message, expected and found, hint.

    Returns
    -------
    str
        For example ``/values/a: key 'a' is also the prefix of 'a.b' (expected x, found y)``.
    """
    text = f'{self.pointer}: {self.message}' if self.pointer else self.message
    if self.expected is not None or self.found is not None:
      text += f' (expected {self.expected}, found {self.found})'
    if self.hint:
      text += f'. {self.hint}'
    return text

  def format(self) -> str:
    """Return a one-line human-readable rendering, starting with the code.

    Returns
    -------
    str
        For example ``E102 /values/a: key 'a' is also the prefix of 'a.b'``.
    """
    return f'{self.code} {self.describe()}'


class ScireportError(Exception):
  """Base class of every error scireport raises on purpose.

  Parameters
  ----------
  message : str
      Summary of the failure.
  code : str
      Stable error code of the first or only problem.
  hint : str or None, default=None
      What to do about it.
  issues : list of Issue or None, default=None
      Every problem found, when the failure aggregates several. Defaults to one issue built
      from ``code`` and ``message``.
  """

  exit_code = 2
  """Process exit code of the CLI: 2 for validation problems (the default)."""

  def __init__(
    self,
    message: str,
    *,
    code: str,
    hint: str | None = None,
    issues: list[Issue] | None = None,
  ) -> None:
    super().__init__(message)
    self.message = message
    self.code = code
    self.hint = hint
    self.issues: list[Issue] = issues if issues is not None else [Issue(code, message, hint=hint)]

  def __str__(self) -> str:
    """Return the code, the message and the hint on one line."""
    text = f'{self.code}: {self.message}'
    return f'{text}. {self.hint}' if self.hint else text


class SpecError(ScireportError):
  """A manifest does not match the data-file specification (E1xx to E3xx)."""

  def __init__(self, issues: list[Issue]) -> None:
    first = issues[0]
    summary = (
      first.format() if len(issues) == 1 else f'{len(issues)} problems, first: {first.format()}'
    )
    super().__init__(summary, code=first.code, issues=issues)


class SpecVersionError(ScireportError):
  """The spec version of a bundle cannot be read by this scireport (E5xx)."""


class BundleError(ScireportError):
  """A bundle cannot be read or written (E4xx)."""


class KeyConflictError(ScireportError):
  """A key is added twice, or collides with another key, in a ``Report`` (E104, E102)."""
