"""Command-line entry point (``scireport``)."""

from __future__ import annotations

import os
import sys
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from scireport._version import __version__
from scireport.cli import agent, bundle, export, mplstyle, new, preprocess, render, spec
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
app.command('new')(new.new)
app.command('validate')(render.validate)
app.command('render')(render.render)
app.command('templates')(render.templates)
app.command('layouts')(render.layouts)
app.command('preprocess')(preprocess.preprocess)
app.command('preprocessors')(preprocess.preprocessors)
app.add_typer(export.app, name='export')
app.add_typer(spec.app, name='spec')
app.add_typer(mplstyle.app, name='mplstyle')
app.add_typer(agent.agent_app, name='agent')
app.add_typer(agent.mcp_app, name='mcp')


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


def run() -> None:
  """Run the command line (the ``scireport`` console script).

  Behaves like calling `app`, except that a closed pipe is not an error: when the reader of
  stdout stops early (``scireport layouts | head``), the command exits with status 1 and prints
  nothing. Standard output is pointed at the null device first, so that the interpreter does not
  complain about the unflushed data when it shuts down.
  """
  try:
    try:
      app()
    finally:
      sys.stdout.flush()
  except BrokenPipeError:
    _silence_stdout()
    sys.exit(1)


def _silence_stdout() -> None:
  """Point the standard output file descriptor at the null device."""
  devnull = os.open(os.devnull, os.O_WRONLY)
  os.dup2(devnull, sys.stdout.fileno())
  os.close(devnull)
