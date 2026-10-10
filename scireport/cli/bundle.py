"""``pack``, ``unpack`` and ``inspect``: working with report bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from scireport.bundle import infer_form, open_bundle, write_bundle
from scireport.bundle.backends import DEFAULT_MAX_BYTES
from scireport.bundle.summary import inspect_bundle
from scireport.cli._common import EXIT_VALIDATION, MEGABYTE, echo_json, reporting_errors
from scireport.errors import BundleError
from scireport.logging_utils import get_logger, log_kv
from scireport.render.registry import pin_manifest
from scireport.spec.manifest import manifest_to_dict

log = get_logger(__name__)

_BUNDLE_SUFFIXES = ('.scireport.zip', '.scireport', '.zip', '.json', '.yaml', '.yml')

Source = Annotated[Path, typer.Argument(help='A bundle: directory, .zip archive or manifest file.')]
Force = Annotated[bool, typer.Option('--force', help='Replace the destination if it exists.')]
MaxSize = Annotated[
  int, typer.Option('--max-size', min=1, help='Size cap of a ZIP bundle, in MiB (uncompressed).')
]
AsJson = Annotated[bool, typer.Option('--json', help='Print the result as JSON (for agents).')]


def pack(
  source: Source,
  output: Annotated[
    Path | None,
    typer.Option(
      '--output', '-o', help='Destination; default <name>.scireport.zip next to SOURCE.'
    ),
  ] = None,
  force: Force = False,
  max_size: MaxSize = DEFAULT_MAX_BYTES // MEGABYTE,
  as_json: AsJson = False,
) -> None:
  """Pack a bundle into a byte-reproducible ZIP with a JSON manifest.

  A hand-authored directory (YAML manifest, asset references without hashes) is completed:
  hashes and sizes are computed and the manifest is written as canonical JSON. Files that no
  value references are left out.
  """
  with reporting_errors(as_json=as_json):
    dest = output or default_destination(source, '.scireport.zip')
    _transfer('pack', source, dest, force, max_size, as_json)


def unpack(
  source: Source,
  output: Annotated[
    Path | None,
    typer.Option('--output', '-o', help='Destination directory; default <name>.scireport/.'),
  ] = None,
  force: Force = False,
  max_size: MaxSize = DEFAULT_MAX_BYTES // MEGABYTE,
  as_json: AsJson = False,
) -> None:
  """Unpack a bundle into a directory (manifest plus assets), checking every hash on the way."""
  with reporting_errors(as_json=as_json):
    dest = output or default_destination(source, '.scireport')
    _transfer('unpack', source, dest, force, max_size, as_json)


def inspect(
  source: Source,
  as_json: AsJson = False,
  verify: Annotated[
    bool, typer.Option('--verify/--no-verify', help='Check every asset hash and size.')
  ] = True,
  key: Annotated[
    str | None, typer.Option('--key', '-k', help='Print the canonical value stored at KEY.')
  ] = None,
  max_size: MaxSize = DEFAULT_MAX_BYTES // MEGABYTE,
) -> None:
  """Show what a bundle contains: metadata, every value and the integrity check.

  Exit code 0 when the bundle is sound, 2 when it is invalid or fails verification.
  """
  with (
    reporting_errors(as_json=as_json),
    open_bundle(source, max_bytes=max_size * MEGABYTE) as bundle,
  ):
    if key is not None:
      if key not in bundle.manifest.values:
        raise BundleError(f'no value with key {key!r}', code='E103')
      echo_json(manifest_to_dict(bundle.manifest)['values'][key])
      return
    report = inspect_bundle(bundle, verify=verify)
    if as_json:
      echo_json(report)
    else:
      _echo_summary(report)
    if not report['ok']:
      raise typer.Exit(EXIT_VALIDATION)


def default_destination(source: Path, suffix: str) -> Path:
  """Derive the default output path for ``pack`` and ``unpack``.

  Parameters
  ----------
  source : pathlib.Path
      The bundle given on the command line.
  suffix : str
      ``.scireport.zip`` or ``.scireport``.

  Returns
  -------
  pathlib.Path
      ``source`` without its bundle suffix, plus ``suffix``, in the same directory.
  """
  name = source.name
  for known in _BUNDLE_SUFFIXES:
    if name.lower().endswith(known) and len(name) > len(known):
      name = name[: -len(known)]
      break
  return source.with_name(name + suffix)


def _transfer(
  verb: str, source: Path, dest: Path, force: bool, max_size: int, as_json: bool
) -> None:
  """Open ``source``, verify it and write it to ``dest``."""
  cap = max_size * MEGABYTE
  with open_bundle(source, max_bytes=cap) as bundle:
    problems = bundle.verify()
    for issue in problems:
      if issue.severity == 'warning':
        log.warning('%s', issue.format())
    errors = [issue for issue in problems if issue.severity == 'error']
    if errors:
      raise BundleError(
        f'{len(errors)} integrity problem(s), first: {errors[0].format()}',
        code=errors[0].code,
        issues=errors,
      )
    to_write = bundle
    if verb == 'pack':
      pinned = pin_manifest(bundle.manifest)
      if pinned is not bundle.manifest:
        log.info(
          'pinned template %s, layout %s, pandoc %s',
          pinned.render.template,
          pinned.render.layout,
          pinned.render.pandoc_version,
        )
        to_write = bundle.with_manifest(pinned)
    written = write_bundle(to_write, dest, overwrite=force, max_bytes=cap)
    form = infer_form(written)
    log_kv(
      log,
      f'{verb} complete',
      {
        'source': source,
        'destination': written,
        'form': form,
        'values': len(bundle.manifest.values),
      },
    )
    if as_json:
      echo_json(
        {
          'ok': True,
          'path': written.as_posix(),
          'form': form,
          'values': len(bundle.manifest.values),
          'assets': len(bundle.asset_paths),
          'warnings': [i.to_dict() for i in problems if i.severity == 'warning'],
        }
      )
    else:
      typer.echo(written.as_posix())


def _echo_summary(report: dict[str, object]) -> None:
  """Print the human-readable form of an :func:`inspect_bundle` report."""
  meta = report['meta']
  assert isinstance(meta, dict)
  assets = report['assets']
  assert isinstance(assets, dict)
  counts = report['counts']
  assert isinstance(counts, dict)
  typer.echo(f'{meta["title"]}')
  typer.echo(f'  spec {report["spec"]}, {report["form"]} bundle: {report["source"] or "memory"}')
  if meta.get('authors'):
    typer.echo('  authors: ' + ', '.join(a['name'] for a in meta['authors']))
  kinds = ', '.join(f'{kind} {n}' for kind, n in counts.items()) or 'none'
  typer.echo(f'  values: {sum(counts.values())} ({kinds})')
  typer.echo(f'  assets: {assets["count"]} files, {assets["bytes"]:,} bytes')
  issues = report['issues']
  assert isinstance(issues, list)
  if not report['verified']:
    typer.echo('  integrity: not checked')
  elif issues:
    typer.echo(f'  integrity: {len(issues)} problem(s)')
    for issue in issues:
      typer.echo(f'    {issue["code"]} {issue["message"]}')
  else:
    typer.echo('  integrity: ok')
  values = report['values']
  assert isinstance(values, list)
  if values:
    width = max(len(v['key']) for v in values)
    typer.echo('')
    for v in values:
      typer.echo(f'  {v["key"]:<{width}}  {v["kind"]:<10}  {v["summary"]}')
