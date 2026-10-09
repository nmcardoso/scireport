"""Command-line entry point (``scireport``)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from scireport._version import __version__
from scireport.cli import bundle, spec
from scireport.logging_utils import setup_logging

app = typer.Typer(
  name='scireport',
  help='Render a scireport data file through a template and a layout.',
  no_args_is_help=True,
  add_completion=False,
)
app.command('pack')(bundle.pack)
app.command('unpack')(bundle.unpack)
app.command('inspect')(bundle.inspect)
app.add_typer(spec.app, name='spec')


class LogLevel(StrEnum):
  """Levels accepted by ``--log-level``."""

  DEBUG = 'DEBUG'
  INFO = 'INFO'
  WARNING = 'WARNING'
  ERROR = 'ERROR'


def _version_callback(value: bool) -> None:
  """Print the version and exit when ``--version`` is given.

  Parameters
  ----------
  value : bool
      True when the flag was passed.
  """
  if value:
    typer.echo(__version__)
    raise typer.Exit()


@app.callback()
def main(
  version: Annotated[
    bool,
    typer.Option('--version', callback=_version_callback, is_eager=True, help='Show the version.'),
  ] = False,
  log_level: Annotated[
    LogLevel, typer.Option('--log-level', help='Console log level (stderr).')
  ] = LogLevel.INFO,
  log_file: Annotated[
    Path | None, typer.Option('--log-file', help='Also write a plain-text log here.')
  ] = None,
) -> None:
  """Scientific report engine."""
  setup_logging(level=log_level.value, log_file=log_file)
