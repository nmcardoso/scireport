"""The built-in layouts, templates, fonts, styles and schemas are frozen per version (ADR-0008).

A change to a file of ``layouts/<name>/<n>/`` or ``templates/<name>/<n>/`` is a visual or structural
change, so it must be a new version directory, never an edit. CI also checks that the freeze list
only grows (``frozen.py``).
"""

from __future__ import annotations

import pytest
from frozen import BUILTINS_LIST, REPO, builtin_files, growth_problems, hash_line, parse_list


def test_every_builtin_file_is_listed_and_unchanged() -> None:
  listed = parse_list(BUILTINS_LIST.read_text(encoding='utf-8'))
  files = builtin_files()
  assert sorted(listed) == files, 'a built-in file was added or removed (new files: a new version)'
  changed = [name for name in files if hash_line(name) != f'{listed[name]}  {name}']
  assert changed == [], f'frozen built-ins changed: {changed}'


def test_the_frozen_set_covers_the_designed_layouts_and_templates() -> None:
  names = set(builtin_files())
  for expected in (
    'scireport/layouts/default/1/layout.yaml',
    'scireport/layouts/modern/1/layout.yaml',
    'scireport/layouts/minimal/1/layout.yaml',
    'scireport/templates/generic/1/template.yaml',
    'scireport/templates/kitchen-sink/1/template.yaml',
    'scireport/spec/schemas/data-1.0.schema.json',
  ):
    assert expected in names
  assert all((REPO / name).is_file() for name in names)


@pytest.mark.parametrize(
  ('base', 'current', 'problems'),
  [
    ('a  x\nb  y\n', 'a  x\nb  y\nc  z\n', []),
    ('a  x\nb  y\n', 'a  x\n', ['removed: y']),
    ('a  x\nb  y\n', 'a  x\nB  y\n', ['changed: y']),
    ('a  x\n', 'A  x\nc  z\n', ['changed: x']),
    ('', 'a  x\n', []),
  ],
)
def test_a_freeze_list_may_only_grow(base: str, current: str, problems: list[str]) -> None:
  assert growth_problems(base, current) == problems
