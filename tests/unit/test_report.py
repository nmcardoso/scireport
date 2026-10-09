"""The Report builder."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest
from matplotlib.figure import Figure

from scireport import KeyConflictError, Report, SpecError, open_bundle
from scireport.report import INLINE_TEXT_BYTES, serialise_table, to_arrow_table


def figure() -> Figure:
  fig = Figure(figsize=(3, 2))
  fig.subplots().plot([1, 2, 3], [3, 1, 2])
  return fig


def codes(error: pytest.ExceptionInfo[Any]) -> list[str]:
  return [issue.code for issue in error.value.issues]


# ---- keys -------------------------------------------------------------------------------------


def test_keys_are_checked() -> None:
  report = Report('R').add_number('a.b', 1)
  with pytest.raises(KeyConflictError) as info:
    report.add_number('a.b', 2)
  assert info.value.code == 'E104'
  with pytest.raises(KeyConflictError) as info:
    report.add_number('a', 2)
  assert info.value.code == 'E102'
  with pytest.raises(KeyConflictError) as info:
    report.add_number('a.b.c', 2)
  assert info.value.code == 'E102'
  with pytest.raises(SpecError) as bad:
    report.add_number('A b', 2)
  assert codes(bad) == ['E101']
  assert bad.value.issues[0].hint == "Did you mean 'a-b'?"
  assert report.keys == ['a.b']


def test_failed_add_leaves_the_report_unchanged() -> None:
  report = Report('R')
  with pytest.raises(ValueError, match='infinite'):
    report.add_number('n', float('inf'))
  assert report.keys == []


# ---- scalars ----------------------------------------------------------------------------------


def test_scalars_and_shorthand(tmp_path: Path) -> None:
  report = (
    Report('R', date=dt.date(2026, 10, 9), keywords=['k'], generator=('gzms', '1.1.0'))
    .add_number('n', 3061, unit='pairs', format='int')
    .add_number('nan', float('nan'), missing='n/a')
    .add_number('err', 1.5, uncertainty=0.1)
    .add_number('ival', 2.0, interval=(1.0, 3.0))
    .add_bool('ok', True)
    .add_date('when', dt.date(2026, 10, 9))
    .add_date('stamp', '2026-10-09T10:00:00Z')
    .add('free', {'a': [1, 'x']})
    .add('model', 7)
    .add_math('eq', 'E = mc^2', numbered=True, caption='Mass-energy')
    .add_code('sql', 'SELECT 1', language='sql')
    .add_alert('warn', 'warning', 'Careful')
    .add_status('status', 'success', 'ALL GOOD', detail='no problems')
  )
  with open_bundle(report.write(tmp_path / 'r.zip')) as bundle:
    values = bundle.manifest.values
    assert values['nan'].value is None  # type: ignore[union-attr]
    assert values['nan'].missing == 'n/a'  # type: ignore[union-attr]
    assert values['when'].value == '2026-10-09'  # type: ignore[union-attr]
    assert values['stamp'].value == '2026-10-09T10:00:00+00:00'  # type: ignore[union-attr]
    assert values['free'].kind == 'mapping'
    assert bundle.manifest.meta.date == '2026-10-09'
    assert bundle.manifest.provenance.generator is not None
    assert bundle.manifest.provenance.writer is not None
    assert bundle.manifest.provenance.writer.startswith('scireport ')


def test_collections() -> None:
  report = (
    Report('R')
    .add_list('items', [1, 'two', {'k': 'v'}], ordered=True)
    .add_mapping('meta1', {'Version': '1.0', 'Rows': 5})
    .add_mapping('meta2', [('A', 1), ('B', 2)])
    .add_metrics(
      'kpi',
      [('Pairs', 3061), {'label': 'Rate', 'value': 0.5, 'detail': 'of all'}, ('S', 'ok', 'note')],
    )
    .add_flow('flow', ['INGEST', {'label': 'MATCH', 'detail': ['3,061 pairs'], 'state': 'reused'}])
  )
  manifest = report.manifest()
  assert manifest.values['items'].ordered  # type: ignore[union-attr]
  assert [e.key for e in manifest.values['meta2'].entries] == ['A', 'B']  # type: ignore[union-attr]
  assert [i.label for i in manifest.values['kpi'].items] == ['Pairs', 'Rate', 'S']  # type: ignore[union-attr]
  assert [s.state for s in manifest.values['flow'].stages] == ['done', 'reused']  # type: ignore[union-attr]


# ---- text -------------------------------------------------------------------------------------


def test_short_text_is_inline_and_long_text_is_a_file(tmp_path: Path) -> None:
  report = (
    Report('R')
    .add_text('short', 'a' * INLINE_TEXT_BYTES)
    .add_text('long', 'a' * (INLINE_TEXT_BYTES + 1), format='markdown')
    .add_text('forced', 'tiny', as_asset=True, format='latex', alt={'html': 'x', 'md': 'y'})
    .add_text('kept', 'b' * 9000, as_asset=False)
    .add_code('code', 'x' * 9000, language='python')
  )
  with open_bundle(report.write(tmp_path / 'r')) as bundle:
    values = bundle.manifest.values
    assert values['short'].text is not None  # type: ignore[union-attr]
    assert values['long'].asset.path == 'assets/text/long.md'  # type: ignore[union-attr]
    assert values['forced'].asset.path == 'assets/text/forced.tex'  # type: ignore[union-attr]
    assert values['kept'].text == 'b' * 9000  # type: ignore[union-attr]
    assert values['code'].asset.path == 'assets/text/code.txt'  # type: ignore[union-attr]
    assert bundle.read_text('long') == 'a' * (INLINE_TEXT_BYTES + 1)
    assert bundle.verify() == []


# ---- tables -----------------------------------------------------------------------------------


def test_table_inputs() -> None:
  as_arrow = pa.table({'a': [1, 2], 'b': ['x', 'y']})
  assert to_arrow_table(as_arrow).equals(as_arrow)
  assert to_arrow_table({'a': (1, 2)}).to_pydict() == {'a': [1, 2]}
  assert to_arrow_table([{'a': 1}, {'a': 2}]).to_pydict() == {'a': [1, 2]}
  with pytest.raises(TypeError, match='int'):
    to_arrow_table(3)
  with pytest.raises(TypeError):
    to_arrow_table('rows')


def test_pandas_frames_lose_their_index_and_metadata() -> None:
  pd = pytest.importorskip('pandas')
  frame = pd.DataFrame({'a': [1, 2], 'b': [0.5, 1.5]}, index=[10, 20])
  table = to_arrow_table(frame)
  assert table.column_names == ['a', 'b']
  assert table.schema.metadata is None


def test_arrow_stream_objects_are_accepted() -> None:
  class Stream:
    def __arrow_c_stream__(self, requested_schema: object = None) -> object:
      return pa.table({'a': [1, 2]}).__arrow_c_stream__(requested_schema)

  assert to_arrow_table(Stream()).to_pydict() == {'a': [1, 2]}


def test_tables_are_written_as_parquet_by_default(tmp_path: Path) -> None:
  report = Report('R').add_table(
    't',
    {'a': [1, 2, 3], 'b': [0.1, None, 0.3]},
    columns=['a', {'name': 'b', 'label': 'B', 'unit': 'm'}],
    caption='cap',
    row_status_column='a',
    emphasis=[{'row': 0, 'column': 'a', 'style': 'strong'}],
    max_rows=2,
    overflow_attachment='full',
  )
  report.add_attachment('full', b'a,b\n', filename='t.csv')
  with open_bundle(report.write(tmp_path / 'r')) as bundle:
    table = bundle.manifest.values['t']
    assert table.asset.path == 'assets/tables/t.parquet'  # type: ignore[union-attr]
    assert table.n_rows == 3  # type: ignore[union-attr]
    assert [c.name for c in table.columns] == ['a', 'b']  # type: ignore[union-attr]
    assert bundle.read_table('t').to_pydict()['b'] == [0.1, None, 0.3]


def test_csv_and_inline_tables(tmp_path: Path) -> None:
  report = (
    Report('R')
    .add_table('csv', {'a': [1, 2]}, format='csv')
    .add_table(
      'inline',
      {'a': [1, None], 'b': ['x', 'y'], 'c': [float('nan'), 2.5]},
      inline=True,
      columns=['b', 'a'],
      row_status=['pass', None],
    )
  )
  with open_bundle(report.write(tmp_path / 'r')) as bundle:
    assert bundle.manifest.values['csv'].asset.path == 'assets/tables/csv.csv'  # type: ignore[union-attr]
    inline = bundle.manifest.values['inline']
    assert inline.rows == [['x', 1], ['y', None]]  # type: ignore[union-attr]
    assert inline.row_status == ['pass', None]  # type: ignore[union-attr]


def test_inline_tables_take_json_scalars_only() -> None:
  with pytest.raises(SpecError) as info:
    Report('R').add_table('t', {'when': [dt.date(2026, 10, 9)]}, inline=True)
  assert codes(info) == ['E301']
  with pytest.raises(SpecError) as info:
    Report('R').add_table('t', {'a': [1]}, inline=True, columns=['zzz'])
  assert codes(info) == ['E302']


def test_parquet_bytes_are_deterministic() -> None:
  table = pa.table({'a': list(range(100)), 's': [str(i) for i in range(100)]})
  assert serialise_table(table, 'parquet') == serialise_table(table, 'parquet')
  assert serialise_table(table, 'csv').startswith(b'"a","s"\n0,"0"\n')


# ---- figures and files ------------------------------------------------------------------------


def test_matplotlib_figures_are_deterministic_and_clean(tmp_path: Path) -> None:
  def build() -> Report:
    return Report('R').add_figure(
      'f',
      figure(),
      alt='A line',
      caption='cap',
      width=0.5,
      data={'x': [1, 2, 3]},
      formats=('png', 'pdf', 'svg'),
    )

  one = build().write(tmp_path / '1.zip').read_bytes()
  two = build().write(tmp_path / '2.zip').read_bytes()
  assert one == two
  with open_bundle(tmp_path / '1.zip') as bundle:
    value = bundle.manifest.values['f']
    assert [r.format for r in value.renditions] == ['png', 'pdf', 'svg']  # type: ignore[union-attr]
    assert value.data.path == 'assets/figures/f.data.parquet'  # type: ignore[union-attr]
    png = bundle.read_asset('assets/figures/f.png')
    pdf = bundle.read_asset('assets/figures/f.pdf')
    svg = bundle.read_asset('assets/figures/f.svg')
    assert png.startswith(b'\x89PNG')
    assert b'Software' not in png
    assert pdf.startswith(b'%PDF')
    assert b'CreationDate' not in pdf
    assert b'<dc:date>' not in svg
    assert bundle.read_asset('assets/figures/f.data.parquet')


def test_figures_from_files_and_bytes(tmp_path: Path, png_bytes: bytes) -> None:
  png = tmp_path / 'fig.png'
  png.write_bytes(png_bytes)
  report = (
    Report('R')
    .add_figure('from.path', png, alt='a')
    .add_figure('from.map', {'png': png_bytes, 'pdf': b'%PDF-1.4'}, alt='b')
    .add_figure('from.paths', {'png': png}, alt='c')
  )
  values = report.manifest().values
  assert [r.format for r in values['from.map'].renditions] == ['png', 'pdf']  # type: ignore[union-attr]
  assert values['from.path'].renditions[0].sha256 == values['from.paths'].renditions[0].sha256  # type: ignore[union-attr]


def test_figures_need_alt_text() -> None:
  with pytest.raises(SpecError) as info:
    Report('R').add_figure('f', {'png': b'x'}, alt='  ')
  [issue] = info.value.issues
  assert (issue.code, issue.key) == ('E205', 'f')
  assert issue.pointer == '/values/f'


def test_builder_errors_are_coded_with_pointers() -> None:
  report = Report('R')
  with pytest.raises(SpecError) as info:
    report.add_status('s', 'fine', 'headline')  # type: ignore[arg-type]
  assert [(i.code, i.pointer) for i in info.value.issues] == [('E205', '/values/s/level')]
  with pytest.raises(SpecError) as info:
    report.add_number('n', 1, uncertainty=0.1, interval=(0, 2))
  assert [i.code for i in info.value.issues] == ['E206']
  with pytest.raises(SpecError) as info:
    report.set_render(formats=['rtf'])
  assert info.value.issues[0].pointer == '/formats/0'
  with pytest.raises(SpecError) as info:
    report.add('x', {'kind': 'tabel'})
  assert info.value.issues[0].code == 'E201'
  assert report.keys == []


def test_images(tmp_path: Path, png_bytes: bytes) -> None:
  logo = tmp_path / 'logo.PNG'
  logo.write_bytes(png_bytes)
  report = (
    Report('R')
    .add_image('a', logo, alt='logo', caption='c', width=0.3)
    .add_image('b', png_bytes, suffix='.png')
  )
  assert report.manifest().values['a'].asset.path == 'assets/images/a.png'  # type: ignore[union-attr]
  with pytest.raises(ValueError, match='suffix'):
    report.add_image('c', png_bytes)


def test_attachments(tmp_path: Path) -> None:
  source = tmp_path / 'rows.csv'
  source.write_bytes(b'a\n1\n')
  report = (
    Report('R')
    .add_attachment('csv', source, description='all rows')
    .add_attachment('raw', b'xx', filename='data.bin')
    .add_attachment('noext', b'xx', filename='README', media_type='text/plain')
    .add_attachment('weird', b'xx', filename='a.tar.gz-ish!')
  )
  values = report.manifest().values
  assert values['csv'].filename == 'rows.csv'  # type: ignore[union-attr]
  assert values['csv'].media_type == 'text/csv'  # type: ignore[union-attr]
  assert values['csv'].asset.path == 'assets/attachments/csv.csv'  # type: ignore[union-attr]
  assert values['raw'].media_type is None  # type: ignore[union-attr]
  assert values['noext'].asset.path == 'assets/attachments/noext'  # type: ignore[union-attr]
  assert values['weird'].asset.path == 'assets/attachments/weird'  # type: ignore[union-attr]
  with pytest.raises(ValueError, match='filename'):
    report.add_attachment('x', b'bytes')


# ---- render, outline, preprocess, provenance --------------------------------------------------


def test_render_outline_preprocess_and_inputs(tmp_path: Path) -> None:
  report = (
    Report('R')
    .add_text('intro', 'x')
    .add_number('n', 1)
    .set_render(layout='default@1', formats=['md', 'html'])
    .set_render(pdf_engine='latex')
    .set_outline(['intro', {'title': 'S', 'md_file': 's.md', 'children': ['n']}])
    .add_preprocess('core.histogram', inputs={'table': 'n'}, params={'bins': 10}, version=1, id='h')
    .add_input('objects.parquet', sha256='a' * 64, uri='file:objects.parquet')
  )
  manifest = report.manifest()
  assert manifest.render.layout == 'default@1'
  assert manifest.render.formats == ['md', 'html']
  assert manifest.render.pdf_engine == 'latex'
  assert manifest.outline is not None
  assert manifest.outline[1].children[0].key == 'n'
  assert manifest.preprocess[0].params == {'bins': 10}
  assert manifest.provenance.inputs[0].name == 'objects.parquet'


def test_dangling_outline_is_caught_when_building() -> None:
  report = Report('R').add_number('n', 1).set_outline(['n', 'missing'])
  with pytest.raises(SpecError) as info:
    report.build()
  assert codes(info) == ['E103']


def test_nothing_depends_on_the_clock(tmp_path: Path) -> None:
  manifest = json.loads(
    (Report('R').add_number('n', 1).write(tmp_path / 'r') / 'scireport.json').read_text(
      encoding='utf-8'
    )
  )
  assert 'date' not in manifest['meta']
  assert 'created' not in manifest['provenance']


def test_build_returns_an_in_memory_bundle(png_bytes: bytes) -> None:
  bundle = Report('R').add_image('i', png_bytes, suffix='png').add_text('t', 'x').build()
  assert bundle.verify() == []
  assert bundle.read_asset('assets/images/i.png') == png_bytes
  assert bundle.read_text('t') == 'x'


def test_asset_paths_that_are_too_long_are_refused() -> None:
  key = 'k' * 190
  with pytest.raises(SpecError) as info:
    Report('R').add_text(key, 'x', as_asset=True)
  assert codes(info) == ['E404']


def test_inline_tables_turn_nan_into_missing() -> None:
  report = Report('R').add_table('t', {'a': [float('nan'), 1.5]}, inline=True)
  assert report.manifest().values['t'].rows == [[None], [1.5]]  # type: ignore[union-attr]
