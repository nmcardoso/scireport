from __future__ import annotations

import json
from typing import Any

import pytest
from helpers import asset_ref, minimal_manifest

from scireport.errors import Issue, ScireportError, SpecError, SpecVersionError
from scireport.spec.manifest import (
  Manifest,
  check_manifest,
  manifest_to_dict,
  manifest_to_json,
  parse_manifest,
)


def issues_of(raw: dict[str, Any]) -> list[Issue]:
  with pytest.raises(SpecError) as info:
    parse_manifest(raw)
  return info.value.issues


def test_minimal_manifest_parses_with_defaults() -> None:
  manifest = parse_manifest({'scireport': '1.0', 'meta': {'title': 'T'}})
  assert manifest.meta.language == 'en'
  assert manifest.values == {}
  assert manifest.render.formats == []
  assert manifest.outline is None


def test_meta_authors_accept_names_and_records() -> None:
  raw = {
    'scireport': '1.0',
    'meta': {
      'title': 'T',
      'authors': ['A B', {'name': 'C D', 'orcid': '0000-0002-1825-0097', 'affiliation': 'X'}],
      'date': '20261009',
      'keywords': ['a'],
      'language': 'pt-BR',
    },
  }
  meta = parse_manifest(raw).meta
  assert [a.name for a in meta.authors] == ['A B', 'C D']
  assert meta.date == '2026-10-09'
  assert {
    i.code for i in issues_of({**raw, 'meta': {'title': '', 'language': 'x', 'date': 'soon'}})
  } == {'E205'}


def test_render_block() -> None:
  raw = minimal_manifest()
  raw['render'] = {
    'template': 'generic@1',
    'layout': 'default@1',
    'formats': ['md', 'pdf'],
    'pdf_engine': 'latex',
    'latex_engine': 'lualatex',
    'options': {'paper': 'a4', 'toc': True, 'accent': None},
  }
  assert parse_manifest(raw).render.layout == 'default@1'
  raw['render'] = {'layout': 'bad layout'}
  assert {i.code for i in issues_of(raw)} == {'E205'}
  raw['render'] = {'formats': ['rtf']}
  assert {i.code for i in issues_of(raw)} == {'E205'}


def test_unknown_and_missing_top_level_fields() -> None:
  assert {i.code for i in issues_of({'scireport': '1.0', 'meta': {'title': 'T'}, 'extra': 1})} == {
    'E204'
  }
  assert {i.code for i in issues_of({'scireport': '1.0'})} == {'E203'}


def test_preprocess_and_provenance_blocks() -> None:
  raw = minimal_manifest(a=1)
  raw['preprocess'] = [
    {
      'name': 'core.histogram',
      'version': 1,
      'inputs': {'table': 'a'},
      'params': {'bins': 'auto', 'log': [1, {'x': None}]},
    }
  ]
  raw['provenance'] = {
    'generator': {'name': 'gzms', 'version': '1.1.0'},
    'inputs': [{'name': 'objects.parquet', 'sha256': 'b' * 64, 'uri': 'file:x'}],
  }
  manifest = parse_manifest(raw)
  assert manifest.preprocess[0].params['bins'] == 'auto'
  assert manifest.provenance.generator is not None
  raw['preprocess'] = [{'name': 'bad name!'}]
  assert {i.code for i in issues_of(raw)} == {'E205'}
  raw['preprocess'] = [{'name': 'x', 'inputs': {'p': 'Bad Key'}}]
  assert {i.code for i in issues_of(raw)} == {'E101'}


def test_pointer_skips_union_tags_and_key_markers() -> None:
  raw = minimal_manifest(good=1, bad={'kind': 'number', 'value': 'x'})
  [issue] = issues_of(raw)
  assert issue.pointer == '/values/bad/value'
  assert issue.key == 'bad'


def test_nested_pointer_through_lists() -> None:
  raw = minimal_manifest(
    m={'kind': 'metrics', 'items': [{'label': 'a', 'value': 1}, {'label': '', 'value': 2}]}
  )
  [issue] = issues_of(raw)
  assert issue.pointer == '/values/m/items/1/label'


def test_key_errors_carry_a_suggestion() -> None:
  [issue] = issues_of(minimal_manifest(**{'Cross Match': 1}))
  assert (issue.code, issue.pointer, issue.key) == ('E101', '/values/Cross Match', 'Cross Match')
  assert issue.hint is not None
  assert 'cross-match' in issue.hint


def test_pointer_escapes_slashes_and_tildes() -> None:
  [issue] = issues_of(minimal_manifest(**{'a/b~': 1}))
  assert issue.pointer == '/values/a~1b~0'
  assert issue.key == 'a/b~'


def test_unknown_kind_has_did_you_mean() -> None:
  [issue] = issues_of(minimal_manifest(x={'kind': 'tabel'}))
  assert issue.code == 'E201'
  assert issue.hint == "Did you mean 'table'?"
  assert issue.found == 'tabel'
  assert issue.expected is not None
  assert 'table' in issue.expected


def test_all_structural_problems_are_reported_together() -> None:
  raw = minimal_manifest(
    **{'Bad': 1},
    x={'kind': 'tabel'},
    y={'kind': 'bool', 'value': 'maybe'},
    z={'kind': 'figure', 'renditions': [], 'alt': 'a'},
  )
  raw['bogus'] = 1
  codes = sorted(i.code for i in issues_of(raw))
  assert codes == ['E101', 'E201', 'E204', 'E205', 'E205']


def test_prefix_conflict_is_e102() -> None:
  issues = issues_of(minimal_manifest(**{'a.b': 1, 'a.b.c': 2, 'a': 3}))
  assert [(i.code, i.key) for i in issues] == [('E102', 'a'), ('E102', 'a.b')]
  assert issues[0].pointer == '/values/a'


def test_outline_leaves_must_exist() -> None:
  raw = minimal_manifest(intro='x', **{'stats.n': 1})
  raw['outline'] = ['intro', {'title': 'Stats', 'children': ['stats.m', 'nope']}]
  issues = issues_of(raw)
  assert [(i.code, i.pointer) for i in issues] == [
    ('E103', '/outline/1/children/0/key'),
    ('E103', '/outline/1/children/1/key'),
  ]
  assert issues[0].hint == "Did you mean 'stats.n'?"
  assert issues[1].hint is None


def test_outline_node_rules() -> None:
  raw = minimal_manifest(a=1)
  for node in [
    {'title': 'T', 'key': 'a'},
    {},
    {'key': 'a', 'children': ['a']},
    {'key': 'a', 'md_file': 'a.md'},
    {'title': 'T', 'md_file': 'sub/dir.md'},
  ]:
    raw['outline'] = [node]
    assert issues_of(raw), node


def test_outline_markdown_files_must_be_unique() -> None:
  raw = minimal_manifest(a=1)
  raw['outline'] = [
    {'title': 'One', 'md_file': 'one.md', 'children': ['a']},
    {'title': 'Two', 'md_file': 'one.md'},
  ]
  [issue] = issues_of(raw)
  assert (issue.code, issue.pointer) == ('E205', '/outline/1/md_file')


def test_overflow_attachment_must_be_an_attachment() -> None:
  table = {'kind': 'table', 'columns': [{'name': 'a'}], 'rows': [[1]]}
  attachment = {
    'kind': 'attachment',
    'asset': asset_ref('assets/attachments/a.csv'),
    'filename': 'a.csv',
  }
  good = minimal_manifest(t={**table, 'overflow_attachment': 'all'}, all=attachment)
  parse_manifest(good)
  wrong = minimal_manifest(t={**table, 'overflow_attachment': 'other'}, other='text')
  [issue] = issues_of(wrong)
  assert (issue.code, issue.expected, issue.found) == ('E202', 'attachment', 'text')
  missing = minimal_manifest(t={**table, 'overflow_attachment': 'all'})
  [issue] = issues_of(missing)
  assert issue.code == 'E103'
  assert issue.pointer == '/values/t/overflow_attachment'


def test_one_asset_path_cannot_have_two_hashes() -> None:
  one = {'kind': 'image', 'asset': asset_ref('assets/images/x.png', 'a' * 64, 1)}
  two = {'kind': 'image', 'asset': asset_ref('assets/images/x.png', 'b' * 64, 2)}
  [issue] = issues_of(minimal_manifest(one=one, two=two))
  assert issue.code == 'E411'
  assert issue.pointer == '/values/two/asset'
  same = minimal_manifest(one=one, two=one)
  parse_manifest(same)


def test_version_errors_come_first() -> None:
  with pytest.raises(SpecVersionError) as info:
    parse_manifest({'scireport': '1.1', 'meta': {}})
  assert info.value.code == 'E501'
  assert info.value.exit_code == 2
  assert 'newer' in info.value.message
  assert info.value.hint is not None


def test_canonical_json_is_stable_and_sorted() -> None:
  one = parse_manifest(minimal_manifest(b=2, a='x', c=None))
  two = parse_manifest(minimal_manifest(c=None, a='x', b=2))
  assert manifest_to_json(one) == manifest_to_json(two)
  text = manifest_to_json(one)
  assert text.endswith('}\n')
  data = json.loads(text)
  assert list(data['values']) == ['a', 'b', 'c']
  assert data['render'] == {'formats': [], 'options': {}}
  assert 'subtitle' not in data['meta']


def test_canonical_form_round_trips() -> None:
  raw = minimal_manifest(
    a={'x': [1, 2.5, 'é', None], 'y': True},
    f={'kind': 'figure', 'renditions': [asset_ref('assets/figures/f.png')], 'alt': 'ünïcode'},
  )
  first = parse_manifest(raw)
  again = parse_manifest(manifest_to_dict(first))
  assert again == first
  assert 'ünïcode' in manifest_to_json(first)


def test_check_manifest_on_constructed_models() -> None:
  manifest = Manifest.model_validate(minimal_manifest(a=1))
  assert check_manifest(manifest) == []


def test_issue_formatting() -> None:
  issue = Issue(
    'E103', 'no value', pointer='/outline/0/key', expected='x', found='y', hint='Try z.'
  )
  assert issue.format() == 'E103 /outline/0/key: no value (expected x, found y). Try z.'
  assert issue.describe() == '/outline/0/key: no value (expected x, found y). Try z.'
  assert Issue('E101', 'bad').format() == 'E101 bad'
  assert issue.severity == 'error'
  assert issue.to_dict() == {
    'code': 'E103',
    'severity': 'error',
    'message': 'no value',
    'pointer': '/outline/0/key',
    'expected': 'x',
    'found': 'y',
    'hint': 'Try z.',
  }
  assert Issue('W402', 'stray').severity == 'warning'


def test_error_classes_carry_codes() -> None:
  error = ScireportError('boom', code='E410', hint='retry')
  assert str(error) == 'E410: boom. retry'
  assert [i.code for i in error.issues] == ['E410']
  many = SpecError([Issue('E101', 'a'), Issue('E102', 'b')])
  assert many.code == 'E101'
  assert '2 problems' in many.message
