"""Command-line entry point (``scireport``). Phase S0 ships only ``--version``."""

from __future__ import annotations

import typer

from scireport import __version__

app = typer.Typer(
  name='scireport',
  help='Render a scireport data file through a template and a layout.',
  no_args_is_help=True,
  add_completion=False,
)


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
  version: bool = typer.Option(
    False, '--version', callback=_version_callback, is_eager=True, help='Show the version.'
  ),
) -> None:
  """Scientific report engine."""
