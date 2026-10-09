"""``scireport spec``: the data-file specification (schema, kinds, migration)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from scireport.bundle.textio import parse_manifest_text
from scireport.cli._common import echo_json, reporting_errors
from scireport.logging_utils import get_logger
from scireport.spec import kinds as kinds_module
from scireport.spec.migrations import migrate
from scireport.spec.schema import manifest_json_schema, schema_text
from scireport.spec.version import SPEC_VERSION

log = get_logger(__name__)

app = typer.Typer(name='spec', help='Inspect the data-file specification.', no_args_is_help=True)


@app.command('version')
def version() -> None:
  """Print the newest spec version this scireport reads and writes."""
  typer.echo(SPEC_VERSION)


@app.command('schema')
def schema(
  output: Annotated[
    Path | None, typer.Option('--output', '-o', help='Write the schema here instead of stdout.')
  ] = None,
) -> None:
  """Print the JSON Schema of the manifest (generated from the pydantic models)."""
  with reporting_errors():
    text = schema_text(manifest_json_schema())
    if output is None:
      typer.echo(text, nl=False)
    else:
      output.write_text(text, encoding='utf-8', newline='\n')
      log.info('wrote the %s schema to %s', SPEC_VERSION, output)


@app.command('kinds')
def kinds(
  as_json: Annotated[bool, typer.Option('--json', help='Print as JSON.')] = False,
) -> None:
  """List the value kinds with their fields."""
  rows = [_describe(kind) for kind in kinds_module.KINDS]
  if as_json:
    echo_json(rows)
    return
  width = max(len(row['kind']) for row in rows)
  for row in rows:
    typer.echo(f'{row["kind"]:<{width}}  {row["summary"]}')
    typer.echo(f'{"":<{width}}  fields: {", ".join(row["fields"])}')


@app.command('migrate')
def migrate_command(
  source: Annotated[Path, typer.Argument(help='A manifest file (.json or .yaml).')],
  output: Annotated[
    Path | None, typer.Option('--output', '-o', help='Write the migrated manifest here.')
  ] = None,
  to: Annotated[str, typer.Option('--to', help='Target spec version.')] = SPEC_VERSION,
) -> None:
  """Migrate a manifest to a spec version (pure dict-to-dict; the input is not changed)."""
  with reporting_errors():
    raw = parse_manifest_text(
      source.read_bytes(),
      yaml_format=source.suffix.lower() in ('.yaml', '.yml'),
      origin=str(source),
    )
    text = json.dumps(migrate(raw, target=to), indent=2, ensure_ascii=False) + '\n'
    if output is None:
      typer.echo(text, nl=False)
    else:
      output.write_text(text, encoding='utf-8', newline='\n')
      log.info('wrote the spec %s manifest to %s', to, output)


def _describe(kind: str) -> dict[str, Any]:
  """Describe one kind from its model: the first line of its docstring and its fields."""
  model = getattr(kinds_module, f'{kind.capitalize()}Value')
  doc = (model.__doc__ or '').strip().splitlines()[0].replace('``', '')
  return {'kind': kind, 'summary': doc, 'fields': [n for n in model.model_fields if n != 'kind']}
