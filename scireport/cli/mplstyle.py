"""``mplstyle``: the matplotlib style and palette of a layout, for people who draw figures."""

from __future__ import annotations

from typing import Annotated

import typer

from scireport.cli._common import echo_json, reporting_errors
from scireport.logging_utils import get_logger
from scireport.styles import mplstyle_path, palette

log = get_logger(__name__)

app = typer.Typer(
  name='mplstyle',
  help='The matplotlib style and palette of a layout (figures that look like the report).',
  no_args_is_help=True,
)

LayoutArg = Annotated[
  str, typer.Argument(help='A layout: name, name@version or a directory (default: default).')
]
AsJson = Annotated[bool, typer.Option('--json', help='Print the result as JSON.')]


@app.command('path')
def path(layout: LayoutArg = 'default', as_json: AsJson = False) -> None:
  """Print the path of the .mplstyle file of a layout (use it as plt.style.use(path))."""
  with reporting_errors(as_json=as_json):
    found = mplstyle_path(layout)
    if as_json:
      echo_json({'layout': layout, 'path': found.as_posix()})
    else:
      typer.echo(found.as_posix())


@app.command('show')
def show(layout: LayoutArg = 'default') -> None:
  """Print the contents of the .mplstyle file of a layout."""
  with reporting_errors():
    typer.echo(mplstyle_path(layout).read_text(encoding='utf-8'), nl=False)


@app.command('palette')
def show_palette(layout: LayoutArg = 'default', as_json: AsJson = False) -> None:
  """Print the palette of a layout: colours, chart roles, fonts and page geometry."""
  with reporting_errors(as_json=as_json):
    data = palette(layout).model_dump(mode='json')
    if as_json:
      echo_json(data)
      return
    for name, value in data.items():
      typer.echo(f'{name}: {value}')
