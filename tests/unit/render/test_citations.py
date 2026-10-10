"""Citations in prose, the parts that need no pandoc: parsing, tokens, biblatex output."""

from __future__ import annotations

from typing import Any

import pytest

from scireport import Report
from scireport.render import render_bundle
from scireport.render.citations import (
  BIB_FILE,
  Citations,
  CitedWork,
  bibliography_keys,
  parse_group,
)
from scireport.spec.kinds import BibliographyValue

BIB = (
  '@comment{ignored}\n'
  '@string{jt = "Journal of Things"}\n'
  '@article{doe2020,\n  author = {Doe, Jane},\n  title = {A study},\n  journal = jt,\n'
  '  year = {2020}\n}\n'
  '@book(smith_2018:v2,\n  author = {Smith, John},\n  title = {The Book},\n  year = {2018}\n)\n'
)


def citations(target: str = 'tex', style: str | None = None) -> Citations:
  value = BibliographyValue.model_validate(
    {
      'kind': 'bibliography',
      'asset': {'path': 'assets/text/refs.bib', 'sha256': 'a' * 64, 'bytes': 1},
      'style': style,
    }
  )
  return Citations(value, BIB.encode(), None, target)  # type: ignore[arg-type]


def test_bibliography_keys_skip_comments_strings_and_preambles() -> None:
  assert bibliography_keys(BIB) == ['doe2020', 'smith_2018:v2']


@pytest.mark.parametrize(
  ('body', 'expected'),
  [
    ('@doe2020', [CitedWork('doe2020', '', '', False)]),
    ('see @doe2020, p. 3', [CitedWork('doe2020', 'see', ', p. 3', False)]),
    ('-@doe2020', [CitedWork('doe2020', '', '', True)]),
    (
      '@doe2020; @smith_2018:v2, ch. 2',
      [CitedWork('doe2020', '', '', False), CitedWork('smith_2018:v2', '', ', ch. 2', False)],
    ),
    ('@doe2020.', [CitedWork('doe2020', '', '.', False)]),
  ],
)
def test_parse_group_reads_pandoc_syntax(body: str, expected: list[CitedWork]) -> None:
  assert list(parse_group(body) or ()) == expected


@pytest.mark.parametrize('body', ['me@example.org', 'no key here', '@', 'a; b'])
def test_parse_group_rejects_what_is_not_a_citation(body: str) -> None:
  assert parse_group(body) is None


def test_protect_replaces_groups_and_leaves_code_and_non_citations() -> None:
  cite = citations()
  text, issues = cite.protect(
    'A [@doe2020] b `[@doe2020]` c\n\n```\n[@doe2020]\n```\n\nmail [me@example.org] [link](http://x)'
  )
  assert issues == []
  assert text.count('SRCITE') == 1
  assert '`[@doe2020]`' in text and '[me@example.org]' in text and '[link](http://x)' in text
  assert '```\n[@doe2020]\n```' in text


def test_protect_leaves_reference_links_and_footnotes_alone() -> None:
  text, issues = citations().protect('[@doe2020](http://x) and [@doe2020][1] and [@doe2020]: x')
  assert issues == [] and 'SRCITE' not in text


def test_an_unknown_key_is_e212_with_a_suggestion() -> None:
  _, issues = citations().protect('see [@doe2021]')
  assert [i.code for i in issues] == ['E212']
  assert issues[0].key is None and issues[0].found == 'doe2021'
  assert "'doe2020'" in (issues[0].hint or '')


def test_unused_citations_write_nothing() -> None:
  cite = citations()
  assert not cite.used
  assert cite.tex_preamble() == '' and cite.tex_files() == {}
  assert cite.resolve('x', 'y') == ('x', 'y')


def test_tex_commands() -> None:
  cite = citations()
  text, _ = cite.protect(
    '[@doe2020] [-@doe2020] [@doe2020, p. 3] [see @doe2020] [see @doe2020, p. 3; @smith_2018:v2]'
  )
  (out,) = cite.resolve(text)
  assert out == (
    r'\autocite{doe2020} \autocite*{doe2020} \autocite[p. 3]{doe2020} '
    r'\autocite[see][]{doe2020} '
    r'\autocites[see][p. 3]{doe2020}{smith_2018:v2}'
  )


def test_tex_notes_are_escaped() -> None:
  cite = citations()
  text, _ = cite.protect('[100% of @doe2020, p. 3 & 4]')
  (out,) = cite.resolve(text)
  assert out == r'\autocite[100\% of][p. 3 \& 4]{doe2020}'


def test_tex_preamble_and_files_follow_the_style() -> None:
  cite = citations(style='authoryear')
  text, _ = cite.protect('[@doe2020]')
  cite.resolve(text)
  assert cite.tex_preamble() == (
    '% scireport: citations (bibliography kind), printed by biblatex and biber.\n'
    '\\usepackage[backend=biber,style=authoryear]{biblatex}\n'
    f'\\addbibresource{{{BIB_FILE}}}\n'
  )
  assert cite.tex_files() == {BIB_FILE: BIB.encode()}


def test_the_reference_list_in_tex_is_the_biblatex_command() -> None:
  cite = citations()
  assert cite.references() == '\\printbibliography[heading=none]'
  assert cite.used and cite.references(everything=True).startswith('\\nocite{*}')
  assert cite.tex_files()


def test_numbers_follow_the_first_text_that_holds_them() -> None:
  cite = citations()
  first, _ = cite.protect('[@doe2020]')
  second, _ = cite.protect('[@smith_2018:v2]')
  document = f'{second} then {first}'
  assert cite._order([document]) == ['SRCITE2Z', 'SRCITE1Z']


def render_tex(report: Report, **options: Any) -> dict[str, bytes]:
  result = render_bundle(
    report.build(), template='generic@1', layout='minimal@1', formats=['tex'], flat=True, **options
  )
  return result.files


def test_a_tex_project_cites_with_biblatex_and_needs_no_pandoc() -> None:
  report = Report('Cites')
  report.add_text('intro', 'Agrees with [@doe2020, p. 3] and later work.', format='markdown')
  report.add_bibliography('refs', BIB.encode(), style='numeric')
  report.set_outline(['intro', 'refs'])
  files = render_tex(report)
  tex = files['report.tex'].decode()
  assert files[BIB_FILE] == BIB.encode()
  assert '\\usepackage[backend=biber,style=numeric]{biblatex}' in tex
  assert tex.index('{biblatex}') < tex.index('\\begin{document}')
  assert 'Agrees with \\autocite[p. 3]{doe2020} and later work.' in tex
  assert '\\printbibliography[heading=none]' in tex


def test_a_bundle_without_citations_is_untouched() -> None:
  report = Report('Plain').add_text('intro', 'No citation here.', format='markdown')
  report.add_bibliography('refs', BIB.encode())
  report.set_outline(['intro'])
  files = render_tex(report)
  assert BIB_FILE not in files
  assert 'biblatex' not in files['report.tex'].decode()


def test_text_with_at_signs_is_unchanged_when_the_bundle_has_no_bibliography() -> None:
  report = Report('Plain').add_text('intro', 'Look: [@doe2020].', format='markdown')
  report.set_outline(['intro'])
  assert '[@doe2020]' in render_tex(report)['report.tex'].decode()


def test_an_unknown_citation_key_stops_the_render_with_e212() -> None:
  from scireport import RenderError

  report = Report('T').add_text('intro', 'See [@nope].', format='markdown')
  report.add_bibliography('refs', BIB.encode()).set_outline(['intro'])
  with pytest.raises(RenderError) as caught:
    render_tex(report)
  assert 'E212' in [i.code for i in caught.value.issues]


def test_references_without_a_bibliography_is_e208(tmp_path: object) -> None:
  from pathlib import Path

  from render_helpers import render_issues

  report = Report('T').add_text('t', 'x')
  issues = render_issues(report.build(), '{{ c.references() }}', 'tex', Path(str(tmp_path)))
  assert [i.code for i in issues if i.severity == 'error'] == ['E208']
