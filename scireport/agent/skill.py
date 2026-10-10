"""The packaged skill: where it is, its pages, and installing it into a project.

The skill is a folder, ``scireport/agent/skill/scireport/``, with a ``SKILL.md`` and a
``references/`` folder. It ships inside the wheel and the sdist, so an agent in a project that
only has the package installed can read it (``scireport agent install-skill``) and the MCP server
serves its pages as resources. The reference pages are partly generated from the code
(:mod:`scireport.agent.skillgen`); a test fails when they drift.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from scireport.errors import BundleError
from scireport.logging_utils import get_logger

log = get_logger(__name__)

SKILL_NAME = 'scireport'
"""Name of the skill, and of its folder."""
SKILL_DIR = Path(__file__).resolve().parent / 'skill' / SKILL_NAME
"""The packaged skill folder."""

_NAME_RE = re.compile(r'^name:\s*(\S+)\s*$', re.MULTILINE)


@dataclass(frozen=True)
class SkillCheck:
  """How an installed copy of the skill compares with the packaged one.

  Parameters
  ----------
  path : pathlib.Path
      The installed folder (``<dest>/scireport``).
  missing : tuple of str
      Files of the packaged skill that the installed folder lacks (all of them when it does
      not exist).
  changed : tuple of str
      Files whose content differs.
  extra : tuple of str
      Files in the installed folder that the packaged skill does not have.
  """

  path: Path
  missing: tuple[str, ...] = ()
  changed: tuple[str, ...] = ()
  extra: tuple[str, ...] = ()

  @property
  def current(self) -> bool:
    """Whether the installed copy is identical to the packaged skill."""
    return not (self.missing or self.changed or self.extra)


def skill_files() -> list[str]:
  """List the files of the packaged skill as POSIX paths relative to its folder, sorted."""
  return sorted(
    path.relative_to(SKILL_DIR).as_posix()
    for path in SKILL_DIR.rglob('*')
    if path.is_file() and '__pycache__' not in path.parts
  )


def read_page(name: str) -> str:
  """Read one page of the skill.

  Parameters
  ----------
  name : str
      ``SKILL.md`` or ``references/<page>.md``.

  Returns
  -------
  str
      The page.

  Raises
  ------
  FileNotFoundError
      When the skill has no such page.
  """
  if name not in skill_files():
    raise FileNotFoundError(name)
  return (SKILL_DIR / name).read_text(encoding='utf-8')


def check_skill(dest: Path) -> SkillCheck:
  """Compare ``<dest>/scireport`` with the packaged skill.

  Parameters
  ----------
  dest : pathlib.Path
      The skills directory of a project (``.claude/skills``, ``.agents/skills``).

  Returns
  -------
  SkillCheck
      What is missing, changed or extra.
  """
  target = dest / SKILL_NAME
  packaged = skill_files()
  present = (
    sorted(p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file())
    if target.is_dir()
    else []
  )
  changed = tuple(
    name
    for name in packaged
    if name in present and (target / name).read_bytes() != (SKILL_DIR / name).read_bytes()
  )
  return SkillCheck(
    target,
    missing=tuple(name for name in packaged if name not in present),
    changed=changed,
    extra=tuple(name for name in present if name not in packaged),
  )


def install_skill(dest: Path) -> Path:
  """Copy the packaged skill to ``<dest>/scireport``, replacing an earlier copy.

  Files are written byte for byte with no timestamps kept, so installing twice gives the same
  tree. Nothing outside ``<dest>/scireport`` is touched.

  Parameters
  ----------
  dest : pathlib.Path
      The skills directory of a project; created when missing.

  Returns
  -------
  pathlib.Path
      The installed folder.

  Raises
  ------
  BundleError
      With ``E410`` when ``<dest>/scireport`` exists and is not a copy of this skill (its
      ``SKILL.md`` names another skill, or it is a non-empty folder without one), so that
      something else is never overwritten. A copy whose ``SKILL.md`` was edited is replaced.
  """
  target = dest / SKILL_NAME
  if target.exists():
    marker = target / 'SKILL.md'
    found = _NAME_RE.search(marker.read_text(encoding='utf-8')) if marker.is_file() else None
    foreign = (found is not None and found.group(1) != SKILL_NAME) or (
      not marker.is_file() and any(target.iterdir())
    )
    if foreign:
      raise BundleError(
        f'{target} exists and is not the scireport skill',
        code='E410',
        hint='Choose another --dest, or remove that folder.',
      )
    shutil.rmtree(target)
  for name in skill_files():
    out = target / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((SKILL_DIR / name).read_bytes())
  log.info('installed the skill to %s', target)
  return target
