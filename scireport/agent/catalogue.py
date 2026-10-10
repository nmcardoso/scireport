"""What scireport offers, as plain data: templates, layouts, pre-processors, the schema, errors.

The command line (``--json``), the MCP server and the generated skill tables all describe the
same things; they call these functions, so the three cannot disagree. Every function returns
JSON-ready dicts and lists.
"""

from __future__ import annotations

from typing import Any

from scireport.error_help import HELP
from scireport.errors import CODES
from scireport.preprocess.params import params_schema
from scireport.preprocess.registry import Preprocessor, get_preprocessor, list_preprocessors
from scireport.render.layout import Layout
from scireport.render.registry import list_layouts, list_templates, load_layout, load_template
from scireport.render.template import Template
from scireport.spec import kinds as kinds_module
from scireport.spec.schema import manifest_json_schema
from scireport.spec.version import SPEC_VERSION

FAMILIES: dict[str, str] = {
  'E1': 'keys: the key grammar, and values the template reads',
  'E2': 'kinds and value fields',
  'E3': 'table schema',
  'E4': 'assets and bundles',
  'E5': 'versions of the spec, templates, layouts and pandoc',
  'E6': 'pre-processing',
  'E7': 'template and layout definitions',
  'E8': 'rendering and export',
  'E9': 'PDF engines and optional extras',
  'W4': 'unused items',
  'W5': 'versions',
  'W6': 'math',
  'W7': 'Markdown prose',
  'W9': 'PDF engine warnings',
}
"""The first two characters of an error code to what that family is about."""


def list_templates_data() -> list[dict[str, Any]]:
  """List every template version: reference, title, formats and origin."""
  return [_listing(item) for item in list_templates()]


def list_layouts_data() -> list[dict[str, Any]]:
  """List every layout version: reference, title, formats and origin."""
  return [_listing(item) for item in list_layouts()]


def describe_template(ref: str) -> dict[str, Any]:
  """Describe a template: what it reads, which formats it writes, how to use it.

  Parameters
  ----------
  ref : str
      ``name``, ``name@version`` or a template directory.

  Returns
  -------
  dict
      ``ref``, ``title``, ``description``, ``spec``, ``formats``, ``dynamic_keys`` and ``fields``
      (key pattern, kinds, required, description, table columns, figure renditions).

  Raises
  ------
  TemplateError
      With ``E701`` or ``E504`` when the template does not exist.
  """
  template = load_template(ref)
  return _describe_template(template)


def describe_layout(ref: str) -> dict[str, Any]:
  """Describe a layout: formats, PDF engines and options with their defaults.

  Parameters
  ----------
  ref : str
      ``name``, ``name@version`` or a layout directory.

  Returns
  -------
  dict
      ``ref``, ``title``, ``description``, ``spec``, ``formats``, ``pdf_engines``, ``options``
      (name, type, default, choices, description) and ``fonts``.

  Raises
  ------
  TemplateError
      With ``E701`` or ``E504`` when the layout does not exist.
  """
  return _describe_layout(load_layout(ref))


def list_preprocessors_data() -> list[dict[str, Any]]:
  """List the registered pre-processors: reference, summary and the extra they need."""
  return [describe_row(entry, full=False) for entry in list_preprocessors()]


def describe_preprocessor(name: str) -> dict[str, Any]:
  """Describe a pre-processor: its ports and the JSON Schema of its parameters.

  Parameters
  ----------
  name : str
      ``core.histogram``, or with a version, ``core.histogram@1``.

  Returns
  -------
  dict
      ``ref``, ``name``, ``version``, ``summary``, ``requires``, ``inputs``, ``outputs`` and
      ``params`` (a JSON Schema).

  Raises
  ------
  PreprocessError
      With ``E601`` when no such pre-processor is registered.
  """
  base, _, version = name.partition('@')
  if version.isdigit():
    return describe_row(get_preprocessor(base, int(version)), full=True)
  return describe_row(get_preprocessor(name), full=True)


def describe_row(entry: Preprocessor, *, full: bool) -> dict[str, Any]:
  """Return the listing row of a pre-processor, with ports and parameters when ``full``."""
  row: dict[str, Any] = {
    'ref': entry.ref,
    'name': entry.name,
    'version': entry.version,
    'summary': entry.summary,
    'requires': entry.requires,
  }
  if full:
    for direction, ports in (('inputs', entry.inputs), ('outputs', entry.outputs)):
      row[direction] = {
        port: {'kind': spec.kind, 'optional': spec.optional, 'description': spec.description}
        for port, spec in ports.items()
      }
    row['params'] = params_schema(entry)
  return row


def spec_schema() -> dict[str, Any]:
  """Return the JSON Schema of the data file for the newest spec version.

  Returns
  -------
  dict
      The schema generated from the pydantic models, with the spec version under ``version``.
  """
  return {'version': SPEC_VERSION, 'schema': manifest_json_schema()}


def spec_kinds() -> list[dict[str, Any]]:
  """List the value kinds: tag, a one-line summary and the fields."""
  rows = []
  for kind in kinds_module.KINDS:
    model = getattr(kinds_module, f'{kind.capitalize()}Value')
    summary = (model.__doc__ or '').strip().splitlines()[0].replace('``', '')
    rows.append(
      {
        'kind': kind,
        'summary': summary,
        'fields': [name for name in model.model_fields if name != 'kind'],
      }
    )
  return rows


def error_help(code: str) -> dict[str, Any]:
  """Explain an error or warning code.

  Parameters
  ----------
  code : str
      For example ``E103`` or ``W401`` (case does not matter).

  Returns
  -------
  dict
      ``code``, ``severity``, ``title``, ``family``, ``fix`` (the usual cause and what to do)
      and ``known``. For an unknown code ``known`` is False and ``similar`` lists the codes of
      the same family.
  """
  wanted = code.strip().upper()
  family = FAMILIES.get(wanted[:2], '')
  if wanted not in CODES:
    return {
      'code': wanted,
      'known': False,
      'family': family,
      'similar': [name for name in CODES if wanted[:2] and name.startswith(wanted[:2])],
    }
  return {
    'code': wanted,
    'known': True,
    'severity': 'warning' if wanted.startswith('W') else 'error',
    'title': CODES[wanted],
    'family': family,
    'fix': HELP.get(wanted, ''),
  }


def _listing(item: Any) -> dict[str, Any]:
  """Return the JSON row of a template or layout listing."""
  return {
    'ref': item.ref,
    'name': item.name,
    'version': item.version,
    'title': item.title,
    'formats': list(item.formats),
    'origin': item.origin,
  }


def _describe_template(template: Template) -> dict[str, Any]:
  """Return the JSON description of a loaded template."""
  definition = template.definition
  return {
    'ref': template.ref,
    'title': definition.title,
    'description': definition.description,
    'spec': definition.spec,
    'origin': template.origin,
    'formats': list(definition.formats),
    'dynamic_keys': definition.dynamic_keys,
    'fields': [
      {
        'key': field.key,
        'kinds': field.kinds,
        'required': field.required,
        'description': field.description,
        'columns': [
          {'name': column.name, 'dtype': column.dtype, 'required': column.required}
          for column in field.columns
        ],
        'renditions': list(field.renditions),
      }
      for field in definition.fields
    ],
  }


def _describe_layout(layout: Layout) -> dict[str, Any]:
  """Return the JSON description of a loaded layout."""
  definition = layout.definition
  return {
    'ref': layout.ref,
    'title': definition.title,
    'description': definition.description,
    'spec': definition.spec,
    'origin': layout.origin,
    'formats': list(definition.formats),
    'pdf_engines': list(definition.pdf_engines),
    'options': [
      {
        'name': option.name,
        'type': option.type,
        'default': option.default,
        'choices': list(option.choices) if option.choices is not None else None,
        'description': option.description,
      }
      for option in definition.options
    ],
    'fonts': list(definition.fonts),
  }
