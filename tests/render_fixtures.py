"""Builders of small, fully deterministic bundles for the render tests."""

from __future__ import annotations

from typing import Any

from helpers import PNG_BYTES

from scireport import Bundle, Report

PDF_BYTES = (
  b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
  b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
  b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 10 10]>>endobj\n'
  b'trailer<</Root 1 0 R>>\n%%EOF\n'
)
SVG_BYTES = (
  b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
  b'<rect width="10" height="10" fill="#1f4e79"/></svg>\n'
)
CSV_ALL_ROWS = b'id,z\n' + b''.join(f'{i},{i / 10:.1f}\n'.encode() for i in range(1, 41))


def real_pictures() -> tuple[Any, bytes]:
  """Return a small matplotlib figure and a valid PNG, for tests that compile or draw them."""
  import io

  from matplotlib.figure import Figure

  figure = Figure(figsize=(2, 1.5))
  figure.add_subplot().plot([0, 1, 2], [0, 1, 4])
  buffer = io.BytesIO()
  Figure(figsize=(0.4, 0.4)).savefig(buffer, format='png', dpi=50)
  return figure, buffer.getvalue()


def kitchen_sink(*, split: bool = True, outline: bool = True, real: bool = False) -> Bundle:
  """Build a bundle that uses every kind and every presentation feature once.

  Parameters
  ----------
  split : bool, default=True
      Give the second chapter its own Markdown file.
  real : bool, default=False
      Draw the figure and the image with matplotlib so that a TeX engine can read them; the
      default uses fixed placeholder bytes, which keeps golden files independent of matplotlib.
  outline : bool, default=True
      Include an outline that lists every value (otherwise the generic template builds one).

  Returns
  -------
  Bundle
      An in-memory bundle.
  """
  report = Report(
    'Cross-match & QA: 50% done_',
    subtitle='Every component, once',
    authors=['N. Cardoso', {'name': 'A. Reviewer', 'affiliation': 'Example Institute'}],
    date='2026-10-09',
    version='1.2.3',
    pipeline='kitchen-sink',
    footer='scireport test bundle',
    abstract='This report uses **every** component with $\\alpha = 0.05$.',
    keywords=['test', 'render'],
  )
  report.add_text(
    'intro.prose',
    'The sample holds **3,061** pairs.\n\n- first item\n- second item with `code_x`\n\n'
    '| a | b |\n|:--|--:|\n| 1 | $x^2$ |\n',
    format='markdown',
  )
  report.add_text('intro.plain', 'Plain text with _ % & # $ ~ ^ { }.\n\nSecond paragraph.')
  report.add_text(
    'intro.latex',
    'The mass is \\textbf{$M_\\odot$}.',
    format='latex',
    alt={'html': 'The mass is <b>M</b>.', 'md': 'The mass is **M**.'},
  )
  report.add_number('facts.n_pairs', 3061, format='int', unit='pairs')
  report.add_number('facts.complete', 0.9875, format='pct')
  report.add_number('facts.sep', 1.234, uncertainty=0.04, unit='arcsec', format=',.2f')
  report.add_number('facts.range', 1.5, interval=(1.1, 1.9), unit='mag')
  report.add_number('facts.flux', 123456.0, format='sci', unit='erg s^-1 cm^-2')
  report.add_number('facts.missing', None, missing='n/a')
  report.add_bool('facts.flag', True)
  report.add_date('facts.when', '2026-10-09')
  report.add_list('facts.list', ['alpha', 2, False, ['nested', 'list']])
  report.add_mapping('facts.mapping', {'host': 'node-1', 'seed': 42, 'ok': True})
  report.add_table(
    'tables.inline',
    {'name': ['a_b', 'c&d', '50%'], 'value': [1, 2.5, None], 'path': ['/data/x_y/z.fits'] * 3},
    columns=[
      {'name': 'name', 'label': 'Name'},
      {'name': 'value', 'label': 'Value', 'unit': 'deg^2', 'format': ',.1f'},
      {'name': 'path', 'label': 'Path', 'align': 'path'},
    ],
    caption='An inline table',
    inline=True,
    row_status=['pass', 'warn', 'fail'],
    emphasis=[{'row': 0, 'column': 'name', 'style': 'strong'}],
  )
  report.add_table(
    'tables.parquet',
    {'id': [1, 2, 3], 'z': [0.1, 0.2, 0.3], 'flux': [1.5e-5, 2.25e3, 0.0]},
    columns=[
      {'name': 'id', 'label': 'ID', 'width': 0.2},
      {'name': 'z', 'label': 'Redshift', 'format': '.3f', 'width': 0.3},
      {'name': 'flux', 'label': 'Flux', 'format': 'sci', 'unit': 'Jy', 'width': 0.5},
    ],
    caption='A Parquet table',
  )
  report.add_table(
    'tables.csv', {'k': ['x', 'y'], 'n': [10, 20]}, format='csv', caption='A CSV table'
  )
  report.add_attachment(
    'files.all_rows', CSV_ALL_ROWS, filename='all_rows.csv', media_type='text/csv',
    description='All 40 rows behind the cut table',
  )
  report.add_table(
    'tables.cut',
    {'id': list(range(1, 41)), 'z': [i / 10 for i in range(1, 41)]},
    caption='A table cut to five rows',
    max_rows=5,
    overflow_attachment='files.all_rows',
  )
  figure, png = real_pictures() if real else (None, PNG_BYTES)
  report.add_figure(
    'figures.curve',
    figure if real else {'png': PNG_BYTES, 'pdf': PDF_BYTES, 'svg': SVG_BYTES},
    alt='A rising curve',
    caption='y = x squared',
    width=0.6,
    **({'formats': ('png', 'pdf', 'svg')} if real else {}),
  )
  report.add_image('figures.logo', png, suffix='png', alt='The project logo', caption='Logo')
  report.add_math('math.mass', 'E = mc^2', numbered=True, caption='Mass-energy equivalence')
  report.add_code('code.query', 'SELECT COUNT(*)\nFROM pairs\nWHERE sep < 1.0;', language='sql')
  report.add_metrics(
    'dash.metrics',
    [
      {'label': 'Pairs', 'value': 3061, 'detail': 'after cuts'},
      {'label': 'Status', 'value': 'ok'},
    ],
  )
  report.add_status('dash.status', 'success', 'COMPLETED SUCCESSFULLY', 'All checks passed.')
  report.add_alert('dash.alert', 'warning', 'Redshift 999 is a sentinel.')
  report.add_flow(
    'dash.flow',
    [
      {'label': 'INGEST', 'detail': ['12 rows'], 'state': 'done'},
      {'label': 'MATCH', 'state': 'reused'},
      {'label': 'PUBLISH', 'state': 'skipped'},
    ],
  )
  if outline:
    nodes: list[Any] = [
      'dash.status',
      {
        'title': 'Facts',
        'children': [
          'intro.prose',
          'intro.plain',
          'intro.latex',
          'facts.n_pairs',
          'facts.complete',
          'facts.sep',
          'facts.range',
          'facts.flux',
          'facts.missing',
          'facts.flag',
          'facts.when',
          {'title': 'Lists', 'children': ['facts.list', 'facts.mapping']},
        ],
      },
      {
        'title': 'Data',
        **({'md_file': 'data.md'} if split else {}),
        'children': [
          'tables.inline',
          'tables.parquet',
          'tables.csv',
          'tables.cut',
          'files.all_rows',
          'figures.curve',
          'figures.logo',
          'math.mass',
          'code.query',
        ],
      },
      {
        'title': 'Dashboard',
        'page_break': True,
        'children': ['dash.metrics', 'dash.alert', 'dash.flow'],
      },
    ]
    report.set_outline(nodes)
  report.set_render(template='generic@1', layout='minimal@1')
  return report.build()
