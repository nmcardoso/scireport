from collections.abc import Sequence
from pathlib import Path

import pytest
from helpers import PNG_BYTES
from render_fixtures import PDF_BYTES, SVG_BYTES, kitchen_sink
from render_helpers import Format, render_body, render_issues

from scireport import Bundle, Report
from scireport.errors import Issue

FORMATS: list[Format] = ['md', 'html', 'tex']


def small() -> Report:
  return Report('T')


def codes(issues: Sequence[Issue]) -> list[str]:
  return [i.code for i in issues]


@pytest.mark.parametrize('fmt', FORMATS)
@pytest.mark.parametrize(
  'call',
  [
    'c.value(data.intro.prose)',
    'c.value(data.intro.plain)',
    'c.value(data.intro.latex)',
    "c.value(data.facts.n_pairs, label='N')",
    "c.value(data.facts.flag, label='Flag')",
    'c.value(data.facts.when)',
    'c.value(data.facts.list)',
    'c.value(data.facts.mapping)',
    'c.value(data.tables.inline)',
    'c.value(data.tables.parquet)',
    'c.value(data.tables.csv)',
    'c.value(data.tables.cut)',
    'c.value(data.files.all_rows)',
    'c.value(data.figures.curve)',
    'c.value(data.figures.logo)',
    'c.value(data.math.mass)',
    'c.value(data.code.query)',
    'c.value(data.dash.metrics)',
    'c.value(data.dash.status)',
    'c.value(data.dash.alert)',
    'c.value(data.dash.flow)',
    "c.table('tables.csv')",
    'c.number(data.facts.sep)',
    "c.math('x^2')",
    'c.spacer(4)',
    'c.page_break()',
  ],
)
def test_every_component_renders_in_every_format(call: str, fmt: Format, tmp_path: Path) -> None:
  bundle = kitchen_sink(outline=False)
  text = render_body(bundle, '{{ ' + call + ' }}', fmt, tmp_path)
  assert text.strip()


@pytest.mark.parametrize('fmt', FORMATS)
def test_call_blocks(fmt: Format, tmp_path: Path) -> None:
  body = (
    "{% call c.details('More & more') %}{{ c.math('x') }}{% endcall %}"
    "{% call c.note() %}{{ c.math('y') }}{% endcall %}"
  )
  text = render_body(small().build(), body, fmt, tmp_path)
  assert {'md': 'More &amp; more', 'html': 'More &amp; more', 'tex': r'More \& more'}[fmt] in text


def test_chapters_and_headings_in_markdown(tmp_path: Path) -> None:
  body = "{{ c.chapter('One') }}{{ c.heading('A') }}{{ c.heading('B', 2) }}{{ c.heading('C', 3) }}"
  text = render_body(small().build(), body, 'md', tmp_path)
  assert '## One' in text
  assert '### A' in text and '#### B' in text and '##### C' in text


def test_chapters_and_headings_in_html_and_tex(tmp_path: Path) -> None:
  body = (
    "{{ c.chapter('One', page_break=True) }}{{ c.heading('A') }}"
    "{{ c.heading('X', in_contents=False) }}"
  )
  html = render_body(small().build(), body, 'html', tmp_path)
  assert '<section class="chapter page-break" id="a1">' in html
  assert '<h2 id="a2"><span class="number">1.1</span> A</h2>' in html
  assert '<h2 id="a3">X</h2>' in html
  tex = render_body(small().build(), body, 'tex', tmp_path)
  assert tex.count(r'\clearpage') == 1
  assert r'\section{One}\label{a1}' in tex
  assert r'\subsection{A}\label{a2}' in tex
  assert r'\subsection*{X}\label{a3}' in tex


def test_titles_are_escaped_per_format(tmp_path: Path) -> None:
  body = "{{ c.chapter('R&D_50%') }}"
  bundle = small().build()
  assert 'R&amp;D_50%' in render_body(bundle, body, 'html', tmp_path)
  assert r'R\&D\_50\%' in render_body(bundle, body, 'tex', tmp_path)
  assert r'R\&D_50%' in render_body(bundle, body, 'md', tmp_path)


def test_invalid_arguments_are_reported_together(tmp_path: Path) -> None:
  body = "{{ c.chapter('A', md_file='bad name.txt') }}{{ c.heading('B', 7) }}"
  issues = render_issues(small().build(), body, 'md', tmp_path)
  assert codes(issues) == ['E801', 'E801']
  assert issues[0].location == 'report.j2:1'


def test_the_wrong_kind_is_reported_with_the_expected_one(tmp_path: Path) -> None:
  issues = render_issues(
    kitchen_sink(outline=False),
    '{{ c.table(data.facts.n_pairs) }}{{ c.figure(data.tables.csv) }}',
    'md',
    tmp_path,
  )
  errors = [i for i in issues if i.severity == 'error']
  assert codes(errors) == ['E208', 'E208']
  assert errors[0].expected == 'table' and errors[0].found == 'number'
  assert errors[0].key == 'facts.n_pairs'


def test_a_namespace_is_not_a_value(tmp_path: Path) -> None:
  issues = render_issues(kitchen_sink(outline=False), '{{ c.table(data.tables) }}', 'md', tmp_path)
  assert codes([i for i in issues if i.severity == 'error']) == ['E208']
  assert 'several values' in issues[0].message


def test_missing_keys_in_a_template_are_aggregated_with_lines(tmp_path: Path) -> None:
  body = (
    "{{ c.table(data.tables.inlin) }}\n{{ c.number(data.facts.n_pair) }}\n{{ c.value(v('zzz')) }}"
  )
  issues = render_issues(kitchen_sink(outline=False), body, 'md', tmp_path)
  errors = [i for i in issues if i.code == 'E106']
  assert [i.key for i in errors] == ['tables.inlin', 'facts.n_pair', 'zzz']
  assert errors[0].hint == "Did you mean 'tables.inline'?"
  assert [i.location for i in errors] == ['report.j2:1', 'report.j2:2', 'report.j2:3']


def test_a_table_cut_with_an_attachment(tmp_path: Path) -> None:
  bundle = kitchen_sink(outline=False)
  md = render_body(bundle, '{{ c.table(data.tables.cut) }}', 'md', tmp_path)
  assert (
    '*Showing the first 5 of 40 rows.* All rows: [all_rows.csv](attachments/all_rows.csv).' in md
  )
  assert '| 5 | 0.5 |' in md and '| 6 |' not in md
  html = render_body(bundle, '{{ c.table(data.tables.cut, max_rows=3) }}', 'html', tmp_path)
  assert 'Showing the first 3 of 40 rows.' in html
  assert 'href="data:text/csv;base64,' in html and 'download="all_rows.csv"' in html


def test_an_empty_table_says_so(tmp_path: Path) -> None:
  report = small().add_table('t', {'a': []}, inline=True, columns=['a'])
  cases: list[tuple[Format, str]] = [
    ('md', '*Nothing recorded.*'),
    ('html', 'Nothing recorded.'),
    ('tex', 'Nothing recorded.'),
  ]
  for fmt, expected in cases:
    assert expected in render_body(report.build(), '{{ c.table(data.t) }}', fmt, tmp_path)


def test_long_tables_use_longtable_in_latex(tmp_path: Path) -> None:
  report = small().add_table('t', {'n': list(range(30))}, caption='Long')
  tex = render_body(report.build(), '{{ c.table(data.t) }}', 'tex', tmp_path)
  assert r'\begin{longtable}' in tex and r'\endhead' in tex
  short = small().add_table('t', {'n': [1]})
  assert r'\begin{tabular}' in render_body(short.build(), '{{ c.table(data.t) }}', 'tex', tmp_path)


def test_row_verdicts_and_emphasis(tmp_path: Path) -> None:
  bundle = kitchen_sink(outline=False)
  html = render_body(bundle, '{{ c.table(data.tables.inline) }}', 'html', tmp_path)
  assert '<tr class="row--pass">' in html and '<tr class="row--fail">' in html
  assert 'cell--strong' in html
  tex = render_body(bundle, '{{ c.table(data.tables.inline) }}', 'tex', tmp_path)
  assert r'\rowcolor{warn!12}' in tex and r'\textbf{a\_b}' in tex
  md = render_body(bundle, '{{ c.table(data.tables.inline) }}', 'md', tmp_path)
  assert '| Name | Value (deg²) | Path | Status |' in md and '| pass |' in md


def test_a_status_column_drives_the_verdicts(tmp_path: Path) -> None:
  report = small().add_table(
    't', {'n': [1, 2], 'v': ['pass', 'fail']}, row_status_column='v', columns=['n', 'v']
  )
  html = render_body(report.build(), '{{ c.table(data.t) }}', 'html', tmp_path)
  assert 'row--pass' in html and 'row--fail' in html and '<th' in html and html.count('<th ') == 1


def test_a_declared_column_missing_from_the_data_is_reported(tmp_path: Path) -> None:
  report = small().add_table('t', {'a': [1]}, columns=['a', 'b'])
  issues = render_issues(report.build(), '{{ c.table(data.t) }}', 'md', tmp_path)
  assert 'E305' in codes(issues)


@pytest.mark.parametrize(
  ('fmt', 'expected'),
  [
    ('md', '![A rising curve](figures/figures.curve.png)'),
    ('tex', r'\includegraphics[width=0.6\linewidth]{figures/figures.curve.pdf}'),
  ],
)
def test_figures_pick_the_rendition_for_the_format(
  fmt: Format, expected: str, tmp_path: Path
) -> None:
  text = render_body(
    kitchen_sink(outline=False), '{{ c.figure(data.figures.curve) }}', fmt, tmp_path
  )
  assert expected in text


def test_html_embeds_the_png(tmp_path: Path) -> None:
  html = render_body(
    kitchen_sink(outline=False), '{{ c.figure(data.figures.curve) }}', 'html', tmp_path
  )
  assert 'src="data:image/png;base64,' in html and 'alt="A rising curve"' in html
  assert 'Figure 1.' in html


def test_figures_without_a_usable_rendition_are_errors(tmp_path: Path) -> None:
  pdf_only = small().add_figure('f', {'pdf': PDF_BYTES}, alt='x').build()
  svg_only = small().add_figure('f', {'svg': SVG_BYTES}, alt='x').build()
  cases: list[tuple[Bundle, Format]] = [(pdf_only, 'md'), (pdf_only, 'html'), (svg_only, 'tex')]
  for bundle, fmt in cases:
    issues = render_issues(bundle, '{{ c.figure(data.f) }}', fmt, tmp_path)
    assert 'E210' in codes(issues)


def test_images_and_decorative_images(tmp_path: Path) -> None:
  report = small().add_image('i', PNG_BYTES, suffix='png')
  html = render_body(report.build(), '{{ c.image(data.i) }}', 'html', tmp_path)
  assert 'role="presentation"' in html and 'alt=""' in html
  md = render_body(report.build(), '{{ c.image(data.i) }}', 'md', tmp_path)
  assert '![](images/i.png)' in md
  pdf = small().add_image('i', PDF_BYTES, suffix='pdf', alt='x')
  assert 'E210' in codes(render_issues(pdf.build(), '{{ c.image(data.i) }}', 'html', tmp_path))
  assert r'\includegraphics' in render_body(pdf.build(), '{{ c.image(data.i) }}', 'tex', tmp_path)


def test_equations(tmp_path: Path) -> None:
  bundle = kitchen_sink(outline=False)
  assert r'E = mc^2 \tag{1}' in render_body(
    bundle, '{{ c.equation(data.math.mass) }}', 'md', tmp_path
  )
  tex = render_body(bundle, '{{ c.equation(data.math.mass) }}', 'tex', tmp_path)
  assert r'\begin{equation}' in tex and 'E = mc^2' in tex
  html = render_body(bundle, '{{ c.equation(data.math.mass) }}', 'html', tmp_path)
  assert '<img class="math-display"' in html and '(1)' in html


def test_inline_math(tmp_path: Path) -> None:
  assert '$x_1$' in render_body(small().build(), '{{ c.math("x_1") }}', 'md', tmp_path)
  assert '$x_1$' in render_body(small().build(), '{{ c.math("x_1") }}', 'tex', tmp_path)
  assert '<img class="math-inline"' in render_body(
    small().build(), '{{ c.math("x_1") }}', 'html', tmp_path
  )


def test_math_that_cannot_be_drawn_warns_and_shows_the_source(tmp_path: Path) -> None:
  bundle = small().add_math('m', r'\begin{align} x \end{align}').build()
  body = '{{ c.equation(data.m) }}'
  issues = render_issues(bundle, body, 'html', tmp_path)
  assert 'W601' in codes(issues)
  assert '<code>' in render_body(bundle, body, 'html', tmp_path)
  strict = render_issues(bundle, body, 'html', tmp_path, strict=True)
  assert 'W601' in codes(strict)
  assert not [i for i in render_issues(bundle, body, 'tex', tmp_path) if i.code == 'W601']


def test_dashboard_components(tmp_path: Path) -> None:
  bundle = kitchen_sink(outline=False)
  body = (
    '{{ c.metrics(data.dash.metrics) }}{{ c.status(data.dash.status) }}'
    '{{ c.alert(data.dash.alert) }}{{ c.flow(data.dash.flow) }}'
  )
  md = render_body(bundle, body, 'md', tmp_path)
  assert '| Pairs | 3061 | after cuts |' in md
  assert '> **SUCCESS:** COMPLETED SUCCESSFULLY' in md and '> **WARNING:** Redshift 999' in md
  assert '1. **INGEST** (done) — 12 rows' in md and '3. **PUBLISH** (skipped)' in md
  html = render_body(bundle, body, 'html', tmp_path)
  assert 'status--success' in html and 'alert--warning' in html and 'flow-stage--reused' in html
  tex = render_body(bundle, body, 'tex', tmp_path)
  assert r'\textcolor{pass}{SUCCESS}' in tex and r'\textcolor{warn}{WARNING}' in tex
  assert r'\item \textbf{INGEST} \textit{done} --- 12 rows' in tex


def test_lists_and_mappings(tmp_path: Path) -> None:
  bundle = kitchen_sink(outline=False)
  body = '{{ c.bullets(data.facts.list) }}{{ c.metadata(data.facts.mapping) }}'
  md = render_body(bundle, body, 'md', tmp_path)
  assert '- alpha' in md and '- - nested' in md and '- **host:** node-1' in md
  html = render_body(bundle, body, 'html', tmp_path)
  assert '<dt>host</dt>' in html and html.count('<ul') == 2
  ordered = small().add_list('l', ['a', 'b'], ordered=True).build()
  assert '1. a' in render_body(ordered, '{{ c.bullets(data.l) }}', 'md', tmp_path)
  assert r'\begin{enumerate}' in render_body(ordered, '{{ c.bullets(data.l) }}', 'tex', tmp_path)


def test_code_blocks_use_a_fence_the_code_cannot_close(tmp_path: Path) -> None:
  report = small().add_code('c', 'a ``` b\nline', language='md')
  md = render_body(report.build(), '{{ c.code(data.c) }}', 'md', tmp_path)
  assert '\n````md\na ``` b\nline\n````\n' in md
  html = render_body(report.build(), '{{ c.code(data.c) }}', 'html', tmp_path)
  assert '<code class="language-md">a ``` b' in html
  tricky = small().add_code('c', r'\end{verbatim} x')
  assert r'\end {verbatim} x' in render_body(
    tricky.build(), '{{ c.code(data.c) }}', 'tex', tmp_path
  )


def test_plain_text_becomes_escaped_paragraphs(tmp_path: Path) -> None:
  report = small().add_text('t', 'a & b\n\nc_d')
  assert '<p>a &amp; b</p>' in render_body(report.build(), '{{ c.text(data.t) }}', 'html', tmp_path)
  assert 'a \\& b\n\nc_d' in render_body(report.build(), '{{ c.text(data.t) }}', 'md', tmp_path)
  assert 'a \\& b\n\nc\\_d' in render_body(report.build(), '{{ c.text(data.t) }}', 'tex', tmp_path)


def test_raw_latex_needs_a_replacement_outside_latex(tmp_path: Path) -> None:
  bare = small().add_text('t', r'\textbf{x}', format='latex').build()
  assert r'\textbf{x}' in render_body(bare, '{{ c.text(data.t) }}', 'tex', tmp_path)
  for fmt in ('md', 'html'):
    assert 'E209' in codes(render_issues(bare, '{{ c.text(data.t) }}', fmt, tmp_path))
  with_alt = small().add_text('t', r'\textbf{x}', format='latex', alt={'md': '**x**'}).build()
  assert '**x**' in render_body(with_alt, '{{ c.text(data.t) }}', 'md', tmp_path)
  assert 'E209' in codes(render_issues(with_alt, '{{ c.text(data.t) }}', 'html', tmp_path))


def test_numbers_print_with_units_in_every_format(tmp_path: Path) -> None:
  bundle = kitchen_sink(outline=False)
  assert '1.23 ± 0.04 arcsec' in render_body(
    bundle, '{{ c.number(data.facts.sep) }}', 'md', tmp_path
  )
  assert '1.23×10<sup>5</sup>&nbsp;erg' in render_body(
    bundle, '{{ c.number(data.facts.flux) }}', 'html', tmp_path
  )
  assert r'\ensuremath{1.23\times10^{5}}' in render_body(
    bundle, '{{ c.number(data.facts.flux) }}', 'tex', tmp_path
  )


def test_attachments_are_files_next_to_the_document_or_embedded(tmp_path: Path) -> None:
  from render_fixtures import write_template

  from scireport.render import render_bundle

  bundle = kitchen_sink(outline=False)
  template = write_template(tmp_path / 't', body='{{ c.attachment(data.files.all_rows) }}')
  result = render_bundle(bundle, template=template, layout='minimal@1', formats=['md', 'tex'])
  assert (
    'md/attachments/all_rows.csv' in result.files and 'tex/attachments/all_rows.csv' in result.files
  )
  assert result.files['md/attachments/all_rows.csv'].startswith(b'id,z')


def test_large_attachments_are_not_embedded_in_html(
  tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
  from scireport.render import components

  monkeypatch.setattr(components, 'EMBED_LIMIT_BYTES', 10)
  html = render_body(
    kitchen_sink(outline=False), '{{ c.attachment(data.files.all_rows) }}', 'html', tmp_path
  )
  assert 'data:text/csv' not in html and 'all_rows.csv' in html


def test_components_accept_keys(tmp_path: Path) -> None:
  text = render_body(
    kitchen_sink(outline=False),
    "{{ c.table('tables.csv') }}{{ c.number('facts.n_pairs') }}",
    'md',
    tmp_path,
  )
  assert '| k | n |' in text and '3,061 pairs' in text


def test_unknown_kinds_in_lists_are_reported(tmp_path: Path) -> None:
  from scireport.spec.kinds import value_adapter  # noqa: F401

  report = small().add('l', {'kind': 'list', 'items': [{'kind': 'math', 'latex': 'x'}]})
  issues = render_issues(report.build(), '{{ c.bullets(data.l) }}', 'md', tmp_path)
  assert 'E208' in codes(issues)
