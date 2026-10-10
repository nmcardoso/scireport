"""``export tex``: LaTeX fragments of a bundle for a manuscript."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from scireport.bundle import open_bundle
from scireport.bundle.backends import DEFAULT_MAX_BYTES
from scireport.cli._common import MEGABYTE, echo_json, reporting_errors
from scireport.export import export_tex, write_export
from scireport.logging_utils import get_logger, log_kv

log = get_logger(__name__)

app = typer.Typer(
  name='export', help='Export values of a bundle for other documents.', no_args_is_help=True
)


@app.command('tex')
def tex(
  source: Annotated[
    Path, typer.Argument(help='A bundle: directory, .zip archive or manifest file.')
  ],
  output: Annotated[
    Path,
    typer.Option(
      '--output', '-o', help='Directory for the fragments (for example paper/generated).'
    ),
  ],
  keys: Annotated[
    list[str] | None,
    typer.Option(
      '--keys',
      '-k',
      help='Keys to export; * and ? match several (crossmatch.*). Repeat, or separate with commas. '
      'Default: every number, table and figure.',
    ),
  ] = None,
  prefix: Annotated[
    str, typer.Option('--prefix', help='Letters in front of every macro name in numbers.tex.')
  ] = '',
  bare: Annotated[
    bool,
    typer.Option(
      '--bare', help='Write a bare tabular and \\includegraphics, without float or caption.'
    ),
  ] = False,
  graphics_prefix: Annotated[
    str | None,
    typer.Option(
      '--graphics-prefix',
      help='Path written before a figure file in \\includegraphics, from the directory LaTeX '
      'runs in (default: the name of the output directory and a slash).',
    ),
  ] = None,
  max_rows: Annotated[
    int | None, typer.Option('--max-rows', min=1, help='Cut every table to this many rows.')
  ] = None,
  as_json: Annotated[bool, typer.Option('--json', help='Print the result as JSON.')] = False,
  max_size: Annotated[
    int,
    typer.Option('--max-size', min=1, help='Size cap of a ZIP bundle, in MiB (uncompressed).'),
  ] = DEFAULT_MAX_BYTES // MEGABYTE,
) -> None:
  r"""Write tab_<key>.tex, fig_<key>.tex and numbers.tex for a manuscript to \input.

  numbers.tex holds one \newcommand per number value (CamelCase key, optional prefix); two keys
  with the same macro name are an error. Figures are written next to their fragment.
  """
  with (
    reporting_errors(as_json=as_json),
    open_bundle(source, max_bytes=max_size * MEGABYTE) as bundle,
  ):
    wanted = [part for item in keys or () for part in item.split(',') if part.strip()]
    graphics = graphics_prefix if graphics_prefix is not None else f'{output.resolve().name}/'
    result = export_tex(
      bundle,
      wanted or None,
      prefix=prefix,
      bare=bare,
      graphics_prefix=graphics,
      max_rows=max_rows,
    )
    written = write_export(result, output)
    log_kv(log, 'export written', {'directory': output, 'files': len(written)})
    if as_json:
      echo_json(
        {
          'ok': True,
          'output': output.as_posix(),
          'files': [path.relative_to(output).as_posix() for path in written],
          'macros': result.macros,
        }
      )
    else:
      for path in written:
        typer.echo(path.relative_to(output).as_posix())
