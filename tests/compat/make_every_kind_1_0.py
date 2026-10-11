"""Add the ``every-kind`` case to the frozen spec-1.0 compat corpus.

``full-kinds`` holds a value of 16 kinds, but its outline lists four values, and ``generic@1``
renders only what the outline lists, so the other kinds never reach a frozen render. This case has
the same values, a ``bibliography`` value, and an outline that lists all of them, so that the frozen
Markdown, HTML, LaTeX and PDF renders show every one of the 17 v1.0 kinds. It has no citation in
the prose, because a citation needs pandoc in Markdown and HTML (the ``bibliography`` case has
them).

The script only adds files, writes the case's ``expected/manifest.json`` and
``expected/summary.json`` and appends the hashes to ``FROZEN.sha256``. It refuses to run twice. Run
``make_render_complete_1_0.py`` afterwards for the renders.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from make_bibliography_1_0 import BIB
from make_spec_1_0 import ROOT, full_kinds, sha256_of, write_expected

from scireport import Report

CASE = 'every-kind'
OUTLINE = [
  {'title': 'Text', 'children': ['kinds.text', 'kinds.text-long', 'kinds.latex']},
  {
    'title': 'Scalars',
    'children': [
      'kinds.number',
      'kinds.number-interval',
      'kinds.number-missing',
      'kinds.bool',
      'kinds.date',
    ],
  },
  {'title': 'Collections', 'children': ['kinds.list', 'kinds.mapping']},
  {
    'title': 'Tables',
    'children': [
      'kinds.table-parquet',
      'kinds.table-csv',
      'kinds.table-inline',
      'kinds.table-cut',
      'kinds.attachment',
    ],
  },
  {'title': 'Figures', 'children': ['kinds.figure', 'kinds.image']},
  {'title': 'Code and math', 'children': ['kinds.math', 'kinds.code']},
  {
    'title': 'Status',
    'children': ['kinds.metrics', 'kinds.status', 'kinds.alert', 'kinds.flow'],
  },
  {'title': 'References', 'children': ['kinds.bibliography']},
]


def build() -> Report:
  """Return the ``full-kinds`` report with a bibliography and an outline of every value."""
  report = full_kinds()
  report.add_bibliography('kinds.bibliography', BIB.encode(), style='authoryear')
  report.set_outline(OUTLINE)
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
  added = [
    f'{sha256_of(path)}  {path.relative_to(ROOT).as_posix()}'
    for path in sorted(case.rglob('*'))
    if path.is_file()
  ]
  merged = sorted([*frozen, *added])
  assert set(frozen) <= set(merged) and len(merged) == len(frozen) + len(added)
  (ROOT / 'FROZEN.sha256').write_text('\n'.join(merged) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
  main()
