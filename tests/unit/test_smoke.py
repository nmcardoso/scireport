import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

import scireport
from scireport.cli import app

ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = ROOT / 'scireport' / 'agent' / 'skill' / 'scireport'
FRONTMATTER_RE = re.compile(r'\A---\n(.*?)\n---\n', re.S)


def test_version_is_exposed() -> None:
  assert re.fullmatch(r'\d+\.\d+\.\d+(\.dev\d+|rc\d+)?', scireport.__version__)


def test_cli_prints_version() -> None:
  result = CliRunner().invoke(app, ['--version'])
  assert result.exit_code == 0
  assert result.stdout.strip() == scireport.__version__


def test_logging_utils_is_importable() -> None:
  from scireport.logging_utils import get_logger

  assert get_logger('scireport.smoke').name


def test_logging_utils_matches_skill_copy() -> None:
  canonical = ROOT / '.agents' / 'skills' / 'python-logging' / 'logging_utils.py'
  if not canonical.is_file():  # sdist or wheel checkout without the agent files
    return
  assert canonical.read_bytes() == (ROOT / 'scireport' / 'logging_utils.py').read_bytes()


def test_packaged_skill_frontmatter() -> None:
  match = FRONTMATTER_RE.match((SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8'))
  assert match is not None
  meta = yaml.safe_load(match.group(1))
  assert meta['name'] == SKILL_DIR.name == 'scireport'
  assert re.fullmatch(r'[a-z0-9-]{1,64}', meta['name'])
  assert 0 < len(meta['description']) <= 1024
