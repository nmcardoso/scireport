"""``validate`` and ``render``: check a bundle against a template, or write its outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from scireport.bundle import open_bundle
from scireport.bundle.backends import DEFAULT_MAX_BYTES
from scireport.cli._common import MEGABYTE, echo_json, reporting_errors
from scireport.errors import TemplateError
from scireport.logging_utils import get_logger
from scireport.render.definition import FORMATS
from scireport.render.pdf import PDF_ENGINES
from scireport.render.pipeline import (
  DEFAULT_LATEX_ENGINE,
  DEFAULT_PDF_ENGINE,
  check_bundle,
  render_bundle,
)
from scireport.render.registry import list_layouts, list_templates

log = get_logger(__name__)

Source = Annotated[Path, typer.Argument(help='A bundle: directory, .zip archive or manifest file.')]
TemplateOpt = Annotated[
  str | None,
  typer.Option('--template', '-t', help='Template: name, name@version or a directory.'),
]
LayoutOpt = Annotated[
  str | None, typer.Option('--layout', '-l', help='Layout: name, name@version or a directory.')
]
FormatOpt = Annotated[
  list[str] | None,
  typer.Option('--format', '-f', help='Output format: md, html, tex or pdf (repeat for several).'),
]
OptionOpt = Annotated[
  list[str] | None,
  typer.Option('--option', '-O', help='Layout option as name=value (repeat for several).'),
]
StrictOpt = Annotated[bool, typer.Option('--strict', help='Treat warnings as errors.')]
JsonOpt = Annotated[bool, typer.Option('--json', help='Print the result as JSON (for agents).')]
MaxSize = Annotated[
  int, typer.Option('--max-size', min=1, help='Size cap of a ZIP bundle, in MiB (uncompressed).')
]


def validate(
  source: Source,
  template: TemplateOpt = None,
  layout: LayoutOpt = None,
  formats: FormatOpt = None,
  option: OptionOpt = None,
  strict: StrictOpt = False,
  as_json: JsonOpt = False,
  dry_render: Annotated[
    bool,
    typer.Option(
      '--render/--no-render', help='Also render in memory to find what only a render shows.'
    ),
  ] = True,
  max_size: MaxSize = DEFAULT_MAX_BYTES // MEGABYTE,
) -> None:
  """Check a bundle against a template and a layout; nothing is written.

  Reports every problem at once, each with a stable code, the key, the template line and a
  suggestion. Exit code 0: valid; 2: errors (with --strict also warnings).
  """
  with (
    reporting_errors(as_json=as_json),
    open_bundle(source, max_bytes=max_size * MEGABYTE) as bundle,
  ):
    report = check_bundle(
      bundle,
      template=template,
      layout=layout,
      formats=_formats(formats),
      options=_options(option),
      strict=strict,
      render=dry_render,
    )
    if as_json:
      echo_json(report.to_dict())
    else:
      for issue in report.issues:
        typer.echo(issue.format())
      counts = report.to_dict()['counts']
      verdict = 'valid' if report.ok else 'invalid'
      typer.echo(f'{verdict}: {counts["errors"]} error(s), {counts["warnings"]} warning(s)')
    if not report.ok:
      raise typer.Exit(report.exit_code)


def render(
  source: Source,
  output: Annotated[
    Path, typer.Option('--output', '-o', help='Directory to write the outputs to.')
  ],
  template: TemplateOpt = None,
  layout: LayoutOpt = None,
  formats: FormatOpt = None,
  option: OptionOpt = None,
  pdf_engine: Annotated[
    str | None,
    typer.Option(
      '--pdf-engine',
      help=f'How a PDF is made: {", ".join(PDF_ENGINES)} (default {DEFAULT_PDF_ENGINE}).',
    ),
  ] = None,
  latex_engine: Annotated[
    str | None,
    typer.Option(
      '--latex-engine',
      help=f'TeX engine of the LaTeX project and the PDF (default {DEFAULT_LATEX_ENGINE}).',
    ),
  ] = None,
  markup_engine: Annotated[
    str | None, typer.Option('--markup-engine', help='Markdown converter (mistletoe).')
  ] = None,
  math_renderer: Annotated[
    str | None,
    typer.Option('--math-renderer', help='Math renderer for HTML: mathtext or usetex.'),
  ] = None,
  md_split: Annotated[
    bool | None,
    typer.Option(
      '--md-split/--no-md-split',
      help='Split Markdown by chapter md_file (default: when the template names files).',
    ),
  ] = None,
  flat: Annotated[
    bool, typer.Option('--flat', help='Write one format straight into the directory.')
  ] = False,
  strict: StrictOpt = False,
  as_json: JsonOpt = False,
  max_size: MaxSize = DEFAULT_MAX_BYTES // MEGABYTE,
) -> None:
  """Render a bundle to Markdown, HTML, a LaTeX project and/or a PDF.

  Each format goes to its own folder of the output directory (md/, html/, tex/, pdf/), next to
  render-manifest.json. A PDF needs system libraries: pango for --pdf-engine weasyprint, TeX Live
  for --pdf-engine latex (exit code 3 when they are missing). Nothing is written when validation
  or rendering finds an error.
  """
  with (
    reporting_errors(as_json=as_json),
    open_bundle(source, max_bytes=max_size * MEGABYTE) as bundle,
  ):
    result = render_bundle(
      bundle,
      template=template,
      layout=layout,
      formats=_formats(formats),
      options=_options(option),
      markup_engine=markup_engine,
      math_renderer=math_renderer,
      pdf_engine=pdf_engine,
      latex_engine=latex_engine,
      md_split=md_split,
      flat=flat,
      strict=strict,
    )
    written = result.write(output)
    names = [path.relative_to(output).as_posix() for path in written]
    if as_json:
      echo_json(
        {
          'ok': True,
          'output': output.as_posix(),
          'files': names,
          'warnings': [issue.to_dict() for issue in result.issues],
        }
      )
    else:
      for name in names:
        typer.echo(name)


def templates(as_json: JsonOpt = False) -> None:
  """List the templates that can be used: built in and from plugins."""
  _echo_listing(list_templates(), as_json)


def layouts(as_json: JsonOpt = False) -> None:
  """List the layouts that can be used: built in and from plugins."""
  _echo_listing(list_layouts(), as_json)


def _echo_listing(listing: list[Any], as_json: bool) -> None:
  """Print templates or layouts, one per line, or as JSON."""
  rows = [
    {
      'ref': item.ref,
      'title': item.title,
      'formats': list(item.formats),
      'origin': item.origin,
    }
    for item in listing
  ]
  if as_json:
    echo_json(rows)
    return
  for row in rows:
    typer.echo(
      f'{row["ref"]:<16} {",".join(row["formats"]):<12} {row["origin"]:<10} {row["title"]}'
    )


def _formats(names: list[str] | None) -> list[str] | None:
  """Check the formats given on the command line."""
  if not names:
    return None
  allowed = (*FORMATS, 'pdf')
  chosen: list[str] = []
  for name in names:
    if name not in allowed:
      later = {'docx': 'phase S5', 'odt': 'phase S5', 'epub': 'phase S5'}
      hint = f'{name} output arrives in {later[name]}.' if name in later else None
      raise TemplateError(
        f'unknown output format {name!r} (this version writes: {", ".join(allowed)})',
        code='E805' if name in later else 'E801',
        hint=hint,
      )
    chosen.append(name)
  return chosen


def _options(items: list[str] | None) -> dict[str, str]:
  """Parse repeated ``name=value`` options."""
  parsed: dict[str, str] = {}
  for item in items or ():
    name, sep, value = item.partition('=')
    if not sep or not name:
      raise TemplateError(f'option {item!r} must be written name=value', code='E806')
    parsed[name.strip()] = value
  return parsed
