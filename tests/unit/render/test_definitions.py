from pathlib import Path

import pytest
from render_fixtures import write_layout, write_template

from scireport.errors import TemplateError
from scireport.render.definition import spec_in_range, spec_range_problem
from scireport.render.layout import load_layout_dir
from scireport.render.template import FieldSpec, load_template_dir


@pytest.mark.parametrize(
  ('text', 'version', 'expected'),
  [
    ('1.0', '1.0', True),
    ('1.0', '1.7', True),
    ('1.0', '2.0', False),
    ('1.2', '1.1', False),
    ('>=1.0,<2.0', '1.5', True),
    ('>=1.0,<2.0', '2.0', False),
    ('>1.0', '1.0', False),
    ('<=1.0', '1.0', True),
    ('==1.1', '1.1', True),
    ('==1.1', '1.2', False),
  ],
)
def test_spec_ranges(text: str, version: str, expected: bool) -> None:
  assert spec_in_range(text, version) is expected


@pytest.mark.parametrize('text', ['', 'one', '>=1', '~=1.0', '>=1.0,<'])
def test_malformed_spec_ranges_are_explained(text: str) -> None:
  assert spec_range_problem(text)


@pytest.mark.parametrize(
  ('pattern', 'key', 'expected'),
  [
    ('a.b', 'a.b', True),
    ('a.b', 'a.c', False),
    ('qa.*.summary', 'qa.x.summary', True),
    ('qa.*.summary', 'qa.x.y.summary', False),
    ('qa.*', 'qa.x', True),
    ('qa.*', 'qa', False),
    ('qa.**', 'qa.x.y.z', True),
    ('qa.**', 'qa', False),
    ('qa.**.end', 'qa.a.b.end', True),
    ('qa.**.end', 'qa.end', False),
  ],
)
def test_field_patterns(pattern: str, key: str, expected: bool) -> None:
  assert FieldSpec(key=pattern, kind='table').matches(key) is expected


def test_a_template_directory_loads(tmp_path: Path) -> None:
  root = write_template(
    tmp_path / 't', extra='fields:\n  - {key: a.b, kind: [table, figure], required: false}'
  )
  template = load_template_dir(root)
  assert template.ref == 'mine@1'
  assert template.template_files() == ['report.j2']
  assert template.definition.fields[0].kinds == ['table', 'figure']
  assert len(template.sha256) == 64


def test_template_overrides_are_detected(tmp_path: Path) -> None:
  root = write_template(tmp_path / 't')
  (root / 'report.tex.j2').write_text('x', encoding='utf-8')
  template = load_template_dir(root)
  assert template.entry_for('tex') == 'report.tex.j2'
  assert template.entry_for('md') == 'report.j2'
  assert template.is_neutral('html')
  assert not template.is_neutral('tex')
  assert template.template_files() == ['report.j2', 'report.tex.j2']


def test_an_invalid_template_reports_every_problem(tmp_path: Path) -> None:
  root = write_template(
    tmp_path / 't',
    version=0,
    extra=(
      'fields:\n'
      '  - {key: "Bad Key", kind: table}\n'
      '  - {key: a, kind: nonsense}\n'
      '  - {key: b, kind: number, columns: [{name: x}]}\n'
    ),
  )
  with pytest.raises(TemplateError) as caught:
    load_template_dir(root)
  assert caught.value.code == 'E702'
  assert len(caught.value.issues) >= 4
  assert {issue.code for issue in caught.value.issues} == {'E702'}
  assert all(issue.location == 't/template.yaml' for issue in caught.value.issues)


@pytest.mark.parametrize(
  ('write', 'code'),
  [
    (lambda p: None, 'E703'),
    (lambda p: p.joinpath('template.yaml').write_text('- a list', encoding='utf-8'), 'E702'),
    (lambda p: p.joinpath('template.yaml').write_text('a: [unclosed', encoding='utf-8'), 'E702'),
  ],
)
def test_unreadable_template_files(tmp_path: Path, write: object, code: str) -> None:
  root = tmp_path / 't'
  root.mkdir()
  write(root)  # type: ignore[operator]
  with pytest.raises(TemplateError) as caught:
    load_template_dir(root)
  assert caught.value.code == code


def test_a_missing_entry_file_is_reported(tmp_path: Path) -> None:
  root = write_template(tmp_path / 't')
  (root / 'report.j2').unlink()
  with pytest.raises(TemplateError, match=r'report\.j2'):
    load_template_dir(root)


def test_the_entry_file_cannot_leave_the_directory(tmp_path: Path) -> None:
  root = write_template(tmp_path / 't', extra='entry: ../outside.j2')
  (tmp_path / 'outside.j2').write_text('x', encoding='utf-8')
  with pytest.raises(TemplateError, match='leaves the directory'):
    load_template_dir(root)


def test_a_layout_directory_loads(tmp_path: Path) -> None:
  layout = load_layout_dir(write_layout(tmp_path / 'l', name='mine', version=3))
  assert layout.ref == 'mine@3'
  assert set(layout.definition.formats) == {'md', 'html', 'tex'}
  assert layout.files('html').css == ['html/minimal.css']
  assert 'html/components.html.j2' in layout.jinja_files()
  assert layout.read('html/minimal.css').startswith('/* minimal@1')


def test_a_layout_without_a_format_says_which_it_supports(tmp_path: Path) -> None:
  root = write_layout(tmp_path / 'l')
  text = (root / 'layout.yaml').read_text(encoding='utf-8')
  head, _, rest = text.partition('  html:')
  tail = rest.split('  tex:', 1)[1]
  (root / 'layout.yaml').write_text(head + '  tex:' + tail, encoding='utf-8')
  layout = load_layout_dir(root)
  with pytest.raises(TemplateError) as caught:
    layout.files('html')
  assert caught.value.code == 'E706'
  assert 'md, tex' in caught.value.message


def test_a_missing_layout_file_is_reported(tmp_path: Path) -> None:
  root = write_layout(tmp_path / 'l')
  (root / 'html' / 'minimal.css').unlink()
  with pytest.raises(TemplateError) as caught:
    load_layout_dir(root)
  assert caught.value.code == 'E703'


@pytest.mark.parametrize(
  ('given', 'expected'),
  [
    (
      {},
      {'toc': True, 'cover': True, 'accent': '#1f4e79', 'paper': 'a4', 'numbered_captions': True},
    ),
    ({'toc': 'false', 'paper': 'letter'}, {'toc': False, 'paper': 'letter'}),
    ({'toc': 'yes'}, {'toc': True}),
    ({'accent': '#AABBCC'}, {'accent': '#AABBCC'}),
    ({'accent': None}, {'accent': '#1f4e79'}),
  ],
)
def test_layout_options_are_merged_and_converted(
  tmp_path: Path, given: dict[str, object], expected: dict[str, object]
) -> None:
  layout = load_layout_dir(write_layout(tmp_path / 'l'))
  resolved = layout.resolve_options(given)
  assert {k: resolved[k] for k in expected} == expected
  assert list(resolved) == ['toc', 'cover', 'accent', 'paper', 'numbered_captions']


def test_bad_layout_options_are_all_reported(tmp_path: Path) -> None:
  layout = load_layout_dir(write_layout(tmp_path / 'l'))
  with pytest.raises(TemplateError) as caught:
    layout.resolve_options(
      {'toc': 'maybe', 'paper': 'tabloid', 'accent': 'red;}', 'acent': 'x', 'color': 'y'}
    )
  messages = [issue.message for issue in caught.value.issues]
  assert len(messages) == 5
  assert any('expects a bool' in m for m in messages)
  assert any('must be one of a4, letter' in m for m in messages)
  assert any('must match' in m for m in messages)
  assert any('no option' in m for m in messages)
  assert caught.value.code == 'E806'
  hints = [issue.hint for issue in caught.value.issues if issue.key == 'acent']
  assert hints == ["Did you mean 'accent'?"]


def test_option_definitions_are_checked(tmp_path: Path) -> None:
  root = write_layout(tmp_path / 'l')
  text = (root / 'layout.yaml').read_text(encoding='utf-8').replace('default: a4', 'default: 3')
  (root / 'layout.yaml').write_text(text, encoding='utf-8')
  with pytest.raises(TemplateError) as caught:
    load_layout_dir(root)
  assert caught.value.code == 'E702'
