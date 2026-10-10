"""``new``: write a starter data file."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from scireport.bundle import open_bundle
from scireport.bundle.scaffold import make_scaffold, write_scaffold
from scireport.cli._common import echo_json, reporting_errors
from scireport.logging_utils import get_logger
from scireport.render.registry import load_template

log = get_logger(__name__)


def new(
  dest: Annotated[
    Path, typer.Argument(help='Directory to create (it becomes a directory bundle).')
  ],
  title: Annotated[str, typer.Option('--title', help='The report title.')] = 'Untitled report',
  template: Annotated[
    str | None,
    typer.Option(
      '--template', '-t', help='Template whose required fields get placeholders (default: generic).'
    ),
  ] = None,
  layout: Annotated[
    str | None, typer.Option('--layout', '-l', help='Layout to write into the render block.')
  ] = None,
  force: Annotated[
    bool, typer.Option('--force', help='Replace the scireport.yaml of an existing directory.')
  ] = False,
  as_json: Annotated[bool, typer.Option('--json', help='Print the result as JSON.')] = False,
) -> None:
  """Write a starter scireport.yaml that already reads as a valid data file.

  With --template, every required field of that template gets a placeholder value; values that
  need a file (figures, images, attachments) are listed so that you can add them.
  """
  with reporting_errors(as_json=as_json):
    loaded = load_template(template) if template else None
    scaffold = make_scaffold(title, template=loaded, layout=layout)
    manifest = write_scaffold(dest, scaffold, overwrite=force)
    with open_bundle(dest) as bundle:
      count = len(bundle.manifest.values)
    if as_json:
      echo_json(
        {
          'ok': True,
          'manifest': manifest.as_posix(),
          'values': count,
          'notes': list(scaffold.notes),
        }
      )
      return
    typer.echo(manifest.as_posix())
    for note in scaffold.notes:
      log.warning('still to add: %s', note)
