"""One group of tests per v1.0 kind, plus the canonicalisation of bare JSON."""

from __future__ import annotations

from typing import Any

import pytest
from helpers import asset_ref
from pydantic import ValidationError

from scireport.spec.kinds import (
  KINDS,
  AlertValue,
  AttachmentValue,
  BoolValue,
  CodeValue,
  DateValue,
  FigureValue,
  FlowValue,
  ImageValue,
  ListValue,
  MappingValue,
  MathValue,
  MetricsValue,
  NumberValue,
  StatusValue,
  TableValue,
  TextValue,
  canonicalise,
  value_adapter,
)
from scireport.spec.manifest import issues_from_validation_error

PNG = asset_ref('assets/figures/f.png')
PDF = asset_ref('assets/figures/f.pdf')


def codes(raw: Any) -> set[str]:
  """Return the error codes produced by validating ``raw`` as a value."""
  try:
    value_adapter.validate_python(raw)
  except ValidationError as exc:
    return {issue.code for issue in issues_from_validation_error(exc, raw)}
  return set()


def test_all_sixteen_kinds_are_listed() -> None:
  assert len(KINDS) == 16
  assert len(set(KINDS)) == 16


# ---- shorthand --------------------------------------------------------------------------------


@pytest.mark.parametrize(
  ('raw', 'cls', 'check'),
  [
    ('hello', TextValue, lambda v: v.text == 'hello' and v.format == 'plain'),
    (True, BoolValue, lambda v: v.value is True),
    (3, NumberValue, lambda v: v.value == 3 and isinstance(v.value, int)),
    (2.5, NumberValue, lambda v: v.value == 2.5),
    (None, NumberValue, lambda v: v.value is None),
    ([1, 'a'], ListValue, lambda v: [i.kind for i in v.items] == ['number', 'text']),
    ({'b': 1, 'a': 'x'}, MappingValue, lambda v: [e.key for e in v.entries] == ['b', 'a']),
  ],
)
def test_bare_json_is_canonicalised(raw: Any, cls: type, check: Any) -> None:
  value = value_adapter.validate_python(raw)
  assert isinstance(value, cls)
  assert check(value)


def test_bool_is_not_a_number() -> None:
  assert isinstance(value_adapter.validate_python(False), BoolValue)
  assert codes({'kind': 'number', 'value': True}) == {'E205'}


def test_object_with_kind_is_always_an_envelope() -> None:
  assert codes({'kind': 'nonsense'}) == {'E201'}
  assert codes({'text': 'no kind but this is a mapping'}) == set()


def test_unrecognised_python_objects_are_rejected() -> None:
  assert codes(object()) == {'E205'}


def test_canonicalise_is_idempotent_on_envelopes() -> None:
  envelope = {'kind': 'bool', 'value': True}
  assert canonicalise(envelope) is envelope
  model = value_adapter.validate_python('x')
  assert canonicalise(model) is model


def test_dates_become_date_values() -> None:
  import datetime as dt

  assert value_adapter.validate_python(dt.date(2026, 10, 9)).value == '2026-10-09'


def test_nested_shorthand_in_lists_and_mappings() -> None:
  value = value_adapter.validate_python({'a': [1, {'b': None}]})
  inner = value.entries[0].value
  assert isinstance(inner, ListValue)
  assert isinstance(inner.items[1], MappingValue)


# ---- text -------------------------------------------------------------------------------------


def test_text_inline_or_asset() -> None:
  assert codes({'kind': 'text', 'text': 'x'}) == set()
  assert codes({'kind': 'text', 'asset': asset_ref('assets/text/t.md')}) == set()
  assert codes({'kind': 'text'}) == {'E206'}
  assert codes({'kind': 'text', 'text': 'x', 'asset': asset_ref('assets/text/t.md')}) == {'E206'}


def test_text_alt_only_for_latex() -> None:
  assert codes({'kind': 'text', 'text': 'x', 'alt': {'html': 'y'}}) == {'E205'}
  ok = {
    'kind': 'text',
    'text': r'\alpha',
    'format': 'latex',
    'alt': {'html': 'α', 'md': '$\\alpha$'},
  }
  assert codes(ok) == set()
  assert codes({'kind': 'text', 'text': 'x', 'format': 'rtf'}) == {'E205'}


# ---- number -----------------------------------------------------------------------------------


def test_number_fields() -> None:
  full = {'kind': 'number', 'value': 1.5, 'unit': 'deg', 'format': '.2f', 'uncertainty': 0.1}
  assert codes(full) == set()
  assert codes({'kind': 'number', 'value': 1, 'interval': [0, 2]}) == set()
  assert codes({'kind': 'number', 'value': None, 'missing': 'n/a'}) == set()


@pytest.mark.parametrize(
  ('raw', 'expected'),
  [
    ({'kind': 'number', 'value': 1, 'uncertainty': 0.1, 'interval': [0, 2]}, {'E206'}),
    ({'kind': 'number', 'value': 1, 'interval': [3, 2]}, {'E205'}),
    ({'kind': 'number', 'value': 1, 'uncertainty': -1}, {'E205'}),
    ({'kind': 'number', 'uncertainty': 0.1}, {'E205'}),
    ({'kind': 'number', 'value': '1'}, {'E205'}),
    ({'kind': 'number', 'value': float('nan')}, {'E205'}),
    ({'kind': 'number', 'value': float('inf')}, {'E205'}),
  ],
)
def test_number_rejections(raw: dict[str, Any], expected: set[str]) -> None:
  assert codes(raw) == expected


def test_number_keeps_integers_integral() -> None:
  assert type(value_adapter.validate_python(7).value) is int
  assert type(value_adapter.validate_python(7.0).value) is float


# ---- bool and date ----------------------------------------------------------------------------


def test_bool_is_strict() -> None:
  assert codes({'kind': 'bool', 'value': 'yes'}) == {'E205'}
  assert codes({'kind': 'bool', 'value': 1}) == {'E205'}


@pytest.mark.parametrize(
  ('raw', 'expected'),
  [
    ('2026-10-09', '2026-10-09'),
    ('20261009', '2026-10-09'),
    ('2026-10-09T10:30:00', '2026-10-09T10:30:00'),
    ('2026-10-09T10:30:00Z', '2026-10-09T10:30:00+00:00'),
  ],
)
def test_date_is_canonicalised(raw: str, expected: str) -> None:
  value = value_adapter.validate_python({'kind': 'date', 'value': raw})
  assert isinstance(value, DateValue)
  assert value.value == expected
  assert value_adapter.validate_python({'kind': 'date', 'value': expected}).value == expected


@pytest.mark.parametrize('raw', ['yesterday', '2026-13-01', '', '10/09/2026'])
def test_date_rejects_non_iso(raw: str) -> None:
  assert codes({'kind': 'date', 'value': raw}) == {'E205'}


# ---- list and mapping -------------------------------------------------------------------------


def test_list_ordered_flag_and_nesting() -> None:
  value = value_adapter.validate_python({'kind': 'list', 'items': [[1], 'a'], 'ordered': True})
  assert isinstance(value, ListValue)
  assert value.ordered


def test_mapping_needs_unique_nonempty_labels() -> None:
  entry = {'key': 'a', 'value': 1}
  assert codes({'kind': 'mapping', 'entries': [entry]}) == set()
  assert codes({'kind': 'mapping', 'entries': [entry, entry]}) == {'E205'}
  assert codes({'kind': 'mapping', 'entries': [{'key': '', 'value': 1}]}) == {'E205'}


# ---- table ------------------------------------------------------------------------------------


def table(**fields: Any) -> dict[str, Any]:
  return {'kind': 'table', **fields}


def test_table_from_parquet_or_csv() -> None:
  parquet = value_adapter.validate_python(table(asset=asset_ref('assets/tables/t.parquet')))
  csv = value_adapter.validate_python(table(asset=asset_ref('assets/tables/t.csv')))
  inline = value_adapter.validate_python(table(columns=[{'name': 'a'}], rows=[[1]]))
  assert (parquet.format, csv.format, inline.format) == ('parquet', 'csv', 'inline')
  assert isinstance(parquet, TableValue)


@pytest.mark.parametrize(
  ('raw', 'expected'),
  [
    (table(), {'E206'}),
    (table(asset=asset_ref('assets/tables/t.csv'), rows=[[1]], columns=[{'name': 'a'}]), {'E206'}),
    (table(asset=asset_ref('assets/tables/t.txt')), {'E205'}),
    (table(rows=[[1]]), {'E301'}),
    (table(columns=[{'name': 'a'}, {'name': 'b'}], rows=[[1]]), {'E301'}),
    (table(columns=[{'name': 'a'}, {'name': 'a'}], rows=[[1, 2]]), {'E302'}),
    (table(columns=[{'name': 'a'}], rows=[[1]], n_rows=2), {'E301'}),
    (table(columns=[{'name': 'a'}], rows=[[1]], row_status=['pass', 'fail']), {'E301'}),
    (table(columns=[{'name': 'a'}], rows=[[1]], row_status=['ok']), {'E205'}),
    (
      table(columns=[{'name': 'a'}], rows=[[1]], row_status=[None], row_status_column='a'),
      {'E206'},
    ),
    (table(columns=[{'name': 'a'}], rows=[[1]], row_status_column='zz'), {'E302'}),
    (
      table(
        columns=[{'name': 'a'}],
        rows=[[1]],
        emphasis=[{'row': 0, 'column': 'zz', 'style': 'strong'}],
      ),
      {'E302'},
    ),
    (table(columns=[{'name': 'a'}], rows=[[{'x': 1}]]), {'E205'}),
    (table(columns=[{'name': 'a', 'width': 0}], rows=[[1]]), {'E205'}),
    (table(columns=[{'name': 'a', 'align': 'middle'}], rows=[[1]]), {'E205'}),
    (table(columns=[{'name': 'a'}], rows=[[1]], max_rows=0), {'E205'}),
    (table(columns=[{'name': 'a'}], rows=[[1]], overflow_attachment='Bad Key'), {'E101'}),
  ],
)
def test_table_rules(raw: dict[str, Any], expected: set[str]) -> None:
  assert codes(raw) == expected


def test_table_full_presentation() -> None:
  raw = table(
    columns=[
      {'name': 'a', 'label': 'A', 'unit': 'm', 'format': '.1f', 'align': 'right', 'width': 0.5},
      {'name': 'b', 'description': 'text', 'align': 'path'},
    ],
    rows=[[1.5, 'x'], [None, True]],
    row_status=['pass', None],
    emphasis=[{'row': 0, 'column': 'a', 'style': 'strong'}],
    max_rows=10,
    overflow_attachment='all.rows',
    caption='c',
    n_rows=2,
  )
  assert codes(raw) == set()


# ---- figure and image -------------------------------------------------------------------------


def figure(**fields: Any) -> dict[str, Any]:
  return {'kind': 'figure', 'renditions': [PNG], 'alt': 'a plot', **fields}


def test_figure_requires_alt_text() -> None:
  without = figure()
  del without['alt']
  assert codes(without) == {'E203'}
  assert codes(figure(alt='')) == {'E205'}
  assert codes(figure(alt='   ')) == {'E205'}


def test_figure_renditions() -> None:
  value = value_adapter.validate_python(figure(renditions=[PNG, PDF]))
  assert isinstance(value, FigureValue)
  assert [r.format for r in value.renditions] == ['png', 'pdf']
  assert codes(figure(renditions=[])) == {'E205'}
  assert codes(figure(renditions=[PNG, PNG])) == {'E205'}
  mismatch = {**PNG, 'format': 'pdf'}
  assert codes(figure(renditions=[mismatch])) == {'E205'}
  assert codes(figure(renditions=[asset_ref('assets/figures/f.gif')])) == {'E205'}


def test_figure_width_and_sidecar() -> None:
  assert (
    codes(figure(width=0.5, caption='c', data=asset_ref('assets/figures/f.data.parquet'))) == set()
  )
  assert codes(figure(width=1.5)) == {'E205'}
  assert codes(figure(width=0)) == {'E205'}
  assert codes(figure(data=asset_ref('assets/figures/f.data.bin'))) == {'E205'}


def test_image_suffixes() -> None:
  ok = {'kind': 'image', 'asset': asset_ref('assets/images/logo.svg')}
  assert isinstance(value_adapter.validate_python(ok), ImageValue)
  assert codes({**ok, 'alt': 'logo', 'caption': 'c', 'width': 0.3}) == set()
  assert codes({'kind': 'image', 'asset': asset_ref('assets/images/logo.bmp')}) == {'E205'}


# ---- math, code -------------------------------------------------------------------------------


def test_math() -> None:
  assert isinstance(value_adapter.validate_python({'kind': 'math', 'latex': 'x^2'}), MathValue)
  assert codes({'kind': 'math', 'latex': ''}) == {'E205'}
  assert codes({'kind': 'math'}) == {'E203'}


def test_code_inline_or_asset() -> None:
  assert isinstance(value_adapter.validate_python({'kind': 'code', 'source': 'x = 1'}), CodeValue)
  assert (
    codes({'kind': 'code', 'asset': asset_ref('assets/text/c.txt'), 'language': 'sql'}) == set()
  )
  assert codes({'kind': 'code'}) == {'E206'}


# ---- dashboard blocks -------------------------------------------------------------------------


def test_metrics_accept_bare_values() -> None:
  value = value_adapter.validate_python(
    {
      'kind': 'metrics',
      'items': [{'label': 'N', 'value': 3061, 'detail': 'pairs'}, {'label': 'S', 'value': 'ok'}],
    }
  )
  assert isinstance(value, MetricsValue)
  assert [i.value.kind for i in value.items] == ['number', 'text']
  assert codes({'kind': 'metrics', 'items': []}) == {'E205'}
  assert codes({'kind': 'metrics', 'items': [{'label': 'N', 'value': True}]}) == {'E201'}


def test_status_and_alert_levels() -> None:
  assert isinstance(
    value_adapter.validate_python({'kind': 'status', 'level': 'success', 'headline': 'OK'}),
    StatusValue,
  )
  assert codes({'kind': 'status', 'level': 'fine', 'headline': 'OK'}) == {'E205'}
  assert codes({'kind': 'status', 'level': 'failed', 'headline': ''}) == {'E205'}
  assert isinstance(
    value_adapter.validate_python({'kind': 'alert', 'level': 'info', 'text': 'x'}), AlertValue
  )
  assert codes({'kind': 'alert', 'level': 'success', 'text': 'x'}) == {'E205'}


def test_flow_defaults_and_states() -> None:
  value = value_adapter.validate_python(
    {
      'kind': 'flow',
      'stages': [{'label': 'INGEST', 'detail': ['1 row']}, {'label': 'X', 'state': 'skipped'}],
    }
  )
  assert isinstance(value, FlowValue)
  assert value.stages[0].state == 'done'
  assert codes({'kind': 'flow', 'stages': []}) == {'E205'}
  assert codes({'kind': 'flow', 'stages': [{'label': 'A', 'state': 'broken'}]}) == {'E205'}


# ---- attachment -------------------------------------------------------------------------------


def test_attachment_filename_rules() -> None:
  ok = {
    'kind': 'attachment',
    'asset': asset_ref('assets/attachments/a.csv'),
    'filename': 'full.csv',
  }
  assert isinstance(value_adapter.validate_python(ok), AttachmentValue)
  for bad in ['a/b.csv', 'a\\b.csv', '..', '.', 'x\x00y']:
    assert codes({**ok, 'filename': bad}) == {'E205'}, bad
  assert codes({**ok, 'media_type': 'text/csv', 'description': 'd'}) == set()


# ---- strictness and immutability --------------------------------------------------------------


def test_unknown_fields_are_rejected_everywhere() -> None:
  assert codes({'kind': 'bool', 'value': True, 'extra': 1}) == {'E204'}
  assert codes({'kind': 'table', 'rows': [[1]], 'columns': [{'name': 'a', 'bogus': 1}]}) == {'E204'}


def test_models_are_frozen() -> None:
  value = value_adapter.validate_python(True)
  with pytest.raises(ValidationError):
    value.value = False
