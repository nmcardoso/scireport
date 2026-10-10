"""Starter data files: what ``scireport new`` writes.

A starter is a hand-authored directory bundle with a ``scireport.yaml`` that already validates
against its template, so a person (or an agent) edits values instead of learning the format first.
With the built-in ``generic`` template it is a small report; with another template it holds a
placeholder for every field the template requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scireport.bundle.backends import YAML_MANIFEST_NAMES
from scireport.errors import BundleError
from scireport.render.template import ColumnSpec, FieldSpec, Template
from scireport.spec.version import SPEC_VERSION

_SAMPLE_DATE = '2000-01-01'
_CELLS: dict[str, Any] = {
  'int': 1,
  'float': 1.5,
  'number': 1,
  'string': 'text',
  'bool': True,
  'date': _SAMPLE_DATE,
  'timestamp': f'{_SAMPLE_DATE}T00:00:00',
  'any': 'text',
}
_NEEDS_FILES = frozenset({'figure', 'image', 'attachment', 'bibliography'})


@dataclass(frozen=True)
class Scaffold:
  """A starter data file.

  Parameters
  ----------
  text : str
      The content of ``scireport.yaml``.
  notes : tuple of str
      What the author still has to add (values that need a file).
  """

  text: str
  notes: tuple[str, ...] = ()


def make_scaffold(
  title: str, *, template: Template | None = None, layout: str | None = None
) -> Scaffold:
  """Build the content of a starter ``scireport.yaml``.

  Parameters
  ----------
  title : str
      The report title.
  template : Template or None, default=None
      A loaded template; its required fields get placeholder values. None writes the starter
      for the built-in ``generic`` template.
  layout : str or None, default=None
      The layout reference written to ``render.layout``; the default layout when None.

  Returns
  -------
  Scaffold
      The text and the notes about values that need files.
  """
  render: dict[str, Any] = {'template': template.ref if template else 'generic@1'}
  if layout:
    render['layout'] = layout
  render['formats'] = ['md', 'html']
  meta = {'title': title, 'authors': ['Your Name'], 'date': _SAMPLE_DATE, 'language': 'en'}
  head = {'scireport': SPEC_VERSION, 'meta': meta, 'render': render}
  notes: list[str] = []
  if template is None or not template.definition.fields:
    body: dict[str, Any] = {
      'outline': [
        'summary',
        {'title': 'Results', 'children': ['results.n_items', 'results.table']},
      ],
      'values': _generic_values(),
    }
  else:
    values: dict[str, Any] = {}
    for spec in template.definition.fields:
      if spec.required:
        _add_field(values, spec, notes)
    body = {'values': values}
  text = (
    f'# Starter data file for scireport {SPEC_VERSION}. Edit the values; run\n'
    '#   scireport validate . && scireport render . -o out\n'
    + yaml.safe_dump(head, sort_keys=False, allow_unicode=True)
    + yaml.safe_dump(body, sort_keys=False, allow_unicode=True)
  )
  return Scaffold(text, tuple(notes))


def write_scaffold(dest: Path, scaffold: Scaffold, *, overwrite: bool = False) -> Path:
  """Write a starter into a directory.

  Parameters
  ----------
  dest : pathlib.Path
      The bundle directory; created when missing.
  scaffold : Scaffold
      What :func:`make_scaffold` returned.
  overwrite : bool, default=False
      Replace an existing ``scireport.yaml``.

  Returns
  -------
  pathlib.Path
      The manifest file.

  Raises
  ------
  BundleError
      With ``E410`` when the directory already holds files and ``overwrite`` is false.
  """
  manifest = dest / YAML_MANIFEST_NAMES[0]
  if dest.exists() and any(dest.iterdir()) and not (overwrite and manifest.exists()):
    raise BundleError(
      f'{dest} is not empty',
      code='E410',
      hint='Choose a new directory, or use --force to replace its scireport.yaml.',
    )
  dest.mkdir(parents=True, exist_ok=True)
  manifest.write_text(scaffold.text, encoding='utf-8', newline='\n')
  return manifest


def _generic_values() -> dict[str, Any]:
  """Return the values of the generic starter."""
  return {
    'summary': 'One paragraph that says what this report shows.',
    'results.n_items': {'kind': 'number', 'value': 3061, 'format': 'int', 'unit': 'items'},
    'results.table': {
      'kind': 'table',
      'caption': 'An example table.',
      'columns': [
        {'name': 'name', 'label': 'Name'},
        {'name': 'value', 'label': 'Value', 'unit': 'arcsec', 'format': '.2f'},
      ],
      'rows': [['alpha', 1.25], ['beta', 2.5]],
    },
  }


def _add_field(values: dict[str, Any], spec: FieldSpec, notes: list[str]) -> None:
  """Add a placeholder for one required field, or a note when it needs a file."""
  key = spec.key.replace('**', 'example.group').replace('*', 'example')
  kind = spec.kinds[0]
  if kind in _NEEDS_FILES:
    notes.append(f'{key}: a {kind} needs a file in assets/; add it and list it under values')
    return
  values[key] = _placeholder(kind, spec.columns)


def _placeholder(kind: str, columns: list[ColumnSpec]) -> Any:
  """Return a value of a kind that validates."""
  if kind == 'text':
    return 'Replace this text.'
  if kind == 'number':
    return 0
  if kind == 'bool':
    return False
  if kind == 'date':
    return {'kind': 'date', 'value': _SAMPLE_DATE}
  if kind == 'list':
    return ['item']
  if kind == 'mapping':
    return {'name': 'value'}
  if kind == 'table':
    names = [column.name for column in columns] or ['column']
    dtypes = [column.dtype for column in columns] or ['any']
    return {
      'kind': 'table',
      'columns': [{'name': name} for name in names],
      'rows': [[_CELLS[dtype] for dtype in dtypes]],
    }
  if kind == 'math':
    return {'kind': 'math', 'latex': 'x = 1'}
  if kind == 'code':
    return {'kind': 'code', 'source': 'print("hello")', 'language': 'python'}
  if kind == 'metrics':
    return {'kind': 'metrics', 'items': [{'label': 'Items', 'value': 0}]}
  if kind == 'status':
    return {'kind': 'status', 'level': 'success', 'headline': 'COMPLETED'}
  if kind == 'alert':
    return {'kind': 'alert', 'level': 'info', 'text': 'Replace this message.'}
  return {'kind': 'flow', 'stages': [{'label': 'STAGE'}]}
