import json
from pathlib import Path
from typing import Any

import pytest
from helpers import PNG_BYTES
from render_fixtures import PDF_BYTES, kitchen_sink, write_template

from scireport import Bundle, Report
from scireport.errors import RenderError
from scireport.render import load_layout, load_template
from scireport.render.definition import Format
from scireport.spec.kinds import TableValue
from scireport.validate import validate_bundle
from scireport.validate.checks import abstract_dtype, check_fields, table_dtypes
from scireport.validate.report import ValidationReport, dedupe


def check(
  report: Report,
  template_extra: str,
  tmp_path: Path,
  body: str = '',
  formats: tuple[Format, ...] = ('md',),
  **kw: Any,
) -> ValidationReport:
  template = load_template(write_template(tmp_path / 't', body=body, extra=template_extra))
  return validate_bundle(report.build(), template, load_layout('minimal'), list(formats), **kw)


def table_value(bundle: Bundle, key: str) -> TableValue:
  value = bundle.manifest.values[key]
  assert isinstance(value, TableValue)
  return value


def codes(report: ValidationReport) -> list[str]:
  return [i.code for i in report.issues]


def test_a_valid_bundle_passes() -> None:
  bundle = kitchen_sink()
  report = validate_bundle(
    bundle, load_template('generic'), load_layout('minimal'), ['md', 'html', 'tex']
  )
  assert report.ok and report.issues == ()
  assert report.exit_code == 0 and report.warnings == () and report.errors == ()


def test_required_fields_missing_from_the_bundle(tmp_path: Path) -> None:
  extra = (
    'fields:\n'
    '  - {key: crossmatch.pairs, kind: table, description: the matched pairs}\n'
    '  - {key: qa.*.summary, kind: table}\n'
    '  - {key: optional.thing, kind: text, required: false}\n'
  )
  report = Report('T').add_table('crossmatch.pair', {'a': [1]})
  found = check(report, extra, tmp_path)
  assert codes(found) == ['E105', 'E105']
  first, second = found.issues
  assert first.hint == "Did you mean 'crossmatch.pair'?"
  assert 'the matched pairs' in first.message and first.location == 'template.yaml fields[0]'
  assert "pattern 'qa.*.summary'" in second.message


def test_a_value_of_the_wrong_kind(tmp_path: Path) -> None:
  found = check(
    Report('T').add_number('n', 1), 'fields:\n  - {key: n, kind: [table, figure]}', tmp_path
  )
  assert codes(found) == ['E207']
  assert found.issues[0].expected == 'table or figure' and found.issues[0].found == 'number'


def test_table_columns_are_checked(tmp_path: Path) -> None:
  extra = (
    'fields:\n  - key: t\n    kind: table\n    columns:\n'
    '      - {name: id, dtype: int}\n      - {name: z, dtype: float}\n'
    '      - {name: label, dtype: string}\n      - {name: gone}\n'
    '      - {name: opt, required: false}\n'
    '      - {name: n, dtype: number}\n'
  )
  table = {'id': [1.5], 'z': [1.0], 'lable': ['x'], 'n': [1]}
  found = check(Report('T').add_table('t', table), extra, tmp_path)
  assert codes(found) == ['E304', 'E303', 'E303']
  assert "column 'id'" in found.issues[0].message
  assert found.issues[1].hint == "Did you mean 'lable'?"


def test_figure_renditions_are_checked(tmp_path: Path) -> None:
  extra = 'fields:\n  - {key: f, kind: figure, renditions: [png, pdf]}'
  png_only = Report('T').add_figure('f', {'png': PNG_BYTES}, alt='x')
  assert codes(check(png_only, extra, tmp_path)) == ['E210']
  both = Report('T').add_figure('f', {'png': PNG_BYTES, 'pdf': PDF_BYTES}, alt='x')
  assert codes(check(both, extra, tmp_path)) == []


def test_keys_the_template_reads_must_exist(tmp_path: Path) -> None:
  report = Report('T').add_number('crossmatch.n_pairs', 1).add_table('tables.t', {'a': [1]})
  body = (
    "{{ data.crossmatch.n_pairs.value }}\n{{ data.crossmatch.n_pair }}\n{{ v('tables.tt') }}\n"
    "{{ data.crossmatch }}\n{{ has('nothing.here') }}\n{{ data.tables.t.columns }}"
  )
  found = check(report, '', tmp_path, body=body)
  e106 = [i for i in found.issues if i.code == 'E106']
  assert [(i.key, i.location) for i in e106] == [
    ('crossmatch.n_pair', 'report.j2:2'),
    ('tables.tt', 'report.j2:3'),
    ('nothing', 'report.j2:5'),
  ]
  assert e106[0].hint == "Did you mean 'crossmatch.n_pairs'?"
  assert not found.ok


def test_computed_keys_only_warn(tmp_path: Path) -> None:
  found = check(
    Report('T').add_number('a.b', 1), '', tmp_path, body="{{ v('a.' ~ x) }}{{ data.a[x] }}"
  )
  assert codes(found) == ['W403', 'W403'] or set(codes(found)) == {'W403'}
  assert found.ok


def test_bad_number_formats_are_reported(tmp_path: Path) -> None:
  report = (
    Report('T')
    .add_number('n', 1, format='bogus')
    .add_table('t', {'a': [1]}, columns=[{'name': 'a', 'format': '.2q'}])
  )
  found = check(report, '', tmp_path)
  assert codes(found) == ['E205', 'E205']
  assert found.issues[1].pointer == '/values/t/columns/0/format'


def test_declared_columns_must_exist_in_the_data(tmp_path: Path) -> None:
  found = check(Report('T').add_table('t', {'a': [1]}, columns=['a', 'b']), '', tmp_path)
  assert codes(found) == ['E305']
  assert found.issues[0].pointer == '/values/t/columns/1'


def test_raw_latex_needs_a_replacement_for_each_format(tmp_path: Path) -> None:
  report = Report('T').add_text('t', r'\x', format='latex', alt={'md': 'x'})
  assert codes(check(report, '', tmp_path, formats=('md', 'tex'))) == []
  assert codes(check(report, '', tmp_path, formats=('md', 'html', 'tex'))) == ['E209']


def test_math_is_checked_only_when_html_is_written(tmp_path: Path) -> None:
  report = Report('T').add_math('m', r'\begin{align} x \end{align}')
  assert codes(check(report, '', tmp_path, formats=('tex',))) == []
  found = check(report, '', tmp_path, formats=('html',))
  assert codes(found) == ['W601'] and found.ok
  assert check(report, '', tmp_path, formats=('html',), strict=True).exit_code == 2


def test_figures_need_a_rendition_each_format_can_use(tmp_path: Path) -> None:
  report = Report('T').add_figure('f', {'pdf': PDF_BYTES}, alt='x')
  found = check(report, '', tmp_path, formats=('md', 'html', 'tex'))
  assert codes(found) == ['E210', 'E210']


def test_asset_problems_are_included(tmp_path: Path) -> None:
  bundle = kitchen_sink()
  out = tmp_path / 'b'
  from scireport import write_bundle

  write_bundle(bundle, out)
  (out / 'assets' / 'figures' / 'figures.curve.png').write_bytes(b'tampered')
  from scireport import open_bundle

  with open_bundle(out) as opened:
    found = validate_bundle(opened, load_template('generic'), load_layout('minimal'), ['md'])
  assert 'E403' in codes(found) or 'E402' in codes(found)


def test_layout_options_are_validated(tmp_path: Path) -> None:
  found = check(Report('T'), '', tmp_path, options={'paper': 'tabloid'})
  assert codes(found) == ['E806']


def test_report_semantics() -> None:
  from scireport.errors import Issue

  issues = (Issue('E101', 'a'), Issue('W401', 'b'))
  loose = ValidationReport(issues)
  assert [i.code for i in loose.errors] == ['E101'] and [i.code for i in loose.warnings] == ['W401']
  strict = ValidationReport((Issue('W401', 'b'),), strict=True)
  assert not strict.ok and strict.exit_code == 2 and strict.warnings == ()
  assert ValidationReport((Issue('W401', 'b'),)).ok
  data = loose.to_dict()
  assert data['ok'] is False and data['counts'] == {'errors': 1, 'warnings': 1}
  assert json.dumps(data)
  with pytest.raises(RenderError) as caught:
    loose.raise_for_errors()
  assert caught.value.code == 'E101' and len(caught.value.issues) == 2
  ValidationReport(()).raise_for_errors()


def test_dedupe_keeps_order() -> None:
  from scireport.errors import Issue

  a, b = Issue('E101', 'a'), Issue('E102', 'b')
  assert dedupe([a, b, a, b, a]) == [a, b]


def test_dtypes_of_inline_parquet_and_csv_tables() -> None:
  report = Report('T')
  report.add_table(
    'i', {'a': [1, 2], 'b': [1.5, None], 'c': ['x', 'y'], 'd': [True, False]}, inline=True
  )
  report.add_table('p', {'a': [1], 'ts': ['2026-01-01']})
  report.add_table('c', {'a': [1], 'b': ['x']}, format='csv')
  bundle = report.build()
  assert table_dtypes(bundle, table_value(bundle, 'i')) == {
    'a': 'int',
    'b': 'float',
    'c': 'string',
    'd': 'bool',
  }
  assert table_dtypes(bundle, table_value(bundle, 'p')) == {'a': 'int', 'ts': 'string'}
  assert table_dtypes(bundle, table_value(bundle, 'c')) == {'a': 'int', 'b': 'string'}


def test_abstract_dtype_covers_arrow_types() -> None:
  import pyarrow as pa

  assert [
    abstract_dtype(t)
    for t in (
      pa.int8(),
      pa.float32(),
      pa.decimal128(5, 2),
      pa.large_string(),
      pa.bool_(),
      pa.timestamp('s'),
      pa.date32(),
      pa.list_(pa.int8()),
    )
  ] == ['int', 'float', 'float', 'string', 'bool', 'timestamp', 'date', 'other']


def test_check_fields_without_fields_finds_nothing() -> None:
  bundle = kitchen_sink()
  assert check_fields(load_template('generic'), bundle) == []
