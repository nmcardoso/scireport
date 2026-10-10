"""The packaged skill follows the monorepo rules and its generated tables match the code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scireport.agent import skillgen
from scireport.agent.skill import (
  SKILL_DIR,
  SKILL_NAME,
  check_skill,
  install_skill,
  read_page,
  skill_files,
)

EXPECTED_REFERENCES = {
  'data-file.md',
  'python-api.md',
  'cli.md',
  'templates-and-layouts.md',
  'preprocessors.md',
  'mplstyle.md',
  'errors.md',
  'recipes.md',
}


def frontmatter() -> dict[str, str]:
  text = (SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8')
  match = re.match(r'^---\n(.*?)\n---\n', text, re.DOTALL)
  assert match, 'SKILL.md has no frontmatter'
  fields: dict[str, str] = {}
  for line in match.group(1).splitlines():
    key, _, value = line.partition(':')
    fields[key.strip()] = value.strip()
  return fields


def test_the_folder_and_the_name_agree() -> None:
  assert SKILL_DIR.name == SKILL_NAME == frontmatter()['name']
  assert re.fullmatch(r'[a-z0-9-]+', SKILL_NAME)


def test_the_description_fits_the_monorepo_limit() -> None:
  description = frontmatter()['description']
  assert description and len(description) <= 1024


def test_every_reference_page_exists_and_is_linked_from_the_skill() -> None:
  names = {
    name.removeprefix('references/') for name in skill_files() if name.startswith('references/')
  }
  assert names == EXPECTED_REFERENCES
  skill = read_page('SKILL.md')
  for name in EXPECTED_REFERENCES:
    assert f'references/{name}' in skill


def test_the_skill_never_tells_an_agent_to_install_from_a_local_path() -> None:
  for name in skill_files():
    text = read_page(name)
    assert 'file:///' not in text and '/home/' not in text, name


def test_the_generated_tables_match_the_code() -> None:
  """``make skill`` regenerates them; a stale page means the code changed without it."""
  import difflib

  stale = [
    ''.join(
      list(
        difflib.unified_diff(
          p.read_text().splitlines(keepends=True),
          skillgen.render_page(p.read_text()).splitlines(keepends=True),
        )
      )[:12]
    )
    for p in skillgen.stale_pages()
  ]
  assert stale == [], f'run "make skill": {stale}'


def test_every_marker_names_a_generator_and_every_generator_is_used() -> None:
  used: set[str] = set()
  for page in skillgen.pages():
    used.update(skillgen.generated_blocks(page.read_text(encoding='utf-8')))
  assert used <= set(skillgen.GENERATORS)
  assert set(skillgen.GENERATORS) <= used, f'unused generators: {set(skillgen.GENERATORS) - used}'


def test_render_page_replaces_only_marked_blocks() -> None:
  text = 'before\n<!-- generated:exit-codes -->\nold\n<!-- /generated -->\nafter\n'
  out = skillgen.render_page(text)
  assert out.startswith('before\n<!-- generated:exit-codes -->\n| Code | Meaning |')
  assert out.endswith('<!-- /generated -->\nafter\n')
  with pytest.raises(KeyError):
    skillgen.render_page('<!-- generated:nope -->\n<!-- /generated -->')


def test_numpy_params_and_summary() -> None:
  doc = """Do a thing.

  More text.

  Parameters
  ----------
  a : int
      First value.
      Continued.
  b : str or None
      Second value.

  Returns
  -------
  int
      Result.
  """
  assert skillgen.numpy_params(doc) == {
    'a': ('int', 'First value. Continued.'),
    'b': ('str or None', 'Second value.'),
  }
  assert skillgen.summary(doc) == 'Do a thing.'
  assert skillgen.numpy_params(None) == {} and skillgen.numpy_params('no sections') == {}


def test_the_tables_escape_pipes() -> None:
  assert skillgen.table(['A'], [['x|y\nz']]) == '| A |\n|---|\n| x\\|y z |'


def test_main_check_and_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
  folder = tmp_path / 'scireport'
  folder.mkdir()
  page = folder / 'x.md'
  page.write_text('<!-- generated:exit-codes -->\nold\n<!-- /generated -->\n', encoding='utf-8')
  monkeypatch.setattr(skillgen, 'SKILL_DIR', folder)
  assert skillgen.main(['--check']) == 1
  assert skillgen.main([]) == 0
  assert skillgen.main(['--check']) == 0 and 'Success' in page.read_text(encoding='utf-8')


def test_install_and_check_round_trip(tmp_path: Path) -> None:
  assert not check_skill(tmp_path).current
  target = install_skill(tmp_path)
  assert target == tmp_path / SKILL_NAME and check_skill(tmp_path).current
  assert install_skill(tmp_path) == target
