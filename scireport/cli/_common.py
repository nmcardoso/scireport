"""Helpers shared by the CLI commands: error reporting and exit codes."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import typer

from scireport.errors import ScireportError
from scireport.logging_utils import get_logger

log = get_logger(__name__)

EXIT_RUNTIME = 1
"""Exit code for a failure that is not a validation problem (I/O error, bug)."""

EXIT_VALIDATION = 2
"""Exit code for an invalid manifest or bundle."""

EXIT_MISSING_DEPENDENCY = 3
"""Exit code for a missing system dependency (pango, TeX Live, ...); used from phase S3."""

MEGABYTE = 1024 * 1024


def echo_json(payload: Any) -> None:
  """Print ``payload`` as indented JSON on stdout, the command's result.

  Parameters
  ----------
  payload : Any
      A JSON-serialisable object.
  """
  typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@contextmanager
def reporting_errors(*, as_json: bool = False) -> Iterator[None]:
  """Turn the exceptions of a command into logged errors and an exit code.

  A :class:`~scireport.errors.ScireportError` logs each of its issues (or, with ``as_json``,
  prints ``{"ok": false, "issues": [...]}`` on stdout) and exits with its ``exit_code``; an
  ``OSError`` logs and exits 1.

  Parameters
  ----------
  as_json : bool, default=False
      Report problems as JSON on stdout instead of log lines.

  Raises
  ------
  typer.Exit
      With the exit code of the failure.
  """
  try:
    yield
  except ScireportError as exc:
    if as_json:
      echo_json({'ok': False, 'issues': [issue.to_dict() for issue in exc.issues]})
    else:
      for issue in exc.issues:
        (log.warning if issue.severity == 'warning' else log.error)('%s', issue.format())
    raise typer.Exit(exc.exit_code) from exc
  except OSError as exc:
    if as_json:
      echo_json(
        {'ok': False, 'issues': [{'code': 'E410', 'severity': 'error', 'message': str(exc)}]}
      )
    else:
      log.error('%s', exc)
    raise typer.Exit(EXIT_RUNTIME) from exc
