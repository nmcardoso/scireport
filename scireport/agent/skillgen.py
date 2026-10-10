"""Generate the tables of the packaged skill from the code (``make skill``).

The pages of ``scireport/agent/skill/scireport/`` are written by hand, except for blocks between
markers::

    <!-- generated:cli -->
    ...whatever is here is replaced...
    <!-- /generated -->

:data:`GENERATORS` maps the name in the marker to a function that returns the Markdown of the
block. ``python -m scireport.agent.skillgen`` rewrites the blocks; with ``--check`` it only
reports pages whose blocks differ from the code, and exits with 1 (a test runs the same check, so
the skill cannot drift from the code, ADR-0009).
"""

from __future__ import annotations

import argparse
import inspect
import re
import sys
import types
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Annotated, Any, ForwardRef, Literal, Union, get_args, get_origin

from scireport.agent import catalogue
from scireport.agent.skill import SKILL_DIR
from scireport.error_help import HELP
from scireport.errors import CODES

_BLOCK_RE = re.compile(
  r'<!-- generated:(?P<name>[a-z0-9-]+) -->\n.*?<!-- /generated -->', re.DOTALL
)
_PARAM_RE = re.compile(r'^(?P<name>\*{0,2}\w+)\s*:\s*(?P<type>.+)$')


def generated_blocks(text: str) -> list[str]:
  """List the names of the generated blocks in a page, in order."""
  return [match['name'] for match in _BLOCK_RE.finditer(text)]


def render_page(text: str) -> str:
  """Replace every generated block of a page with the output of its generator.

  Parameters
  ----------
  text : str
      The page.

  Returns
  -------
  str
      The page with current blocks.

  Raises
  ------
  KeyError
      When a marker names a generator that does not exist.
  """

  def fill(match: re.Match[str]) -> str:
    name = match['name']
    return f'<!-- generated:{name} -->\n{GENERATORS[name]().rstrip()}\n<!-- /generated -->'

  return _BLOCK_RE.sub(fill, text)


def pages() -> list[Path]:
  """List the Markdown pages of the skill."""
  return sorted(SKILL_DIR.rglob('*.md'))


def stale_pages() -> list[Path]:
  """List the pages whose generated blocks differ from what the code gives."""
  return [
    page
    for page in pages()
    if render_page(page.read_text(encoding='utf-8')) != page.read_text(encoding='utf-8')
  ]


def update_pages() -> list[Path]:
  """Rewrite the generated blocks of every page; return the pages that changed."""
  changed = []
  for page in stale_pages():
    page.write_text(render_page(page.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
    changed.append(page)
  return changed


def main(argv: list[str] | None = None) -> int:
  """Run ``python -m scireport.agent.skillgen [--check]``; return the exit code."""
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
  parser.add_argument('--check', action='store_true', help='report stale pages, change nothing')
  args = parser.parse_args(argv)
  if args.check:
    stale = stale_pages()
    for page in stale:
      sys.stderr.write(f'stale: {page.relative_to(SKILL_DIR).as_posix()}\n')
    return 1 if stale else 0
  for page in update_pages():
    sys.stdout.write(f'updated {page.relative_to(SKILL_DIR).as_posix()}\n')
  return 0


# ---- tables ---------------------------------------------------------------------------------


def table(header: list[str], rows: Iterable[Iterable[Any]]) -> str:
  """Format a Markdown table; ``|`` and newlines in cells are escaped."""
  lines = [
    '| ' + ' | '.join(header) + ' |',
    '|' + '|'.join('---' for _ in header) + '|',
  ]
  lines.extend('| ' + ' | '.join(_cell(cell) for cell in row) + ' |' for row in rows)
  return '\n'.join(lines)


def _cell(value: Any) -> str:
  """Format one table cell."""
  text = '' if value is None else str(value)
  return ' '.join(text.replace('|', '\\|').split())


def summary(doc: str | None) -> str:
  """Return the first sentence-line of a docstring, without Markdown backticks doubled."""
  if not doc:
    return ''
  first = inspect.cleandoc(doc).split('\n\n')[0].replace('\n', ' ')
  return first.replace('``', '`')


def numpy_params(doc: str | None) -> dict[str, tuple[str, str]]:
  """Parse the ``Parameters`` section of a NumPy docstring into name to (type, description)."""
  if not doc:
    return {}
  lines = inspect.cleandoc(doc).splitlines()
  try:
    start = next(i for i, line in enumerate(lines) if line.strip() == 'Parameters') + 2
  except StopIteration:
    return {}
  found: dict[str, tuple[str, str]] = {}
  name = ''
  kind = ''
  text: list[str] = []
  for line in lines[start:]:
    if line and not line.startswith(' '):
      if _PARAM_RE.match(line):
        if name:
          found[name] = (kind, ' '.join(part for part in text if part))
        match = _PARAM_RE.match(line)
        assert match is not None
        name, kind, text = match['name'], match['type'], []
        continue
      break
    text.append(line.strip())
  if name:
    found[name] = (kind, ' '.join(part for part in text if part))
  return found


def signature(obj: Any, *, drop_self: bool = True) -> str:
  """Return a call signature as text, without ``self``."""
  try:
    sig = inspect.signature(obj)
  except (TypeError, ValueError):
    return '(...)'
  params = [p for p in sig.parameters.values() if not (drop_self and p.name in ('self', 'cls'))]
  return str(sig.replace(parameters=params))


# ---- generators -----------------------------------------------------------------------------


def gen_kinds() -> str:
  """Write every value kind with its fields, types and defaults."""
  from scireport.spec import kinds as module

  parts = []
  for kind in module.KINDS:
    model = getattr(module, f'{kind.capitalize()}Value')
    docs = numpy_params(model.__doc__)
    rows = []
    for name, field in model.model_fields.items():
      if name == 'kind':
        continue
      default = 'required' if field.is_required() else repr(field.default)
      rows.append(
        (f'`{name}`', f'`{_type(field.annotation)}`', default, docs.get(name, ('', ''))[1])
      )
    parts.append(f'### `{kind}`\n\n{summary(model.__doc__)}\n\n')
    parts.append(table(['Field', 'Type', 'Default', 'Meaning'], rows) + '\n\n')
  return ''.join(parts).rstrip()


def gen_manifest() -> str:
  """Write the blocks of the manifest with their fields."""
  from scireport.spec import manifest as module

  parts = []
  for class_name in (
    'Manifest',
    'Meta',
    'Author',
    'Render',
    'OutlineNode',
    'PreprocessStep',
    'Provenance',
  ):
    model = getattr(module, class_name)
    docs = numpy_params(model.__doc__)
    rows = []
    for name, field in model.model_fields.items():
      default = 'required' if field.is_required() else repr(field.default)
      rows.append(
        (f'`{name}`', f'`{_type(field.annotation)}`', default, docs.get(name, ('', ''))[1])
      )
    parts.append(f'### `{class_name}`\n\n{summary(model.__doc__)}\n\n')
    parts.append(table(['Field', 'Type', 'Default', 'Meaning'], rows) + '\n\n')
  return ''.join(parts).rstrip()


def _type(annotation: Any) -> str:
  """Render a type annotation briefly: metadata of ``Annotated`` is dropped, so no addresses."""
  origin = get_origin(annotation)
  args = get_args(annotation)
  if annotation is None or annotation is type(None):
    return 'None'
  if isinstance(annotation, ForwardRef):
    return annotation.__forward_arg__
  if origin is Annotated:
    return _type(args[0])
  if origin in (Union, types.UnionType):
    return ' | '.join(_type(arg) for arg in args)
  if origin is Literal:
    return 'Literal[' + ', '.join(repr(arg) for arg in args) + ']'
  if origin is not None:
    name = getattr(origin, '__name__', str(origin))
    return f'{name}[{", ".join(_type(arg) for arg in args)}]' if args else name
  if isinstance(annotation, type):
    return annotation.__name__
  return re.sub(r' at 0x[0-9a-f]+', '', str(annotation)).replace('typing.', '')


def gen_cli() -> str:
  """Write every command with its arguments and options, from the Typer application."""
  import typer

  from scireport.cli import app

  root = typer.main.get_command(app)
  parts: list[str] = []

  def visit(command: Any, path: list[str]) -> None:
    subcommands = getattr(command, 'commands', None)
    if subcommands is not None:
      if path[1:]:
        parts.append(f'### `{" ".join(path)}`\n\n{summary(command.help)}\n')
      for name in sorted(subcommands):
        visit(subcommands[name], [*path, name])
      return
    arguments = [p for p in command.params if not any(o.startswith('-') for o in p.opts)]
    options = [p for p in command.params if any(o.startswith('-') for o in p.opts)]
    shown = ' '.join(
      p.name.upper() if p.required else f'[{p.name.upper()}]' for p in arguments if p.name
    )
    parts.append(
      f'### `{" ".join(path)}{" " + shown if shown else ""}`\n\n{_first_paragraph(command.help)}\n'
    )
    rows = [(f'`{p.name.upper()}`', 'argument', '', _argument_help(p)) for p in arguments if p.name]
    for param in options:
      flags = ' / '.join(f'`{flag}`' for flag in (*param.opts, *param.secondary_opts))
      choices = getattr(param.type, 'choices', None)
      kind = '|'.join(map(str, choices)) if choices else param.type.name
      if getattr(param, 'is_flag', False):
        kind = 'flag'
      default = '' if param.default in (None, False) or param.multiple else f'`{param.default}`'
      rows.append(
        (flags, kind + (' (repeat)' if param.multiple else ''), default, param.help or '')
      )
    if rows:
      parts.append(table(['Option', 'Type', 'Default', 'Meaning'], rows) + '\n')

  visit(root, ['scireport'])
  return '\n'.join(parts).rstrip()


def _argument_help(param: Any) -> str:
  """Return the help text of an argument, if the command gave one."""
  return str(getattr(param, 'help', '') or '')


def _first_paragraph(doc: str | None) -> str:
  """Return the docstring text of a command up to the first blank line, plus the next block."""
  if not doc:
    return ''
  return inspect.cleandoc(doc).replace('\b', '').strip()


def gen_exit_codes() -> str:
  """Write the process exit codes of the command line."""
  return table(
    ['Code', 'Meaning'],
    [
      (0, 'Success.'),
      (
        1,
        'A failure that is not a problem in the data file (I/O error, pandoc or a PDF engine '
        'failed, `agent install-skill --check` found a difference).',
      ),
      (
        2,
        'The data file, template, layout or an export is invalid (errors; with `--strict` '
        'also warnings).',
      ),
      (
        3,
        'A system dependency or optional extra is missing (pango, TeX Live, '
        '`scireport[pandoc]`, `scireport[mcp]`); the message says how to install it.',
      ),
    ],
  )


def gen_api() -> str:
  """Write the public Python API: every name of ``scireport.__all__``."""
  import scireport

  rows = []
  for name in scireport.__all__:
    obj = getattr(scireport, name)
    if inspect.isclass(obj):
      kind = 'class'
      sig = '(see its fields)' if hasattr(obj, 'model_fields') else signature(obj)
    elif callable(obj):
      kind, sig = 'function', signature(obj)
    else:
      kind, sig = 'constant', f'= {obj!r}'
    doc = obj.__doc__ if (inspect.isclass(obj) or callable(obj)) else None
    rows.append((f'`{name}`', kind, f'`{sig}`' if sig else '', summary(doc)))
  return table(['Name', 'Kind', 'Signature', 'What it does'], rows)


def gen_report_methods() -> str:
  """Write the ``Report`` builder: every public method with its signature."""
  from scireport.report import Report

  rows = []
  for name, member in inspect.getmembers(Report, predicate=inspect.isfunction):
    if name.startswith('_'):
      continue
    rows.append((f'`{name}`', f'`{signature(member)}`', summary(member.__doc__)))
  return table(['Method', 'Signature', 'What it does'], rows)


def gen_components() -> str:
  """Write the components a template calls (``c.chapter``, ``c.table`` ...)."""
  from scireport.render.components import Components

  rows = []
  for name, member in inspect.getmembers(Components, predicate=inspect.isfunction):
    if name.startswith('_'):
      continue
    rows.append((f'`c.{name}`', f'`{signature(member)}`', summary(member.__doc__)))
  return table(['Component', 'Signature', 'What it does'], rows)


def gen_filters() -> str:
  """Write the Jinja filters available in templates."""
  from scireport.render.filters import FILTERS

  rows = [
    (f'`{name}`', f'`{signature(func)}`', summary(func.__doc__)) for name, func in FILTERS.items()
  ]
  return table(['Filter', 'Signature', 'What it does'], rows)


def gen_templates() -> str:
  """Write the built-in and installed templates."""
  rows = [
    (f'`{row["ref"]}`', ', '.join(row['formats']), row['origin'], row['title'])
    for row in catalogue.list_templates_data()
  ]
  return table(['Template', 'Formats', 'Origin', 'Title'], rows)


def gen_layouts() -> str:
  """Write the layouts with their options."""
  parts = []
  for row in catalogue.list_layouts_data():
    detail = catalogue.describe_layout(row['ref'])
    parts.append(
      f'### `{detail["ref"]}`\n\n{detail["title"]}. {detail["description"]}\n\n'
      f'Formats: {", ".join(detail["formats"])}. '
      f'PDF engines: {", ".join(detail["pdf_engines"])}.\n\n'
    )
    options = [
      (
        f'`{o["name"]}`',
        o['type'],
        f'`{o["default"]}`',
        '|'.join(map(str, o['choices'])) if o['choices'] else '',
        o['description'],
      )
      for o in detail['options']
    ]
    if options:
      parts.append(table(['Option', 'Type', 'Default', 'Choices', 'Meaning'], options) + '\n\n')
  return ''.join(parts).rstrip()


def gen_preprocessors() -> str:
  """Write the pre-processor catalogue."""
  rows = [
    (
      f'`{row["name"]}`',
      row['version'],
      row['requires'] or '',
      row['summary'],
    )
    for row in catalogue.list_preprocessors_data()
  ]
  return table(['Name', 'Version', 'Extra', 'What it does'], rows)


def gen_palette() -> str:
  """Write the fields of a layout palette (``scireport.palette(...)``)."""
  from scireport.styles.palette import Palette

  docs = numpy_params(Palette.__doc__)
  rows = [
    (f'`{name}`', f'`{_type(field.annotation)}`', docs.get(name, ('', ''))[1])
    for name, field in Palette.model_fields.items()
  ]
  return table(['Field', 'Type', 'Meaning'], rows)


def gen_errors() -> str:
  """Write every error and warning code with what to do about it."""
  rows = [
    (f'`{code}`', 'warning' if code.startswith('W') else 'error', title, HELP.get(code, ''))
    for code, title in sorted(CODES.items())
  ]
  return table(['Code', 'Severity', 'Meaning', 'What to do'], rows)


def gen_families() -> str:
  """Write the families of codes."""
  return table(
    ['Prefix', 'About'],
    [(f'`{prefix}xx`', about) for prefix, about in catalogue.FAMILIES.items()],
  )


def gen_engines() -> str:
  """Write the engines and renderers a render can choose from."""
  from scireport.render.markup import MARKUP_ENGINES
  from scireport.render.office import OFFICE_FORMATS, OFFICE_SOURCES
  from scireport.render.pdf import LATEX_ENGINES, PDF_ENGINES

  return table(
    ['Choice', 'Values (first is the default)'],
    [
      ('`--pdf-engine`', ', '.join(f'`{v}`' for v in PDF_ENGINES)),
      ('`--latex-engine`', ', '.join(f'`{v}`' for v in LATEX_ENGINES)),
      ('`--markup-engine`', ', '.join(f'`{v}`' for v in MARKUP_ENGINES)),
      ('`--math-renderer`', '`mathtext`, `usetex`'),
      ('office formats', ', '.join(f'`{v}`' for v in OFFICE_FORMATS)),
      ('`--office-source`', ', '.join(f'`{v}`' for v in OFFICE_SOURCES)),
    ],
  )


GENERATORS: dict[str, Callable[[], str]] = {
  'api': gen_api,
  'cli': gen_cli,
  'components': gen_components,
  'engines': gen_engines,
  'errors': gen_errors,
  'exit-codes': gen_exit_codes,
  'families': gen_families,
  'filters': gen_filters,
  'kinds': gen_kinds,
  'layouts': gen_layouts,
  'manifest': gen_manifest,
  'palette': gen_palette,
  'preprocessors': gen_preprocessors,
  'report-methods': gen_report_methods,
  'templates': gen_templates,
}
"""Name in a ``<!-- generated:NAME -->`` marker to the function that writes the block."""


if __name__ == '__main__':
  sys.exit(main())
