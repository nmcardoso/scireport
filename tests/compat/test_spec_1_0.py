"""The frozen spec-1.0 corpus: fixtures never change and every form still loads the same way."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scireport import open_bundle
from scireport.bundle.summary import inspect_bundle
from scireport.spec.manifest import manifest_to_json

CORPUS = Path(__file__).resolve().parent / 'spec-1.0'
CASES = {
  'minimal': ['bundle.scireport', 'bundle.scireport.zip'],
  'text-only': ['source', 'single.json', 'bundle.scireport.zip'],
  'full-kinds': ['bundle.scireport', 'bundle.scireport.zip'],
  'bibliography': ['bundle.scireport', 'bundle.scireport.zip'],
}
UNFROZEN = {'FROZEN.sha256', 'README.md'}


def corpus_files() -> list[str]:
  return sorted(
    path.relative_to(CORPUS).as_posix()
    for path in CORPUS.rglob('*')
    if path.is_file() and path.name not in UNFROZEN
  )


def test_fixtures_are_frozen() -> None:
  """CI fails if a fixture is added, removed or changed (ADR-0008)."""
  listed: dict[str, str] = {}
  for line in (CORPUS / 'FROZEN.sha256').read_text(encoding='utf-8').splitlines():
    digest, _, name = line.partition('  ')
    listed[name] = digest
  assert sorted(listed) == corpus_files()
  changed = [
    name
    for name, digest in listed.items()
    if hashlib.sha256((CORPUS / name).read_bytes()).hexdigest() != digest
  ]
  assert changed == [], f'frozen fixtures changed: {changed}'


def test_corpus_covers_the_minimum_cases() -> None:
  assert {'minimal', 'text-only', 'full-kinds'} <= set(CASES)
  for case, forms in CASES.items():
    for form in forms:
      assert (CORPUS / case / form).exists(), f'{case}/{form}'


@pytest.mark.parametrize(('case', 'form'), [(c, f) for c, forms in CASES.items() for f in forms])
def test_every_form_loads_to_the_expected_manifest(case: str, form: str) -> None:
  expected = (CORPUS / case / 'expected' / 'manifest.json').read_bytes().decode('utf-8')
  with open_bundle(CORPUS / case / form) as bundle:
    assert manifest_to_json(bundle.manifest) == expected
    assert bundle.verify() == []


@pytest.mark.parametrize(('case', 'form'), [(c, f) for c, forms in CASES.items() for f in forms])
def test_every_form_inspects_to_the_expected_summary(case: str, form: str) -> None:
  expected = json.loads((CORPUS / case / 'expected' / 'summary.json').read_text(encoding='utf-8'))
  with open_bundle(CORPUS / case / form) as bundle:
    summary = inspect_bundle(bundle)
  summary.pop('source')
  summary.pop('form')
  assert summary == expected


def test_the_corpus_uses_every_kind() -> None:
  """``full-kinds`` holds the kinds of the first draft; ``bibliography`` (S5) has its own case."""
  from scireport.spec.kinds import KINDS

  used: set[str] = set()
  for case in ('full-kinds', 'bibliography'):
    with open_bundle(CORPUS / case / 'bundle.scireport.zip') as bundle:
      used |= {value.kind for value in bundle.manifest.values.values()}
  assert used == set(KINDS)


def test_directory_and_zip_forms_hold_the_same_assets() -> None:
  with (
    open_bundle(CORPUS / 'full-kinds' / 'bundle.scireport') as directory,
    open_bundle(CORPUS / 'full-kinds' / 'bundle.scireport.zip') as archive,
  ):
    assert directory.asset_paths == archive.asset_paths
    assert len(directory.asset_paths) == 10
    for path in directory.asset_paths:
      assert directory.read_asset(path) == archive.read_asset(path)


def test_text_only_forms_agree_with_the_hand_authored_source() -> None:
  with open_bundle(CORPUS / 'text-only' / 'source') as source:
    assert source.asset_paths == []
    canonical = manifest_to_json(source.manifest)
  assert (CORPUS / 'text-only' / 'single.json').read_bytes().decode('utf-8') == canonical
