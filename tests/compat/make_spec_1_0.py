"""Generate the frozen spec-1.0 compat corpus (``tests/compat/spec-1.0/``).

Run once, at the moment the corpus is created, with ``uv run python tests/compat/make_spec_1_0.py``.
Never run it again for spec 1.0: the fixtures are frozen (ADR-0008) and ``FROZEN.sha256`` makes CI
fail if one changes. A new spec version gets its own ``spec-<version>/`` folder and its own script.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from matplotlib.figure import Figure

from scireport import Report, open_bundle, write_bundle
from scireport.bundle.summary import inspect_bundle
from scireport.spec.manifest import manifest_to_json

ROOT = Path(__file__).resolve().parent / 'spec-1.0'

TEXT_ONLY_YAML = """\
# A hand-authored, text-only report: bare JSON shorthand throughout, no assets.
scireport: "1.0"
meta:
  title: Text-only report
  subtitle: Written by hand in YAML
  authors:
    - N. Cardoso
    - {name: A. Reviewer, affiliation: Example Institute}
  date: 2026-10-09
  language: en
render:
  template: generic@1
  layout: default@1
  formats: [md, html]
outline:
  - summary
  - title: Results
    md_file: results.md
    children:
      - stats.n_pairs
      - stats.completeness
      - checks
  - title: Notes
    children: [notes.list, equation, query, status, alert, flow]
values:
  summary: This report has no assets, so it is a single manifest file.
  stats.n_pairs: 3061
  stats.completeness: 0.9875
  stats.complete: true
  stats.missing: null
  checks:
    answer: yes
    time: 12:30
    octal-looking: 007
    nested: {a: 1, b: [1, 2, {c: three}]}
  notes.list: [alpha, 2, false, [nested, list]]
  when: {kind: date, value: '20261009'}
  equation: {kind: math, latex: 'E = mc^2', numbered: true, caption: Mass-energy equivalence}
  query: {kind: code, source: "SELECT COUNT(*) FROM pairs;", language: sql}
  status:
    kind: status
    level: success
    headline: COMPLETED SUCCESSFULLY
    detail: All checks passed.
  alert: {kind: alert, level: warning, text: Redshift 999 is a sentinel.}
  flow:
    kind: flow
    stages:
      - {label: INGEST, detail: ["12,483,921 objects"]}
      - {label: CROSS-MATCH, state: reused}
      - {label: PUBLISH, state: skipped}
  kpi:
    kind: metrics
    items:
      - {label: Pairs, value: 3061, detail: after cuts}
      - {label: Status, value: ok}
"""


def minimal() -> Report:
  """Return the smallest useful report: a title and one text value."""
  return Report('Minimal report').add_text('note', 'A minimal report.')


def full_kinds() -> Report:
  """Return a report that uses every one of the 16 v1.0 kinds, with assets."""
  report = Report(
    'Full-kinds report',
    subtitle='Every v1.0 kind',
    authors=['N. Cardoso'],
    date='2026-10-09',
    version='1.0.0',
    pipeline='compat corpus',
    footer='scireport compat corpus, spec 1.0',
    abstract='A report that exercises **every** kind.',
    keywords=['compat', 'spec-1.0'],
    generator=('scireport-compat', '1.0'),
  )
  report.set_render(
    template='generic@1',
    layout='default@1',
    formats=['md', 'html', 'tex', 'pdf'],
    pdf_engine='weasyprint',
    latex_engine='lualatex',
    markup_engine='mistletoe',
    math_renderer='mathtext',
    options={'paper': 'a4', 'toc': True, 'accent': None},
  )
  report.add_input('objects.parquet', sha256='0' * 64, uri='file:data/objects.parquet')
  report.add_text('kinds.text', 'Short **markdown** text.', format='markdown')
  report.add_text('kinds.text-long', 'A long paragraph. ' * 400, format='markdown')
  report.add_text(
    'kinds.latex',
    r'\textbf{Raw} LaTeX with $\alpha$',
    format='latex',
    alt={'html': '<b>Raw</b> LaTeX with α', 'md': '**Raw** LaTeX with $\\alpha$'},
  )
  report.add_number('kinds.number', 1.2345, unit='arcsec', format='.2f', uncertainty=0.01)
  report.add_number('kinds.number-interval', 3061, format='int', interval=(3000, 3100))
  report.add_number('kinds.number-missing', None, missing='n/a')
  report.add_bool('kinds.bool', True)
  report.add_date('kinds.date', '2026-10-09')
  report.add_list('kinds.list', ['alpha', 2, False, ['nested']], ordered=True)
  report.add_mapping('kinds.mapping', {'Release': '1.0.0', 'Rows': 3061, 'Public': True})
  data = {'id': [1, 2, 3], 'z': [0.1, None, 0.3], 'label': ['a', 'b', 'c']}
  report.add_table(
    'kinds.table-parquet',
    data,
    columns=[
      {'name': 'id', 'label': 'ID', 'align': 'right'},
      {'name': 'z', 'label': 'Redshift', 'format': '.3f', 'align': 'right', 'unit': ''},
      {'name': 'label', 'description': 'A label', 'width': 0.5},
    ],
    caption='A Parquet table',
  )
  report.add_table('kinds.table-csv', {'a': [1, 2], 'b': ['x', 'y']}, format='csv')
  report.add_table(
    'kinds.table-inline',
    {'check': ['nesting', 'sizes'], 'result': ['ok', 'FAILED']},
    inline=True,
    row_status=['pass', 'fail'],
    emphasis=[{'row': 1, 'column': 'result', 'style': 'fail'}],
  )
  report.add_table(
    'kinds.table-cut',
    {'n': list(range(50))},
    max_rows=5,
    overflow_attachment='kinds.attachment',
    caption='First rows only',
  )
  report.add_attachment(
    'kinds.attachment',
    ('n\n' + ''.join(f'{i}\n' for i in range(50))).encode(),
    filename='all_rows.csv',
    description='The 50 rows behind the cut table',
  )
  fig = Figure(figsize=(3.2, 2.2))
  ax = fig.subplots()
  ax.plot([0, 1, 2, 3], [0, 1, 4, 9])
  report.add_figure(
    'kinds.figure',
    fig,
    alt='A rising curve',
    caption='y = x squared',
    width=0.6,
    data={'x': [0, 1, 2, 3], 'y': [0, 1, 4, 9]},
    formats=('png', 'pdf', 'svg'),
  )
  fig2 = Figure(figsize=(2, 2))
  fig2.subplots().bar([1, 2], [3, 4])
  report.add_image('kinds.image', _png_of(fig2), suffix='png', alt='A bar chart', width=0.4)
  report.add_math('kinds.math', r'\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}', numbered=True)
  report.add_code(
    'kinds.code', 'def f(x):\n    return x * 2\n', language='python', caption='Doubling'
  )
  report.add_metrics(
    'kinds.metrics', [('Pairs', 3061), {'label': 'Rate', 'value': 0.5, 'detail': 'of all'}]
  )
  report.add_status(
    'kinds.status', 'partial', 'PARTIALLY COMPLETE', detail='One stage was skipped.'
  )
  report.add_alert('kinds.alert', 'error', 'A check failed.')
  report.add_flow(
    'kinds.flow',
    [{'label': 'INGEST', 'detail': ['12 rows']}, {'label': 'MATCH', 'state': 'reused'}, 'PUBLISH'],
  )
  report.set_outline(
    [
      'kinds.text',
      {
        'title': 'Values',
        'md_file': 'values.md',
        'children': ['kinds.number', 'kinds.table-parquet', 'kinds.figure'],
      },
    ]
  )
  return report


def _png_of(fig: Figure) -> bytes:
  """Render a matplotlib figure to PNG bytes with the builder's metadata rules."""
  from scireport.report import _render_figure

  return _render_figure(fig, 'png', 100)


def sha256_of(path: Path) -> str:
  """Return the SHA-256 of a file."""
  return hashlib.sha256(path.read_bytes()).hexdigest()


def write_expected(case: Path, source: Path) -> None:
  """Write ``expected/manifest.json`` and ``expected/summary.json`` for a case."""
  expected = case / 'expected'
  expected.mkdir(parents=True, exist_ok=True)
  with open_bundle(source) as bundle:
    (expected / 'manifest.json').write_bytes(manifest_to_json(bundle.manifest).encode('utf-8'))
    summary = inspect_bundle(bundle)
    for volatile in ('source', 'form'):
      summary.pop(volatile)
    text = json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + '\n'
    (expected / 'summary.json').write_bytes(text.encode('utf-8'))


def main() -> None:
  """Build every case and the freeze list."""
  if ROOT.exists():
    raise SystemExit(f'{ROOT} exists: the spec-1.0 corpus is frozen and is never regenerated.')
  ROOT.mkdir(parents=True)
  for name, report in (('minimal', minimal()), ('full-kinds', full_kinds())):
    case = ROOT / name
    case.mkdir()
    report.write(case / 'bundle.scireport.zip')
    report.write(case / 'bundle.scireport')
    write_expected(case, case / 'bundle.scireport')
  case = ROOT / 'text-only'
  (case / 'source').mkdir(parents=True)
  (case / 'source' / 'scireport.yaml').write_text(TEXT_ONLY_YAML, encoding='utf-8', newline='\n')
  with open_bundle(case / 'source') as bundle:
    write_bundle(bundle, case / 'single.json')
    write_bundle(bundle, case / 'bundle.scireport.zip')
  write_expected(case, case / 'single.json')
  lines = sorted(
    f'{sha256_of(path)}  {path.relative_to(ROOT).as_posix()}'
    for path in ROOT.rglob('*')
    if path.is_file()
  )
  (ROOT / 'FROZEN.sha256').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
  shutil.copy(Path(__file__).with_name('SPEC-1.0-README.md'), ROOT / 'README.md')


if __name__ == '__main__':
  main()
