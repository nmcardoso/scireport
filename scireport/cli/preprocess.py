"""``preprocess`` and ``preprocessors``: run the steps of a bundle, and list what can run."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from scireport.bundle import open_bundle, write_bundle
from scireport.bundle.backends import DEFAULT_MAX_BYTES
from scireport.cli._common import MEGABYTE, echo_json, reporting_errors
from scireport.logging_utils import get_logger
from scireport.preprocess import (
  get_preprocessor,
  list_preprocessors,
  params_schema,
  preprocess_bundle,
  write_back,
)
from scireport.preprocess.registry import Preprocessor

log = get_logger(__name__)

AllowImportOpt = Annotated[
  bool,
  typer.Option(
    '--allow-import',
    help='Let a step name module:function (imports and runs that code). Only for files you trust.',
  ),
]
CacheDirOpt = Annotated[
  Path | None,
  typer.Option(
    '--cache-dir', help='Pre-processor cache (default: $SCIREPORT_CACHE_DIR or the XDG cache).'
  ),
]
JsonOpt = Annotated[bool, typer.Option('--json', help='Print the result as JSON (for agents).')]


def preprocess(
  source: Annotated[
    Path, typer.Argument(help='A bundle: directory, .zip archive or manifest file.')
  ],
  output: Annotated[
    Path | None,
    typer.Option('--output', '-o', help='Write the pre-processed bundle here (directory, .zip).'),
  ] = None,
  write_back_to_source: Annotated[
    bool,
    typer.Option(
      '--write-back', help='Replace SOURCE with the pre-processed bundle (steps stay in it).'
    ),
  ] = False,
  work_dir: Annotated[
    Path,
    typer.Option('--work-dir', help='Where the new figures and tables and the run record go.'),
  ] = Path('scireport-work'),
  layout: Annotated[
    str | None, typer.Option('--layout', '-l', help='Layout whose style the figures use.')
  ] = None,
  seed: Annotated[int, typer.Option('--seed', help='Base seed; each step derives its own.')] = 0,
  cache_dir: CacheDirOpt = None,
  no_cache: Annotated[
    bool, typer.Option('--no-cache', help='Neither read nor write the cache.')
  ] = False,
  allow_import: AllowImportOpt = False,
  as_json: JsonOpt = False,
  max_size: Annotated[
    int, typer.Option('--max-size', min=1, help='Size cap of a ZIP bundle, in MiB.')
  ] = DEFAULT_MAX_BYTES // MEGABYTE,
) -> None:
  """Run the pre-processing steps of a bundle: figures and tables from its data.

  The plan is checked first and every problem is reported at once; nothing runs if there is one.
  New files go to the work directory; SOURCE is left untouched unless --write-back is given.
  Results are cached by content, so running again is a no-op.
  """
  if write_back_to_source and output is not None:
    raise typer.BadParameter('give --output or --write-back, not both')
  with (
    reporting_errors(as_json=as_json),
    open_bundle(source, max_bytes=max_size * MEGABYTE) as bundle,
  ):
    result = preprocess_bundle(
      bundle,
      work_dir=work_dir,
      cache_dir=cache_dir,
      allow_import=allow_import,
      layout=layout,
      seed=seed,
      use_cache=not no_cache,
    )
    if write_back_to_source:
      write_back(result, source)
    elif output is not None:
      write_bundle(result.bundle, output)
    if as_json:
      echo_json({'ok': True, 'work_dir': work_dir.as_posix(), **result.to_dict()})
    else:
      for step in result.steps:
        typer.echo(f'{step.label:<24} {step.name}@{step.version}  {step.cache:<5} {step.key[:12]}')
      if not result.steps:
        typer.echo('no steps')


def preprocessors(
  name: Annotated[
    str | None, typer.Argument(help='Show one pre-processor: its ports and parameters.')
  ] = None,
  as_json: JsonOpt = False,
) -> None:
  """List the registered pre-processors, or describe one."""
  with reporting_errors(as_json=as_json):
    if name is not None:
      entry = get_preprocessor(name)
      detail = _describe(entry, full=True)
      if as_json:
        echo_json(detail)
      else:
        _echo_detail(detail)
      return
    rows = [_describe(entry, full=False) for entry in list_preprocessors()]
    if as_json:
      echo_json(rows)
      return
    for row in rows:
      needs = f'[{row["requires"]}]' if row['requires'] else ''
      typer.echo(f'{row["ref"]:<34} {needs:<8} {row["summary"]}')


def _describe(entry: Preprocessor, *, full: bool) -> dict[str, Any]:
  """Return the listing row of a pre-processor, with its ports and parameters when ``full``."""
  row: dict[str, Any] = {
    'ref': entry.ref,
    'name': entry.name,
    'version': entry.version,
    'summary': entry.summary,
    'requires': entry.requires,
  }
  if full:
    row['inputs'] = {
      port: {'kind': spec.kind, 'optional': spec.optional, 'description': spec.description}
      for port, spec in entry.inputs.items()
    }
    row['outputs'] = {
      port: {'kind': spec.kind, 'optional': spec.optional, 'description': spec.description}
      for port, spec in entry.outputs.items()
    }
    row['params'] = params_schema(entry)
  return row


def _echo_detail(detail: dict[str, Any]) -> None:
  """Print one pre-processor for a person."""
  typer.echo(f'{detail["ref"]}: {detail["summary"]}')
  if detail['requires']:
    typer.echo(f'needs: pip install "scireport[{detail["requires"]}]"')
  for direction in ('inputs', 'outputs'):
    typer.echo(f'{direction}:')
    for port, spec in detail[direction].items():
      optional = ' (optional)' if spec['optional'] else ''
      typer.echo(f'  {port}: {spec["kind"]}{optional}  {spec["description"]}'.rstrip())
  typer.echo('parameters:')
  required = set(detail['params'].get('required', []))
  for param, schema in detail['params'].get('properties', {}).items():
    default = '' if param in required else f' = {schema.get("default")!r}'
    kind = schema.get('type') or schema.get('anyOf') or schema.get('$ref', '')
    typer.echo(f'  {param}{" (required)" if param in required else ""}{default}  {kind}')
