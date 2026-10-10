"""The ``bibliography`` kind: validation, assets, the one-per-bundle rule and the builder."""

from __future__ import annotations

import pytest
from helpers import asset_ref, minimal_manifest

from scireport import Report, SpecError, parse_manifest
from scireport.spec.kinds import KINDS, BibliographyValue, value_adapter
from scireport.spec.manifest import manifest_to_dict
from scireport.spec.walk import iter_assets

BIB = b'@article{doe2020,\n  author = {Doe, J.},\n  title = {T},\n  year = {2020}\n}\n'


def test_the_kind_is_listed_last() -> None:
  assert KINDS[-1] == 'bibliography'


def test_a_bibliography_needs_a_bib_file() -> None:
  ok = value_adapter.validate_python(
    {'kind': 'bibliography', 'asset': asset_ref('assets/text/refs.bib'), 'style': 'authoryear'}
  )
  assert isinstance(ok, BibliographyValue) and ok.csl is None
  with pytest.raises(ValueError, match=r'a \.bib file'):
    value_adapter.validate_python({'kind': 'bibliography', 'asset': asset_ref('assets/text/r.txt')})


def test_a_citation_style_needs_a_csl_file() -> None:
  with pytest.raises(ValueError, match=r'\.csl file'):
    value_adapter.validate_python(
      {
        'kind': 'bibliography',
        'asset': asset_ref('assets/text/r.bib'),
        'csl': asset_ref('assets/text/s.xml'),
      }
    )


def test_the_biblatex_style_is_a_plain_word() -> None:
  with pytest.raises(ValueError, match='pattern'):
    value_adapter.validate_python(
      {'kind': 'bibliography', 'asset': asset_ref('assets/text/r.bib'), 'style': 'a b'}
    )


def test_both_assets_are_walked() -> None:
  manifest = parse_manifest(
    minimal_manifest(
      refs={
        'kind': 'bibliography',
        'asset': asset_ref('assets/text/refs.bib'),
        'csl': asset_ref('assets/text/refs.csl', 'b' * 64),
      }
    )
  )
  assert [pointer for pointer, _ in iter_assets(manifest)] == [
    '/values/refs/asset',
    '/values/refs/csl',
  ]


def test_a_second_bibliography_is_e211() -> None:
  one = {'kind': 'bibliography', 'asset': asset_ref('assets/text/a.bib')}
  two = {'kind': 'bibliography', 'asset': asset_ref('assets/text/b.bib', 'b' * 64)}
  with pytest.raises(SpecError) as caught:
    parse_manifest(minimal_manifest(a=one, b=two))
  assert [i.code for i in caught.value.issues] == ['E211']
  assert caught.value.issues[0].key == 'b'


def test_the_builder_stores_the_files_and_round_trips() -> None:
  report = Report('T').add_bibliography('refs', BIB, csl=b'<style/>', style='numeric')
  bundle = report.build()
  value = bundle.manifest.values['refs']
  assert isinstance(value, BibliographyValue)
  assert value.asset.path == 'assets/text/refs.bib' and value.csl is not None
  assert bundle.read_asset(value.asset) == BIB
  assert manifest_to_dict(bundle.manifest)['values']['refs']['style'] == 'numeric'


def test_the_builder_refuses_two_bibliographies_at_build_time() -> None:
  report = Report('T').add_bibliography('a', BIB).add_bibliography('b', BIB + b'\n')
  with pytest.raises(SpecError, match='E211'):
    report.build()


def test_the_pandoc_version_is_a_dotted_number() -> None:
  assert (
    parse_manifest(
      {**minimal_manifest(), 'render': {'pandoc_version': '3.9'}}
    ).render.pandoc_version
    == '3.9'
  )
  with pytest.raises(SpecError):
    parse_manifest({**minimal_manifest(), 'render': {'pandoc_version': 'latest'}})
