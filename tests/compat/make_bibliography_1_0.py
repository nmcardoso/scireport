"""Add the ``bibliography`` case to the frozen spec-1.0 compat corpus.

The ``bibliography`` kind arrived in phase S5, before spec 1.0 was released, so ``full-kinds``
(created in S1) does not hold it. This script adds a case of its own: the bundle in two forms,
the expected manifest and summary, and the LaTeX render with ``generic@1`` and ``minimal@1``
(the Markdown and HTML renders need pandoc, whose output is not frozen). It only adds files,
appends their hashes to ``FROZEN.sha256`` and refuses to run twice.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from make_spec_1_0 import ROOT, sha256_of, write_expected
from render_helpers import normalised

from scireport import Report, open_bundle
from scireport.render import render_bundle

CASE = 'bibliography'
BIB = (
  '@article{doe2020,\n  author = {Doe, Jane},\n  title = {A study of things},\n'
  '  journal = {Journal of Things},\n  year = {2020}\n}\n'
  '@book{smith2018,\n  author = {Smith, John},\n  title = {The Book},\n  year = {2018}\n}\n'
)


def build() -> Report:
  """Build the case: two citations in prose, a bibliography and a reference list."""
  report = Report('Bibliography case', date='2026-10-09')
  report.add_text(
    'intro', 'Agreement with [@smith2018, p. 3; @doe2020] and [-@doe2020].', format='markdown'
  )
  report.add_bibliography('refs', BIB.encode(), style='authoryear')
  report.set_outline(
    [{'title': 'Intro', 'children': ['intro']}, {'title': 'Refs', 'children': ['refs']}]
  )
  return report


def main() -> None:
  """Write the case and extend the freeze list."""
  case = ROOT / CASE
  if case.exists():
    raise SystemExit(f'{case} exists: the corpus is frozen and the case is never regenerated.')
  frozen = (ROOT / 'FROZEN.sha256').read_text(encoding='utf-8').splitlines()
  case.mkdir()
  report = build()
  report.write(case / 'bundle.scireport.zip')
  report.write(case / 'bundle.scireport')
  write_expected(case, case / 'bundle.scireport')
  with open_bundle(case / 'bundle.scireport') as bundle:
    result = render_bundle(
      bundle, template='generic@1', layout='minimal@1', formats=['tex'], flat=True
    )
  for name, data in normalised(result.files).items():
    target = case / 'expected' / 'render-generic-1-minimal-1' / 'tex' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
  added = sorted(
    f'{sha256_of(path)}  {path.relative_to(ROOT).as_posix()}'
    for path in case.rglob('*')
    if path.is_file()
  )
  merged = sorted([*frozen, *added])
  assert set(frozen) <= set(merged) and len(merged) == len(frozen) + len(added)
  (ROOT / 'FROZEN.sha256').write_text('\n'.join(merged) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
  main()
